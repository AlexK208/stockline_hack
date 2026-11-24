"""
« Avant le camion » : the calls the agent makes itself, before the trucks leave.

Every morning the orders of the day are weighed and loaded. When a product is missing on the truck (or a weight is
far from what was ordered), the client finds out when he opens the box, in the middle of his prep. The house rule
(data/context/04-playbook-clients.md) says: call BEFORE the truck leaves. Nobody has the time at 04:45.

This module finds those calls in the ERP, in code (no model, nothing invented):

    truck_board(erp)            → every prepared order of the day checked line by line: the calls to make, the gaps
                                  that are normal and need no call, what was already settled (GET /outbound/truck-calls)
    truck_brief(erp, order_id)  → the facts of ONE call for the agent: what is missing and why (the stock movement's own
                                  note), where the truck is, the client's substitution rule, what can still be loaded
                                  (real stock, his price, the lot that would go), when the product comes back
    add_complement(...)         → the only write of such a call: a complement order on today's truck (tools/truck.py)

When to call (thresholds from the wholesaler's side of the table, not from us):
    a product ordered and absent from the truck       → always
    a weight short by 5 % or more and 15 € or more    → yes (he planned his service on it)
    a weight over by 5 % or more and 50 € or more     → yes (he pays more than he ordered)
    anything else (9,45 kg for 9 ordered…)            → no call: this is meat, it is sold at the real weight
"""

import asyncio
import json
import re
import time
import uuid
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from app.config import settings
from app.schemas import ChatMessage, ToolCall
from app.tools.erp import ErpClient, enc, pick

TOLERANCE = 0.05  # a weight within ±5 % of the order is a normal weighing
SHORT_EUR = 15.0  # below this a short weight is not worth waking a chef up
OVER_EUR = 50.0  # the client pays more than he ordered: we only call above this
MAX_OPTIONS = 3
# A complement repairs a delivery: it weighs what is missing, plus a margin because pieces do not come by the gram
# (4,5 kg of onglet replaced by three bavettes of 1,5 to 2 kg). « Twice the missing weight » let « rajoutez vingt
# kilos » through on a 21 kg line (Claudio's replay R2): the margin is now 20 %, and never less than 2 kg.
COMPLEMENT_MARGIN = 0.20
COMPLEMENT_MARGIN_MIN_KG = 2.0
TAG = "appel-camion"
NOT_REACHED_TAG = "a-rappeler"  # on the report of a call where the person who decides was not on the line
COMPLEMENT_NOTE = "Complément camion"
KIND_LABEL = {"missing": "absent du camion", "short": "poids court", "over": "poids au-dessus de la commande", "replaced": "remplacé dans le camion"}
JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]


def r2(x: float) -> float:
    return round(x + 0.0, 2)


def complement_cap(missing_qty: float) -> float:
    """The most a complement may weigh for this much missing: 4,5 → 6,5 kg, 21 → 25,2 kg."""
    return r2(missing_qty + max(COMPLEMENT_MARGIN_MIN_KG, COMPLEMENT_MARGIN * missing_qty)) if missing_qty > 0 else 0.0


def euros(x: float) -> str:
    return f"{x:.2f} €".replace(".", ",")


def jour(iso: str | None) -> str:
    try:
        d = date.fromisoformat((iso or "")[:10])
    except ValueError:
        return iso or ""
    return f"{JOURS[d.weekday()]} {d.day}"


def say_time(hhmm: str | None) -> str:
    """ "05:51" → "5 h 50" (rounded to five minutes: an arrival time is a plan, not a promise to the minute)."""
    try:
        h, m = (int(x) for x in (hhmm or "").split(":")[:2])
    except ValueError:
        return hhmm or ""
    m = 5 * round(m / 5)
    if m == 60:
        h, m = h + 1, 0
    return f"{h} h {m:02d}" if m else f"{h} h"


# ───────────────────────── which lines deserve a call ─────────────────────────


