"""« Date courte » : what will expire unsold, the human price, what the agent may write. No model, no network."""

import json

import pytest

from app.agent.loop import NO_CONSENT_OFFER, call_guard
from app.schemas import ChatMessage, ToolCall
from app.services import short_dated as sd
from app.services.call_report import build_report
from app.services.voice_session import APPROVE_OFFER, OFFER_CALL, OUTGOING, Conversation, outgoing_ack
from app.tools.registry import ToolContext

TODAY = "2026-11-24"


def lot(expires, qty, id="lot"):
    return {"id": f"{id}_{expires[-2:]}", "expiresAt": expires, "qtyRemaining": qty}


# ── what will expire unsold ──


def test_unsold_is_what_expires_minus_what_orders_already_take():
    lots = [lot("2026-11-27", 115.0), lot("2026-11-28", 4.0), lot("2026-12-02", 300.0)]
    rows = sd.expiry_rows(lots, {"2026-11-26": 5.81, "2026-11-27": 5.81}, TODAY)
    assert [(r["useBy"], r["lastDelivery"], r["unsold"], r["tooLate"]) for r in rows] == [("2026-11-27", "2026-11-26", 109.19, False)]
    # the 4 kg that expire on the 28th are less than the minimum worth a call; the lot of 2 December is not short-dated


def test_a_lot_that_must_leave_today_is_too_late_and_is_not_counted_twice():
    lots = [lot("2026-11-25", 134.0), lot("2026-11-27", 204.0)]
    rows = sd.expiry_rows(lots, {TODAY: 111.84, "2026-11-26": 144.84}, TODAY)
    late, sellable = rows
    assert (late["useBy"], late["unsold"], late["tooLate"]) == ("2026-11-25", 22.16, True)  # trucks are loaded: lost
    assert (sellable["useBy"], sellable["unsold"], sellable["tooLate"]) == ("2026-11-27", 171.0, False)  # 193,16 − the 22,16 above


def test_nothing_to_offer_when_orders_already_take_the_lot():
    assert sd.expiry_rows([lot("2026-11-26", 40.0)], {"2026-11-25": 60.0}, TODAY) == []


def test_only_his_delivery_days_before_the_use_by_date_and_never_today():
    assert sd.delivery_days(TODAY, ["tue", "thu"], "2026-11-26") == [{"date": "2026-11-26", "jour": "jeudi 26"}]
    assert sd.delivery_days(TODAY, ["tue", "sat"], "2026-11-26") == []  # no truck goes to him in time: no call
    assert [d["date"] for d in sd.delivery_days(TODAY, [], "2026-11-26")] == ["2026-11-25", "2026-11-26"]


def test_the_approved_price_is_read_back_from_the_note_a_person_wrote():
    body = "Prix approuvé : 6.90 € par kg, jusqu'au 2026-11-26 (à consommer avant le 2026-11-27)\n\n115 kg de Chair à saucisse…"
    m = sd.PRICE_LINE.search(body)
    assert (m.group(1), m.group(3), m.group(4)) == ("6.90", "2026-11-26", "2026-11-27")
    assert not sd.PRICE_LINE.search("On pourrait la vendre à 6,90 € le kilo.")  # a remark is not an approval


def test_the_commands_typed_or_sent_by_the_page():
    assert OFFER_CALL.match("/appel prd_0047 cli_0017").groups() == ("prd_0047", "cli_0017")
    assert APPROVE_OFFER.match("/offre prd_0047 6,90").groups() == ("prd_0047", "6,90")
    assert APPROVE_OFFER.match("/offre prd_0044 9.2 €") and not APPROVE_OFFER.match("/offre prd_0044")
    assert OUTGOING.match("/appel ord_020800") and not OUTGOING.match("/appel prd_0047 cli_0017")  # the truck call is untouched


# ── the rails ──


class NoErp:
    async def get(self, path, query=None):
        raise AssertionError(f"the guard must refuse before reading the ERP ({path})")


def test_nothing_is_sold_without_the_clients_yes():
    call = ToolCall(id="c1", name="take_offer", arguments={"productId": "prd_0044", "qty": 40, "deliveryDate": "2026-11-25"})
    ctx = ToolContext(erp=NoErp(), actor="voice_agent", on_call=True, caller="cli_0004", heard="Bon, mettez-m'en quarante kilos.")
    with pytest.raises(PermissionError) as refused:
        import asyncio

        asyncio.run(call_guard(call, ctx))
    assert str(refused.value) == NO_CONSENT_OFFER.format(heard=ctx.heard)


