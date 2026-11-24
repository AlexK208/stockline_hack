"""« Avant le camion » : which lines deserve a call, what a complement may be, what the report says. No model, no network."""

import asyncio
import json

import pytest

from app.agent.loop import NO_CONSENT_TRUCK, call_guard
from app.schemas import ChatMessage, ToolCall
from app.services import truck_calls as tc
from app.services.call_report import build_report
from app.services.voice_session import OUTGOING
from app.tools.registry import ToolContext

TODAY = "2026-11-24"


def line(product, qty, loaded, price=20.0, **extra):
    return {"id": f"lin_{product}", "productId": product, "productName": product, "unit": "kg", "qty": qty, "preparedQty": loaded, "unitPrice": price, **extra}


# ── which lines deserve a call ──


def test_a_missing_product_is_always_a_call():
    g = tc.line_gap(line("onglet", 4.5, 0.0, 20.16))
    assert g["kind"] == "missing" and g["call"] and g["amount"] == -90.72


def test_a_normal_weighing_is_not_a_gap():
    assert tc.line_gap(line("paleron", 7.5, 7.39)) is None  # −1,5 %
    assert tc.line_gap(line("faux-filet", 6.5, 6.71)) is None  # +3 %


def test_five_percent_over_for_a_few_euros_is_seen_but_nobody_is_called():
    g = tc.line_gap(line("bavette", 9.0, 9.45, 17.09))  # exactly +5 %, 7,69 €
    assert g["kind"] == "over" and not g["call"] and g["amount"] == 7.69


def test_a_short_weight_is_a_call_only_when_it_is_worth_it():
    assert not tc.line_gap(line("joue", 2.0, 1.8, 13.6))["call"]  # −10 % but 2,72 €
    assert tc.line_gap(line("cote", 10.0, 8.5, 31.5))["call"]  # −15 %, 47 €


def test_a_heavy_overweight_is_a_call():
    assert tc.line_gap(line("filet", 10.0, 11.5, 44.0))["call"]  # +66 € the client did not order


def test_a_product_already_replaced_on_the_order_is_a_call_to_inform_not_a_missing_product():
    order = {"lines": [
        line("prd_0015", 5.0, 0.0, 20.16),
        line("prd_0014", 5.0, 5.0, 17.09, substituteFor="prd_0015", note="Remplace Onglet de bœuf (accord client)"),
        line("prd_0009", 6.5, 6.71, 24.48),
    ]}  # fmt: skip
    (g,) = tc.order_gaps(order)
    assert g["kind"] == "replaced" and g["call"]
    assert g["replacedBy"]["productId"] == "prd_0014" and g["replacedBy"]["amount"] == 85.45
    assert g["amount"] == -15.35  # 100,80 € of onglet less, 85,45 € of bavette more


def test_substitution_rule_is_read_from_the_clients_file_and_never_assumed():
    assert tc.substitution_rule("Livré mar. jeu. Refuse les substitutions : appeler avant toute modification.")[0] == "refuse"
    assert tc.substitution_rule("Côte maturée le lundi. Accepte les substitutions équivalentes si on prévient.")[0] == "ok"
    assert tc.substitution_rule("Livré le mardi.") == ("ask", "")
    assert tc.substitution_rule(None)[0] == "ask"


def test_arrival_time_is_said_rounded():
    assert tc.say_time("05:51") == "5 h 50" and tc.say_time("05:33") == "5 h 35" and tc.say_time("05:58") == "6 h"


def test_house_substitutes_are_read_from_the_glossary(tmp_path):
    (tmp_path / "context").mkdir()
    (tmp_path / "context" / "03-glossaire-produits.md").write_text(
        "## Substitutions habituelles\n\n- Onglet de bœuf (prd_0015) → Bavette d'aloyau PAD (prd_0014)\n- Ris (prd_0038) → Rognon (prd_0039)\n", encoding="utf-8"
    )
    assert tc.house_substitutes(tmp_path) == {"prd_0015": "prd_0014", "prd_0038": "prd_0039"}


def test_the_outgoing_command_is_exact():
    assert OUTGOING.match("/appel ord_020798").group(1) == "ord_020798"
    assert OUTGOING.match("  /APPEL ord_1 ")
    assert not OUTGOING.match("Bonjour, /appel ord_020798") and not OUTGOING.match("/appel cli_0013")


# ── the writes, against a small fake ERP ──


