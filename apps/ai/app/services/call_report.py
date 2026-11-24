"""
Call report: what happened during a phone call, written to the client's history when the call ends.

Built in code from the tool calls of the conversation (no model, no cost, nothing invented): the orders as they
ended up, what was refused and why, what was logged for the team. A salesperson who opens the client's history,
or the "to call back" list, sees in ten seconds what the agent did, and what it left for a human:
an order still in draft because the caller hung up before saying yes is the first thing to follow up.

    build_report(history)  → {"clientId", "body"} or None when there is nothing worth a report
    write_report(erp, history, start) → posts it as a client event (type "call")
"""

import json
import re

from app.schemas import ChatMessage
from app.tools.erp import ErpClient, enc
from app.tools.history import without_none

ORDER_TOOLS = {
    "create_draft_order", "add_order_line", "update_order_line", "remove_order_line", "update_order", "confirm_order", "cancel_order",
    "add_to_truck", "take_offer",
}  # fmt: skip
OFFER_TAG = "offre-date-courte"  # outgoing call that offers short-dated stock (services/short_dated.py reads it back)
TRUCK_TAG = "appel-camion"  # outgoing call before the truck leaves (services/truck_calls.py reads it back for the board)
NOT_REACHED_TAG = "a-rappeler"  # … where the person who decides was not on the line: the call is still to make

# The person who picked up says, in his own words, that he is not the one who decides. Read in code from what was
# heard, like the yes before a confirmation: in a replay (Claudio's R4) a commis answered « le chef arrive à sept
# heures », the agent rightly wrote nothing, and the report still said « client prévenu », resolved.
ABSENT = re.compile(
    r"\b(il|elle|le chef|la cheffe|le patron|la patronne|monsieur \w+|madame \w+) (n'|n )?est pas (encore )?(là|la|arrivée?|dispo\w*|joignable)\b"
    r"|\b(le chef|la cheffe|le patron|la patronne) (arrive|revient|sera là|est absente?|dort)\b"
    r"|\bpas encore (là|arrivée?)\b"
    r"|\bc'?est pas (lui|elle|moi qui)\b"
    r"|\bje (ne )?suis (pas le|pas la|que le|que la|qu'un|qu'une|le|la|un|une) (chef|cheffe|patron|patronne|commis|plongeur|plongeuse|second|seconde|serveur|serveuse|apprentie?|stagiaire)\b"
    r"|\bc'?est (le|la) (commis|plongeur|plongeuse|serveur|serveuse|apprentie?|stagiaire)\b"
    r"|\brappele[zr] (plus tard|tout à l'heure|vers|à|dans|après)\b",
    re.I,
)
TO_CALL_BACK = re.compile(r"à rappeler|a rappeler|absente?\b|pas (là|joint|joignable)|non joint", re.I)  # the agent's own note


def decider_absent(heard: list[str], contact: str | None, logged: list[str]) -> bool:
    """True when the outgoing call reached someone who cannot decide: he said so, or the agent wrote it down."""
    first = (contact or "").split()[0] if contact else ""
    not_him = re.compile(rf"\bc'?est pas {re.escape(first)}\b", re.I) if first else None
    said = any(ABSENT.search(h) or (not_him and not_him.search(h)) for h in heard)
    return bool(said or any(TO_CALL_BACK.search(t) for t in logged))
QUESTION_TOOLS = {"check_products": "stock ou délai", "get_price": "prix", "order_history": "livraison passée"}
STATUS = {"draft": "en brouillon", "confirmed": "confirmée", "cancelled": "annulée", "prepared": "préparée"}
WEEKDAYS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]


def day(iso: str | None) -> str:
    """ "2026-11-26" → "jeudi 26/11"."""
    from datetime import date

    try:
        d = date.fromisoformat((iso or "")[:10])
    except ValueError:
        return iso or "?"
    return f"{WEEKDAYS[d.weekday()]} {d.day:02d}/{d.month:02d}"


