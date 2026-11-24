"""Le cadran annoncé: tell the butchers how this week's market quote moved their carcass prices (lane B, 24/11/2026).

Why: carcasses and quarters are priced on the weekly quote of the Limoges market (« cadran », published on Monday,
05-prix-et-credit.md), so a butcher's price moves every week. The company's own note for today says « Cotation du lundi
en hausse de 6 centimes sur la génisse : prévenir les bouchers », and 16 client files list « les hausses de cotation
non annoncées » as a risk (a lost butcher among them). On the phone, butchers react with « Encore une hausse ? ».

What this module does, in plain rules and only from data the ERP already has:
  - for a client and each carcass product he buys: today's price for him (the same resolver as the order lines), the
    price he paid on his last delivery BEFORE this week's Monday, and the price about four weeks earlier;
  - the sentence the agent may say, built from those numbers only;
  - whether he has already been told this week (a client event tagged « cotation-annoncee »);
  - the week's board: every client who bought carcasses in the last 60 days, told or not yet.
Nothing here changes a price, an order or a rule. Announcing writes one client event, that is all.
"""

from __future__ import annotations

from datetime import date, timedelta

from app import crud
from app.core.activity import Ctx, log_event, today
from app.core.db import Doc, transactional
from app.core.errors import validation_error
from app.services import client_events, pricing

CATEGORY = "carcasses"  # the products priced on the weekly quote
TAG = "cotation-annoncee"
SHORT = {  # how a butcher says it
    "prd_0001": "l'arrière", "prd_0002": "l'avant", "prd_0003": "la demi-carcasse de bœuf", "prd_0004": "le veau",
    "prd_0005": "le demi-veau", "prd_0006": "l'agneau", "prd_0007": "le cul noir", "prd_0008": "le demi-porc",
}  # fmt: skip


def _monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _euros(x: float) -> str:
    e, c = int(round(x * 100)) // 100, int(round(x * 100)) % 100
    return f"{e} euros {c:02d}" if c else f"{e} euros"


def _paid(client_id: str, product_id: str) -> list[tuple[str, float]]:
    """(delivery date, unit price) of every line of that product the client received, oldest first."""
    out = []
    for o in crud.orders.all():
        if o["clientId"] != client_id or o.get("status") == "cancelled":
            continue
        for ln in o.get("lines") or []:
            if ln["productId"] == product_id and ln.get("unitPrice"):
                out.append(((o.get("deliveryDate") or "")[:10], float(ln["unitPrice"])))
    return sorted(out)


def _carcass_ids() -> list[str]:
    return [p["id"] for p in crud.products.all() if p.get("category") == CATEGORY and p.get("active", True)]


def announced_this_week(client_id: str) -> Doc | None:
    monday = _monday(date.fromisoformat(today())).isoformat()
    evs = [e for e in crud.client_events.all() if e["clientId"] == client_id and TAG in (e.get("tags") or []) and (e.get("at") or "")[:10] >= monday]
    return max(evs, key=lambda e: e["at"]) if evs else None


def for_client(client_id: str, product_ids: list[str] | None = None) -> Doc:
    """This week's move for each carcass product the client buys (or the ones asked), and what the agent may say."""
    client = crud.clients.require(client_id)
    day = date.fromisoformat(today())
    monday = _monday(day)
    month_ago = (monday - timedelta(days=28)).isoformat()
    ids = [p for p in (product_ids or _carcass_ids()) if crud.products.require(p).get("category") == CATEGORY]
    rows = []
    for pid in ids:
        paid = _paid(client_id, pid)
        before = [x for x in paid if x[0] < monday.isoformat()]
        if not before:
            continue  # never bought it before this week: no move to tell him about
        now_price = round(pricing.price_for(client_id, pid, 1, today()), 2)
        last_date, last_price = before[-1]
        old = [x for x in before if x[0] <= month_ago]
        row = {
            "productId": pid,
            "productName": crud.products.require(pid)["name"],
            "short": SHORT.get(pid, crud.products.require(pid)["name"]),
            "priceNow": now_price,
            "lastWeekPrice": last_price,
            "lastWeekDate": last_date,
            "delta": round(now_price - last_price, 2),
            **({"monthAgoPrice": old[-1][1], "monthAgoDate": old[-1][0], "deltaMonth": round(now_price - old[-1][1], 2)} if old else {}),
        }
        rows.append(row)
    moved = [r for r in rows if abs(r["delta"]) >= 0.01]
    told = announced_this_week(client_id)
    return {
        "clientId": client_id,
        "clientName": client["name"],
        "weekOf": monday.isoformat(),
        "products": rows,
        "announcedThisWeek": bool(told),
        **({"announcedAt": told["at"]} if told else {}),
        **({"say": _sentence(moved)} if moved and not told else {}),
        **({"ifAsked": _trend_sentence(rows)} if any("deltaMonth" in r for r in rows) else {}),
    }