class FakeErp:
    def __init__(self, order, stock=None, existing=None):
        self.order, self.stock, self.existing = order, stock or {}, existing or []
        self.posts, self.patches = [], []

    async def get(self, path, query=None):
        if path == "/api/meta":
            return {"today": TODAY, "company": "Chevillard du Limousin"}
        if path == f"/api/orders/{self.order['id']}":
            return self.order
        if path.startswith("/api/orders/"):
            return next(o for o in self.existing if path.endswith(o["id"]))
        if path == "/api/orders":
            return self.existing
        if path == "/api/route-runs":
            return [{"route": {"name": "Tournée Corrèze", "driver": "Laurent", "departureTime": "04:45"}, "stops": [{"orderId": self.order["id"], "eta": "05:51", "seq": 3}]}]
        if path == "/api/stock/availability":
            return [{"productId": i, "availableOn": self.stock.get(i, 0)} for i in query["productIds"].split(",")]
        if path.endswith("/alternatives"):
            return [{"id": i, "name": i, "available": q} for i, q in self.stock.items()]
        if path.startswith("/api/products/"):
            return {"id": path.rsplit("/", 1)[-1], "name": path.rsplit("/", 1)[-1], "origin": "Haute-Vienne", "stock": {"lots": []}, "movements": []}
        if path == "/api/prices/resolve":
            return {"price": 17.09}
        if path == "/api/purchase-orders":
            return []
        if path.endswith("/usual"):
            return []
        raise AssertionError(f"unexpected GET {path}")

    async def post(self, path, body=None):
        self.posts.append((path, body))
        if path == "/api/orders":
            return {"id": "ord_new", **body}
        return {"id": "ord_new", "number": "CMD-NEW", "status": "confirmed", "deliveryDate": TODAY, "totalHt": 76.91,
                "lines": [{"id": "lin_new", "productId": "prd_0014", "productName": "Bavette d'aloyau PAD", "qty": 4.5, "unit": "kg", "unitPrice": 17.09}]}  # fmt: skip

    async def patch(self, path, body=None):
        self.patches.append((path, body))
        return {**self.order, "lines": [{**l, **body} if path.endswith(l["id"]) else l for l in self.order["lines"]]}


def leroy(**extra):
    return {
        "id": "ord_020800", "number": "CMD-2026-006238", "status": "prepared", "deliveryDate": TODAY,
        "client": {"id": "cli_0024", "name": "Restaurant Leroy", "preferences": "Refuse les substitutions : appeler avant toute modification.", "contacts": [{"name": "Nicolas Peyrat", "role": "Chef-patron"}]},
        "lines": [line("prd_0015", 4.5, 0.0, 20.16), line("prd_0009", 9.5, 9.44, 24.48)],
        **extra,
    }  # fmt: skip


def run(coro):
    return asyncio.run(coro)


def test_brief_follows_the_clients_rule_and_caps_the_complement():
    brief = run(tc.truck_brief(FakeErp(leroy(), {"prd_0014": 400}), "ord_020800"))
    assert brief["substitution"] == "refuse" and "AUCUN produit" in brief["do"]
    assert brief["maxComplementKg"] == 9.0 and brief["truck"]["etaSay"] == "vers 5 h 50"
    assert brief["problems"][0]["options"][0]["productId"] == "prd_0014"


def test_no_brief_and_no_call_when_nothing_is_missing():
    full = leroy(lines=[line("prd_0009", 9.5, 9.44, 24.48)])
    with pytest.raises(ValueError, match="aucun appel"):
        run(tc.truck_brief(FakeErp(full), "ord_020800"))


def test_complement_is_written_dated_today_and_confirmed():
    erp = FakeErp(leroy(), {"prd_0014": 400})
    result = run(tc.add_complement(erp, "ord_020800", [{"productId": "prd_0014", "qty": 4.5}]))
    (path, body), (confirm, _) = erp.posts
    assert path == "/api/orders" and body["deliveryDate"] == TODAY and body["clientId"] == "cli_0024"
    assert body["lines"] == [{"productId": "prd_0014", "qty": 4.5, "substituteFor": "prd_0015"}]
    assert body["note"].startswith(tc.COMPLEMENT_NOTE) and confirm.endswith("/confirm")
    assert result["status"] == "confirmed" and result["truck"]["etaSay"] == "vers 5 h 50"


def test_complement_is_refused_above_twice_what_is_missing():
    erp = FakeErp(leroy(), {"prd_0009": 400})
    with pytest.raises(ValueError, match="Trop pour un complément"):
        run(tc.add_complement(erp, "ord_020800", [{"productId": "prd_0009", "qty": 20}]))
    assert not erp.posts


def test_complement_is_refused_without_stock_today():
    erp = FakeErp(leroy(), {"prd_0014": 2.0})
    with pytest.raises(ValueError, match="Pas assez de stock"):
        run(tc.add_complement(erp, "ord_020800", [{"productId": "prd_0014", "qty": 4.5}]))
    assert not erp.posts


def test_complement_is_written_once():
    done = {"id": "ord_c", "number": "CMD-C", "source": "voice_agent", "note": f"{tc.COMPLEMENT_NOTE} du mardi 24", "totalHt": 76.91,
            "lines": [{"productName": "Bavette", "qty": 4.5, "unit": "kg"}]}  # fmt: skip
    erp = FakeErp(leroy(), {"prd_0014": 400}, existing=[done])
    with pytest.raises(ValueError, match="déjà dans le camion"):
        run(tc.add_complement(erp, "ord_020800", [{"productId": "prd_0014", "qty": 4.5}]))
    assert not erp.posts