def line_gap(line: dict) -> dict | None:
    """The gap between ordered and loaded for one order line, or None when it is within a normal weighing."""
    ordered, loaded = float(line.get("qty") or 0), line.get("preparedQty")
    if loaded is None or ordered <= 0:
        return None
    loaded = float(loaded)
    diff = loaded - ordered
    amount = r2(diff * float(line.get("unitPrice") or 0))
    pct = round(diff / ordered, 4)  # (9,45 − 9) / 9 is 0.04999… in floating point: it is 5 %
    if loaded <= 0:
        kind = "missing"
    elif pct <= -TOLERANCE:
        kind = "short"
    elif pct >= TOLERANCE:
        kind = "over"
    else:
        return None
    call = kind == "missing" or (kind == "short" and -amount >= SHORT_EUR) or (kind == "over" and amount >= OVER_EUR)
    return {
        "kind": kind,
        "call": call,
        **pick(line, "productId", "productName", "unit", "unitPrice"),
        "ordered": ordered,
        "onTruck": loaded,
        "gapPct": round(pct * 100),
        "amount": amount,  # euros on the invoice compared with the order (negative = less invoiced)
    }


def order_gaps(order: dict) -> list[dict]:
    """The gaps of an order. A missing product that the team already replaced on the same order (a loaded line marked
    `substituteFor`) becomes kind "replaced": nothing is missing on the truck any more, but a replacement is never
    silent (« jamais sans accord », « si on prévient »): the client is called to hear it and say yes or no."""
    lines = order.get("lines") or []
    substitutes = {l["substituteFor"]: l for l in lines if l.get("substituteFor") and float(l.get("preparedQty") or 0) > 0}
    gaps = []
    for line in lines:
        if line.get("substituteFor"):
            continue  # judged with the product it replaces
        g = line_gap(line)
        if not g:
            continue
        sub = substitutes.get(g["productId"]) if g["kind"] in ("missing", "short") else None
        if sub:
            loaded = float(sub["preparedQty"])
            g = {
                **g,
                "kind": "replaced",
                "call": True,
                "replacedBy": {
                    "lineId": sub["id"],
                    **pick(sub, "productId", "productName", "unit"),
                    "qty": loaded,
                    "pricePerKg": sub.get("unitPrice"),
                    "amount": r2(loaded * float(sub.get("unitPrice") or 0)),
                    **({"noteOnOrder": sub["note"]} if sub.get("note") else {}),
                },
            }
            g["amount"] = r2(g["amount"] + g["replacedBy"]["amount"])  # what the invoice really moves by
        gaps.append(g)
    return gaps


def substitution_rule(preferences: str | None) -> tuple[str, str]:
    """("ok" | "refuse" | "ask", the sentence of the client's file that says so). Read from the free text of the
    file: when it says nothing we ask, we never assume a client accepts a replacement."""
    for sentence in re.split(r"(?<=[.!?])\s+", preferences or ""):
        if re.search(r"substitu|remplac", sentence, re.I):
            if re.search(r"refus|jamais|aucun|pas de", sentence, re.I):
                return "refuse", sentence.strip()
            if re.search(r"accept|d'accord|possible|ok\b", sentence, re.I):
                return "ok", sentence.strip()
            return "ask", sentence.strip()
    return "ask", ""


def house_substitutes(data_dir: Path | None = None) -> dict[str, str]:
    """productId → the house's usual replacement, from « Substitutions habituelles » in the product glossary
    (data/context/*glossaire*.md): « - Onglet de bœuf (prd_0015) → Bavette d'aloyau PAD (prd_0014) »."""
    out: dict[str, str] = {}
    try:
        files = [p for p in ((data_dir or settings.data_dir) / "context").iterdir() if "glossaire" in p.name and p.name.endswith(".md")]
        for p in files:
            for line in p.read_text(encoding="utf-8").splitlines():
                m = re.match(r"\s*-\s.*\((prd_\w+)\)\s*(?:→|->)\s*.*\((prd_\w+)\)", line)
                if m:
                    out[m.group(1)] = m.group(2)
    except OSError:
        pass
    return out


# ───────────────────────── reading the day in the ERP ─────────────────────────


async def gather_limited(coros: list, limit: int = 12) -> list:
    gate = asyncio.Semaphore(limit)

    async def one(c):
        async with gate:
            return await c

    return await asyncio.gather(*(one(c) for c in coros))


async def day_orders(erp: ErpClient, today: str) -> list[dict]:
    """Every order of today that has been weighed and loaded, with its lines."""
    rows = await erp.get("/api/orders", {"status": "prepared", "date": today, "limit": 500})
    rows = rows.get("items", rows) if isinstance(rows, dict) else rows
    return await gather_limited([erp.get(f"/api/orders/{enc(o['id'])}") for o in rows])


