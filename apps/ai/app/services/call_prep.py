"""
What the voice session does in CODE around the model, to cut dead air and model round-trips:

    choose_ack        what a person at the order desk says the instant the caller stops ("Bonjour Christian.",
                      "Je regarde.", "Je corrige.", or nothing), chosen from the live transcript: no model, no tool.
                      It never states a fact, so it cannot be wrong about the order.
    (The caller is also identified in code before the model runs: that lives in the agent loop, agent/loop.py,
    with tools/desk.py prefetch_identify, so the text chat and the test runner get it too.)

Best effort: any doubt (two plausible clients, ERP slow) → say a plain "Bonjour." and let the model do the rest.
"""

import asyncio
import os
import re

from app.tools import ErpClient
from app.tools import desk

GREETED = re.compile(r"\b(bonjour|bonsoir|salut|allo|allô|coucou)\b", re.I)

# What kind of thing did the caller just say? Checked in this order; the first that matches wins.
# A goodbye ends the call. "C'est tout" does not: it ends the list, and the read-back follows. And "oui, valide,
# merci, au revoir" is first of all a yes that needs a tool (seen live: 5 s of silence, because it was filed as a
# goodbye and got no word at all).
GOODBYE = re.compile(r"\b(au revoir|bonne journée|bonne soirée|bon week-?end|à bientôt|à demain|à plus|merci beaucoup)\b", re.I)
DONE = re.compile(r"\b(c'est tout|ce sera tout|ça ira|rien d'autre|c'est bon comme ça)\b", re.I)
VALIDATE = re.compile(r"\b(valide|validez|valider|confirme|confirmez|confirmer|vas-y|allez-y|envoie|envoyez)\b", re.I)
PLEA = re.compile(r"\b(tu vas pas|vous (n')?allez pas|sois sympa|soyez sympa|juste un|juste une|promis|allez,? (un|une|juste|quoi|s'il))\b", re.I)
COMPLAINT = re.compile(
    r"\b(pas normal|inadmissible|n'importe quoi|encore une fois|toujours pareil|jamais reçu|pas reçu|il manqu\w+|pas content\w*|"
    r"(?<!pas de )(?<!aucun )problème|réclamation|rembours\w+|un avoir|pas ce qui était prévu)\b",
    re.I,
)
# A change of mind needs a word that changes something: a bare "non" or "attendez" is often a protest or a correction of us.
CHANGE = re.compile(r"\b(finalement|plutôt|enlève|enlevez|retire|retirez|laisse tomber|laissez tomber|au lieu|à la place|change|changez|passe-le|passez-le|décale|décalez)\b", re.I)
HABIT = re.compile(r"\b(comme d'hab\w*|la même chose|pareil que|comme (mardi|mercredi|jeudi|vendredi|samedi|lundi|la dernière fois)|dernière commande|où en est)\b", re.I)
LOOKUP = re.compile(r"\?|\b(est-ce que|combien|quand|c'est quoi|quel prix|quelle date|il (vous|te|t'en) reste|vous avez|tu as|avez-vous|as-tu)\b", re.I)
YES = re.compile(r"\b(oui|ouais|ok|okay|vas-y|allez-y|c'est bon|ça marche|parfait|d'accord|exact|valide|validez|confirme|confirmez|impeccable)\b", re.I)
ORDER = re.compile(
    r"\d|\b(kilos?|kg|pièces?|mets|mettez|rajoute|rajoutez|ajoute|ajoutez|il me faut|il me faudrait|je voudrais|je prends|"
    r"je vais prendre|commande|un|une|deux|trois|quatre|cinq|six|sept|huit|neuf|dix|douze|quinze|vingt|trente|demi)\b",
    re.I,
)

# What a person at a French order desk says the instant the caller stops, while the real answer is being prepared.
# Chosen from what conversation research and call-centre practice say (sources: DECISIONS.md, "Les mots d'attente"):
#   - a request gets a word that ANNOUNCES THE WORK ("je note", "je regarde"), never "d'accord / ça marche / parfait":
#     in French those accept the request, and the stockout or the lead time may come right after;
#   - "alors", "voyons", "euh" before an answer are heard as trouble coming: not used;
#   - a "oui" gets "Très bien." at once: it answers HIS yes, it promises nothing more (measured: 2.9 s of silence after
#     "c'est bon, vas-y" when we said nothing);
#   - nothing on a goodbye, nothing when we cannot place the turn;
#   - never the same words on two turns in a row, and not again within a few turns: a fixed filler sounds mechanical.
# Silence is the worse fault: a turn that needs a tool takes 2 to 5 s, and a silent line that long sounds dead.
TOKENS = {
    "order": ("Je note.", "Un instant.", "Je regarde ça.", "Deux secondes.", "Je prépare ça."),  # he is ordering
    "lookup": ("Je regarde.", "Un instant.", "Je vérifie.", "Je regarde ça.", "Deux secondes."),  # question, short answer
    "yes": ("Très bien.", "Entendu."),  # his agreement, received
    "change": ("Je corrige.", "Je modifie ça."),  # change of mind
    "complaint": ("Je regarde ça tout de suite.",),  # neutral and prompt, never cheerful
    "plea": ("Je comprends.",),  # the only sound that fits before a refusal
}
POOL = {"order": "order", "lookup": "lookup", "short": "lookup", "yes": "yes", "done": "yes", "change": "change", "complaint": "complaint", "plea": "plea"}

# VOICE_ACK in .env: smart (default) | sparse (never on two turns in a row, nothing after a yes) | greeting (only
# "Bonjour …" on the first turn) | off
MODE = (os.environ.get("VOICE_ACK") or "smart").strip().lower()


