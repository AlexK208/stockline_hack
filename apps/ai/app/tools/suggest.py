"""
suggest_items: the products a client FORGOT from an order he places again and again. Plain code over ERP data, no
model: the model only phrases what comes back. [] is a valid answer, and the usual one.

The rule (Pablo, 24/11 ~04:00). Asking « vous n'oubliez rien ? » is a service when the order is clearly his usual
one with a gap, and nagging when he is simply ordering something else. So we suggest only when:
    - he has placed the SAME order (the same set of products) at least 3 times in the last 6 months;
    - and the current order is clearly that order: at most 2 products missing, at most 2 extra, at most 3
      differences in all, and no more than 35 % of that order missing.
Then ALL the missing products are offered at once, in one sentence, with the quantity he usually takes.

    gather()     reads his recent orders (with their lines) and the products, in parallel
    forgotten()  pure: the rule above, on product sets (tested on crafted orders)
    then check_items (desk.py): the same stock / lead time / delivery-day checks as the order tools; a product that
    cannot be delivered is dropped (never suggest what we cannot deliver)
Hard filters: blocked client → []; deliveries 19–31 December → [] (the carnet des fêtes, tools/festive.py, proposes
last year's holiday basket itself).
"""

from __future__ import annotations

import asyncio
from collections import Counter
from datetime import date, timedelta
from statistics import median

from pydantic import Field

from .desk import Item, check_items, fmt, jour, piece_kg, problems_of
from .erp import ErpClient, enc
from .registry import ToolContext, tool

WINDOW_DAYS = 180  # his habits: the last 6 months of deliveries
MIN_REPEATS = 3  # « the same order more than two times »
MAX_MISSING = 2  # forgotten products, at most
MAX_EXTRA = 2  # products added that are not in the repeated order, at most
MAX_DIFFERENCES = 3  # missing + extra: beyond that it is clearly another order
MAX_MISSING_SHARE = 0.35  # of the repeated order
FESTIVE = ("12-19", "12-31")  # the carnet des fêtes' dates: no order, no suggestion
PLACED = {"confirmed", "prepared", "delivered", "invoiced"}  # what counts as an order he placed (no draft, no cancelled)


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


def forgotten(history: list[dict], current: set[str]) -> dict | None:
    """The rule, pure. `history`: his placed orders, each {"date": "YYYY-MM-DD", "lines": {productId: qty}};
    `current`: the product ids of the order being taken.
    → {"missing": [pid…], "times": n, "last": date, "qty": {pid: usual qty}} or None (nothing worth asking)."""
    if not current:
        return None
    sets = Counter(frozenset(o["lines"]) for o in history if o["lines"])
    best = None
    for basket, times in sets.items():
        if times < MIN_REPEATS:
            continue
        missing, extra = basket - current, current - basket
        if not missing or len(missing) > MAX_MISSING or len(extra) > MAX_EXTRA:
            continue
        if len(missing) + len(extra) > MAX_DIFFERENCES or len(missing) / len(basket) > MAX_MISSING_SHARE:
            continue
        key = (len(missing) + len(extra), -times)  # the closest repeated order, then the most frequent one
        if best is None or key < best[0]:
            best = (key, basket, times, missing)
    if not best:
        return None
    _, basket, times, missing = best
    same = [o for o in history if frozenset(o["lines"]) == basket]
    return {
        "missing": sorted(missing),
        "times": times,
        "last": max(o["date"] for o in same),
        "qty": {pid: median(o["lines"][pid] for o in same) for pid in missing},
    }


