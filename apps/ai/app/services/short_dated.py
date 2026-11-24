"""
« Date courte » : the calls that sell stock before it expires, instead of throwing it away.

A fresh product has a few days. When a lot is close to its use-by date and no order will take it, somebody should
phone the clients who usually buy that product and offer it, at a price the house has decided. Nobody has the time,
so it goes to waste. This module finds those lots in the ERP, in code (no model, nothing invented), and prepares the
calls. The agent makes them, with the same rails as the truck calls (services/truck_calls.py).

    board(erp)                         → what will expire unsold, how much it is worth, who usually buys it, what was
                                         approved and what the calls sold (GET /outbound/short-dated)
    approve(erp, product_id, price)    → THE HUMAN STEP. A person sets the price of the offer. Without it no call starts.
    brief(erp, product_id, client_id)  → the facts of ONE call for the agent
    take(erp, client_id, ...)          → the only write of such a call: an order line at the approved price, for one of
                                         the client's delivery days before the use-by date

What the agent can and cannot do is fixed here:
  - no approved price, no call (« agents act only after team approval »);
  - the price is the approved one, never lower, and the house's approval is refused below the purchase cost;
  - the use-by date is said in the first sentence: the client decides knowing it;
  - never more than what is still unsold, nor more than three times what this client usually takes;
  - only a delivery day of his that falls BEFORE the use-by date; a lot that can no longer be delivered in time is
    listed as lost, not offered.

« Unsold » = the lots that expire on or before a date, minus everything orders have already reserved up to the day
before. It is what will be thrown away if no new order comes.
"""

import asyncio
import json
import re
import time
import uuid
from datetime import date, timedelta

from app.schemas import ChatMessage, ToolCall
from app.tools.erp import ErpClient, enc, pick

from .truck_calls import JOURS, Opening, euros, gather_limited, jour, r2

HORIZON_DAYS = 4  # lots that expire within this many days are looked at
MIN_UNSOLD = 5.0  # below this (kg or units) a call costs more than the product
MAX_CANDIDATES = 6
HABIT_FACTOR = 3.0  # an offer never puts more than three times a client's usual quantity on his order
TAG = "offre-date-courte"
LINE_NOTE = "Offre date courte"
WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
PRICE_LINE = re.compile(r"^Prix approuvé : ([0-9]+(?:[.,][0-9]+)?) € par (\S+), jusqu'au (\d{4}-\d{2}-\d{2}) \(à consommer avant le (\d{4}-\d{2}-\d{2})\)", re.M)

_cache: dict[str, tuple[float, object]] = {}


async def cached(key: str, ttl: float, make):
    hit = _cache.get(key)
    if hit and time.monotonic() - hit[0] < ttl:
        return hit[1]
    value = await make()
    _cache[key] = (time.monotonic(), value)
    return value


def add_days(iso: str, n: int) -> str:
    return (date.fromisoformat(iso) + timedelta(days=n)).isoformat()


def qty_text(q: float, unit: str | None) -> str:
    return f"{q:g} {'kg' if (unit or 'kg') == 'kg' else unit}".replace(".", ",")


# ───────────────────────── what will expire unsold ─────────────────────────


def expiry_rows(lots: list[dict], reserved_by: dict[str, float], today: str) -> list[dict]:
    """For each use-by date within the horizon: how much of the lots that expire by then no order will take.
    `reserved_by[d]` = everything reserved for deliveries up to day d. A lot must be delivered before its use-by date,
    so the lots that expire on E only count the orders delivered up to E − 1."""
    lots = sorted((l for l in lots if (l.get("qtyRemaining") or 0) > 0 and l.get("expiresAt")), key=lambda l: l["expiresAt"])
    rows, counted = [], 0.0
    for e in sorted({l["expiresAt"] for l in lots if l["expiresAt"] <= add_days(today, HORIZON_DAYS)}):
        last_delivery = add_days(e, -1)
        on_hand = sum(l["qtyRemaining"] for l in lots if l["expiresAt"] <= e)
        unsold = max(0.0, on_hand - reserved_by.get(max(last_delivery, today), 0.0))
        fresh = r2(max(0.0, unsold - counted))  # not already counted with an earlier date
        counted = max(counted, unsold)
        if fresh >= MIN_UNSOLD:
            rows.append(
                {
                    "useBy": e,
                    "lastDelivery": last_delivery,
                    "unsold": fresh,
                    "lots": [l["id"] for l in lots if l["expiresAt"] == e],
                    # today's trucks are loaded: what must be delivered today at the latest can no longer be sold
                    "tooLate": last_delivery <= today,
                }
            )
    return rows