def qty(value) -> str:
    try:
        return f"{float(value):g}".replace(".", ",")
    except (TypeError, ValueError):
        return str(value)


def money(value) -> str:
    try:
        return f"{float(value):.2f} €".replace(".", ",")
    except (TypeError, ValueError):
        return f"{value} €"


def parsed(content: str | None):
    try:
        return json.loads(content or "")
    except ValueError:
        return None


def build_report(history: list[ChatMessage], start: int = 0) -> dict | None:
    """The report of the turns from `start` on (the caller is looked up in the whole history).
    None when no client was identified or when those turns hold nothing a salesperson needs to read."""
    results = {m.tool_call_id: m for m in history if m.role == "tool"}
    client: dict = {}
    for m in history:
        if m.role == "tool" and m.name == "identify_caller":
            r = parsed(m.content)
            if isinstance(r, dict) and r.get("status") == "found":
                client = r.get("client") or {}
    if not client.get("id"):
        return None

    brief: dict = {}  # outgoing call « avant le camion »: the facts the agent called about
    offer: dict = {}  # outgoing call « date courte »: the offer the agent called about
    for m in history:
        if m.role == "tool" and m.name in ("truck_call_brief", "short_date_brief"):
            r = parsed(m.content)
            if isinstance(r, dict) and r.get("outgoingCall"):
                brief, offer = (r, {}) if m.name == "truck_call_brief" else ({}, r)

    orders: dict[str, dict] = {}  # order id → the order as the last tool left it
    complements: list[dict] = []  # what add_to_truck put on today's truck
    taken: list[dict] = []  # what take_offer wrote (short-dated offer accepted)
    removed: list[str] = []  # replacements take_off_truck took back off the truck
    refused: list[str] = []
    logged: list[str] = []
    questions: list[str] = []
    other_client = False
    turns = 0
    heard: list[str] = []  # the caller's own sentences, without the notes added for the model
    for m in history[start:]:
        if m.role == "user":
            turns += 1
            heard.append((m.content or "").split("\n\n[Système", 1)[0])
        if m.role != "assistant":
            continue
        for call in m.tool_calls or []:
            res = results.get(call.id)
            r = parsed(res.content) if res else None
            if not isinstance(r, dict):
                r = {}
            err = str(r.get("error") or "")
            if "Refusé : pendant un appel" in err:
                other_client = True
            elif err.startswith("Refusé"):
                pass  # the agent tried a tool before knowing the caller: internal, not for the report
            elif call.name == "take_off_truck":
                if r.get("removed"):
                    removed.append(str(r["removed"]))
            elif call.name in ORDER_TOOLS:
                if r.get("number"):
                    orders[r.get("id") or r["number"]] = r
                    if call.name == "add_to_truck":
                        complements.append(r)
                    if call.name == "take_offer":
                        taken.append(r)
                for p in r.get("problems") or []:
                    if p not in refused:
                        refused.append(p)
                if err and "Compte bloqué" not in err and err[:140] not in refused:
                    refused.append(err[:140])
            elif call.name == "log_client_event" and not r.get("error"):
                logged.append(str((call.arguments or {}).get("title") or r.get("title") or "événement"))
            elif call.name in QUESTION_TOOLS and QUESTION_TOOLS[call.name] not in questions:
                questions.append(QUESTION_TOOLS[call.name])

    blocked = bool(client.get("BLOCKED"))
    if offer:
        return offer_report(client, offer, taken, orders, logged, turns, heard[1:])
    if brief:
        return truck_report(client, brief, orders, complements, removed, refused, logged, turns, heard[1:])
    if not (orders or refused or other_client):
        return None  # only questions, or events the agent already logged itself: nothing to add

    live = [o for o in orders.values() if o.get("status") != "cancelled"]
    drafts = [o for o in live if o.get("status") == "draft"]
    lines = [f"Appel traité par l'agent vocal, {turns} tour(s) de parole."]
    for o in orders.values():
        what = ", ".join(f"{qty(l.get('qty'))} {l.get('unit') or ''} {l.get('productName') or l.get('productId')}".replace("  ", " ") for l in o.get("lines") or [])
        lines.append(f"- Commande {o['number']} {STATUS.get(o.get('status'), o.get('status'))} pour {day(o.get('deliveryDate'))} : {what or 'aucune ligne'}.")
    if drafts:
        lines.append("- ⚠ Restée en brouillon à la fin de l'appel (pas d'accord explicite du client) : à rappeler pour valider.")
    if refused:
        lines.append("- Non servi ou refusé pendant l'appel : " + " ; ".join(refused[:6]) + ".")
    if blocked:
        lines.append("- Compte bloqué : aucune commande prise.")
    if other_client:
        lines.append("- A demandé des informations ou une action sur un autre client : refusé (confidentialité).")
    if logged:
        lines.append("- Noté pour l'équipe : " + " ; ".join(logged[:6]) + ".")
    if questions:
        lines.append("- Questions posées : " + ", ".join(questions) + ".")

    if drafts:
        title = f"Appel : commande à valider pour {day(drafts[0].get('deliveryDate'))} (brouillon)"
    elif live:
        title = f"Appel : commande {STATUS.get(live[0].get('status'), '')} pour {day(live[0].get('deliveryDate'))}".replace("  ", " ")
        if len(live) > 1:
            title = f"Appel : {len(live)} commandes, dont {day(live[0].get('deliveryDate'))}"
    elif orders:
        title = "Appel : commande annulée"
    else:
        title = "Appel sans commande : demande non servie"
    needs_follow_up = bool(drafts or (refused and not live) or other_client)
    first = next(iter(live or orders.values()), None)
    body = {
        "type": "call",
        "title": title,
        "description": "\n".join(lines),
        "severity": "medium" if needs_follow_up else "low",
        "status": "open" if needs_follow_up else "resolved",
        "tags": ["compte-rendu", "agent-vocal"],
        "orderId": first.get("id") if first else None,
    }
    return {"clientId": client["id"], "body": without_none(body)}