async def truck_stops(erp: ErpClient, today: str) -> dict[str, dict]:
    """orderId → where it sits on today's trucks."""
    runs = await erp.get("/api/route-runs", {"date": today})
    out: dict[str, dict] = {}
    for run in runs or []:
        route, stops = run.get("route") or {}, run.get("stops") or []
        for s in stops:
            out[s.get("orderId")] = {
                "route": route.get("name"),
                "driver": route.get("driver"),
                "departure": route.get("departureTime"),
                "eta": s.get("eta"),
                "etaSay": f"vers {say_time(s.get('eta'))}" if s.get("eta") else None,
                "stop": s.get("seq"),
                "stops": len(stops),
            }
    return out


async def complements(erp: ErpClient, client_id: str, today: str) -> list[dict]:
    """The complement orders already put on today's truck for this client (tools/truck.py writes them)."""
    rows = await erp.get("/api/orders", {"clientId": client_id, "date": today, "status": "confirmed,prepared", "limit": 20})
    rows = rows.get("items", rows) if isinstance(rows, dict) else rows
    details = await gather_limited([erp.get(f"/api/orders/{enc(o['id'])}") for o in rows if o.get("source") == "voice_agent"])
    return [o for o in details if str(o.get("note") or "").startswith(COMPLEMENT_NOTE)]


async def call_events(erp: ErpClient, client_id: str, order_id: str, today: str) -> tuple[dict | None, dict | None]:
    """(the report of the call already made about this order, the open issue the ERP holds about it)."""
    events = await erp.get(f"/api/clients/{enc(client_id)}/events", {"limit": 12})
    events = events.get("items", events) if isinstance(events, dict) else events
    about = [e for e in events or [] if e.get("orderId") == order_id and str(e.get("at") or "")[:10] == today]
    reports = [e for e in about if TAG in (e.get("tags") or [])]  # newest first
    report = next((e for e in reports if NOT_REACHED_TAG not in (e.get("tags") or [])), reports[0] if reports else None)
    issue = next((e for e in about if TAG not in (e.get("tags") or []) and e.get("status") == "open"), None)
    return report, issue


def why_missing(product: dict, today: str) -> str:
    """The reason written on the stock movement that emptied the product (the night inventory's own note)."""
    for m in product.get("movements") or []:
        if str(m.get("at") or "")[:10] == today and m.get("reason") in ("adjustment", "waste") and (m.get("qty") or 0) < 0 and m.get("note"):
            return m["note"]
    return ""


async def back_in_stock(erp: ErpClient, product_id: str) -> str:
    """When the product comes back, as far as the ERP knows: a purchase order and how firm it is. Never a promise."""
    try:
        pos = await erp.get("/api/purchase-orders", {"status": "draft,sent,confirmed,partially_received", "limit": 60})
        pos = pos.get("items", pos) if isinstance(pos, dict) else pos
        details = await gather_limited([erp.get(f"/api/purchase-orders/{enc(p['id'])}") for p in pos or []])
    except Exception:
        return ""
    best = None
    for po in details:
        if any(l.get("productId") == product_id and (l.get("qty") or 0) > (l.get("receivedQty") or 0) for l in po.get("lines") or []):
            if best is None or str(po.get("expectedDate")) < str(best.get("expectedDate")):
                best = po
    if not best:
        return "Aucun arrivage annoncé : ne promets aucune date."
    when = jour(best.get("expectedDate"))
    if best.get("status") == "draft":
        return f"Recommandé chez l'éleveur pour {when}, mais la commande n'est pas encore confirmée : dis « on espère {when}, sans garantie », ne promets pas."
    return f"Arrivage attendu {when} (commande fournisseur envoyée). Attendu, pas garanti."


LOT_NOTE = "lot en cours de sortie pour ce produit (le plus ancien en stock) : le numéro exact est sur l'étiquette du colis"


def label_of(product: dict) -> dict:
    """What is printed on the box, as far as the ERP knows before the delivery is closed: origin, size, the lot going out."""
    lots = sorted((l for l in (product.get("stock") or {}).get("lots") or [] if (l.get("qtyRemaining") or 0) > 0), key=lambda l: l.get("expiresAt") or "")
    lot = lots[0] if lots else None
    return {
        **pick(product, "origin", "caliber"),
        **({"lot": {"id": lot["id"], "receivedAt": lot.get("receivedAt"), "useBy": lot.get("expiresAt")}, "lotNote": LOT_NOTE} if lot else {}),
    }