async def product_rows(erp: ErpClient, product: dict, today: str) -> list[dict]:
    lots = (product.get("stock") or {}).get("lots") or []
    dates = sorted({l["expiresAt"] for l in lots if (l.get("qtyRemaining") or 0) > 0 and l.get("expiresAt") and l["expiresAt"] <= add_days(today, HORIZON_DAYS)})
    if not dates:
        return []
    days = sorted({max(add_days(e, -1), today) for e in dates})
    levels = await gather_limited([erp.get("/api/stock/availability", {"date": d, "productIds": product["id"]}) for d in days])
    reserved_by = {d: float((lv[0] if lv else {}).get("reservedByDate") or 0) for d, lv in zip(days, levels)}
    return expiry_rows(lots, reserved_by, today)


async def at_risk(erp: ErpClient) -> tuple[str, list[dict]]:
    """(today, one entry per product that has short-dated stock nobody ordered)."""

    async def read():
        meta, products = await asyncio.gather(erp.get("/api/meta"), erp.get("/api/products", {"limit": 500}))
        products = products.get("items", products) if isinstance(products, dict) else products
        today = meta["today"]
        soon = [p for p in products if p.get("nextExpiry") and p["nextExpiry"] <= add_days(today, HORIZON_DAYS) and (p.get("onHand") or 0) > 0]
        details = await gather_limited([erp.get(f"/api/products/{enc(p['id'])}") for p in soon])
        rows = await gather_limited([product_rows(erp, d, today) for d in details])
        out = []
        for d, rr in zip(details, rows):
            if rr:
                out.append({**pick(d, "id", "name", "unit", "price", "cost", "origin", "caliber"), "rows": rr})
        return today, out

    return await cached("at_risk", 5.0, read)


# ───────────────────────── the human step: the price ─────────────────────────


async def offers(erp: ErpClient, product_id: str) -> dict | None:
    """The offer a person approved for this product, read back from the ERP (a context entry of kind « pricing »)."""
    found = await erp.get("/api/context/for", {"entityType": "product", "id": product_id})
    for e in found.get("entries") or []:
        m = PRICE_LINE.search(e.get("body") or "") if TAG in (e.get("tags") or []) else None
        if m:
            return {"id": e["id"], "price": float(m.group(1).replace(",", ".")), "validTo": m.group(3), "useBy": m.group(4), "title": e.get("title"), "at": e.get("updatedAt")}
    return None


async def approve(erp: ErpClient, product_id: str, price: float) -> dict:
    """A person sets the price of the offer. Refused below the purchase cost, and when there is nothing to sell in
    time. Written in the ERP as a pricing note on the product, so it is visible and survives a restart."""
    today, products = await at_risk(erp)
    product = next((p for p in products if p["id"] == product_id), None)
    row = next((r for r in (product or {}).get("rows", []) if not r["tooLate"]), None)
    if not product or not row:
        raise ValueError("Rien à vendre en date courte sur ce produit (pas de lot proche de sa date, ou plus livrable à temps).")
    if price <= 0 or price >= float(product["price"]):
        raise ValueError(f"Le prix de l'offre doit être inférieur au prix catalogue ({euros(product['price'])}).")
    if price < float(product.get("cost") or 0):
        raise ValueError(f"Refusé : {euros(price)} est sous le coût d'achat ({euros(product['cost'])}). Une offre date courte ne se vend pas à perte.")
    old = await offers(erp, product_id)
    body = (
        f"Prix approuvé : {price:.2f} € par {product['unit']}, jusqu'au {row['lastDelivery']} (à consommer avant le {row['useBy']})\n\n"
        f"{qty_text(row['unsold'], product['unit'])} de {product['name']} sans commande au moment de l'approbation, lot(s) {', '.join(row['lots'])}. "
        f"Prix catalogue {euros(product['price'])}. L'agent vocal propose ce prix aux clients qui en prennent d'habitude, pour une "
        f"livraison au plus tard {jour(row['lastDelivery'])}. Il ne descend jamais sous ce prix."
    )
    entry = {
        "entityType": "product",
        "entityId": product_id,
        "kind": "pricing",
        "title": f"Offre date courte : {product['name']} à {euros(price)} jusqu'au {jour(row['lastDelivery'])}",
        "body": body,
        "tags": [TAG],
    }
    saved = await (erp.patch(f"/api/context/{enc(old['id'])}", entry) if old else erp.post("/api/context", entry))
    _cache.clear()
    return {"productId": product_id, "product": product["name"], "price": price, "validTo": row["lastDelivery"], "useBy": row["useBy"], "contextId": saved.get("id")}