def order_line(o: dict) -> str:
    return ", ".join(f"{qty(l.get('qty'))} {l.get('unit') or ''} {l.get('productName') or l.get('productId')}".replace("  ", " ") for l in o.get("lines") or [])


def truck_report(
    client: dict, brief: dict, orders: dict, complements: list[dict], removed: list[str], refused: list[str], logged: list[str], turns: int,
    heard: list[str] | None = None,
) -> dict | None:  # fmt: skip
    """The report of an outgoing call before the truck leaves, attached to the order the call was about. Written as
    soon as the client has answered, whatever he decided: the point of the call is that he was told."""
    problems = brief.get("problems") or []
    what = ", ".join(str(p.get("productName")) for p in problems) or "écart sur la livraison"
    replaced = [p["replacedBy"] for p in problems if p.get("kind") == "replaced" and p.get("replacedBy")]
    order = brief.get("order") or {}
    truck = brief.get("truck") or {}
    answered = turns >= 2  # the first "turn" is the client picking up
    if not answered:
        return None  # he never said a word (the call was started twice, or cut at once): nothing happened, the call is still to make
    later = [o for o in orders.values() if o not in complements and o.get("status") != "cancelled"]
    drafts = [o for o in later if o.get("status") == "draft"]
    # Nothing decided on the truck and the person on the line was not the one who decides: the client was NOT told.
    absent = not complements and not removed and decider_absent(heard or [], (brief.get("askFor") or {}).get("name"), logged)
    kinds = {p.get("kind") for p in problems}
    state = "remplacé" if replaced and not removed else "en poids court" if kinds == {"short"} else "manquant"

    def gap(p: dict) -> str:
        text = f"{p.get('productName')} : {qty(p.get('ordered'))} {p.get('unit') or 'kg'} commandés, {qty(p.get('onTruck'))} dans le camion"
        if p.get("replacedBy"):
            by = p["replacedBy"]
            text += f", remplacé par {qty(by.get('qty'))} {by.get('unit') or 'kg'} {by.get('productName')}"
        return text + (f" ({p['why']})" if p.get("why") else "")

    lines = [
        f"Appel SORTANT de l'agent vocal avant le départ du camion ({truck.get('route') or 'tournée du jour'}, départ {truck.get('departure') or '?'}).",
        f"- Motif : {' ; '.join(gap(p) for p in problems)}. Commande {order.get('number')}.",
    ]
    if removed:
        lines.append(f"- Le client ne veut pas du remplacement : {', '.join(removed)} retiré(s) du camion, non facturé(s).")
    for c in complements:
        lines.append(f"- Accord du client : complément {c.get('number')} ajouté au camion de ce matin : {order_line(c)} ({money(c.get('totalHt'))} HT).")
    if complements:
        outcome = f"remplacé par {order_line(complements[0])}"
    elif removed:
        outcome = "remplacement refusé par le client, retiré du camion"
    elif absent:
        who = (brief.get("askFor") or {}).get("name") or "la personne qui décide"
        lines.append(f"- ⚠ {who} n'était pas en ligne : le message a été laissé à la personne qui a décroché, rien n'a été décidé. À RAPPELER avant le départ du camion.")
        outcome = f"{who} non joint, message laissé : à rappeler"
    elif replaced:
        lines.append("- Client prévenu du remplacement, qui reste dans le camion.")
        outcome = f"client prévenu, garde {qty(replaced[0].get('qty'))} {replaced[0].get('unit') or 'kg'} {replaced[0].get('productName')}"
    else:
        lines.append("- Client prévenu. Pas de remplacement dans le camion de ce matin : seul ce qui est livré sera facturé.")
        outcome = "client prévenu, pas de remplacement"
    for o in later:
        lines.append(f"- Commande {o.get('number')} {STATUS.get(o.get('status'), o.get('status'))} pour {day(o.get('deliveryDate'))} : {order_line(o) or 'aucune ligne'}.")
    if drafts:
        lines.append("- ⚠ Restée en brouillon à la fin de l'appel : à rappeler pour valider.")
    if refused:
        lines.append("- Refusé pendant l'appel : " + " ; ".join(refused[:4]) + ".")
    if logged:
        lines.append("- Noté pour l'équipe : " + " ; ".join(logged[:6]) + ".")
    # Something the agent wrote down for the team and no decision on the truck (« le chef n'est pas là », « il veut
    # un geste ») : a human still has something to do, the report stays open and so does the ERP's own issue.
    follow_up = bool(drafts or absent or (logged and not complements and not removed))
    body = {
        "type": "call",
        "title": f"Appel avant camion : {what} {state} — {outcome}",
        "description": "\n".join(lines),
        "severity": "high" if absent else "medium" if follow_up else "low",
        "status": "open" if follow_up else "resolved",
        "tags": ["compte-rendu", "agent-vocal", TRUCK_TAG, *([NOT_REACHED_TAG] if absent else [])],
        "orderId": order.get("id"),
    }
    return {"clientId": client["id"], "body": without_none(body), "settles": None if follow_up else order.get("id")}


