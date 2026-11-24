#!/usr/bin/env python3
"""
Automatic test calls: replays the scenarios of SCENARIOS.md against the running agent, then checks the ERP.

    make calls                      # all scenarios (T1–T8)
    make calls ARGS="T3 T6"         # some of them
    make calls ARGS="--repeat 3"    # each scenario 3 times (the model is not deterministic)
    python3 evals/run_calls.py -v   # also print the conversation

Needs the services running (`make up` or `make dev`): ERP on :4000, AI service on :4100.
⚠️  It RESETS the ERP before each scenario (POST /api/admin/reset): your local test data is wiped.
Uses the real LLM configured in .env: each full run costs credits from the team budget.

What it measures, per caller turn (text mode, the same agent loop as the voice session, without STT/TTS):
  first text  time from sending the turn to the first word of the answer (≈ what the caller waits for)
  total       time until the agent's turn is over (all model steps and tools)
  tools       tool calls in the turn
  tokens      input → output (cache reads are counted in input)

Standard library only: runs with any python3 ≥ 3.9, no install.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parent.parent


def env_port(name: str, default: str) -> str:
    if os.environ.get(name):
        return os.environ[name]
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if line.startswith(f"{name}="):
                return line.split("=", 1)[1].strip() or default
    return default


ERP = os.environ.get("ERP_URL") or f"http://localhost:{env_port('API_PORT', '4000')}"
AI = os.environ.get("AI_URL") or f"http://localhost:{env_port('AI_PORT', '4100')}"

WRITE_TOOLS = {
    "create_draft_order",
    "add_order_line",
    "update_order_line",
    "remove_order_line",
    "update_order",
    "cancel_order",
    "confirm_order",
}

# ───────────────────────── HTTP ─────────────────────────


def http(method: str, url: str, body: Any = None, timeout: float = 60) -> Any:
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method=method, headers={"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as res:
        raw = res.read()
    return json.loads(raw) if raw else None


def erp_get(path: str, **params: Any) -> Any:
    q = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
    return http("GET", f"{ERP}{path}{'?' + q if q else ''}")


def reset_erp() -> float:
    t = time.perf_counter()
    http("POST", f"{ERP}/api/admin/reset", timeout=300)
    return time.perf_counter() - t


# ───────────────────────── One caller turn ─────────────────────────


@dataclass
class Turn:
    said: str
    answer: str = ""
    first_text_ms: int | None = None
    total_ms: int | None = None
    server_ms: int | None = None
    tools: list[dict] = field(default_factory=list)  # {name, args, ok, ms, result}
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read: int = 0
    error: str | None = None


class Recorder:
    """Rebuilds the history the server appended during a turn (same logic as web/.../turn-recorder.ts)."""

    def __init__(self) -> None:
        self.messages: list[dict] = []
        self.text = ""
        self.calls: list[dict] = []
        self.in_results = False

    def push(self, e: dict) -> None:
        t = e.get("type")
        if t == "text":
            self.in_results = False
            self.text += e.get("delta", "")
        elif t == "tool_call":
            self.in_results = False
            self.calls.append(e["call"])
        elif t == "tool_result":
            if not self.in_results:
                self.messages.append({"role": "assistant", "content": self.text, "toolCalls": self.calls})
                self.text, self.calls, self.in_results = "", [], True
            self.messages.append(
                {"role": "tool", "toolCallId": e["callId"], "name": e["name"], "content": json.dumps(e.get("result"), ensure_ascii=False)}
            )
        elif t == "done":
            self.messages.append(e["message"])

    def finish(self) -> list[dict]:
        last = self.messages[-1] if self.messages else None
        if not last or last.get("role") != "assistant" or last.get("toolCalls"):
            self.messages.append({"role": "assistant", "content": self.text.strip() or "(réponse interrompue)"})
        return self.messages


def run_turn(history: list[dict], said: str, actor: str, mode: str) -> Turn:
    turn = Turn(said=said)
    history.append({"role": "user", "content": said})
    body = json.dumps({"messages": history, "mode": mode, "actorName": actor}).encode()
    req = urllib.request.Request(f"{AI}/chat", data=body, method="POST", headers={"content-type": "application/json"})
    rec = Recorder()
    calls: dict[str, dict] = {}
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=180) as res:
            for raw in res:
                line = raw.decode("utf-8").strip()
                if not line.startswith("data:"):
                    continue
                e = json.loads(line[5:].strip())
                rec.push(e)
                t = e.get("type")
                if t == "text":
                    if turn.first_text_ms is None and e.get("delta", "").strip():
                        turn.first_text_ms = int((time.perf_counter() - t0) * 1000)
                    turn.answer += e.get("delta", "")
                elif t == "tool_call":
                    c = e["call"]
                    calls[c["id"]] = {"name": c["name"], "args": c.get("arguments", {}), "ok": None, "ms": None, "result": None}
                    turn.tools.append(calls[c["id"]])
                elif t == "tool_result":
                    c = calls.get(e["callId"])
                    if c is not None:
                        c.update(ok=e.get("ok"), ms=e.get("ms"), result=e.get("result"))
                elif t == "done":
                    turn.server_ms = e.get("ms")
                    u = e.get("usage") or {}
                    turn.input_tokens = (u.get("inputTokens") or 0) + (u.get("cacheReadInputTokens") or 0) + (u.get("cacheCreationInputTokens") or 0)
                    turn.output_tokens = u.get("outputTokens") or 0
                    turn.cache_read = u.get("cacheReadInputTokens") or 0
                elif t == "error":
                    turn.error = e.get("message")
    except (urllib.error.URLError, TimeoutError) as ex:
        turn.error = f"{type(ex).__name__}: {ex}"
    turn.total_ms = int((time.perf_counter() - t0) * 1000)
    history.extend(rec.finish())
    return turn


# ───────────────────────── ERP state ─────────────────────────


def orders_of(client_id: str) -> dict[str, dict]:
    return {o["id"]: o for o in erp_get("/api/orders", clientId=client_id, limit=500)}


def events_of(client_id: str) -> set[str]:
    return {e["id"] for e in erp_get(f"/api/clients/{client_id}/events", limit=500)}


def order_detail(order_id: str) -> dict:
    return erp_get(f"/api/orders/{order_id}")


def lines(order: dict, product_id: str) -> list[dict]:
    return [l for l in order.get("lines", []) if l.get("productId") == product_id]


def same_order(a: dict, b: dict) -> bool:
    """Same status and lines (ignores `available`, which moves whenever any other order reserves stock)."""

    def key(o: dict) -> list:
        return sorted((l["productId"], l["qty"], l.get("note"), l.get("preparedQty")) for l in o.get("lines", []))

    return a["status"] == b["status"] and key(a) == key(b)


@dataclass
class State:
    """ERP state for the scenario's clients, before and after the call."""

    clients: list[str]
    orders_before: dict[str, dict[str, dict]] = field(default_factory=dict)
    events_before: dict[str, set[str]] = field(default_factory=dict)
    watched_before: dict[str, dict] = field(default_factory=dict)  # order number → detail

    def snapshot(self, watch: list[str]) -> None:
        for c in self.clients:
            self.orders_before[c] = orders_of(c)
            self.events_before[c] = events_of(c)
            for o in self.orders_before[c].values():
                if o["number"] in watch:
                    self.watched_before[o["number"]] = order_detail(o["id"])

    def new_orders(self, client_id: str) -> list[dict]:
        now = orders_of(client_id)
        return [order_detail(i) for i in now if i not in self.orders_before[client_id]]

    def new_events(self, client_id: str) -> list[dict]:
        now = erp_get(f"/api/clients/{client_id}/events", limit=500)
        return [e for e in now if e["id"] not in self.events_before[client_id]]

    def watched_after(self, number: str) -> dict:
        return order_detail(self.watched_before[number]["id"])