# ───────────────────────── who to call ─────────────────────────


def delivery_days(today: str, client_days: list[str], last: str) -> list[dict]:
    """The client's delivery days from tomorrow to `last` (today's trucks are loaded)."""
    out, d = [], date.fromisoformat(today) + timedelta(days=1)
    while d.isoformat() <= last:
        if WEEKDAYS[d.weekday()] in (client_days or WEEKDAYS[:6]):
            out.append({"date": d.isoformat(), "jour": f"{JOURS[d.weekday()]} {d.day}"})
        d += timedelta(days=1)
    return out


async def buyers(erp: ErpClient) -> list[dict]:
    """Every active client with his usual basket (cached: the board polls)."""

    async def read():
        clients = await erp.get("/api/clients", {"limit": 500})
        clients = clients.get("items", clients) if isinstance(clients, dict) else clients
        active = [c for c in clients if c.get("status") == "active"]
        usual = await gather_limited([erp.get(f"/api/clients/{enc(c['id'])}/usual") for c in active])
        return [{**c, "usual": u or []} for c, u in zip(active, usual)]

    return await cached("buyers", 120.0, read)


async def offer_lines(erp: ErpClient, client_id: str, product_id: str, today: str) -> list[dict]:
    """What this client already has on order for this product from tomorrow on, and what the offer already sold him."""
    rows = await erp.get("/api/orders", {"clientId": client_id, "status": "draft,confirmed", "limit": 20})
    rows = rows.get("items", rows) if isinstance(rows, dict) else rows
    details = await gather_limited([erp.get(f"/api/orders/{enc(o['id'])}") for o in rows if o.get("deliveryDate", "") > today])
    out = []
    for o in details:
        for l in o["lines"]:
            if l["productId"] == product_id:
                out.append({"orderId": o["id"], "number": o["number"], "status": o["status"], "deliveryDate": o["deliveryDate"], "qty": l["qty"], "unitPrice": l["unitPrice"], "offer": str(l.get("note") or "").startswith(LINE_NOTE)})
    return out


async def candidates(erp: ErpClient, product: dict, row: dict, today: str) -> list[dict]:
    """The clients worth a call: they usually buy this product, and a truck goes to them before the use-by date."""
    found = []
    for c in await buyers(erp):
        habit = next((u for u in c["usual"] if u.get("productId") == product["id"]), None)
        days = delivery_days(today, c.get("deliveryDays") or [], row["lastDelivery"])
        if habit and days:
            found.append((c, habit, days))
    found.sort(key=lambda x: -(float(x[1].get("avgQty") or 0) * float(x[1].get("frequency") or 0)))
    found = found[: MAX_CANDIDATES * 2]
    lines = await gather_limited([offer_lines(erp, c["id"], product["id"], today) for c, _, _ in found])
    # A client who already has this product on order at his normal price is served: calling him to offer the same
    # product cheaper would only reopen the order he placed. He is left alone.
    kept = [(f, ll) for f, ll in zip(found, lines) if not any(not l["offer"] for l in ll)][:MAX_CANDIDATES]
    events = await gather_limited([erp.get(f"/api/clients/{enc(f[0]['id'])}/events", {"limit": 8}) for f, _ in kept])
    out = []
    for ((c, habit, days), ll), ev in zip(kept, events):
        ev = ev.get("items", ev) if isinstance(ev, dict) else ev
        report = next((e for e in ev or [] if TAG in (e.get("tags") or []) and str(e.get("at") or "")[:10] >= today and product["name"] in str(e.get("title"))), None)
        taken = r2(sum(l["qty"] for l in ll if l["offer"]))
        contacts = c.get("contacts") or []
        out.append(
            {
                "clientId": c["id"],
                "clientName": c["name"],
                "city": c.get("city"),
                "type": c.get("type"),
                "contact": pick(contacts[0], "name", "role", "phone") if contacts else None,
                "usualQty": r2(float(habit.get("avgQty") or 0)),
                "lastQty": habit.get("lastQty"),
                "lastOrderedAt": habit.get("lastOrderedAt"),
                "deliveryDays": days,
                "alreadyOnOrder": r2(sum(l["qty"] for l in ll if not l["offer"])),
                "taken": taken,
                "status": "taken" if taken else "done" if report and report.get("status") == "resolved" else "to_call",
                "outcome": pick(report, "id", "title", "status") if report else None,
                "startWith": f"/appel {product['id']} {c['id']}",
            }
        )
    return out