async def find_caller(text: str, erp: ErpClient) -> tuple[dict | None, str | None]:
    """→ (client, first name said) when exactly one client matches what was said, else (None, None)."""
    try:
        clients, stats = await asyncio.wait_for(desk.directory(erp), 1.5)
    except Exception:
        return None, None
    best, _ = desk.match_clients(text, clients, stats)
    if not best:
        return None, None
    said = set(desk.tokens(text))
    first = next((n.split()[0] for n in best["contacts"] if n and desk.norm(n.split()[0]) in said), None)
    return best, first


REREAD = re.compile(r"\b(relis|relisez|relire|récap\w*|recap\w*|répète|répétez|redis|redites)\b", re.I)


def kind_of(text: str) -> str:
    """closing | done | reread | complaint | plea | change | yes | lookup | order | short | other — what the caller's turn mostly is."""
    words = desk.norm(text).split()
    if not words:
        return "other"
    if VALIDATE.search(text) and len(words) <= 12 and not CHANGE.search(text) and not ORDER.search(VALIDATE.sub("", YES.sub("", text))):
        return "yes"  # "oui, valide. Merci, au revoir." : the confirmation comes first, whatever is said around it
    if GOODBYE.search(text):
        return "closing"
    if DONE.search(text):
        return "done"  # the list is finished: the read-back comes next
    if REREAD.search(text):
        return "reread"  # "tu me relis ?": the answer needs no tool, it comes at once
    if COMPLAINT.search(text):
        return "complaint"
    if PLEA.search(text):
        return "plea"
    if CHANGE.search(text):
        return "change"
    if YES.search(text) and len(words) <= 6 and not ORDER.search(YES.sub("", text)):
        return "yes"
    if HABIT.search(text) or (LOOKUP.search(text) and not ORDER.search(LOOKUP.sub("", text))):
        return "lookup"  # "comme d'habitude" has to be looked up; a question that carries no order is a question
    if ORDER.search(text):
        return "order"
    return "short" if len(words) <= 8 else "other"  # a short answer to our question ("Corgnac.", "Celui de la place.")


async def choose_ack(text: str, first_turn: bool, erp: ErpClient | None, recent: list[str] | None = None, blocked: bool = False) -> str:
    """The words spoken the instant the caller stops ("" = nothing). `text` may be a partial transcript.
    `recent` = what was said at the start of the previous turns of this call ("" when nothing), oldest first."""
    if MODE == "off":
        return ""
    if first_turn:
        _, first = await find_caller(text, erp) if erp else (None, None)
        if first:
            return f"Bonjour {first}."
        return "Bonjour." if GREETED.search(text) or len(desk.norm(text).split()) >= 3 else ""
    if MODE not in ("smart", "sparse"):
        return ""
    recent = recent or []
    pool = POOL.get(kind_of(text))
    if not pool:
        return ""  # a goodbye, or something we cannot place: say nothing, the answer speaks
    if blocked and pool != "plea":
        return ""  # blocked account: no "je note" that could sound like the order is being taken
    if MODE == "sparse" and (pool == "yes" or (recent and recent[-1] and not recent[-1].startswith("Bonjour"))):
        return ""  # the quieter setting: nothing after a yes, never on two turns in a row
    words = TOKENS[pool]
    used = set(recent[-max(1, min(4, len(words) - 1)) :])  # not the words of the last turns (at least: not twice in a row)
    return next((t for t in words if t not in used), "")


GREETING_ONLY = re.compile(r"^(bonjour|bonsoir|salut)( [\w' -]{1,30})?[.!]?$", re.I)


def is_waiting_phrase(text: str) -> bool:
    """True for the few words worth saying before a tool runs ("Je regarde.", "Bonjour Céline."). Anything else the
    model writes there is a note to itself ("Paleron: 17 kg.", "pas de commande, je la crée") and is not spoken."""
    said = " ".join((text or "").split())
    known = {desk.norm(t) for pool in TOKENS.values() for t in pool}
    return desk.norm(said) in known or bool(GREETING_ONLY.match(said))


# A sentence the model wrote to itself rather than to the caller: it talks ABOUT the caller in the third person
# (« Il pose la question lui-même, je peux donc proposer. », « Le client refuse les substitutions. ») or about its own
# rules. Heard on a live test (Restaurant Leroy, 24/11). The prompt forbids it; this catches what slips through.
ASIDE = re.compile(
    r"\b(le client|la cliente|l['’]appelant|l['’]interlocuteur)\b"
    r"|^(il|elle) (me |nous )?(pose|demande|dit|veut|souhaite|cherche|parle|appelle|a (dit|demandé|posé|confirmé|accepté|refusé))\b"
    r"|\b(je peux donc|donc je peux|je dois donc|donc je dois)\b"
    r"|\b(mes|les) (règles|consignes|instructions)\b",
    re.I,
)


def is_aside(sentence: str) -> bool:
    """True for a sentence that is the model's note to itself, never for something said to the caller. Not spoken."""
    return bool(ASIDE.search(" ".join((sentence or "").split())))


def said_goodbye(text: str) -> bool:
    """The caller is leaving ("merci, au revoir"): the moment to write the call report."""
    return bool(GOODBYE.search(text or ""))


def ack_note(ack: str) -> str:
    """Tells the model what was already said aloud, so it does not greet twice or add its own filler."""
    return (
        f"[Système : tu viens déjà de dire « {ack} » à voix haute. Enchaîne directement avec la suite, comme si tu "
        "continuais ta phrase : ne salue pas de nouveau, ne redis pas son prénom, et ne commence pas par une autre formule "
        "d'accord ou d'attente (« d'accord », « très bien », « entendu », « un instant », « je regarde », « je vérifie »).]"
    )