def offer_report(client: dict, offer: dict, taken: list[dict], orders: dict, logged: list[str], turns: int, heard: list[str]) -> dict | None:
    """The report of an outgoing call that offered short-dated stock: what was offered, at which approved price, and
    what the client decided. Nothing when he never said a word (the call is still to make)."""
    if turns < 2:
        return None
    product = offer.get("product") or {}
    price = (offer.get("offer") or {}).get("pricePerUnit")
    absent = not taken and decider_absent(heard, (offer.get("askFor") or {}).get("name"), logged)
    lines = [
        "Appel SORTANT de l'agent vocal : offre date courte.",
        f"- Offre : {product.get('name')}, à consommer {product.get('useBySay')}, à {money(price)} par {product.get('unit') or 'kg'} (prix approuvé par l'équipe).",
    ]
    if taken:
        t = taken[0]
        lines.append(f"- Accord du client : {t.get('offerLine')}, sur la commande {t.get('number')} ({STATUS.get(t.get('status'), t.get('status'))}) pour {day(t.get('deliveryDate'))}.")
        took = next((l for l in t.get("lines") or [] if l.get("productId") == product.get("id")), {})
        outcome = f"{qty(took.get('qty'))} {product.get('unit') or 'kg'} pris à {money(price)} pour {day(t.get('deliveryDate'))}"
    elif absent:
        lines.append("- ⚠ La personne qui décide n'était pas en ligne : rien n'a été écrit. À rappeler si l'offre tient encore.")
        outcome = "personne qui décide non jointe : à rappeler"
    else:
        lines.append("- Le client ne prend pas l'offre. Rien n'a été écrit.")
        outcome = "refusée par le client"
    others = [o for o in orders.values() if o not in taken and o.get("status") != "cancelled"]
    for o in others:
        lines.append(f"- Commande {o.get('number')} {STATUS.get(o.get('status'), o.get('status'))} pour {day(o.get('deliveryDate'))} : {order_line(o) or 'aucune ligne'}.")
    if logged:
        lines.append("- Noté pour l'équipe : " + " ; ".join(logged[:6]) + ".")
    body = {
        "type": "call",
        "title": f"Offre date courte : {product.get('name')} — {outcome}",
        "description": "\n".join(lines),
        "severity": "medium" if absent else "low",
        "status": "open" if absent else "resolved",
        "tags": ["compte-rendu", "agent-vocal", OFFER_TAG, *([NOT_REACHED_TAG] if absent else [])],
        "orderId": taken[0].get("id") if taken else None,
    }
    return {"clientId": client["id"], "body": without_none(body)}


