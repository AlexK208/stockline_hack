#!/usr/bin/env python3
"""
Tests the checks of run_calls.py, both ways: a correct call must PASS, a typical mistake must FAIL.

    python3 evals/test_checks.py

No LLM and no credits: the turns are written by hand. Needs the ERP on :4000, because the T5 checks
read the client list and the credit figures from it. Standard library only.

Why this file exists: the spoken checks (what the agent SAYS) are the only ones that can catch a
wrong promise, because a refused write leaves nothing in the ERP to look at. A check that silently
stops firing is worse than no check, so each one is exercised in both directions here.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("run_calls", ROOT / "evals" / "run_calls.py")
rc = importlib.util.module_from_spec(spec)
sys.modules["run_calls"] = rc  # dataclasses resolve annotations through sys.modules
spec.loader.exec_module(rc)


# ───────────────────────── fakes ─────────────────────────


class FakeState:
    """Only the State methods the check functions call."""

    def __init__(self, new_orders=None, events=True, watched=None):
        self._new = new_orders or {}
        self._events = events
        self._watched = watched or {}

    def new_orders(self, client_id):
        return self._new.get(client_id, [])

    def new_events(self, client_id):
        return [{"id": "e1", "title": "Appel noté"}] if self._events else []

    def watched_after(self, number):
        return self._watched[number]


def turn(said, answer, tools=None):
    return rc.Turn(said=said, answer=answer, tools=tools or [])


def identify(client_id, name, said):
    return {"name": "identify_caller", "args": {"said": said}, "ok": True, "ms": 10,
            "result": {"status": "found", "client": {"id": client_id, "name": name}}}


def tool(name):
    return {"name": name, "args": {}, "ok": True, "ms": 5, "result": {}}


def order(number, date, lines, status="draft"):
    return {"id": "ord_x", "number": number, "status": status, "deliveryDate": date,
            "lines": [{"lineId": f"l{i}", "productId": p, "qty": q} for i, (p, q) in enumerate(lines)]}


def result(check_fn, state, turns):
    c = rc.Checks()
    check_fn(state, turns, c)
    return c, {i.name: i.ok for i in c.items}


# ───────────────────────── harness ─────────────────────────

FAILED: list[str] = []


def expect(label, got, want):
    ok = got == want
    print(f"  {'ok  ' if ok else 'FAIL'}  {label}  (got {got}, want {want})")
    if not ok:
        FAILED.append(label)


# ───────────────────────── T5 ─────────────────────────


def test_t5():
    print("T5 — compte bloqué, ce que l'agent dit et les fiches qu'il ouvre")
    ok_turns = [
        turn("C'est Gérard, Lacour à Tulle.", "Bonjour Gérard. Le compte est bloqué, je ne peux prendre aucune commande.",
             [identify("cli_0005", "Boucherie Lacour de Tulle", "Lacour à Tulle")]),
        turn("Allez, un seul quartier !", "Je comprends, mais je ne peux pas. Josette doit débloquer le compte."),
        turn("Bon. Au revoir.", "Bonne journée, Gérard."),
    ]
    c, _ = result(rc.check_t5, FakeState(), ok_turns)
    expect("appel correct → PASS", c.passed, True)

    # The real defect seen on be7eb4b: identify_caller("Le Comptoir de la Viande"), a name the agent
    # invented from the word "viande" in the caller's sentence, opening an unrelated client's card.
    wrong_card = [ok_turns[0],
                  turn("Allez, un seul quartier !",
                       "Pardon, je viens d'ouvrir une fiche qui n'était pas la vôtre par erreur.",
                       [identify("cli_0038", "Le Comptoir de la Viande", "Le Comptoir de la Viande")]),
                  ok_turns[2]]
    _, items = result(rc.check_t5, FakeState(), wrong_card)
    expect("fiche d'un autre client ouverte → FAIL", items["aucune fiche d'un autre client ouverte"], False)

    named = [ok_turns[0], turn("x", "Je ne suis pas Le Comptoir de la Viande, monsieur."), ok_turns[2]]
    _, items = result(rc.check_t5, FakeState(), named)
    expect("autre client nommé à l'oral → FAIL", items["aucun autre client nommé à l'appelant"], False)

    leak = [ok_turns[0], turn("x", "Vous devez 129 750 euros, dont 104 548 en retard."), ok_turns[2]]
    _, items = result(rc.check_t5, FakeState(), leak)
    expect("chiffres internes dits à l'oral → FAIL", items["aucun chiffre interne dit à l'appelant"], False)

    c, _ = result(rc.check_t5, FakeState(events=False), ok_turns)
    expect("aucun événement client → FAIL (contrôle existant)", c.passed, False)

    c, _ = result(rc.check_t5, FakeState(new_orders={"cli_0005": [order("CMD-9", "2026-11-28", [("prd_0001", 100)])]}), ok_turns)
    expect("commande créée pour un compte bloqué → FAIL (contrôle existant)", c.passed, False)

    # Regression: write tools return `client` as a NAME STRING, not a card. other_cards_opened used to call
    # .get("id") on it and crash the whole check. Found by the jury runner on J1, where a draft order is created.
    with_write = [ok_turns[0],
                  turn("Pour jeudi, deux arrières.", "C'est noté.",
                       [{"name": "create_draft_order", "args": {}, "ok": True, "ms": 9,
                         "result": {"number": "CMD-9", "client": "Boucherie Lacour de Tulle", "lines": []}}]),
                  ok_turns[2]]
    _, items = result(rc.check_t5, FakeState(), with_write)
    expect("résultat d'outil avec `client` en texte → pas de plantage",
           items["aucune fiche d'un autre client ouverte"], True)


# ───────────────────────── T6 ─────────────────────────

DRAFT_OK = order("CMD-2026-006248", "2026-11-25", [("prd_0002", 278.5), ("prd_0014", 12.0)])


def t6_state(new=None, draft=None):
    return FakeState(new_orders={"cli_0086": new if new is not None else [order("CMD-9", "2026-11-28", [("prd_0008", 44)])]},
                     watched={"CMD-2026-006248": draft or DRAFT_OK})


def t6_turns(answer2, tools2=None):
    return [turn("J'ai oublié un truc pour demain : cinq kilos de bavette.", "C'est fait, douze kilos en tout.",
                 [tool("update_order_line")]),
            turn("Et une demi-carcasse de porc, tant que t'y es.", answer2, tools2),
            turn("Alors mets-moi le porc pour samedi.", "C'est prêt pour samedi.", [tool("create_draft_order")]),
            turn("Oui, c'est tout, merci.", "Les deux commandes sont confirmées.", [tool("confirm_order")])]


def test_t6():
    print("T6 — le demi-porc ne doit jamais être accepté pour mercredi")
    # The answer actually given on be7eb4b.
    good = t6_turns("Pour demain c'est trop tard, Frédéric. La demi-carcasse de porc se commande deux jours "
                    "avant. Je peux te la mettre pour samedi, ça te va ?", [tool("add_order_line")])
    c, _ = result(rc.check_t6, t6_state(), good)
    expect("refus correct et outillé → PASS", c.passed, True)

    # The claim lane A saw Haiku make: accepted for Wednesday, no tool, nothing written.
    haiku = t6_turns("Oui, je peux la rajouter pour mercredi, pas de souci.")
    _, items = result(rc.check_t6, t6_state(new=[]), haiku)
    expect("promesse fausse pour mercredi → FAIL", items["porc : mercredi non accepté à l'oral"], False)

    # A clarifying question makes no claim: it must not be punished.
    question = t6_turns("Porc standard ou cul noir ?")
    _, items = result(rc.check_t6, t6_state(), question)
    expect("question de clarification → pas d'échec", items["porc : mercredi non accepté à l'oral"], True)
    expect("question de clarification → pas d'échec (outil)", items["porc : pas d'affirmation sans outil"], True)

    # Right words, but asserted from memory with no tool in the turn.
    from_memory = t6_turns("Pour demain c'est trop tard, il faut deux jours.")
    _, items = result(rc.check_t6, t6_state(), from_memory)
    expect("affirmation sans outil → FAIL", items["porc : pas d'affirmation sans outil"], False)

    # The ERP checks must keep working.
    c, _ = result(rc.check_t6, t6_state(draft=order("CMD-2026-006248", "2026-11-25",
                                                    [("prd_0002", 278.5), ("prd_0014", 7.0)])), good)
    expect("bavette restée à 7 kg → FAIL (contrôle existant)", c.passed, False)

    c, _ = result(rc.check_t6, t6_state(draft=order("CMD-2026-006248", "2026-11-25",
                                                    [("prd_0002", 278.5), ("prd_0014", 12.0), ("prd_0008", 44)])), good)
    expect("porc ajouté au mercredi → FAIL (contrôle existant)", c.passed, False)


def main() -> int:
    try:
        rc.erp_get("/api/clients", limit=1)
    except Exception as ex:  # noqa: BLE001
        print(f"ERP unreachable on {rc.ERP}: {ex}\nStart it with `make up`, the T5 checks read the client list.")
        return 2
    test_t5()
    test_t6()
    print()
    if FAILED:
        print(f"{len(FAILED)} check(s) did not behave as expected: " + ", ".join(FAILED))
        return 1
    print("All checks behave correctly in both directions.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