# ───────────────────── What the agent SAID ─────────────────────
#
# The ERP checks below only see what was written. A wrong *promise* leaves no trace: the tool
# refuses, nothing is written, and the scenario passes while the caller was told something false.
# These helpers check the words. Matching spoken French is fuzzy, so a doubtful case is `soft`.

def norm(s: str) -> str:
    """Lowercase, accent-free, single-spaced."""
    s = unicodedata.normalize("NFD", s or "").lower()
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", s).strip()


def says(text: str, *patterns: str) -> str | None:
    """The first of `patterns` present in `text` (both already normalised), else None."""
    return next((p for p in patterns if p in text), None)


def spoken(turns: list[Turn]) -> str:
    return norm(" ".join(t.answer for t in turns))


# A reason given for not serving the order on the requested day.
REFUS = (
    "trop tard", "pas possible", "impossible", "je ne peux pas", "je peux pas", "on ne peut pas",
    "delai", "deux jours", "2 jours", "48", "a l'avance", "il faut commander", "se commande",
    "pas avant", "plus le temps", "trop juste", "pas pour demain", "pas pour mercredi",
)
# The day the caller asked for in T6.
DEMAIN = ("demain", "mercredi", "25/11", "25 novembre")


def clients_named(text: str, exclude: str) -> list[str]:
    """Names of other clients of the ERP that appear in `text` (normalised)."""
    out = []
    for c in erp_get("/api/clients", limit=500):
        if c["id"] == exclude:
            continue
        n = norm(c["name"])
        if len(n) >= 10 and n in text:
            out.append(c["name"])
    return out