def test_the_offer_tools_only_serve_the_client_on_the_phone():
    import asyncio

    from app.tools.short_dated import NO_CALLER, short_date_brief, take_offer

    ctx = ToolContext(erp=NoErp(), actor="voice_agent")  # nobody identified
    for tool, args in ((short_date_brief, {"productId": "prd_0044"}), (take_offer, {"productId": "prd_0044", "qty": 5, "deliveryDate": "2026-11-25"})):
        with pytest.raises(ValueError, match=NO_CALLER[:30]):
            asyncio.run(tool.run(args, ctx))


def test_no_instant_word_after_a_no_in_an_outgoing_call():
    offer_call = Conversation(id="o", history=[ChatMessage(role="tool", tool_call_id="x", name="short_date_brief", content="{}")])
    assert outgoing_ack("Je regarde.", offer_call, "Non merci alors, pas cette semaine.") == ""
    assert outgoing_ack("Je corrige.", offer_call, "Non, laissez tomber, je me débrouille.") == ""
    assert outgoing_ack("Je regarde.", offer_call, "C'est quoi la date exactement ?") == "Je regarde."
    assert outgoing_ack("Je regarde.", Conversation(id="in"), "Non, mets plutôt du paleron.") == "Je regarde."  # incoming calls unchanged


# ── the report ──

OFFER = {
    "outgoingCall": True,
    "reason": "short_dated_offer",
    "askFor": {"name": "Marc Teillet"},
    "product": {"id": "prd_0044", "name": "Viande hachée fraîche 15 % MG", "unit": "kg", "useBySay": "avant vendredi 27"},
    "offer": {"pricePerUnit": 9.2, "hisUsualPrice": 11.2},
}
TAKEN = {"id": "ord_1", "number": "CMD-1", "status": "confirmed", "deliveryDate": "2026-11-25", "totalHt": 5540.75,
         "offerLine": "40 kg de Viande hachée fraîche 15 % MG à 9,20 €, soit 368,00 €",
         "lines": [{"productId": "prd_0009", "productName": "Faux-filet", "qty": 12, "unit": "kg"}, {"productId": "prd_0044", "productName": "Viande hachée", "qty": 40, "unit": "kg"}]}  # fmt: skip


def history(*said, rounds=()):
    card = {"status": "found", "client": {"id": "cli_0004", "name": "Cuisine centrale de Saint-Junien"}}
    h = [
        ChatMessage(role="user", content="Allô ?"),
        ChatMessage(role="assistant", content="", tool_calls=[ToolCall(id="a", name="identify_caller", arguments={}), ToolCall(id="b", name="short_date_brief", arguments={})]),
        ChatMessage(role="tool", tool_call_id="a", name="identify_caller", content=json.dumps(card)),
        ChatMessage(role="tool", tool_call_id="b", name="short_date_brief", content=json.dumps(OFFER)),
        ChatMessage(role="assistant", content="Bonjour Monsieur Teillet…"),
    ]
    h += [ChatMessage(role="user", content=s) for s in said]
    for i, (name, result) in enumerate(rounds):
        h.append(ChatMessage(role="assistant", content="", tool_calls=[ToolCall(id=f"r{i}", name=name, arguments={})]))
        h.append(ChatMessage(role="tool", tool_call_id=f"r{i}", name=name, content=json.dumps(result)))
    return h


def test_report_of_an_offer_taken():
    body = build_report(history("Oui, c'est bon.", rounds=[("take_offer", TAKEN)]))["body"]
    assert body["title"] == "Offre date courte : Viande hachée fraîche 15 % MG — 40 kg pris à 9,20 € pour mercredi 25/11"
    assert body["status"] == "resolved" and "offre-date-courte" in body["tags"] and body["orderId"] == "ord_1"
    assert "prix approuvé par l'équipe" in body["description"]


def test_report_of_an_offer_declined_and_of_a_call_nobody_answered():
    body = build_report(history("Non merci, pas cette semaine."))["body"]
    assert body["title"].endswith("refusée par le client") and body["status"] == "resolved" and "orderId" not in body
    assert build_report(history()) is None  # he never said a word: the call is still to make


def test_report_stays_open_when_the_wrong_person_answered():
    body = build_report(history("C'est le commis, le chef arrive à sept heures."))["body"]
    assert body["status"] == "open" and "a-rappeler" in body["tags"]