async def options_for(erp: ErpClient, client_id: str, gap: dict, today: str, usual: set[str]) -> list[dict]:
    """What can still go on the truck instead: the house's usual replacement first, then the ERP's alternatives
    (same family, close price), only those really in stock today, at THIS client's price, with the lot that would go."""
    product_id, qty = gap["productId"], gap["ordered"] - gap["onTruck"]
    alternatives = await erp.get(f"/api/products/{enc(product_id)}/alternatives")
    house = house_substitutes().get(product_id)
    already = (gap.get("replacedBy") or {}).get("productId")  # already on the truck: not an option to add
    ranked = sorted((p for p in alternatives or [] if p["id"] != already), key=lambda p: p["id"] != house)  # stable: the ERP's order behind the house's choice
    ids = [p["id"] for p in ranked if (p.get("available") or 0) >= qty][:MAX_OPTIONS]
    if not ids:
        return []
    levels, details, prices = await asyncio.gather(
        erp.get("/api/stock/availability", {"date": today, "productIds": ",".join(ids)}),
        gather_limited([erp.get(f"/api/products/{enc(i)}") for i in ids]),
        gather_limited([erp.get("/api/prices/resolve", {"clientId": client_id, "productId": i, "qty": f"{qty:g}"}) for i in ids]),
    )
    free = {l["productId"]: l.get("availableOn") for l in levels or []}
    out = []
    for p, price in zip(details, prices):
        if (free.get(p["id"]) or 0) < qty:
            continue
        out.append(
            {
                "productId": p["id"],
                "product": p["name"],
                **({"houseSubstitute": True} if p["id"] == house else {}),
                **({"clientAlreadyBuysIt": True} if p["id"] in usual else {}),
                "qty": qty,
                "pricePerKg": price.get("price"),
                "amount": r2(qty * float(price.get("price") or 0)),
                "availableToday": free.get(p["id"]),
                **label_of(p),
            }
        )
    return out


# ───────────────────────── one call ─────────────────────────


async def truck_brief(erp: ErpClient, order_id: str) -> dict:
    """Everything the agent may say in the outgoing call about this order. Raises ValueError when there is no reason
    to call (the order is not on today's truck, or nothing is missing)."""
    meta, order = await asyncio.gather(erp.get("/api/meta"), erp.get(f"/api/orders/{enc(order_id)}"))
    today = meta["today"]
    if order.get("deliveryDate") != today or order.get("status") != "prepared":
        raise ValueError(f"La commande {order.get('number')} n'est pas dans un camion de ce matin : aucun appel à passer.")
    gaps = [g for g in order_gaps(order) if g["call"]]
    if not gaps:
        raise ValueError(f"Rien ne manque sur {order.get('number')} : aucun appel à passer.")
    client = order.get("client") or {}
    rule, rule_text = substitution_rule(client.get("preferences"))
    stops, products, done, usual_rows = await asyncio.gather(
        truck_stops(erp, today),
        gather_limited([erp.get(f"/api/products/{enc(g['productId'])}") for g in gaps]),
        complements(erp, client["id"], today),
        erp.get(f"/api/clients/{enc(client['id'])}/usual"),
    )
    usual = {u.get("productId") for u in usual_rows or []}
    problems = []
    for g, p in zip(gaps, products):
        problem = {k: v for k, v in g.items() if k != "call"}
        if g["kind"] != "over":
            problem["why"] = why_missing(p, today) or "raison non notée dans l'ERP : dis que tu ne sais pas pourquoi"
            problem["backInStock"] = await back_in_stock(erp, g["productId"])
            problem["options" if g["kind"] != "replaced" else "otherOptions"] = await options_for(erp, client["id"], g, today, usual)
        if g["kind"] == "replaced":
            by = dict(problem["replacedBy"])
            by.update(label_of(await erp.get(f"/api/products/{enc(by['productId'])}")))
            problem["replacedBy"] = by
        problems.append(problem)
    missing_qty = sum(p["ordered"] - p["onTruck"] for p in problems if p["kind"] != "over")
    contacts = client.get("contacts") or []
    others = len([l for l in order.get("lines") or [] if not l.get("substituteFor")]) - len(gaps)
    replaced = any(p["kind"] == "replaced" for p in problems)
    brief = {
        "outgoingCall": True,
        "order": {**pick(order, "id", "number", "deliveryDate"), "jour": jour(order.get("deliveryDate"))},
        "client": pick(client, "id", "name", "city", "salesRep"),
        "askFor": pick(contacts[0], "name", "role") if contacts else None,
        "truck": stops.get(order["id"]),
        "problems": problems,
        "rest": f"Les {others} autres lignes de la commande sont dans le camion, au poids habituel." if others > 0 else "",
        "invoice": "Seul ce qui est livré est facturé. "
        + (
            f"Avec le remplacement, {euros(abs(sum(p['amount'] for p in problems)))} de {'moins' if sum(p['amount'] for p in problems) <= 0 else 'plus'} que la commande d'origine."
            if replaced
            else f"{euros(abs(sum(p['amount'] for p in problems)))} de moins que prévu si on ne remplace rien."
        ),
        "substitution": rule,
        "substitutionRule": rule_text or "La fiche ne dit rien sur les substitutions : demande.",
        "missingKg": r2(missing_qty),
        "maxComplementKg": complement_cap(missing_qty),
        "alreadyAdded": [f"{o['number']} : " + ", ".join(f"{l['qty']:g} {l.get('unit', 'kg')} {l['productName']}" for l in o["lines"]) for o in done],
        "do": DO["replaced" if replaced else rule],
    }
    return {k: v for k, v in brief.items() if v not in (None, "", [])}