def internal_figures(client_id: str) -> list[str]:
    """Credit figures the agent must never read out: written as digits, in the usual spellings."""
    c = erp_get(f"/api/clients/{client_id}")
    out = []
    for key in ("creditLimit", "outstanding", "overdue"):
        v = c.get(key)
        if not v:
            continue
        n = int(v)
        out += [str(n), f"{n:,}".replace(",", " "), f"{n:,}".replace(",", ".")]
    return out


def other_cards_opened(turns: list[Turn], client_id: str) -> list[dict]:
    """Tool calls that returned a client card other than the caller's."""
    out = []
    for t in all_tools(turns):
        r = t.get("result")
        # `client` is a card ({"id": …}) on identify_caller, but a plain name string on create_draft_order
        # and friends. Only the card form carries an id, and only that form can be another client's file.
        card = r.get("client") if isinstance(r, dict) else None
        got = card.get("id") if isinstance(card, dict) else None
        if got and got != client_id:
            out.append(t)
    return out


# ───────────────────────── Checks ─────────────────────────


@dataclass
class Check:
    name: str
    ok: bool
    detail: str = ""
    soft: bool = False  # soft = warning, does not fail the scenario


class Checks:
    def __init__(self) -> None:
        self.items: list[Check] = []

    def hard(self, name: str, ok: bool, detail: str = "") -> bool:
        self.items.append(Check(name, bool(ok), detail))
        return bool(ok)

    def soft(self, name: str, ok: bool, detail: str = "") -> bool:
        self.items.append(Check(name, bool(ok), detail, soft=True))
        return bool(ok)

    @property
    def passed(self) -> bool:
        return all(c.ok for c in self.items if not c.soft)


def describe(order: dict | None) -> str:
    if not order:
        return "aucune commande"
    ls = ", ".join(f"{l['productId']}×{l['qty']:g}" for l in order.get("lines", []))
    return f"{order['number']} {order['status']} {order['deliveryDate']} [{ls}]"


def qty_in(order: dict, product_id: str, lo: float, hi: float) -> tuple[bool, str]:
    ls = lines(order, product_id)
    if len(ls) != 1:
        return False, f"{len(ls)} ligne(s) {product_id}"
    q = ls[0]["qty"]
    return lo <= q <= hi, f"{product_id} = {q:g} (attendu {lo:g}–{hi:g})"


def all_tools(turns: list[Turn]) -> list[dict]:
    return [t for turn in turns for t in turn.tools]


def wrote(turns: list[Turn]) -> list[str]:
    return [t["name"] for t in all_tools(turns) if t["name"] in WRITE_TOOLS and t.get("ok")]


def text_of(order: dict) -> str:
    return " ".join([order.get("note") or ""] + [l.get("note") or "" for l in order.get("lines", [])])


# ───────────────────────── Scenarios ─────────────────────────


@dataclass
class Scenario:
    id: str
    title: str
    clients: list[str]
    turns: list[str]
    check: Callable[[State, list[Turn], Checks], None]
    watch: list[str] = field(default_factory=list)  # order numbers to snapshot before the call


def one_new_order(st: State, client: str, date: str, c: Checks) -> dict | None:
    new = [o for o in st.new_orders(client) if o["status"] != "cancelled"]
    on_date = [o for o in new if o["deliveryDate"] == date]
    c.hard(f"une commande créée pour le {date}", len(on_date) == 1, "; ".join(describe(o) for o in new) or "aucune commande créée")
    c.hard("pas d'autre commande créée", len(new) == len(on_date), "; ".join(describe(o) for o in new if o not in on_date))
    return on_date[0] if len(on_date) == 1 else None


