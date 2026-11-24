"""
« Qui est servi d'abord » : when part of a lot survives the night, who gets their meat (lane D).

The night inventory writes off most of a lot and, say, 20 kg are left for six clients who ordered 67. Somebody has to
decide who gets what. This module PROPOSES, in code from the ERP (no model), and a PERSON approves before anything is
written:

    propose(erp, product_id, available)        → two plans side by side, each line with its reason in words:
        priority   who is served first, in full, until the stock runs out
        prorata    everyone gets the same share of what is left
      and what each plan costs: clients served in full, calls to make, € not delivered.
    apply(erp, product_id, available, mode)    → writes the approved plan: the stock written down to `available`, then
                                                 each line's prepared (loaded) quantity, with the reason in its note.

Then the « avant le camion » board (services/truck_calls.py) picks the loaded quantities up by itself: kinds `missing`
and `short`, each client's own substitution rule, options from real stock. Nothing in the agent changes.

Priority order, each rule read from the data:
    1. the client's file REFUSES substitutions: he cannot be compensated with another cut, so he goes first;
    2. the EARLIEST truck departure: the 04:45 truck cannot wait for a decision;
    3. the REGULARS of this product (usual basket: average quantity × share of his orders that hold it);
    then the order number, so the plan is the same every time it is computed.
"""

import asyncio
from typing import Literal

from app.services.truck_calls import day_orders, gather_limited, line_gap, substitution_rule, truck_stops
from app.tools.erp import ErpClient, enc

Mode = Literal["priority", "prorata"]
MODES: tuple[Mode, ...] = ("priority", "prorata")


def r2(x: float) -> float:
    return round(x + 0.0, 2)


def fr(x: float) -> str:
    return f"{x:g}".replace(".", ",")


async def _claims(erp: ErpClient, product_id: str) -> tuple[str, dict, list[dict]]:
    """Today's prepared lines of this product (not replacement lines), with what the priority rules need to know."""
    meta = await erp.get("/api/meta")
    today = meta["today"][:10]
    orders, stops, product = await asyncio.gather(day_orders(erp, today), truck_stops(erp, today), erp.get(f"/api/products/{enc(product_id)}"))
    lines = [(o, l) for o in orders for l in o.get("lines") or [] if l.get("productId") == product_id and not l.get("substituteFor") and float(l.get("qty") or 0) > 0]
    client_ids = sorted({o["clientId"] for o, _ in lines})
    cards = await gather_limited([erp.get(f"/api/clients/{enc(c)}") for c in client_ids])
    usuals = await gather_limited([erp.get(f"/api/clients/{enc(c)}/usual") for c in client_ids])
    by_client = {c: (card, usual) for c, card, usual in zip(client_ids, cards, usuals)}

    claims = []
    for o, l in lines:
        card, usual = by_client[o["clientId"]]
        rule, rule_text = substitution_rule(card.get("preferences"))
        habit = next((u for u in usual or [] if u.get("productId") == product_id), None)
        truck = stops.get(o["id"]) or {}
        claims.append({
            "orderId": o["id"],
            "orderNumber": o.get("number"),
            "lineId": l["id"],
            "lineNote": l.get("note"),
            "clientId": o["clientId"],
            "clientName": card.get("name") or o.get("clientName"),
            "ordered": float(l["qty"]),
            "unit": l.get("unit") or product.get("unit"),
            "unitPrice": float(l.get("unitPrice") or 0),
            "substitution": rule,
            "substitutionRule": rule_text,
            "departure": truck.get("departure"),
            "route": truck.get("route"),
            "habit": r2(float(habit["avgQty"]) * float(habit["frequency"])) if habit else 0.0,
            "habitText": (f"habitué : {fr(round(habit['avgQty'], 1))} {product.get('unit', 'kg')} en moyenne, dans {round(habit['frequency'] * 100)} % de ses commandes" if habit else "pas un habitué de ce produit"),
        })
    claims.sort(key=lambda c: (c["substitution"] != "refuse", c["departure"] or "99:99", -c["habit"], c["orderNumber"] or ""))
    return today, product, claims


def _why_first(c: dict) -> str:
    parts = []
    if c["substitution"] == "refuse":
        parts.append("refuse les substitutions : on ne peut pas le dépanner avec une autre pièce")
    if c["departure"]:
        parts.append(f"camion de {c['departure']}" + (f" ({c['route']})" if c["route"] else ""))
    parts.append(c["habitText"])
    return " ; ".join(parts)