DO = {
    "replaced": "Le remplacement est DÉJÀ dans le camion (replacedBy) et la commande note son accord. Tu appelles pour qu'il l'entende avant la livraison, comme sa fiche le demande : après le fait, dis par quoi c'est remplacé (produit, quantité, prix au kilo) et demande si ça lui convient toujours. S'il veut l'étiquette, donne origine, calibre et lot de replacedBy. S'il n'en veut plus : take_off_truck, puis demande s'il veut autre chose à la place (otherOptions, avec add_to_truck après son oui).",
    "ok": "Sa fiche accepte un remplacement s'il est prévenu : après le fait, propose la PREMIÈRE option (produit, quantité, son prix au kilo), dans le camion de ce matin. Rien n'est ajouté sans son oui.",
    "refuse": "Sa fiche REFUSE les substitutions : ne propose AUCUN produit. Dis le fait, puis demande ce qu'il préfère (« on vous met autre chose, ou on laisse comme ça ? »). Les options ne servent que s'il demande lui-même ce qu'on a.",
    "ask": "Sa fiche ne dit rien : dis le fait, puis demande s'il veut qu'on lui mette autre chose à la place. Ne cite un produit que s'il dit oui ou demande ce qu'on a.",
}


async def add_complement(erp: ErpClient, order_id: str, lines: list[dict]) -> dict:
    """Puts a complement on today's truck for the client of `order_id`: a new order dated today, confirmed at once
    (the ERP attaches it to the day's route). Everything is checked here, in code:
      - the order is on a truck of this morning and something is really missing on it;
      - each product is in stock today for the quantity asked;
      - the complement weighs no more than what is missing plus a margin (see complement_cap: it repairs a delivery,
        it is not a way around the order deadline);
      - one complement per order (said twice, written once).
    `lines`: [{"productId", "qty"}]. → the confirmed order."""
    brief = await truck_brief(erp, order_id)
    if brief.get("alreadyAdded"):
        raise ValueError(f"Un complément est déjà dans le camion pour cette commande ({brief['alreadyAdded'][0]}). Ne l'ajoute pas une seconde fois.")
    short = [p for p in brief["problems"] if p["kind"] in ("missing", "short")]
    if not short:
        if any(p["kind"] == "replaced" for p in brief["problems"]):
            raise ValueError("Le produit manquant est déjà remplacé dans le camion : rien à ajouter. Si le client ne veut plus de ce remplacement, retire-le d'abord (take_off_truck).")
        raise ValueError("Rien ne manque sur cette commande : pas de complément à ajouter.")
    wanted = [(str(l["productId"]), float(l["qty"])) for l in lines if float(l.get("qty") or 0) > 0]
    if not wanted:
        raise ValueError("Aucune ligne : donne le produit et la quantité que le client a acceptés.")
    total = sum(q for _, q in wanted)
    if total > brief["maxComplementKg"] + 1e-6:
        raise ValueError(
            f"Trop pour un complément : il manque {brief.get('missingKg', 0):g} kg, le complément est limité à "
            f"{brief['maxComplementKg']:g} kg. Ce qu'il veut en plus, c'est une commande normale pour sa prochaine livraison."
        )
    today = brief["order"]["deliveryDate"]
    levels = await erp.get("/api/stock/availability", {"date": today, "productIds": ",".join(i for i, _ in wanted)})
    free = {l["productId"]: l.get("availableOn") or 0 for l in levels or []}
    for product_id, q in wanted:
        if free.get(product_id, 0) < q:
            raise ValueError(f"Pas assez de stock aujourd'hui pour {product_id} : {free.get(product_id, 0):g} disponible(s) pour {q:g} demandé(s). Propose autre chose.")
    names = ", ".join(p["productName"] for p in short)
    replaced = short[0]["productId"]
    body = {
        "clientId": brief["client"]["id"],
        "deliveryDate": today,
        "source": "voice_agent",
        "note": f"{COMPLEMENT_NOTE} du {jour(today)} — remplace {names} manquant sur {brief['order']['number']} (accord du client par téléphone avant départ)",
        "lines": [{"productId": i, "qty": q, "substituteFor": replaced} for i, q in wanted],
    }
    draft = await erp.post("/api/orders", body)
    try:
        order = await erp.post(f"/api/orders/{enc(draft['id'])}/confirm")
    except Exception:
        with suppress(Exception):  # do not leave a draft nobody asked for
            await erp.post(f"/api/orders/{enc(draft['id'])}/cancel")
        raise
    # The complement rides with the client's delivery: the time to say is the one of his stop, read again after the
    # write (the ERP recomputes the times of a run whenever an order joins it).
    truck = (await truck_stops(erp, today)).get(order_id) or brief.get("truck") or {}
    missing_amount = -sum(p["amount"] for p in short)
    _board_cache.clear()
    return {
        **pick(order, "id", "number", "status", "deliveryDate", "totalHt"),
        "client": brief["client"]["name"],
        "lines": [{"lineId": l["id"], **pick(l, "productId", "productName", "qty", "unit", "unitPrice")} for l in order["lines"]],
        "truck": pick(truck, "route", "driver", "departure", "etaSay"),
        "insteadOf": f"{names} ({euros(missing_amount)} non facturés)",
        "mustSay": [
            "Confirme en UNE phrase : produit, quantité, total, « dans le camion de ce matin », passage prévu "
            f"{truck.get('etaSay') or 'à l’heure habituelle'}. Puis demande s'il lui faut autre chose."
        ],
    }