async def board(erp: ErpClient) -> dict:
    """What will expire unsold, the price a person approved, who to call, what the calls sold."""

    async def read():
        today, products = await at_risk(erp)
        items, lost = [], []
        for p in products:
            for r in p["rows"]:
                if r["tooLate"]:
                    lost.append({"productId": p["id"], "productName": p["name"], "unit": p["unit"], **pick(r, "useBy", "unsold"), "cost": r2(r["unsold"] * float(p.get("cost") or 0)),
                                 "why": "à livrer aujourd'hui au plus tard, et les camions sont chargés : trop tard pour le vendre"})  # fmt: skip
            row = next((r for r in p["rows"] if not r["tooLate"]), None)
            if not row:
                continue
            offer, who = await asyncio.gather(offers(erp, p["id"]), candidates(erp, p, row, today))
            if offer and offer["useBy"] != row["useBy"]:
                offer = None  # approved for an earlier lot: a new decision is needed
            sold = r2(sum(c["taken"] for c in who))
            items.append(
                {
                    "productId": p["id"],
                    "productName": p["name"],
                    "unit": p["unit"],
                    "useBy": row["useBy"],
                    "useByJour": jour(row["useBy"]),
                    "lastDelivery": row["lastDelivery"],
                    "unsold": row["unsold"],  # still without an order right now (it goes down as the calls sell)
                    "listPrice": p["price"],
                    "cost": p.get("cost"),
                    "atStake": r2(row["unsold"] * float(p.get("cost") or 0)),  # what the house loses if it is thrown away
                    "offer": pick(offer, "price", "validTo", "title") if offer else None,
                    "approveWith": f"/offre {p['id']} <prix>",  # typed (or sent by the page) on WS /voice
                    "candidates": who,
                    "sold": sold,
                    "soldValue": r2(sold * offer["price"]) if offer else 0.0,
                }
            )
        items.sort(key=lambda i: (i["useBy"], -i["atStake"]))
        return {
            "today": today,
            "offers": items,
            "tooLate": lost,
            "atStake": r2(sum(i["atStake"] for i in items)),
            "sold": r2(sum(i["soldValue"] for i in items)),
        }

    return await cached("board", 3.0, read)


# ───────────────────────── one call ─────────────────────────