def _plan(claims: list[dict], available: float, mode: Mode) -> list[dict]:
    total = sum(c["ordered"] for c in claims)
    left = available
    out = []
    for rank, c in enumerate(claims, start=1):
        if mode == "priority":
            give = r2(min(c["ordered"], max(left, 0.0)))
        else:
            give = r2(min(c["ordered"], c["ordered"] * available / total)) if total else 0.0
        give = min(give, r2(max(left, 0.0)))  # rounding never hands out more than is there
        left = r2(left - give)
        if give >= c["ordered"]:
            outcome = "servi en entier"
        elif give > 0:
            outcome = f"servi en partie : {fr(give)} sur {fr(c['ordered'])} {c['unit']}"
        else:
            outcome = "rien : le stock est parti avant lui"
        if mode == "priority":
            reason = f"n° {rank} : {_why_first(c)} → {outcome}"
        else:
            reason = f"même part pour tous ({round(available / total * 100) if total else 0} % de la commande) → {outcome}"
        gap = line_gap({**c, "productId": "", "qty": c["ordered"], "preparedQty": give})
        out.append({
            **{k: c[k] for k in ("orderId", "orderNumber", "lineId", "lineNote", "clientId", "clientName", "ordered", "unit", "unitPrice", "substitution", "substitutionRule", "departure", "route")},
            "rank": rank,
            "loaded": give,
            "missing": r2(c["ordered"] - give),
            "notDelivered": r2((c["ordered"] - give) * c["unitPrice"]),
            "outcome": outcome,
            "reason": reason,
            "call": bool(gap and gap["call"]),  # the truck board's own rule (5 % and 15 €, or absent)
        })
    return out


def _summary(lines: list[dict]) -> dict:
    return {
        "fullyServed": sum(1 for l in lines if l["missing"] <= 0),
        "partly": sum(1 for l in lines if 0 < l["loaded"] < l["ordered"]),
        "nothing": sum(1 for l in lines if l["loaded"] <= 0),
        "toCall": sum(1 for l in lines if l["call"]),
        "notDelivered": r2(sum(l["notDelivered"] for l in lines)),
    }


async def propose(erp: ErpClient, product_id: str, available: float) -> dict:
    """Both plans for what is left of `product_id` (kg or the product's unit). Read-only."""
    if available < 0:
        raise ValueError("la quantité disponible ne peut pas être négative")
    today, product, claims = await _claims(erp, product_id)
    ordered = r2(sum(c["ordered"] for c in claims))
    plans = {}
    for mode in MODES:
        lines = _plan(claims, min(available, ordered), mode)
        plans[mode] = {"lines": lines, **_summary(lines)}
    return {
        "today": today,
        "productId": product_id,
        "productName": product.get("name"),
        "unit": product.get("unit"),
        "onHand": float(product.get("onHand") or 0),
        "available": available,
        "ordered": ordered,
        "clients": len(claims),
        "rules": [
            "1. refuse les substitutions d'abord (pas de dépannage possible avec une autre pièce)",
            "2. puis le camion qui part le plus tôt",
            "3. puis les habitués de ce produit",
        ],
        "plans": plans,
        "recommended": "priority",
    }


async def apply(erp: ErpClient, product_id: str, available: float, mode: Mode = "priority", why: str = "") -> dict:
    """Writes the approved plan, recomputed here from the ERP (the page never sends quantities). Called only after a
    person has seen the plan: the HTTP route and `make chaos … --apply` are the two ways in."""
    if mode not in MODES:
        raise ValueError(f"mode inconnu : {mode}")
    proposal = await propose(erp, product_id, available)
    on_hand = proposal["onHand"]
    if available > on_hand:
        raise ValueError(f"il n'y a que {fr(on_hand)} {proposal['unit']} en stock, pas {fr(available)}")
    if on_hand - available > 0:
        await erp.post("/api/stock/adjust", {"productId": product_id, "qty": -r2(on_hand - available), "reason": "adjustment", "note": why or "Lot écarté cette nuit"})
    plan = proposal["plans"][mode]
    for l in plan["lines"]:
        note = f"Répartition du stock restant : {l['reason']}"
        if l.get("lineNote"):  # keep what was already written on the line (client instructions, « client prévenu »…)
            note = f"{l['lineNote']} · {note}"
        await erp.patch(f"/api/orders/{enc(l['orderId'])}/lines/{enc(l['lineId'])}", {"preparedQty": l["loaded"], "note": note})
    return {"applied": mode, **{k: proposal[k] for k in ("productId", "productName", "unit", "available", "ordered", "clients")}, **plan}