async def take_off(erp: ErpClient, order_id: str, product_id: str) -> dict:
    """Takes a replacement back off today's truck because the client does not want it: the loaded quantity of that
    line goes to zero (the only change the ERP accepts on a prepared order), so it is neither delivered nor invoiced.
    Only a line the team added as a replacement (`substituteFor`): what the client ordered himself cannot be removed
    this way."""
    meta, order = await asyncio.gather(erp.get("/api/meta"), erp.get(f"/api/orders/{enc(order_id)}"))
    if order.get("deliveryDate") != meta["today"] or order.get("status") != "prepared":
        raise ValueError(f"La commande {order.get('number')} n'est pas dans un camion de ce matin.")
    line = next((l for l in order["lines"] if l["productId"] == product_id and l.get("substituteFor")), None)
    if not line:
        raise ValueError("Ce produit n'est pas un remplacement sur cette commande : seul un produit mis à la place d'un manquant peut être retiré ainsi.")
    if float(line.get("preparedQty") or 0) <= 0:
        raise ValueError("Ce remplacement est déjà retiré du camion.")
    note = "Retiré du camion à la demande du client (appel avant départ)"
    updated = await erp.patch(f"/api/orders/{enc(order_id)}/lines/{enc(line['id'])}", {"preparedQty": 0, "note": note})
    _board_cache.clear()
    return {
        **pick(updated, "id", "number", "status", "deliveryDate", "totalHt"),
        "removed": f"{float(line['preparedQty']):g} {line.get('unit', 'kg')} {line['productName']}",
        "lines": [{"lineId": l["id"], **pick(l, "productId", "productName", "qty", "unit"), "onTruck": l.get("preparedQty")} for l in updated["lines"]],
        "mustSay": ["Dis en une phrase que c'est retiré du camion et que ce ne sera pas facturé, puis demande s'il veut autre chose à la place."],
    }


# ───────────────────────── starting the call ─────────────────────────

