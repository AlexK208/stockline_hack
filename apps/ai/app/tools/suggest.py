"""
suggest_items: at most 2 extra products worth offering at the end of an order call, each with a reason the client can
check. Plain code over ERP data, no model: the model only phrases what comes back. [] is a valid answer.

    gather()  reads the facts from the ERP (one round of parallel reads)
    rank()    pure: the five sources, the hard filters that need no ERP, the ranking (tested on crafted facts)
    then check_items (desk.py) = the same stock / lead time / delivery-day checks as the order tools

Sources (reasonKind), in this order of priority:
    l'an dernier  seasonal for THIS client: in those weeks of the last two years (±10 days) it was in a clearly larger
                  share of his deliveries than over the last 12 months (a staple bought all year is "habitude")
    réservation   veal, lamb and matured ribs ordered for Christmas before: booked a week ahead
    habitude      in the usual basket (60 days, one delivery out of two or more) but not in this order
    promo         a temporary price rule (with an end date) valid ON the delivery date, for a product the client buys
    lot à écouler a lot expiring 1 to 3 days after the delivery (the client still has a day to sell it), in a
                  category the client buys
Hard filters: blocked client → []; never a product already in the order; inactive products out; a client who
refuses substitutions only gets products he has bought himself; then check_items: stock at the date, lead time,
delivery day (a reservation skips the stock check: it is booked precisely because the stock is not there yet).
"""

from __future__ import annotations

import asyncio
import re
from datetime import date, timedelta

from pydantic import Field

from .desk import Item, check_items, fmt, jour, piece_kg, problems_of
from .erp import ErpClient, enc
from .registry import ToolContext, tool

MAX_SUGGESTIONS = 2  # "at most 2 suggestions per call": enforced here, the prompt alone let a third one through
SEASON_HALF_WINDOW = 10  # days around the same date in past years
YEARS_BACK = 2
HABIT_MIN_FREQUENCY = 0.5  # in at least one delivery out of two in the last 60 days
LOT_EXPIRY_DAYS = 3  # a lot expiring within this many days after the delivery is "à écouler"
CATEGORY_MIN_ORDERS = 2
SEASON_LIFT = 1.5  # share of deliveries in those weeks ≥ 1.5 × the share over the last 12 months
SEASON_MIN_ORDERS = 2  # and in at least two deliveries of those weeks (one is chance)  # "buys this category" = at least two orders with it in the last 12 months
# Booked a week ahead (data/context/02-journee-type.md): whole and half veal, lamb carcass, 21-day matured ribs.
RESERVE_DAYS = {"prd_0004": 7, "prd_0005": 7, "prd_0006": 7, "prd_0011": 7}
CHRISTMAS = ("12-15", "12-24")  # deliveries for the holidays
REFUSES_SUBSTITUTES = re.compile(r"(refuse|aucune|jamais|sans l['’]appeler|appeler avant)", re.I)
KIND_RANK = {"l'an dernier": 0, "réservation": 1, "habitude": 2, "promo": 3, "lot à écouler": 4}


def refuses_substitutes(preferences: str | None) -> bool:
    """Same reading as the Voix page's client card: the sentence about substitutions says no."""
    return any("substitu" in s.lower() and REFUSES_SUBSTITUTES.search(s) for s in re.split(r"(?<=\.)\s+", preferences or ""))


def dd_mm(iso: str) -> str:
    return f"{iso[8:10]}/{iso[5:7]}"


def shift_year(iso: str, years: int) -> date:
    d = date.fromisoformat(iso)
    try:
        return d.replace(year=d.year - years)
    except ValueError:  # 29 February
        return d.replace(year=d.year - years, day=28)


def round_qty(qty: float, product: dict) -> tuple[float, float | None]:
    """A sensible quantity to offer: whole pieces when the product has a piece weight, else a clean number."""
    rng = piece_kg(product.get("caliber")) if product.get("unit") == "kg" else None
    if rng and rng[0] >= 10:  # carcasses and quarters: count pieces
        mid = (rng[0] + rng[1]) / 2
        pieces = max(1, round(qty / mid))
        return round(pieces * mid, 1), pieces
    if product.get("unit") == "kg":
        return max(0.5, round(qty * 2) / 2), None
    return max(1, round(qty)), None


