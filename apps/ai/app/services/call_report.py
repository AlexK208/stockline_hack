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

from app.schemas import ChatMessage
from app.tools.erp import ErpClient, enc
from app.tools.history import without_none

ORDER_TOOLS = {
    "create_draft_order", "add_order_line", "update_order_line", "remove_order_line", "update_order", "confirm_order", "cancel_order",
}  # fmt: skip
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

    orders: dict[str, dict] = {}  # order id → the order as the last tool left it
    refused: list[str] = []
    logged: list[str] = []
    questions: list[str] = []
    other_client = False
    turns = 0
    for m in history[start:]:
        if m.role == "user":
            turns += 1
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
            elif call.name in ORDER_TOOLS:
                if r.get("number"):
                    orders[r.get("id") or r["number"]] = r
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


async def write_report(erp: ErpClient, history: list[ChatMessage], start: int = 0) -> dict | None:
    """Posts the report to the client's history. → the created event, or None when there was nothing to report."""
    report = build_report(history, start)
    if not report:
        return None
    return await erp.post(f"/api/clients/{enc(report['clientId'])}/events", report["body"])