# The rules of an outgoing call travel with the call (first message of the conversation), not in the system prompt:
# an ordinary incoming call runs on exactly the prompt it had before this feature existed.
OPENING_NOTE = """[Système : APPEL SORTANT. C'est TOI qui appelles ce client, avant le départ du camion de ce matin. Il vient de décrocher. Sa fiche (identify_caller) et le brief de l'appel (truck_call_brief) suivent. Pour cet appel, ces consignes passent avant les règles habituelles du premier tour et du prix :
1. Ta première réponse : « Bonjour Monsieur » ou « Bonjour Madame » avec son nom de famille (askFor) si tu le vouvoies, son prénom seul si sa fiche dit qu'on le tutoie, puis « c'est l'assistant de la maison {company} », puis le fait tout de suite, en une phrase : ce qui manque sur sa livraison de ce matin, la quantité, et pourquoi en quelques mots simples (why). Cette phrase contient toujours le mot « désolé » (« désolé, il manque… »), et c'est le seul de l'appel. Pas de « comment allez-vous », pas de numéro de commande, pas de liste.
2. Dans la même réponse, une dernière phrase : ce que dit `do` du brief, à la lettre (c'est SA règle de substitution). Si tu proposes un produit, dis le produit, la quantité, son prix au kilo, et que ça part dans le camion de ce matin, puis demande si ça lui va.
3. Rien ne s'ajoute sans son oui. Après son oui sur le produit et la quantité : add_to_truck (jamais create_draft_order pour aujourd'hui), puis dis le total et l'heure de passage prévue (etaSay : une prévision, dis « prévu vers »).
4. Ne dis rien qui ne soit pas dans le brief ou dans sa fiche. S'il demande le lot, l'origine, la date limite ou le calibre du remplacement : c'est dans l'option, réponds précisément. Ce qui n'y est pas (quelle bête, qui a préparé), tu ne le sais pas et tu le dis.
5. S'il veut le produit d'origine plus tard : dis ce que dit backInStock, sans promettre de date, et rien de plus. Ne propose pas de toi-même de prendre une commande ; s'il en demande une pour sa prochaine livraison, prends-la avec les outils habituels.
6. Aucune remise, aucun avoir, aucun geste commercial : seul ce qui est livré est facturé (invoice). Ne promets un rappel de son commercial QUE s'il réclame un geste ou demande à parler à quelqu'un, et enregistre-le alors (log_client_event). Une simple plainte s'enregistre sans rien promettre.
7. Si la personne qui a décroché n'est pas celle qui décide (commis, plongeur, « le chef n'est pas là ») : n'ajoute et ne retire rien, même si elle dit oui. Dis en une phrase ce qui manque pour qu'elle le transmette, demande à quelle heure rappeler, et enregistre-le avec log_client_event (type call, titre qui commence par « À rappeler : »). L'appel reste à faire.
   S'il ne veut rien (c'est bien lui, et il dit non) : le reste part normalement. Remercie en une phrase et termine, n'écris rien.
8. Il est très tôt et il n'a rien demandé : sois bref et concret, jamais commercial. Une question à la fois.]"""


@dataclass
class Opening:
    """What an outgoing call starts with: the line shown on the page, the conversation as the model finds it (the
    client has just picked up; his file and the brief are already there, as if the agent had fetched them), and the
    two tool results for the page's cards."""

    label: str
    messages: list[ChatMessage]
    tools: list[tuple[str, dict, dict]] = field(default_factory=list)  # (tool name, arguments, result)


async def opening(erp: ErpClient, order_id: str) -> Opening:
    from app.tools.desk import client_card  # (imported here: tools/truck.py imports this module)

    brief, meta = await asyncio.gather(truck_brief(erp, order_id), erp.get("/api/meta"))
    client_id = brief["client"]["id"]
    card = {"status": "found", "client": await client_card(erp, client_id), "how": "Appel sortant : c'est nous qui appelons ce client, à son numéro."}
    calls = [
        ToolCall(id=f"out_{uuid.uuid4().hex[:16]}", name="identify_caller", arguments={"said": brief["client"]["name"], "clientId": client_id}),
        ToolCall(id=f"out_{uuid.uuid4().hex[:16]}", name="truck_call_brief", arguments={"orderId": order_id}),
    ]
    results = [card, brief]
    note = OPENING_NOTE.format(company=meta.get("company") or "votre grossiste")
    messages = [
        ChatMessage(role="user", content=f"Allô ?\n\n{note}"),
        ChatMessage(role="assistant", content="", tool_calls=calls),
        *(ChatMessage(role="tool", tool_call_id=c.id, name=c.name, content=json.dumps(r, ensure_ascii=False, separators=(",", ":"))) for c, r in zip(calls, results)),
    ]
    who = (brief.get("askFor") or {}).get("name")
    what = ", ".join(f"{p['productName']} {KIND_LABEL[p['kind']]}" for p in brief["problems"])
    label = f"Appel sortant → {brief['client']['name']}" + (f" ({who})" if who else "") + f" · {what}"
    return Opening(label=label, messages=messages, tools=[(c.name, c.arguments, r) for c, r in zip(calls, results)])