async def close_open_issue(erp: ErpClient, client_id: str, order_id: str, outcome: str) -> None:
    """The ERP held an open issue about this order (« il faut le prévenir avant le départ du camion »): the call did
    exactly that, so the issue is closed with what was decided. Only issues about this very order, opened today."""
    events = await erp.get(f"/api/clients/{enc(client_id)}/events", {"status": "open", "limit": 12})
    events = events.get("items", events) if isinstance(events, dict) else events
    for e in events or []:
        if e.get("orderId") == order_id and NOT_REACHED_TAG in (e.get("tags") or []):
            # an earlier attempt that only reached the commis: the client has now been told himself
            await erp.patch(f"/api/client-events/{enc(e['id'])}", {"status": "resolved"})
            continue
        if e.get("channel") == "voice_agent":
            continue  # what the agent logged itself during the call (« il demande un geste ») stays open for the team
        if e.get("orderId") == order_id and e.get("type") in ("complaint", "delivery_issue", "quality_issue"):
            await erp.patch(
                f"/api/client-events/{enc(e['id'])}",
                {"status": "resolved", "description": f"{e.get('description') or ''}\n\n→ Traité par l'agent vocal avant le départ du camion : {outcome}".strip()},
            )


async def write_report(erp: ErpClient, history: list[ChatMessage], start: int = 0) -> dict | None:
    """Posts the report to the client's history. → the created event, or None when there was nothing to report."""
    report = build_report(history, start)
    if not report:
        return None
    event = await erp.post(f"/api/clients/{enc(report['clientId'])}/events", report["body"])
    if report.get("settles"):
        try:
            await close_open_issue(erp, report["clientId"], report["settles"], report["body"]["title"].split(" — ", 1)[-1])
        except Exception:
            pass  # the report is written: a leftover open issue is only one more line on the to-do list
    return event