async def gather(erp: ErpClient, client_id: str, delivery_date: str) -> dict:
    """Every ERP fact the ranking needs, read in parallel."""
    day = date.fromisoformat(delivery_date)
    seasons = [(shift_year(delivery_date, y) - timedelta(days=SEASON_HALF_WINDOW), shift_year(delivery_date, y) + timedelta(days=SEASON_HALF_WINDOW)) for y in range(1, YEARS_BACK + 1)]
    xmas = [(f"{day.year - y}-{CHRISTMAS[0]}", f"{day.year - y}-{CHRISTMAS[1]}") for y in range(1, YEARS_BACK + 1)]
    meta, client = await asyncio.gather(erp.get("/api/meta"), erp.get(f"/api/clients/{enc(client_id)}"))
    year_ago = (date.fromisoformat(meta["today"]) - timedelta(days=365)).isoformat()
    buy = lambda a, b: erp.get(f"/api/clients/{enc(client_id)}/purchases", {"from": str(a), "to": str(b)})  # noqa: E731
    usual, products, stock, rules, last_year, *rest = await asyncio.gather(
        erp.get(f"/api/clients/{enc(client_id)}/usual"),
        erp.get("/api/products"),
        erp.get("/api/stock"),
        erp.get("/api/price-rules", {"active": "true", "clientId": client_id}),
        buy(year_ago, meta["today"]),
        *(buy(a, b) for a, b in seasons),
        *(buy(a, b) for a, b in xmas),
    )
    open_ids = [o["id"] for o in client.get("recentOrders") or [] if o["deliveryDate"] == delivery_date and o["status"] in ("draft", "confirmed")]
    orders = await asyncio.gather(*(erp.get(f"/api/orders/{enc(i)}") for i in open_ids))
    return {
        "today": meta["today"],
        "deliveryDate": delivery_date,
        "client": {k: client.get(k) for k in ("id", "status", "preferences", "deliveryDays", "type")},
        "inOrder": sorted({l["productId"] for o in orders for l in o.get("lines") or []}),
        "usual": usual,
        "products": products if isinstance(products, list) else products.get("items", []),
        "stock": stock if isinstance(stock, list) else stock.get("items", []),
        "rules": rules if isinstance(rules, list) else rules.get("items", []),
        "lastYear": last_year,  # {orders, products}: last 12 months
        "seasons": [{"from": str(a), "to": str(b), **got} for (a, b), got in zip(seasons, rest[:YEARS_BACK])],
        "christmas": [{"from": a, "to": b, **got} for (a, b), got in zip(xmas, rest[YEARS_BACK:])],
    }