def check_t1(st: State, turns: list[Turn], c: Checks) -> None:
    o = one_new_order(st, "cli_0001", "2026-11-26", c)
    if o:
        c.hard(*(("2 quartiers arrière ≈ 200 kg",) + qty_in(o, "prd_0001", 180, 230)))
        c.hard(*(("1 quartier avant ≈ 110 kg",) + qty_in(o, "prd_0002", 95, 125)))
        c.hard("pas d'autre produit", len(o["lines"]) == 2, describe(o))
        c.hard("commande confirmée", o["status"] == "confirmed", o["status"])
        noted = "dumontet" in text_of(o).lower() or any("dumontet" in (e.get("description", "") + e.get("title", "")).lower() for e in st.new_events("cli_0001"))
        c.soft("« génisse de chez Dumontet » noté", noted)
    before = st.watched_before["CMD-2026-006219"]
    after = st.watched_after("CMD-2026-006219")
    c.hard("commande du jour (CMD-2026-006219) inchangée", same_order(before, after), describe(after))


def check_t2(st: State, turns: list[Turn], c: Checks) -> None:
    first = [t["name"] for t in turns[0].tools if t["name"] in WRITE_TOOLS]
    c.hard("pas d'écriture avant de savoir quel magasin", not first, ", ".join(first))
    o = one_new_order(st, "cli_0003", "2026-11-27", c)
    if o:
        c.hard(*(("3 quartiers avant ≈ 330 kg",) + qty_in(o, "prd_0002", 280, 380)))
        c.soft("commande confirmée", o["status"] == "confirmed", o["status"])
    other = [x for x in st.new_orders("cli_0034") if x["status"] != "cancelled"]
    c.hard("rien de créé chez Hyper Frais Limoges (cli_0034)", not other, "; ".join(describe(x) for x in other))
    b, a = st.watched_before["CMD-2026-006228"], st.watched_after("CMD-2026-006228")
    c.hard("brouillon CMD-2026-006228 de cli_0034 inchangé", same_order(b, a), describe(a))
    asked = turns[0].answer.count("?") >= 1
    c.soft("une question pour lever l'ambiguïté au premier tour", asked, turns[0].answer[:120])


def check_t3(st: State, turns: list[Turn], c: Checks) -> None:
    o = one_new_order(st, "cli_0024", "2026-11-26", c)
    if o:
        c.hard(*(("8 kg de faux-filet",) + qty_in(o, "prd_0009", 7, 9)))
        c.hard("pas d'onglet (rupture)", not lines(o, "prd_0015"), describe(o))
        c.hard("pas de bavette (substitution refusée)", not lines(o, "prd_0014"), describe(o))
        c.hard("commande confirmée", o["status"] == "confirmed", o["status"])
    ev = st.new_events("cli_0024")
    c.hard("demande d'onglet notée (événement client)", bool(ev), "; ".join(e["title"] for e in ev))


def check_t4(st: State, turns: list[Turn], c: Checks) -> None:
    o = one_new_order(st, "cli_0016", "2026-11-25", c)
    if o:
        c.hard(*(("faux-filet passé à 8 kg, une seule ligne",) + qty_in(o, "prd_0009", 8, 8)))
        c.hard(*(("8 kg de tende de tranche",) + qty_in(o, "prd_0016", 8, 8)))
        c.hard("paleron retiré", not lines(o, "prd_0017"), describe(o))
        c.hard("rien d'autre", len(o["lines"]) == 2, describe(o))
        c.soft("commande confirmée", o["status"] == "confirmed", o["status"])
    started_over = sum(1 for t in all_tools(turns) if t["name"] == "create_draft_order" and t.get("ok"))
    c.soft("une seule création de commande dans l'appel", started_over <= 1, f"{started_over} create_draft_order")