async def gather(erp: ErpClient, client_id: str, delivery_date: str) -> dict:
    """His placed orders of the last 6 months with their lines, the open order(s) for this delivery date, the products,
    and his status, read in parallel."""
    meta, client, summaries, products = await asyncio.gather(
        erp.get("/api/meta"),
        erp.get(f"/api/clients/{enc(client_id)}"),
        erp.get("/api/orders", {"clientId": client_id, "limit": 500}),
        erp.get("/api/products", {"limit": 500}),
    )
    summaries = summaries if isinstance(summaries, list) else summaries.get("items", [])
    since = (date.fromisoformat(meta["today"]) - timedelta(days=WINDOW_DAYS)).isoformat()
    past = [s for s in summaries if since <= (s.get("deliveryDate") or "") < meta["today"] and s.get("status") in PLACED]
    open_ = [s for s in summaries if s.get("deliveryDate") == delivery_date and s.get("status") in ("draft", "confirmed")]
    details = await asyncio.gather(*(erp.get(f"/api/orders/{enc(s['id'])}") for s in past + open_))
    lines = lambda o: {l["productId"]: l.get("qty") or 0 for l in o.get("lines") or []}  # noqa: E731
    products = products if isinstance(products, list) else products.get("items", [])
    return {
        "client": {k: client.get(k) for k in ("id", "status")},
        "history": [{"date": (o.get("deliveryDate") or "")[:10], "lines": lines(o)} for o in details[: len(past)]],
        "current": {pid for o in details[len(past):] for pid in lines(o)},
        "products": {p["id"]: p for p in products},
    }


async def suggest(erp: ErpClient, client_id: str, delivery_date: str) -> list[dict]:
    if FESTIVE[0] <= delivery_date[5:] <= FESTIVE[1]:
        return []
    facts = await gather(erp, client_id, delivery_date)
    if facts["client"].get("status") == "blocked":
        return []
    found = forgotten(facts["history"], facts["current"])
    if not found:
        return []
    out = []
    for pid in found["missing"]:
        p = facts["products"].get(pid)
        if not p or not p.get("active", True):
            continue
        qty, pieces = round_qty(found["qty"][pid], p)
        out.append({
            "productId": pid, "name": p["name"], "qty": qty, "unit": p["unit"], **({"pieces": pieces} if pieces else {}),
            "reasonKind": "habitude",
            "reasonText": f"dans la commande qu'il passe à l'identique ({found['times']} fois en six mois)",
            "evidence": f"{found['times']} commandes identiques en 6 mois, la dernière le {found['last'][8:10]}/{found['last'][5:7]}",
        })  # fmt: skip
    if not out:
        return []
    checked = await check_items(erp, client_id, delivery_date, [Item(product_id=c["productId"], qty=c["qty"]) for c in out])
    if checked.get("deliveryDay"):  # not a delivery day for this client: nothing to add to
        return []
    return [c for c, row in zip(out, checked["items"]) if not problems_of({"items": [row]})]


def _say(c: dict) -> str:
    return f"{fmt(c['pieces'])} pièce(s) de {c['name']}" if c.get("pieces") else f"{fmt(c['qty'])} {c['unit']} de {c['name']}"


@tool
async def suggest_items(
    ctx: ToolContext,
    client_id: str,
    delivery_date: str = Field(description="Date de livraison de la commande, YYYY-MM-DD"),
) -> dict:
    """
    À appeler UNE fois, quand le client dit que sa commande est finie (« c'est tout »), avant la relecture. Rend les produits
    qu'il a probablement OUBLIÉS : seulement si sa commande ressemble nettement à une commande qu'il passe à l'identique
    (au moins 3 fois), avec au plus deux oublis. Déjà vérifiés (stock à la date, délai, jour de livraison). Liste vide = c'est
    une autre commande : ne lui demande pas s'il a oublié quelque chose.
    """
    found = await suggest(ctx.erp, client_id, delivery_date)
    out: dict = {"deliveryDate": delivery_date, "jour": jour(delivery_date), "suggestions": found}
    if found:
        out["plan"] = (
            f"À la fin de ta relecture, UNE seule question qui propose tout en même temps : {' et '.join(_say(c) for c in found)} "
            "(« d'habitude tu prends aussi…, je te les mets ? »). C'est la seule suggestion de l'appel. Au tour suivant : s'il dit "
            "oui à tout ou à une partie, ajoute ce qu'il accepte et, dans la même réponse, relis toute la commande et pose la "
            "question d'accord (ou valide s'il t'a dit de valider) ; s'il dit non, pose la question d'accord."
        )
    else:
        out["plan"] = "Rien à proposer : relecture et question d'accord."
    return out
