"""One call = one client: once the caller is identified, no tool reads or writes another client's data."""

import json

import pytest

from app.agent.loop import call_guard, known_caller, last_heard
from app.schemas import ChatMessage, ToolCall
from app.tools import ToolContext, desk
from tests.test_call_prep import clients


class FakeErp:
    """Orders by id, and a minimal client card for client_card()."""

    def __init__(self, orders=None):
        self.orders = orders or {}

    async def get(self, path, query=None):
        if path.startswith("/api/orders/"):
            return self.orders[path.rsplit("/", 1)[1]]
        raise LookupError(path)


def on_call(caller, heard="", orders=None):
    return ToolContext(erp=FakeErp(orders), actor="voice_agent", on_call=True, caller=caller, heard=heard)


def call(name, **args):
    return ToolCall(id="c1", name=name, arguments=args)


def test_known_caller_reads_compact_and_spaced_json():
    card = {"status": "found", "client": {"id": "cli_0005"}}
    for content in (json.dumps(card), json.dumps(card, separators=(",", ":"))):
        m = ChatMessage(role="tool", name="identify_caller", tool_call_id="x", content=content)
        assert known_caller([m]) == "cli_0005"
    asked = ChatMessage(role="tool", name="identify_caller", tool_call_id="y", content='{"status": "ambiguous", "candidates": []}')
    assert known_caller([asked]) is None
    assert known_caller([m, asked]) == "cli_0005"  # a later question does not forget who is on the phone


def test_last_heard_drops_the_note_added_for_the_model():
    said = ChatMessage(role="user", content="Mets-moi dix kilos de bavette\n\n[Système : tu viens déjà de dire « Je regarde. »]")
    assert last_heard([said, ChatMessage(role="assistant", content="…")]) == "Mets-moi dix kilos de bavette"


async def test_guard_refuses_another_clients_id_and_order():
    orders = {"ord_mine": {"clientId": "cli_0005"}, "ord_other": {"clientId": "cli_0009"}}
    ctx = on_call("cli_0005", orders=orders)
    await call_guard(call("get_client_history", clientId="cli_0005"), ctx)
    await call_guard(call("confirm_order", orderId="ord_mine"), ctx)
    await call_guard(call("check_products", items=[]), ctx)  # names no client: nothing to check
    for bad in (
        call("get_client_history", clientId="cli_0009"),
        call("get_context", entityType="client", id="cli_0009"),
        call("confirm_order", orderId="ord_other"),
        call("update_order_line", orderId="ord_other", lineId="l1", qty=3),
    ):
        with pytest.raises(PermissionError):
            await call_guard(bad, ctx)


async def test_guard_wants_the_caller_identified_first_and_only_on_the_phone():
    with pytest.raises(PermissionError):
        await call_guard(call("create_draft_order", clientId="cli_0005", lines=[]), on_call(None))
    # the web chat (a salesperson, any client) is not a phone call
    await call_guard(call("get_client_history", clientId="cli_0009"), ToolContext(erp=FakeErp(), actor="ai_chat"))


async def test_identify_caller_does_not_switch_client_on_a_guess(monkeypatch):
    rows, stats = clients()

    async def directory(erp):
        return rows, stats

    async def card(erp, client_id):
        return {"id": client_id}

    monkeypatch.setattr(desk, "directory", directory)
    monkeypatch.setattr(desk, "client_card", card)
    identify = desk.identify_caller.fn if hasattr(desk.identify_caller, "fn") else desk.identify_caller

    # Gérard Lacour (blocked) says "tu vas pas me laisser sans viande"; the model tries "Le Comptoir de la Viande".
    ctx = on_call("j", heard="Allez, un seul quartier, tu vas pas me laisser sans viande pour le week-end")
    r = await identify(ctx, said="Le Comptoir de la Viande", client_id=None, wrong_person=False)
    assert r["status"] == "already_identified" and "client" not in r
    r = await identify(ctx, said="Le Comptoir de la Viande", client_id="h", wrong_person=False)
    assert r["status"] == "already_identified"
    # Naming another client is not a correction: "pareil que la Boucherie Peyronnet" must not open Peyronnet's card.
    ctx = on_call("j", heard="Mets-moi pareil que la Boucherie Peyronnet")
    r = await identify(ctx, said="Boucherie Peyronnet", client_id=None, wrong_person=False)
    assert r["status"] == "already_identified"
    # A real correction, in the caller's own words, with the flag: the call moves to that client.
    ctx = on_call("j", heard="Non non, moi c'est Christian, de la Boucherie Peyronnet")
    r = await identify(ctx, said="Christian Boucherie Peyronnet", client_id=None, wrong_person=True)
    assert r == {"status": "found", "client": {"id": "c"}}
    # The flag alone is not enough: the caller's own sentence must name that client.
    ctx = on_call("j", heard="Tu vas pas me laisser sans viande")
    r = await identify(ctx, said="Boucherie Peyronnet", client_id=None, wrong_person=True)
    assert r["status"] == "already_identified"
    # Asking again for the same client is harmless.
    r = await identify(on_call("j", heard="oui"), said="Gérard Lacour à Tulle", client_id=None, wrong_person=False)
    assert r == {"status": "found", "client": {"id": "j"}}


def test_phone_prompt_has_no_named_clients_debts():
    from app.agent.prompts import phone_safe

    text = "\n".join(
        [
            "- Plafond d'encours par client (TTC) ; au-delà, validation par Josette.",
            "- Boucherie Lacour de Tulle (cli_0005) : mauvais payeur, 13 facture échues pour 104 548,27 € TTC — **bloqué**.",
            "- Comptes bloqués : Boucherie Lacour de Tulle (cli_0005), Le Relais du Lac (cli_0006).",
            "- Onglet de bœuf (prd_0015) à zéro.",
        ]
    )
    kept = phone_safe(text)
    assert "Lacour" not in kept and "104" not in kept
    assert "Plafond d'encours" in kept and "Onglet" in kept  # house rules and stock notes stay