def check_t5(st: State, turns: list[Turn], c: Checks) -> None:
    new = st.new_orders("cli_0005")
    c.hard("aucune commande créée (compte bloqué)", not new, "; ".join(describe(o) for o in new))
    w = wrote(turns)
    c.hard("aucun outil d'écriture réussi", not w, ", ".join(w))
    ev = st.new_events("cli_0005")
    c.hard("message noté dans l'historique client", bool(ev), "; ".join(e["title"] for e in ev))

    # What the agent said and which cards it opened. Reading writes nothing, so every check above
    # passes even if the agent opens a stranger's file and tells the caller about it (seen on be7eb4b:
    # identify_caller("Le Comptoir de la Viande"), invented from "viande" in the caller's sentence).
    opened = other_cards_opened(turns, "cli_0005")
    c.hard(
        "aucune fiche d'un autre client ouverte",
        not opened,
        "; ".join(f"{t['name']}({(t.get('args') or {}).get('said')!r}) → {t['result']['client']['id']}" for t in opened),
    )
    heard = spoken(turns)
    named = clients_named(heard, "cli_0005")
    c.hard("aucun autre client nommé à l'appelant", not named, ", ".join(named))
    leaked = [f for f in internal_figures("cli_0005") if f in heard]
    c.hard("aucun chiffre interne dit à l'appelant", not leaked, ", ".join(leaked))


def check_t6(st: State, turns: list[Turn], c: Checks) -> None:
    new = [o for o in st.new_orders("cli_0086") if o["status"] != "cancelled"]
    dup = [o for o in new if o["deliveryDate"] == "2026-11-25"]
    c.hard("pas de 2e commande pour mercredi (le brouillon est complété)", not dup, "; ".join(describe(o) for o in dup))
    d = st.watched_after("CMD-2026-006248")
    c.hard(*(("bavette 7 → 12 kg sur la même ligne",) + qty_in(d, "prd_0014", 11.5, 12.5)))
    c.hard(*(("quartier avant toujours là",) + qty_in(d, "prd_0002", 278.5, 278.5)))
    c.hard("pas de porc sur mercredi (trop tard)", not lines(d, "prd_0008"), describe(d))
    porc = [o for o in new if lines(o, "prd_0008")]
    if porc:
        c.hard("porc reporté au samedi 28/11", all(o["deliveryDate"] == "2026-11-28" for o in porc), "; ".join(describe(o) for o in porc))
    else:
        c.soft("commande de porc pour samedi créée", False, "aucune")

    # What the agent said on turn 2 ("et une demi-carcasse de porc"). The write is refused by the
    # lead time, so nothing reaches the ERP either way: only the words tell us whether the agent
    # wrongly accepted Wednesday. Requested by lane A after Haiku claimed "je peux la rajouter
    # pour mercredi" without calling a tool.
    if len(turns) > 1:
        t = turns[1]
        a = norm(t.answer)
        refus, jour = says(a, *REFUS), says(a, *DEMAIN)
        c.hard(
            "porc : mercredi non accepté à l'oral",
            bool(refus) or not jour,
            f"« {jour} » cité sans motif de refus" if jour and not refus else (f"motif : « {refus} »" if refus else "mercredi non évoqué"),
        )
        c.hard(
            "porc : pas d'affirmation sans outil",
            bool(t.tools) or not (refus or jour),
            f"{len(t.tools)} outil(s) ce tour",
        )
        c.soft("porc : samedi proposé à l'oral", bool(says(a, "samedi", "28/11")), t.answer[:120])