# ───────────────────────── the board (for the page) ─────────────────────────

_board_cache: dict[str, tuple[float, dict]] = {}
BOARD_TTL_S = 3.0  # the page polls: one reading of the day serves the polls of the next seconds


async def truck_board(erp: ErpClient) -> dict:
    """The morning's check: every weighed order of the day, the calls to make, the gaps left alone, what was settled."""
    hit = _board_cache.get("board")
    if hit and time.monotonic() - hit[0] < BOARD_TTL_S:
        return hit[1]
    meta = await erp.get("/api/meta")
    today = meta["today"]
    orders, stops = await asyncio.gather(day_orders(erp, today), truck_stops(erp, today))
    calls, tolerated, lines = [], [], 0
    for o in orders:
        if str(o.get("note") or "").startswith(COMPLEMENT_NOTE):
            continue  # our own complements are not deliveries to check
        lines += len(o.get("lines") or [])
        gaps = order_gaps(o)
        client = o.get("client") or {}
        for g in gaps:
            if not g["call"]:
                tolerated.append(
                    {
                        "orderId": o["id"],
                        "orderNumber": o["number"],
                        "clientName": client.get("name"),
                        **pick(g, "productName", "ordered", "onTruck", "unit", "gapPct", "amount"),
                        "why": "écart de pesée normal : la viande est facturée au poids réel, on ne réveille pas un client pour ça",
                    }
                )
        gaps = [g for g in gaps if g["call"]]
        if not gaps:
            continue
        rule, rule_text = substitution_rule(client.get("preferences"))
        contacts = client.get("contacts") or []
        (report, issue), added = await asyncio.gather(call_events(erp, client["id"], o["id"], today), complements(erp, client["id"], today))
        recovered = r2(sum(float(c.get("totalHt") or 0) for c in added))
        calls.append(
            {
                "orderId": o["id"],
                "orderNumber": o["number"],
                "clientId": client.get("id"),
                "clientName": client.get("name"),
                "city": client.get("city"),
                "contact": pick(contacts[0], "name", "role", "phone") if contacts else None,
                "truck": stops.get(o["id"]),
                "problems": [{k: v for k, v in g.items() if k != "call"} for g in gaps],
                "amount": r2(sum(g["amount"] for g in gaps)),
                "substitution": rule,
                "substitutionRule": rule_text,
                "openIssue": pick(issue, "id", "title", "description") if issue else None,
                # done = the client himself was told. A call that only reached someone who cannot decide is still to make.
                "status": "done" if report and NOT_REACHED_TAG not in (report.get("tags") or []) else "to_call",
                "lastAttempt": report.get("title") if report and NOT_REACHED_TAG in (report.get("tags") or []) else None,
                "followUp": bool(report and report.get("status") == "open"),  # called, but a human still has something to do
                "outcome": pick(report, "id", "title", "description", "status") if report else None,
                "complements": [pick(c, "id", "number", "totalHt") | {"lines": [f"{l['qty']:g} {l.get('unit', 'kg')} {l['productName']}" for l in c["lines"]]} for c in added],
                "recovered": recovered,
                "startWith": f"/appel {o['id']}",  # typed (or sent by the page) on WS /voice: the agent calls this client
            }
        )
    calls.sort(key=lambda c: ((c["truck"] or {}).get("departure") or "99", (c["truck"] or {}).get("eta") or "99"))
    board = {
        "today": today,
        "checked": {"orders": len(orders), "lines": lines},
        "calls": calls,
        "tolerated": tolerated,
        # euros that will not be delivered nor invoiced if nobody calls (a product already replaced is not at stake)
        "atStake": r2(-sum(p["amount"] for c in calls for p in c["problems"] if p["kind"] in ("missing", "short"))),
        "recovered": r2(sum(c["recovered"] for c in calls)),
        "toCall": sum(c["status"] == "to_call" for c in calls),
    }
    _board_cache["board"] = (time.monotonic(), board)
    return board
