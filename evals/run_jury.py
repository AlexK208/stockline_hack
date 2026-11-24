#!/usr/bin/env python3
"""
Replays the jury-style calls of `jury_calls.json` (J1–J18) — the hard cases we expect the jury to try live.

    make jury                      # all of them (~57 turns, costs real credits)
    make jury ARGS="J1 J5"         # some of them
    make jury ARGS="-v"            # also print what the agent said (recommended)

Needs the services running (`make up`): ERP on :4000, AI on :4100. It RESETS the ERP before each scenario.

Why this is a separate runner from `make calls`:

`SCENARIOS.md` (T1–T6) has `check_…` functions that decide PASS or FAIL on their own, because the six calls were
written with one exact right answer in the ERP. The jury calls are not like that: their `expected` is prose, and
several of them have more than one defensible outcome ("the agent asks one short question" — which question?).
Grading them automatically would mean inventing an opinion the scenarios do not state.

So this runner splits the job three ways:

  HARD (FAIL)  the two rules that hold on every call whatever the caller says: no internal credit figure spoken,
               and nothing written before we know who is on the line. A breach is a real defect.
  SOFT (⚠)     evidence a human needs but a runner cannot judge: how many client cards were opened, which other
               clients were named out loud, which tools errored.
  HUMAN        everything in `expected`. Printed next to the transcript and the ERP delta so a person can grade
               a scenario in seconds instead of reconstructing it.

The hard set is deliberately small. Its first version also failed J1, J14 and J15 — for correct behaviour:
J1 *must* name Marty and Deschamps to disambiguate, J14's `client_id` is the owner of the order the caller
wrongly claims rather than the caller, and in J15 the caller corrects their own identity so the call legitimately
moves to a second client. A check that cries wolf on correct behaviour is worse than no check: the team stops
reading it. Those three are soft now, with the evidence printed.

A green run therefore means "nothing catastrophic happened", NOT "the jury would be happy". Read the transcripts.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("run_calls", ROOT / "evals" / "run_calls.py")
rc = importlib.util.module_from_spec(spec)
sys.modules["run_calls"] = rc  # dataclasses resolve annotations through sys.modules
spec.loader.exec_module(rc)

CALLS = ROOT / "evals" / "jury_calls.json"
OUT_DIR = ROOT / "evals" / "results"


# ───────────────────── invariants true on every call ─────────────────────


def callers_identified(turns: list) -> list[dict]:
    """Every distinct client card opened during the call, in order."""
    seen, out = set(), []
    for t in rc.all_tools(turns):
        r = t.get("result")
        card = r.get("client") if isinstance(r, dict) else None
        cid = card.get("id") if isinstance(card, dict) else None
        if cid and cid not in seen:
            seen.add(cid)
            out.append({"id": cid, "name": card.get("name"), "tool": t["name"], "said": (t.get("args") or {}).get("said")})
    return out


def check_invariants(sc: dict, turns: list, c) -> None:
    """
    HARD = broken means a real defect, whatever the scenario. Kept deliberately narrow: the first version of this
    function failed J1, J14 and J15 for behaviour that was correct, which is worse than no check at all.

    Everything judgement-dependent is SOFT: reported with the evidence, decided by a human against `expected`.
    `client_id` in jury_calls.json is the client the scenario is ABOUT (for J14 it is the owner of the order the
    caller wrongly claims), not necessarily the caller — so it must not be used as "who may be opened".
    """
    opened = callers_identified(turns)

    # HARD. Nothing may be written before we know who is on the line.
    before, wrote_blind = True, []
    for t in turns:
        for x in t.tools:
            if x["name"] == "identify_caller" and x.get("ok"):
                before = False
            elif before and x["name"] in rc.WRITE_TOOLS and x.get("ok"):
                wrote_blind.append(x["name"])
    c.hard("aucune écriture avant d'avoir identifié l'appelant", not wrote_blind, ", ".join(wrote_blind))

    # HARD. Credit figures must never be spoken, for any client whose card was opened.
    heard = rc.spoken(turns)
    leaked = []
    for cid in [o["id"] for o in opened] or ([sc["client_id"]] if sc.get("client_id") else []):
        leaked += [f"{cid}:{f}" for f in rc.internal_figures(cid) if f in heard]
    c.hard("aucun chiffre interne dit à l'appelant", not leaked, ", ".join(leaked))

    # SOFT. One call should be one client — but a caller correcting themselves (J15) legitimately switches,
    # and the runner cannot tell that from a wrong guess. Reported, judged by a human.
    c.soft(
        "une seule fiche client ouverte",
        len(opened) <= 1,
        " → ".join(f"{o['id']} {o['name']} (via {o['tool']}, said={o['said']!r})" for o in opened),
    )

    # SOFT. Naming another client can be correct: J1 must ask "Marty ou Deschamps ?" to disambiguate.
    named = [n for n in rc.clients_named(heard, sc.get("client_id") or "") if n]
    c.soft("aucun autre client nommé à l'appelant", not named, ", ".join(named))

    failed = [x["name"] for x in rc.all_tools(turns) if not x.get("ok")]
    c.soft("aucun outil en erreur", not failed, ", ".join(failed))


# ───────────────────────────── running ─────────────────────────────


def erp_delta(st, client_id: str) -> dict:
    """What the call changed for this client, as plain data a human can scan."""
    orders = [
        {
            "number": o["number"],
            "status": o["status"],
            "deliveryDate": o.get("deliveryDate"),
            # substituteFor is printed because an accepted substitution (J19, J20) is only correct if the line
            # says what it replaces: without it the preparer cannot see why a bavette is on an onglet order.
            "lines": [
                f"{l['productId']} × {l['qty']:g} {l.get('unit', '')}".strip()
                + (f" (remplace {l['substituteFor']})" if l.get("substituteFor") else "")
                for l in o.get("lines", [])
            ],
        }
        for o in st.new_orders(client_id)
    ]
    # Holiday reservations (carnet des fêtes, J21–J24). The table is emptied by every reset, so all are new.
    try:
        festive = [
            f"{r['productId']} {r['deliveryDate']} réservé {r['qtyReserved']:g} + attente {r['qtyWaitlist']:g}"
            for r in rc.erp_get("/api/festive/reservations", clientId=client_id)
        ]
    except Exception:  # an ERP without the carnet des fêtes: nothing to show
        festive = []
    # Le cadran annoncé (J25–J29): is this client shown as told on the « Cotation de la semaine » page?
    try:
        row = next((c for c in rc.erp_get("/api/cotation/board")["clients"] if c["clientId"] == client_id), None)
        cotation = None if row is None else ("annoncée" if row.get("announced") else "pas annoncée")
    except Exception:
        cotation = None
    return {"new_orders": orders, "new_events": [e["title"] for e in st.new_events(client_id)], "festive": festive, "cotation": cotation}


def run_one(sc: dict, mode: str, verbose: bool) -> dict:
    # keep_erp: the call follows the previous scenario in the same ERP (J26: the same butcher calls back the same
    # week). Run it right after that scenario: `make jury ARGS="J25 J26"`.
    reset_s = 0.0 if sc.get("keep_erp") else rc.reset_erp()
    client_id = sc.get("client_id") or ""
    st = rc.State([client_id] if client_id else [])
    st.snapshot([])
    history: list[dict] = []
    turns: list = []

    print(f"\n{sc['id']} · {sc['title']} {rc.dim(f'(reset {reset_s:.1f}s)')}")
    if sc.get("trap"):
        print(rc.dim(f"  piège : {sc['trap']}"))
    for said in sc["turns"]:
        t = rc.run_turn(history, said, actor=f"Jury {sc['id']}", mode=mode)
        turns.append(t)
        tools = ", ".join(f"{x['name']}{'' if x.get('ok') else '✗'}" for x in t.tools) or "—"
        ft = f"{t.first_text_ms} ms" if t.first_text_ms is not None else "—"
        print(f"  ☎ {said[:74]}{'…' if len(said) > 74 else ''}")
        print(rc.dim(f"    1er mot {ft} · {len(t.tools)} outil(s): {tools} · {t.input_tokens}→{t.output_tokens} tok"))
        if verbose or t.error:
            print(f"    🤖 {t.answer.strip()}" + (f"\n    [erreur] {t.error}" if t.error else ""))

    checks = rc.Checks()
    try:
        check_invariants(sc, turns, checks)
    except Exception as ex:  # a check that crashes is a failed scenario, not a crashed run
        checks.hard("invariants", False, f"{type(ex).__name__}: {ex}")
    for ch in checks.items:
        mark = "✓" if ch.ok else ("⚠" if ch.soft else "✗")
        print(f"  {rc.color(mark, ch.ok if not ch.soft or ch.ok else None)} {ch.name}" + (rc.dim(f" — {ch.detail}") if ch.detail and not ch.ok else ""))

    delta = erp_delta(st, client_id) if client_id else {"new_orders": [], "new_events": []}
    print(rc.dim("  ERP : ") + (
        "; ".join(f"{o['number']} {o['status']} {o['deliveryDate']} [{', '.join(o['lines'])}]" for o in delta["new_orders"])
        or "aucune commande créée"
    ))
    if delta["new_events"]:
        print(rc.dim("  événements : ") + "; ".join(delta["new_events"]))
    if delta.get("cotation"):
        print(rc.dim("  cotation de la semaine : ") + delta["cotation"])
    if delta.get("festive"):
        print(rc.dim("  carnet des fêtes : ") + "; ".join(delta["festive"]))

    print(rc.dim("  à juger à la main :"))
    for e in sc.get("expected", []):
        print(rc.dim(f"    □ {e}"))

    verdict = "INVARIANTS OK" if checks.passed else "INVARIANT VIOLÉ"
    print(f"  → {rc.color(verdict, checks.passed)}")

    first = [t.first_text_ms for t in turns if t.first_text_ms is not None]
    return {
        "id": sc["id"],
        "title": sc["title"],
        "invariants_ok": checks.passed,
        "checks": [c.__dict__ for c in checks.items],
        "erp": delta,
        "expected": sc.get("expected", []),
        "turns": [t.__dict__ for t in turns],
        "first_text_ms": first,
        "input_tokens": sum(t.input_tokens for t in turns),
        "output_tokens": sum(t.output_tokens for t in turns),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Replay the jury-style calls of jury_calls.json.")
    ap.add_argument("ids", nargs="*", help="J1 J2 … (default: all)")
    ap.add_argument("--mode", default="voice", choices=["voice", "chat"])
    ap.add_argument("-v", "--verbose", action="store_true", help="print the agent's answers (recommended)")
    a = ap.parse_args()

    scenarios = json.loads(CALLS.read_text(encoding="utf-8"))
    wanted = {i.upper() for i in a.ids}
    scenarios = [s for s in scenarios if not wanted or s["id"] in wanted]
    if not scenarios:
        print(f"Aucun scénario ne correspond à {a.ids}.")
        return 2
    try:
        health = rc.http("GET", f"{rc.AI}/health", timeout=5)
        rc.http("GET", f"{rc.ERP}/api/health", timeout=5)
    except Exception as ex:
        print(f"Services injoignables ({rc.ERP}, {rc.AI}) : {ex}\nLancez-les d'abord : make up")
        return 2
    llm = health.get("llm", {})
    turns_total = sum(len(s["turns"]) for s in scenarios)
    print(f"LLM {llm.get('provider')}:{llm.get('model')} · mode {a.mode} · {len(scenarios)} appel(s), {turns_total} tours")
    print(rc.dim("⚠ chaque scénario remet l'ERP à zéro, et consomme des crédits réels"))
    print(rc.dim("  automatique = les invariants ; le reste de `expected` se juge à la main sur les transcriptions"))

    started = time.time()
    results = [run_one(sc, a.mode, a.verbose) for sc in scenarios]

    ok = sum(r["invariants_ok"] for r in results)
    first = sorted(ms for r in results for ms in r["first_text_ms"])
    tok_in = sum(r["input_tokens"] for r in results)
    print("\n" + "─" * 60)
    print(f"Invariants respectés : {ok}/{len(results)}" + ("" if ok == len(results) else "  ← à corriger en priorité"))
    broken = [(r["id"], c["name"]) for r in results for c in r["checks"] if not c["ok"] and not c["soft"]]
    for sid, name in broken:
        print(f"  ✗ {sid} : {name}")
    if first:
        print(f"1er mot : médiane {rc.statistics.median(first):.0f} ms · pire {first[-1]} ms ({len(first)} tours)")
    print(f"Jetons d'entrée : {tok_in:,} ({tok_in // max(len(results), 1):,} par appel)")
    print(rc.dim(f"Durée {time.time() - started:.0f} s"))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = OUT_DIR / f"jury-{stamp}.json"
    path.write_text(json.dumps({"at": stamp, "results": results}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Détail (transcriptions complètes) : {path.relative_to(ROOT)}")
    print(rc.dim("Rappel : invariants verts ≠ jury content. Lisez les transcriptions contre `expected`."))
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