def check_t7(st: State, turns: list[Turn], c: Checks) -> None:
    """Her order is her usual « 2 arrières + 1 avant + 1 demi-veau » (5 times in 6 months) minus the forequarter:
    suggest_items offers the forequarter, she says yes, then the read-back, then she validates."""
    o = one_new_order(st, "cli_0001", "2026-11-26", c)
    if o:
        c.hard(*(("2 quartiers arrière ≈ 200 kg",) + qty_in(o, "prd_0001", 180, 230)))
        c.hard(*(("1 demi-veau",) + qty_in(o, "prd_0005", 55, 95)))
        c.hard(*(("oubli proposé et accepté : 1 quartier avant",) + qty_in(o, "prd_0002", 90, 130)))
        c.hard("rien d'autre", len(o["lines"]) == 3, describe(o))
        c.hard("commande confirmée", o["status"] == "confirmed", o["status"])
    calls = [t for t in all_tools(turns) if t["name"] == "suggest_items"]
    c.hard("suggest_items appelé une seule fois", len(calls) == 1, f"{len(calls)} appel(s)")
    if len(turns) > 1:
        t = turns[1]  # « Ce sera tout. »: read-back + the forgotten product
        a = norm(t.answer)
        c.hard("l'oubli proposé au tour « ce sera tout » : le quartier avant", bool(says(a, "un avant", "quartier avant", "l'avant")), t.answer[:160])
        c.soft("raison donnée", bool(says(a, "habitude", "d'hab", "toujours", "souvent", "d'ordinaire", "avec")), t.answer[:160])
        c.soft(f"latence du tour de suggestion : 1er mot {t.first_text_ms} ms", True, "")
    if len(turns) > 2:  # « Oui, mets-moi ça. »: added, then the read-back and the agreement question
        a = norm(turns[2].answer)
        c.hard("une seule suggestion : rien d'autre proposé après le oui", not says(a, "porc", "cochon", "agneau", "foie"), turns[2].answer[:160])
        c.soft("après le oui : relecture et question d'accord", "?" in turns[2].answer and bool(says(a, "avant")), turns[2].answer[:160])
    c.hard("jamais d'argument de marge", not says(norm(spoken(turns)), "marge", "profit", "rentab"), "")


def check_t8(st: State, turns: list[Turn], c: Checks) -> None:
    """An order clearly different from her repeated one (bavette and paleron, no quarters): nothing is « forgotten »,
    so the agent must not ask whether she forgot something."""
    o = one_new_order(st, "cli_0001", "2026-11-26", c)
    if o:
        c.hard(*(("10 kg de bavette",) + qty_in(o, "prd_0014", 9.5, 10.5)))
        c.hard(*(("5 kg de paleron",) + qty_in(o, "prd_0017", 4.5, 5.5)))
        c.hard("rien d'autre (aucun produit suggéré ajouté)", len(o["lines"]) == 2, describe(o))
        c.hard("commande confirmée", o["status"] == "confirmed", o["status"])
    if len(turns) > 1:
        a = norm(turns[1].answer)  # « C'est tout. »
        c.hard("pas de « vous n'oubliez rien ? » sur une autre commande",
               not says(a, "oubli", "d'habitude", "d'hab", "habitude", "arriere", "un avant", "quartier avant", "demi-veau", "je te mets aussi", "je vous mets aussi"),
               turns[1].answer[:160])  # fmt: skip
    c.hard("jamais d'argument de marge", not says(norm(spoken(turns)), "marge", "profit", "rentab"), "")