def test_only_a_replacement_can_be_taken_off_the_truck():
    order = leroy(lines=[line("prd_0015", 5.0, 0.0), line("prd_0014", 5.0, 5.0, 17.09, substituteFor="prd_0015"), line("prd_0009", 6.5, 6.7)])
    erp = FakeErp(order)
    with pytest.raises(ValueError, match="pas un remplacement"):
        run(tc.take_off(erp, "ord_020800", "prd_0009"))  # what he ordered himself stays
    result = run(tc.take_off(erp, "ord_020800", "prd_0014"))
    assert erp.patches[0][1]["preparedQty"] == 0 and "Bavette" not in result["removed"] and result["removed"].startswith("5 kg")


def test_nothing_goes_on_the_truck_without_the_clients_yes():
    call = ToolCall(id="c1", name="add_to_truck", arguments={"orderId": "ord_020800", "lines": []})
    ctx = ToolContext(erp=FakeErp(leroy()), actor="voice_agent", on_call=True, caller="cli_0024", heard="Mettez-moi quatre kilos et demi de bavette alors.")
    with pytest.raises(PermissionError) as refused:
        run(call_guard(call, ctx))
    assert str(refused.value) == NO_CONSENT_TRUCK.format(heard=ctx.heard)
    ctx.heard = "Oui, allez-y."
    run(call_guard(call, ctx))  # his own order, and he said yes


# ── the report of an outgoing call ──


def history(brief, *rounds, answers=1):
    card = {"status": "found", "client": {"id": "cli_0024", "name": "Restaurant Leroy"}}
    h = [
        ChatMessage(role="user", content="Allô ?"),
        ChatMessage(role="assistant", content="", tool_calls=[ToolCall(id="a", name="identify_caller", arguments={}), ToolCall(id="b", name="truck_call_brief", arguments={})]),
        ChatMessage(role="tool", tool_call_id="a", name="identify_caller", content=json.dumps(card)),
        ChatMessage(role="tool", tool_call_id="b", name="truck_call_brief", content=json.dumps(brief)),
        ChatMessage(role="assistant", content="Bonjour Monsieur Peyrat…"),
    ]
    for _ in range(answers):
        h.append(ChatMessage(role="user", content="Oui, allez-y."))
    for i, (name, result) in enumerate(rounds):
        h.append(ChatMessage(role="assistant", content="", tool_calls=[ToolCall(id=f"r{i}", name=name, arguments={})]))
        h.append(ChatMessage(role="tool", tool_call_id=f"r{i}", name=name, content=json.dumps(result)))
    return h


BRIEF = {
    "outgoingCall": True,
    "order": {"id": "ord_020800", "number": "CMD-2026-006238"},
    "truck": {"route": "Tournée Corrèze", "departure": "04:45"},
    "problems": [{"kind": "missing", "productName": "Onglet de bœuf", "ordered": 4.5, "onTruck": 0.0, "unit": "kg", "why": "Lot déclassé"}],
}
COMPLEMENT = {"id": "ord_new", "number": "CMD-NEW", "status": "confirmed", "deliveryDate": TODAY, "totalHt": 76.91,
              "lines": [{"productName": "Bavette d'aloyau PAD", "qty": 4.5, "unit": "kg"}]}  # fmt: skip


def test_report_of_a_call_that_put_a_complement_on_the_truck():
    report = build_report(history(BRIEF, ("add_to_truck", COMPLEMENT)))
    body = report["body"]
    assert body["title"] == "Appel avant camion : Onglet de bœuf manquant — remplacé par 4,5 kg Bavette d'aloyau PAD"
    assert body["status"] == "resolved" and "appel-camion" in body["tags"] and body["orderId"] == "ord_020800"
    assert "76,91 € HT" in body["description"] and report["settles"] == "ord_020800"


def test_report_when_the_client_wants_nothing():
    body = build_report(history(BRIEF))["body"]
    assert body["title"].endswith("client prévenu, pas de remplacement") and body["status"] == "resolved"


def test_no_report_when_the_client_never_said_a_word():
    assert build_report(history(BRIEF, answers=0)) is None  # started twice, cut at once: the call is still to make


def test_report_stays_open_when_the_agent_left_something_for_the_team():
    logged = ("log_client_event", {"id": "cev_1", "title": "Chef absent, à rappeler"})
    report = build_report(history(BRIEF, logged))
    assert report["body"]["status"] == "open" and report["settles"] is None and "Chef absent" in report["body"]["description"]
    with_complement = build_report(history(BRIEF, logged, ("add_to_truck", COMPLEMENT)))
    assert with_complement["body"]["status"] == "resolved" and with_complement["settles"] == "ord_020800"


def test_report_when_the_client_refuses_the_replacement_already_loaded():
    brief = {**BRIEF, "problems": [{**BRIEF["problems"][0], "kind": "replaced", "replacedBy": {"productName": "Bavette d'aloyau PAD", "qty": 5.0, "unit": "kg"}}]}
    kept = build_report(history(brief))["body"]
    assert kept["title"] == "Appel avant camion : Onglet de bœuf remplacé — client prévenu, garde 5 kg Bavette d'aloyau PAD"
    gone = build_report(history(brief, ("take_off_truck", {"number": "CMD-2026-006238", "removed": "5 kg Bavette d'aloyau PAD"})))["body"]
    assert gone["title"].endswith("remplacement refusé par le client, retiré du camion") and "non facturé" in gone["description"]