async def brief(erp: ErpClient, product_id: str, client_id: str) -> dict:
    """Everything the agent may say in the call that offers this product to this client. Raises ValueError when the
    call must not happen: no approved price, nothing left, no delivery day of his before the use-by date."""
    today, products = await at_risk(erp)
    product = next((p for p in products if p["id"] == product_id), None)
    row = next((r for r in (product or {}).get("rows", []) if not r["tooLate"]), None)
    if not product or not row:
        raise ValueError("Plus rien à vendre en date courte sur ce produit : aucun appel à passer.")
    offer = await offers(erp, product_id)
    if not offer or offer["useBy"] != row["useBy"]:
        raise ValueError(f"Aucun prix approuvé pour {product['name']} : une personne doit d'abord fixer le prix de l'offre (« /offre {product_id} <prix> »). L'agent ne décide pas d'une remise.")
    client, usual, lines = await asyncio.gather(
        erp.get(f"/api/clients/{enc(client_id)}"),
        erp.get(f"/api/clients/{enc(client_id)}/usual"),
        offer_lines(erp, client_id, product_id, today),
    )
    if client.get("status") != "active":
        raise ValueError("Compte non actif : pas d'offre à ce client.")
    days = delivery_days(today, client.get("deliveryDays") or [], row["lastDelivery"])
    if not days:
        raise ValueError(f"Aucune livraison chez {client.get('name')} avant la date limite : pas d'appel.")
    habit = next((u for u in usual or [] if u.get("productId") == product_id), None)
    usual_qty = float((habit or {}).get("avgQty") or 0)
    taken = sum(l["qty"] for l in lines if l["offer"])
    # his price outside the offer: what the ERP would charge him the day after it ends
    normal = await erp.get("/api/prices/resolve", {"clientId": client_id, "productId": product_id, "qty": "1", "date": add_days(offer["validTo"], 30)})
    cap = r2(min(row["unsold"], max(usual_qty * HABIT_FACTOR, MIN_UNSOLD)) if usual_qty else min(row["unsold"], MIN_UNSOLD * 2))
    suggested = r2(min(cap, round(usual_qty) or MIN_UNSOLD))
    contacts = client.get("contacts") or []
    unit = product["unit"]
    b = {
        "outgoingCall": True,
        "reason": "short_dated_offer",
        "client": pick(client, "id", "name", "city", "salesRep"),
        "askFor": pick(contacts[0], "name", "role") if contacts else None,
        "product": {**pick(product, "id", "name", "unit", "origin", "caliber"), "useBy": row["useBy"], "useBySay": f"avant {jour(row['useBy'])}"},
        "offer": {
            "pricePerUnit": offer["price"],
            "hisUsualPrice": normal.get("price"),
            "approvedBy": "l'équipe (prix fixé par la maison, non négociable)",
            "stillAvailable": row["unsold"],
        },
        "habit": {"usualQty": r2(usual_qty), **pick(habit or {}, "lastQty", "lastOrderedAt")} if habit else "il n'en prend pas d'habitude",
        "suggestedQty": suggested,
        "maxQty": cap,
        "deliveryOptions": days,
        "alreadyOnOrder": [f"{qty_text(l['qty'], unit)} sur {l['number']} pour {jour(l['deliveryDate'])}" for l in lines if not l["offer"]],
        "alreadyTaken": [f"{qty_text(l['qty'], unit)} à {euros(l['unitPrice'])} sur {l['number']}" for l in lines if l["offer"]],
        "do": "Propose suggestedQty pour deliveryOptions[0], en disant la date limite et le prix. S'il en veut plus ou moins : jusqu'à maxQty. S'il dit non : remercie et termine.",
    }
    if taken:
        b["do"] = "Il a déjà pris cette offre (alreadyTaken) : ne la repropose pas, demande seulement s'il veut changer quelque chose."
    return {k: v for k, v in b.items() if v not in (None, "", [])}


async def take(erp: ErpClient, client_id: str, product_id: str, qty: float, delivery_date: str) -> dict:
    """Writes the offer the client accepted: a line at the approved price on his order of that day (a new confirmed
    order when he has none). Everything is checked again here, in code."""
    b = await brief(erp, product_id, client_id)
    if b.get("alreadyTaken"):
        raise ValueError(f"Il a déjà pris cette offre ({b['alreadyTaken'][0]}) : ne l'écris pas une seconde fois.")
    if qty <= 0:
        raise ValueError("Quantité invalide.")
    if qty > b["maxQty"] + 1e-6:
        raise ValueError(f"Trop : au prix de l'offre il peut prendre {b['maxQty']:g} au plus (ce qui reste, et pas plus de trois fois son habitude). Le reste se commande au prix normal.")
    day = next((d for d in b["deliveryOptions"] if d["date"] == delivery_date), None)
    if not day:
        ok = ", ".join(d["jour"] for d in b["deliveryOptions"])
        raise ValueError(f"Pas ce jour-là : la date limite est {b['product']['useBySay']}, il peut être livré {ok}.")
    price = b["offer"]["pricePerUnit"]
    line = {"productId": product_id, "qty": qty, "unitPrice": price, "note": f"{LINE_NOTE} : à consommer {b['product']['useBySay']} (prix approuvé par l'équipe)"}
    existing = await erp.get("/api/orders", {"clientId": client_id, "date": delivery_date, "status": "draft,confirmed", "limit": 5})
    existing = existing.get("items", existing) if isinstance(existing, dict) else existing
    if existing:
        order = await erp.post(f"/api/orders/{enc(existing[0]['id'])}/lines", line)
    else:
        draft = await erp.post("/api/orders", {"clientId": client_id, "deliveryDate": delivery_date, "source": "voice_agent", "lines": [line]})
        order = await erp.post(f"/api/orders/{enc(draft['id'])}/confirm")
    _cache.clear()
    unit = b["product"]["unit"]
    return {
        **pick(order, "id", "number", "status", "deliveryDate", "totalHt"),
        "client": b["client"]["name"],
        "lines": [{"lineId": l["id"], **pick(l, "productId", "productName", "qty", "unit", "unitPrice")} for l in order["lines"]],
        "offerLine": f"{qty_text(qty, unit)} de {b['product']['name']} à {euros(price)}, soit {euros(qty * price)}",
        "savedVsUsual": euros(qty * (float(b["offer"].get("hisUsualPrice") or price) - price)),
        "mustSay": [f"Confirme en UNE phrase : la quantité, le total de cette ligne ({euros(qty * price)}), livré {day['jour']}, à consommer {b['product']['useBySay']}."]
        + (["Sa commande de ce jour-là est encore une pré-commande : dis qu'elle reste à valider."] if order.get("status") == "draft" else []),
    }