def rank(f: dict) -> list[dict]:
    """The candidates, best first, one per product, before the stock / lead-time checks. Pure: facts in, list out."""
    if f["client"].get("status") == "blocked":
        return []
    day, today = f["deliveryDate"], f["today"]
    product = {p["id"]: p for p in f["products"]}
    bought = {r["productId"]: r for r in f["lastYear"]["products"]}  # last 12 months
    cat_orders: dict[str, int] = {}
    for r in f["lastYear"]["products"]:
        cat_orders[r["category"]] = cat_orders.get(r["category"], 0) + r["orders"]
    own_only = refuses_substitutes(f["client"].get("preferences"))
    skip = set(f["inOrder"])

    def allowed(pid: str) -> bool:
        p = product.get(pid)
        if not p or not p.get("active", True) or pid in skip:
            return False
        if pid in bought:
            return True
        return not own_only and cat_orders.get(p.get("category", ""), 0) >= CATEGORY_MIN_ORDERS

    def per_order(pid: str) -> float | None:
        r = bought.get(pid)
        return r["qty"] / r["orders"] if r and r["orders"] else None

    out: list[dict] = []

    def add(pid: str, qty: float, kind: str, reason: str, evidence: str, **extra) -> None:
        if not allowed(pid) or qty <= 0 or any(c["productId"] == pid for c in out):
            return
        p = product[pid]
        q, pieces = round_qty(qty, p)
        evidence = re.sub(r"(\d)\.(\d)", r"\1,\2", evidence)  # shown on the Voix page: French decimals
        out.append({"productId": pid, "name": p["name"], "qty": q, "unit": p["unit"], **({"pieces": pieces} if pieces else {}),
                    "reasonKind": kind, "reasonText": reason, "evidence": evidence, **extra})

    # l'an dernier: in a clearly larger share of his deliveries in those weeks than over the year
    season_orders = sum(x["orders"] for x in f["seasons"])
    year_orders = f["lastYear"]["orders"] or 1
    seen: dict[str, dict] = {}
    for x in f["seasons"]:
        for r in x["products"]:
            e = seen.setdefault(r["productId"], {"qty": 0.0, "orders": 0, "years": []})
            e["qty"] += r["qty"]
            e["orders"] += r["orders"]
            e["years"].append(f"{x['from'][:4]} : {r['orders']}/{x['orders']} livraisons, {fmt(round(r['qty'], 1))} {r['unit']}")
    lifted = []
    for pid, e in seen.items():
        share = e["orders"] / max(1, season_orders)
        usual_share = (bought[pid]["orders"] if pid in bought else 0) / year_orders
        if e["orders"] >= SEASON_MIN_ORDERS and share >= SEASON_LIFT * usual_share:
            lifted.append((share / usual_share if usual_share else 99, pid, e, share, usual_share))
    for _, pid, e, share, usual_share in sorted(lifted, key=lambda t: -t[0]):
        add(pid, e["qty"] / e["orders"], "l'an dernier",
            f"à cette période les années d'avant : {round(share * 100)} % de ses livraisons, contre {round(usual_share * 100)} % sur l'année",
            " · ".join(e["years"]))

    # réservation: booked a week ahead, ordered for Christmas before, delivery in the Christmas weeks, still in time
    if CHRISTMAS[0] <= day[5:] <= CHRISTMAS[1]:
        deadline = (date.fromisoformat(day) - timedelta(days=7)).isoformat()
        for pid, days in RESERVE_DAYS.items():
            years = [(x["from"][:4], r) for x in f["christmas"] for r in x["products"] if r["productId"] == pid]
            if years and today <= deadline:
                y, r = years[0]
                add(pid, r["qty"] / r["orders"], "réservation",
                    f"se réserve une semaine avant pour Noël : avant le {dd_mm(deadline)}",
                    f"Noël {y} : {fmt(round(r['qty'], 1))} {r['unit']} · réserver avant le {dd_mm(deadline)}",
                    booking=True)

    # habitude: in the usual basket, missing from this order
    for u in sorted(f["usual"], key=lambda u: -u["frequency"]):
        if u["frequency"] >= HABIT_MIN_FREQUENCY:
            add(u["productId"], u["avgQty"], "habitude", "pris d'habitude, pas dans cette commande",
                f"{round(u['frequency'] * 100)} % de ses livraisons sur 60 jours, {fmt(round(u['avgQty'], 1))} {u['unit']} en moyenne")

    # promo: temporary rule (it has an end date) whose validity covers the delivery date
    for r in f["rules"]:
        scope = r.get("productScope") or {}
        if scope.get("kind") != "product" or not r.get("validTo"):
            continue
        if not (r.get("validFrom", "") <= day <= r["validTo"]):
            continue
        pid = scope["productId"]
        qty = max(r.get("minQty") or 0, per_order(pid) or 0)
        add(pid, qty, "promo", f"{r['name']}, jusqu'au {dd_mm(r['validTo'])}", f"{r['id']} · du {dd_mm(r['validFrom'])} au {dd_mm(r['validTo'])}")

    # lot à écouler: a lot that must go within LOT_EXPIRY_DAYS of the delivery, in a category the client buys
    limit = (date.fromisoformat(day) + timedelta(days=LOT_EXPIRY_DAYS)).isoformat()
    lots = sorted(
        ((s["productId"], lot) for s in f["stock"] for lot in s.get("lots") or [] if lot.get("qtyRemaining", 0) > 0 and day < lot["expiresAt"] <= limit),
        key=lambda x: x[1]["expiresAt"],
    )
    for pid, lot in lots:
        p = product.get(pid) or {}
        typical = per_order(pid)
        if typical is None:
            same = [r for r in f["lastYear"]["products"] if r["category"] == p.get("category")]
            typical = sum(r["qty"] for r in same) / max(1, sum(r["orders"] for r in same)) if same else 0
        add(pid, min(typical, lot["qtyRemaining"]), "lot à écouler", f"lot frais à écouler avant le {dd_mm(lot['expiresAt'])}",
            f"{fmt(round(lot['qtyRemaining'], 1))} {p.get('unit', 'kg')} à vendre avant le {dd_mm(lot['expiresAt'])}")

    return sorted(out, key=lambda c: KIND_RANK[c["reasonKind"]])


async def suggest(erp: ErpClient, client_id: str, delivery_date: str) -> list[dict]:
    facts = await gather(erp, client_id, delivery_date)
    candidates = rank(facts)
    if not candidates:
        return []
    checked = await check_items(erp, client_id, delivery_date, [Item(product_id=c["productId"], qty=c["qty"]) for c in candidates])
    if checked.get("deliveryDay"):  # not a delivery day for this client: nothing to add to
        return []
    ok: list[dict] = []
    for c, row in zip(candidates, checked["items"]):
        problems = problems_of({"items": [row]})
        if c.get("booking"):  # booked ahead: the stock is not there yet, only the lead time counts
            problems = [p for p in problems if "Trop tard" in p]
        if not problems:
            ok.append({k: v for k, v in c.items() if k != "booking"})
        if len(ok) == MAX_SUGGESTIONS:
            break
    return ok


@tool
async def suggest_items(
    ctx: ToolContext,
    client_id: str,
    delivery_date: str = Field(description="Date de livraison de la commande, YYYY-MM-DD"),
) -> dict:
    """
    À appeler UNE fois, quand le client dit que sa commande est finie (« c'est tout »), avant la relecture. Rend au plus deux
    produits à proposer, déjà vérifiés (stock à la date, délai, jour de livraison, pas déjà dans la commande), chacun avec sa
    raison (reasonText) et la quantité. Liste vide = ne propose rien.
    """
    found = await suggest(ctx.erp, client_id, delivery_date)
    return {"deliveryDate": delivery_date, "jour": jour(delivery_date), "suggestions": found}