def _sentence(moved: list[Doc]) -> str:
    """« Cette semaine, l'arrière a pris 5 centimes, à 10 euros 20 le kilo : c'est la cotation de lundi au cadran. »"""
    parts = []
    for r in moved[:2]:  # on the phone: the two products he orders, not a price list
        cents = round(abs(r["delta"]) * 100)
        verb = "a pris" if r["delta"] > 0 else "a baissé de"
        parts.append(f"{r['short']} {verb} {cents} centime{'s' if cents > 1 else ''}, à {_euros(r['priceNow'])} le kilo")
    return "Cette semaine, " + " et ".join(parts) + " : c'est la cotation de lundi au cadran de Limoges."


def _trend_sentence(rows: list[Doc]) -> str:
    r = next(r for r in rows if "deltaMonth" in r)
    way = "monte" if r["deltaMonth"] > 0 else "baisse"
    return (f"Sur un mois, {r['short']} est passé de {_euros(r['monthAgoPrice'])} à {_euros(r['priceNow'])} le kilo : "
            f"la cotation {way} au cadran, c'est la même chose pour tous nos bouchers.")  # fmt: skip


@transactional
def announce(ctx: Ctx, input: Doc) -> Doc:
    """Record that the client was told this week's move (one client event, tagged), plus his reaction if any."""
    client_id = input["clientId"]
    info = for_client(client_id, input.get("productIds") or None)
    moved = [r for r in info["products"] if abs(r["delta"]) >= 0.01]
    if not moved:
        raise validation_error("Rien à annoncer : pas de variation cette semaine sur ses carcasses")
    lines = "; ".join(f"{r['productName']} {r['lastWeekPrice']:.2f} → {r['priceNow']:.2f} € HT/kg" for r in moved)
    reaction = (input.get("reaction") or "").strip()
    ev = client_events.create_client_event(ctx, client_id, {
        "type": "price_negotiation" if reaction else "call",
        "title": "Cotation de la semaine annoncée" + (" — le client réagit" if reaction else ""),
        "description": f"Semaine du {info['weekOf']} : {lines}." + (f" Réaction : « {reaction} »." if reaction else ""),
        "productIds": [r["productId"] for r in moved],
        "tags": [TAG],
        **({"status": "open"} if reaction else {}),
    })  # fmt: skip
    log_event(ctx, "cotation.announced", "client", client_id, f"Cotation annoncée à {info['clientName']} : {lines}")
    return {"announced": True, "eventId": ev["id"], "products": moved, **({"reaction": reaction} if reaction else {})}


def board() -> Doc:
    """The week: every client who bought carcasses in the last 60 days, told or not, with his move."""
    day = date.fromisoformat(today())
    since = (day - timedelta(days=60)).isoformat()
    carc = set(_carcass_ids())
    buyers: dict[str, int] = {}
    for o in crud.orders.all():
        if (o.get("deliveryDate") or "") >= since and o.get("status") != "cancelled" and any(l["productId"] in carc for l in o.get("lines") or []):
            buyers[o["clientId"]] = buyers.get(o["clientId"], 0) + 1
    rows = []
    for cid, n in buyers.items():
        c = crud.clients.table.rows.get(cid)
        if not c or c.get("status") == "blocked":
            continue
        info = for_client(cid)
        moved = [r for r in info["products"] if abs(r["delta"]) >= 0.01]
        rows.append({
            "clientId": cid, "clientName": c["name"], "type": c.get("type"), "salesRep": c.get("salesRep"),
            "orders60d": n, "announced": info["announcedThisWeek"], "announcedAt": info.get("announcedAt"),
            "moves": [{"short": r["short"], "lastWeekPrice": r["lastWeekPrice"], "priceNow": r["priceNow"], "delta": r["delta"]} for r in moved],
            "sensitive": _sensitive(cid),
        })  # fmt: skip
    rows.sort(key=lambda r: (r["announced"], not r["sensitive"], -r["orders60d"]))
    return {"weekOf": _monday(day).isoformat(), "today": today(), "clients": rows,
            "told": sum(r["announced"] for r in rows), "total": len(rows)}  # fmt: skip


def _sensitive(client_id: str) -> bool:
    """His file lists unannounced quote rises as something that annoys him."""
    return any(
        x.get("entityId") == client_id and x.get("kind") == "risk" and "cotation" in (x.get("body") or "").lower()
        for x in crud.context_entries.all()
    )