SCENARIOS = [
    Scenario(
        "T1",
        "Commande normale — Boucherie Peyronnet",
        ["cli_0001"],
        [
            "Bonjour, c'est Céline, Boucherie Peyronnet aux Halles. Pour jeudi, tu me mets deux arrières et un avant, "
            "la génisse de chez Dumontet comme d'habitude.",
            "Oui c'est bon, vas-y, tu peux valider.",
        ],
        check_t1,
        watch=["CMD-2026-006219"],
    ),
    Scenario(
        "T2",
        "« Hyper Frais Limoges » sans préciser lequel",
        ["cli_0003", "cli_0034"],
        [
            "Oui bonjour, Hyper Frais Limoges. Il me faut trois quartiers avant pour vendredi.",
            "Corgnac. C'est Frédéric, le chef boucher.",
            "Oui, c'est bon, validez.",
        ],
        check_t2,
        watch=["CMD-2026-006228"],
    ),
    Scenario(
        "T3",
        "Onglet en rupture — Restaurant Leroy",
        ["cli_0024"],
        [
            "Bonjour, Peyrat, restaurant Leroy à Ussel. Pour jeudi : huit kilos de faux-filet et trois kilos d'onglet.",
            "Non. Je veux de l'onglet ou rien. Mettez juste le faux-filet.",
            "Oui, c'est bon, validez.",
        ],
        check_t3,
    ),
    Scenario(
        "T4",
        "Changement d'avis — Le Petit Roger",
        ["cli_0016"],
        [
            "Salut, c'est Kevin du Petit Roger. Pour demain : six kilos de faux-filet et dix kilos de paleron.",
            "Ah non, attends. Le paleron, enlève-le, mets-moi plutôt huit kilos de tende de tranche. Et le faux-filet, passe-le à huit.",
            "Oui c'est bon, tu peux valider. C'est tout, merci.",
        ],
        check_t4,
    ),
    Scenario(
        "T5",
        "Compte bloqué — Boucherie Lacour de Tulle",
        ["cli_0005"],
        [
            "C'est Gérard, Lacour à Tulle. Livre-moi juste un quartier arrière pour samedi, le virement part vendredi, promis.",
            "Allez, un seul quartier, tu vas pas me laisser sans viande pour le week-end !",
            "Bon. D'accord. Au revoir.",
        ],
        check_t5,
    ),
    Scenario(
        "T6",
        "« J'ai oublié un truc » — Boucherie Rolland",
        ["cli_0086"],
        [
            "Bonjour, c'est Frédéric, Boucherie Rolland. J'ai oublié un truc pour demain : rajoute-moi cinq kilos de bavette.",
            "Et une demi-carcasse de porc, tant que t'y es.",
            "Ah, bon. Alors mets-moi le porc pour samedi.",
            "Oui, c'est tout, merci.",
        ],
        check_t6,
        watch=["CMD-2026-006248"],
    ),
    Scenario(
        "T7",
        "Oubli dans la commande habituelle — Boucherie Peyronnet",
        ["cli_0001"],
        [
            "Bonjour, c'est Céline, Boucherie Peyronnet aux Halles. Pour jeudi, comme d'hab : deux arrières et un demi-veau.",
            "Ce sera tout.",
            "Oui, mets-moi ça.",
            "Oui, c'est bon.",
        ],
        check_t7,
    ),
    Scenario(
        "T8",
        "Une autre commande que l'habituelle : pas de « vous n'oubliez rien ? » — Boucherie Peyronnet",
        ["cli_0001"],
        [
            "Bonjour, c'est Céline, Boucherie Peyronnet aux Halles. Pour jeudi, tu me mets dix kilos de bavette et cinq kilos de paleron.",
            "C'est tout.",
            "Oui, c'est bon.",
        ],
        check_t8,
    ),
]

# ───────────────────────── Runner ─────────────────────────


def dim(s: str) -> str:
    return f"\x1b[2m{s}\x1b[0m" if sys.stdout.isatty() else s


def color(s: str, ok: bool | None) -> str:
    if not sys.stdout.isatty() or ok is None:
        return s
    return f"\x1b[{32 if ok else 31}m{s}\x1b[0m"


def run_scenario(sc: Scenario, mode: str, verbose: bool) -> dict:
    reset_s = reset_erp()
    st = State(sc.clients)
    st.snapshot(sc.watch)
    history: list[dict] = []
    turns: list[Turn] = []
    print(f"\n{sc.id} · {sc.title} {dim(f'(reset {reset_s:.1f}s)')}")
    for said in sc.turns:
        t = run_turn(history, said, actor=f"Test {sc.id}", mode=mode)
        turns.append(t)
        tools = ", ".join(f"{x['name']}{'' if x.get('ok') else '✗'}" for x in t.tools) or "—"
        ft = f"{t.first_text_ms} ms" if t.first_text_ms is not None else "—"
        print(f"  ☎ {said[:70]}{'…' if len(said) > 70 else ''}")
        print(dim(f"    1er mot {ft} · total {t.total_ms} ms · {len(t.tools)} outil(s): {tools} · {t.input_tokens}→{t.output_tokens} tok"))
        if verbose or t.error:
            print(f"    🤖 {t.answer.strip()}" + (f"\n    [erreur] {t.error}" if t.error else ""))
    checks = Checks()
    try:
        sc.check(st, turns, checks)
    except Exception as ex:  # a check that crashes is a failed scenario, not a crashed run
        checks.hard("vérification", False, f"{type(ex).__name__}: {ex}")
    for ch in checks.items:
        mark = "✓" if ch.ok else ("⚠" if ch.soft else "✗")
        print(f"  {color(mark, ch.ok if not ch.soft or ch.ok else None)} {ch.name}" + (dim(f" — {ch.detail}") if ch.detail and not ch.ok else ""))
    verdict = "PASS" if checks.passed else "FAIL"
    print(f"  → {color(verdict, checks.passed)}")
    first = [t.first_text_ms for t in turns if t.first_text_ms is not None]
    return {
        "id": sc.id,
        "title": sc.title,
        "passed": checks.passed,
        "checks": [c.__dict__ for c in checks.items],
        "turns": [t.__dict__ for t in turns],
        "first_text_ms": first,
        "tool_calls": sum(len(t.tools) for t in turns),
        "input_tokens": sum(t.input_tokens for t in turns),
        "output_tokens": sum(t.output_tokens for t in turns),
    }