# ───────────────────────── starting the call ─────────────────────────

OPENING_NOTE = """[Système : APPEL SORTANT, offre date courte. C'est TOI qui appelles ce client : il n'a rien demandé. Il vient de décrocher. Sa fiche (identify_caller) et le brief de l'appel (short_date_brief) suivent. Pour cet appel, ces consignes passent avant les règles habituelles du premier tour et du prix :
1. Ta première réponse : « Bonjour Monsieur » ou « Bonjour Madame » avec son nom de famille (askFor) si tu le vouvoies, son prénom seul si sa fiche dit qu'on le tutoie, puis « c'est l'assistant de la maison {company} ». Puis l'offre en UNE phrase : le produit, « à consommer {use_by} », son prix au kilo ou à l'unité « au lieu de » son prix habituel. Puis la question : la quantité suggérée (suggestedQty), pour son jour de livraison (deliveryOptions, le premier). Rien d'autre.
2. La date limite se dit toujours dans la première phrase, et à nouveau s'il hésite : il décide en le sachant. Ne dis jamais « promotion » ni « bonne affaire ».
3. C'est une offre, pas une vente forcée. S'il dit non : « très bien », remercie en une phrase et termine. Une seule proposition, jamais d'insistance, jamais d'autre produit.
4. Le prix est celui de l'offre, fixé par l'équipe : tu ne le baisses pas et tu ne négocies pas (« c'est le prix fixé par la maison »). Aucune autre remise.
5. Après son oui sur la quantité et le jour : take_offer (jamais create_draft_order pour cette offre). Puis dis le total et le jour, en une phrase.
6. Ne dis rien qui ne soit pas dans le brief ou dans sa fiche. S'il demande l'origine ou le calibre : c'est dans product. Ce qui n'y est pas, tu ne le sais pas.
7. S'il veut commander autre chose pendant l'appel : outils habituels, règles habituelles.
8. Si la personne qui a décroché n'est pas celle qui décide : n'écris aucune commande. Dis l'offre en une phrase, et enregistre-le avec log_client_event (type call, titre qui commence par « À rappeler : »).
9. Sois bref : il n'a rien demandé. Une question à la fois.]"""


async def opening(erp: ErpClient, product_id: str, client_id: str) -> Opening:
    from app.tools.desk import client_card  # (imported here: tools/short_dated.py imports this module)

    b, meta = await asyncio.gather(brief(erp, product_id, client_id), erp.get("/api/meta"))
    card = {"status": "found", "client": await client_card(erp, client_id), "how": "Appel sortant : c'est nous qui appelons ce client, à son numéro."}
    calls = [
        ToolCall(id=f"out_{uuid.uuid4().hex[:16]}", name="identify_caller", arguments={"said": b["client"]["name"], "clientId": client_id}),
        ToolCall(id=f"out_{uuid.uuid4().hex[:16]}", name="short_date_brief", arguments={"productId": product_id}),
    ]
    results = [card, b]
    note = OPENING_NOTE.format(company=meta.get("company") or "votre grossiste", use_by=b["product"]["useBySay"])
    messages = [
        ChatMessage(role="user", content=f"Allô ?\n\n{note}"),
        ChatMessage(role="assistant", content="", tool_calls=calls),
        *(ChatMessage(role="tool", tool_call_id=c.id, name=c.name, content=json.dumps(r, ensure_ascii=False, separators=(",", ":"))) for c, r in zip(calls, results)),
    ]
    who = (b.get("askFor") or {}).get("name")
    label = f"Appel sortant → {b['client']['name']}" + (f" ({who})" if who else "") + f" · offre date courte : {b['product']['name']}, à consommer {b['product']['useBySay']}"
    return Opening(label=label, messages=messages, tools=[(c.name, c.arguments, r) for c, r in zip(calls, results)])
