"""
What the voice session does in CODE around the model, to cut dead air and model round-trips:

    choose_ack        a one- or two-word acknowledgement spoken the instant the caller stops ("Bonjour Christian.",
                      "Alors…"), from the live transcript: no model, no tool. It is only a courtesy
                      sound: it never states a fact, so it cannot be wrong about the order.
    (The caller is also identified in code before the model runs: that lives in the agent loop, agent/loop.py,
    with tools/desk.py prefetch_identify, so the text chat and the test runner get it too.)

Best effort: any doubt (two plausible clients, ERP slow) → say a plain "Bonjour." and let the model do the rest.
"""

import asyncio
import re

from app.tools import ErpClient
from app.tools import desk

GREETED = re.compile(r"\b(bonjour|bonsoir|salut|allo|allô|coucou)\b", re.I)
CLOSING = re.compile(r"\b(au revoir|bonne journée|bonne soirée|à bientôt|à demain|merci beaucoup|c'est tout)\b", re.I)


# Neutral on purpose: "D'accord." before "je ne peux pas" would sound like a yes (blocked account, stockout).
FILLERS = ("Alors…", "Voyons…")


async def find_caller(text: str, erp: ErpClient) -> tuple[dict | None, str | None]:
    """→ (client, first name said) when exactly one client matches what was said, else (None, None)."""
    try:
        clients, idf = await asyncio.wait_for(desk.directory(erp), 1.5)
    except Exception:
        return None, None
    best, _ = desk.match_clients(text, clients, idf)
    if not best:
        return None, None
    said = set(desk.tokens(text))
    first = next((n.split()[0] for n in best["contacts"] if n and desk.norm(n.split()[0]) in said), None)
    return best, first


async def choose_ack(text: str, first_turn: bool, erp: ErpClient) -> str:
    """The instant acknowledgement for this turn ("" = say nothing). `text` may be a partial transcript."""
    words = desk.norm(text).split()
    if first_turn:
        _, first = await find_caller(text, erp)
        if first:
            return f"Bonjour {first}."
        return "Bonjour." if GREETED.search(text) or len(words) >= 3 else ""
    if not words or CLOSING.search(text):
        return ""  # "merci, au revoir": a filler would sound odd
    return FILLERS[len(words) % len(FILLERS)]  # varies from turn to turn, so it does not sound like a recording


def ack_note(ack: str) -> str:
    """Tells the model what was already said aloud, so it does not greet twice or add its own filler."""
    return (
        f"[Système : tu viens déjà de dire « {ack} » à voix haute. Enchaîne directement avec la suite, comme si tu "
        "continuais ta phrase : ne salue pas de nouveau, ne redis pas son prénom, et ne commence pas par une autre formule "
        "d'accord ou d'attente (« d'accord », « très bien », « entendu », « c'est noté », « je regarde »).]"
    )