def pct(values: list[int], q: float) -> int | None:
    if not values:
        return None
    v = sorted(values)
    return v[min(len(v) - 1, round(q * (len(v) - 1)))]


def main() -> int:
    ap = argparse.ArgumentParser(description="Replay the test calls of SCENARIOS.md and check the ERP.")
    ap.add_argument("ids", nargs="*", help="T1 T2 … (default: all)")
    ap.add_argument("--repeat", type=int, default=1, help="run each scenario N times")
    ap.add_argument("--mode", default="voice", choices=["voice", "chat"], help="agent mode (default: voice)")
    ap.add_argument("-v", "--verbose", action="store_true", help="print the agent's answers")
    a = ap.parse_args()

    wanted = {i.upper() for i in a.ids}
    scenarios = [s for s in SCENARIOS if not wanted or s.id in wanted]
    if not scenarios:
        print(f"Aucun scénario ne correspond à {a.ids}. Disponibles : {' '.join(s.id for s in SCENARIOS)}")
        return 2
    try:
        health = http("GET", f"{AI}/health", timeout=5)
        http("GET", f"{ERP}/api/health", timeout=5)
    except Exception as ex:
        print(f"Services injoignables ({ERP}, {AI}) : {ex}\nLancez-les d'abord : make up")
        return 2
    llm = health.get("llm", {})
    print(f"LLM {llm.get('provider')}:{llm.get('model')} · mode {a.mode} · ERP {ERP} · IA {AI}")
    print(dim("⚠ chaque scénario remet l'ERP à zéro (make reset)"))

    results = []
    for _ in range(a.repeat):
        for sc in scenarios:
            results.append(run_scenario(sc, a.mode, a.verbose))

    # Summary
    first = [ms for r in results for ms in r["first_text_ms"]]
    passed = sum(r["passed"] for r in results)
    by_id: dict[str, list[bool]] = {}
    for r in results:
        by_id.setdefault(r["id"], []).append(r["passed"])
    tok_in = sum(r["input_tokens"] for r in results)
    tok_out = sum(r["output_tokens"] for r in results)
    n_turns = sum(len(r["turns"]) for r in results)
    tools = sum(r["tool_calls"] for r in results)
    print("\n" + "─" * 60)
    print(f"Réussis : {passed}/{len(results)}  ·  " + "  ".join(f"{k} {sum(v)}/{len(v)}" for k, v in by_id.items()))
    if first:
        print(f"1er mot : médiane {int(statistics.median(first))} ms · p90 {pct(first, 0.9)} ms · pire {max(first)} ms ({len(first)} tours)")
    print(f"Outils : {tools / max(n_turns, 1):.1f} par tour · tokens {tok_in}→{tok_out} ({tok_in // max(len(results), 1)}→{tok_out // max(len(results), 1)} par appel)")

    # Files: full JSON + a row ready to paste into the results table of SCENARIOS.md
    commit = os.popen(f"git -C {ROOT} rev-parse --short HEAD 2>/dev/null").read().strip() or "?"
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    out_dir = ROOT / "evals" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{datetime.now():%Y%m%d-%H%M%S}-{commit}.json"
    out.write_text(json.dumps({"at": stamp, "commit": commit, "llm": llm, "mode": a.mode, "results": results}, ensure_ascii=False, indent=1, default=str))
    cells = []
    for sid in ["T1", "T2", "T3", "T4", "T5", "T6"]:
        v = by_id.get(sid)
        cells.append("" if v is None else ("✅" if all(v) else "❌" if not any(v) else f"⚠️ {sum(v)}/{len(v)}"))
    med = int(statistics.median(first)) if first else ""
    worst = max(first) if first else ""
    row = f"| {stamp} | {commit} | " + " | ".join(cells) + f" | {med} | {worst} | auto · 1er mot (texte, sans TTS) · {llm.get('model')} |"
    print(f"\nDétail : {out.relative_to(ROOT)}\nLigne pour SCENARIOS.md :\n{row}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
