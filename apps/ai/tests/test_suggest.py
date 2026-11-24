"""suggest_items (tools/suggest.py): the ranking on crafted facts, then the whole tool on the seed data (read-only;
those tests are skipped when the ERP is not running; run `make reset` first for the exact seed state)."""

import httpx
import pytest

from app.config import settings
from app.tools.erp import ErpClient
from app.tools.suggest import rank, refuses_substitutes, suggest

# ───────────────────────── rank(): pure, crafted facts ─────────────────────────


def product(pid, category="pad-boeuf", caliber=None, active=True):
    return {"id": pid, "name": f"Produit {pid}", "category": category, "unit": "kg", "caliber": caliber, "active": active}


def facts(**over):
    f = {
        "today": "2026-11-24",
        "deliveryDate": "2026-11-26",
        "client": {"id": "cli_x", "status": "active", "preferences": "Accepte les substitutions équivalentes.", "deliveryDays": ["thu"]},
        "inOrder": [],
        "usual": [{"productId": "prd_a", "productName": "A", "unit": "kg", "avgQty": 10, "frequency": 0.8}],
        "products": [product("prd_a"), product("prd_b"), product("prd_c", category="porc"), product("prd_p", category="charcuterie")],
        "stock": [],
        "rules": [],
        "lastYear": {"orders": 50, "products": [
            {"productId": "prd_a", "category": "pad-boeuf", "unit": "kg", "qty": 400, "orders": 40},
            {"productId": "prd_p", "category": "charcuterie", "unit": "kg", "qty": 60, "orders": 5},
        ]},
        "seasons": [{"from": "2025-11-16", "to": "2025-12-06", "orders": 6, "products": []}],
        "christmas": [{"from": "2025-12-15", "to": "2025-12-24", "orders": 4, "products": []}],
    }
    f.update(over)
    return f


def test_habit_missing_from_the_order_is_offered_with_its_reason():
    out = rank(facts())
    assert [(c["productId"], c["reasonKind"]) for c in out] == [("prd_a", "habitude")]
    assert out[0]["qty"] == 10 and out[0]["evidence"]


def test_never_something_already_in_the_order():
    assert rank(facts(inOrder=["prd_a"])) == []


def test_blocked_client_gets_nothing():
    assert rank(facts(client={"id": "cli_x", "status": "blocked", "preferences": ""})) == []


def test_inactive_product_is_never_offered():
    assert rank(facts(products=[product("prd_a", active=False)])) == []


def test_a_staple_is_not_seasonal_but_a_lifted_product_is():
    seasons = [{"from": "2025-11-16", "to": "2025-12-06", "orders": 6, "products": [
        {"productId": "prd_a", "unit": "kg", "qty": 50, "orders": 5},  # 5/6 vs 40/50: bought all year
        {"productId": "prd_p", "unit": "kg", "qty": 30, "orders": 4},  # 4/6 vs 5/50: seasonal
    ]}]
    kinds = {c["productId"]: c["reasonKind"] for c in rank(facts(seasons=seasons))}
    assert kinds == {"prd_p": "l'an dernier", "prd_a": "habitude"}


LOT = {"productId": "prd_b", "lots": [{"qtyRemaining": 30, "expiresAt": "2026-11-28"}]}


def test_lot_in_a_category_the_client_buys():
    out = rank(facts(usual=[], stock=[LOT]))
    assert [(c["productId"], c["reasonKind"]) for c in out] == [("prd_b", "lot à écouler")]


def test_lot_expiring_on_the_delivery_day_is_not_offered():
    lot = {"productId": "prd_b", "lots": [{"qtyRemaining": 30, "expiresAt": "2026-11-26"}]}
    assert rank(facts(usual=[], stock=[lot])) == []


def test_client_refusing_substitutes_only_gets_what_he_bought():
    refuses = {"id": "cli_x", "status": "active", "preferences": "Génisses U+. Aucune substitution sans l'appeler."}
    assert refuses_substitutes(refuses["preferences"])
    assert rank(facts(usual=[], stock=[LOT], client=refuses)) == []  # prd_b: same category, never bought by him
    own = {"productId": "prd_a", "lots": [{"qtyRemaining": 30, "expiresAt": "2026-11-28"}]}
    assert [c["productId"] for c in rank(facts(usual=[], stock=[own], client=refuses))] == ["prd_a"]


RULE = {"id": "prl_0008", "name": "Fêtes 2026 : chair à saucisse −8 % dès 10 kg", "productScope": {"kind": "product", "productId": "prd_p"},
        "minQty": 10, "validFrom": "2026-12-01", "validTo": "2026-12-31"}


def test_promo_only_when_valid_on_the_delivery_date():
    assert rank(facts(usual=[], rules=[RULE])) == []  # delivered 26/11: the offer starts 01/12
    out = rank(facts(usual=[], rules=[RULE], deliveryDate="2026-12-03"))
    assert [(c["productId"], c["reasonKind"], c["qty"]) for c in out] == [("prd_p", "promo", 12)]  # his 12 kg, above the 10 kg


def test_permanent_discount_is_not_a_promo():
    assert rank(facts(usual=[], rules=[{**RULE, "validTo": None, "validFrom": "2025-01-01"}])) == []


def test_reservation_only_for_christmas_deliveries_and_in_time():
    xmas = [{"from": "2025-12-15", "to": "2025-12-24", "orders": 4, "products": [{"productId": "prd_0005", "unit": "kg", "qty": 300, "orders": 4}]}]
    f = dict(usual=[], christmas=xmas, products=[product("prd_0005", category="carcasses", caliber="demi 65-80 kg")],
             lastYear={"orders": 50, "products": [{"productId": "prd_0005", "category": "carcasses", "unit": "kg", "qty": 900, "orders": 12}]})
    assert rank(facts(**f)) == []  # delivered 26/11: not for the holidays
    out = rank(facts(**f, deliveryDate="2026-12-22"))
    assert [(c["productId"], c["reasonKind"], c.get("pieces")) for c in out] == [("prd_0005", "réservation", 1)]
    assert "15/12" in out[0]["reasonText"]
    assert rank(facts(**f, deliveryDate="2026-12-22", today="2026-12-16")) == []  # past the booking deadline


# ───────────────────────── suggest(): the seed data, through the ERP ─────────────────────────


def erp_up() -> bool:
    try:
        return httpx.get(f"{settings.erp_api_url}/api/meta", timeout=2).status_code == 200
    except httpx.HTTPError:
        return False


seed = pytest.mark.skipif(not erp_up(), reason="ERP not running")
KINDS = {"l'an dernier", "réservation", "habitude", "promo", "lot à écouler"}


async def suggested(client_id: str, day: str) -> list[dict]:
    return await suggest(ErpClient("voice_agent"), client_id, day)


async def bought_last_year(client_id: str) -> set[str]:
    got = await ErpClient("voice_agent").get(f"/api/clients/{client_id}/purchases", {"from": "2025-11-24", "to": "2026-11-24"})
    return {r["productId"] for r in got["products"]}


@seed
async def test_seed_peyronnet_thursday():
    out = await suggested("cli_0001", "2026-11-26")
    assert 1 <= len(out) <= 3
    for c in out:
        assert c["reasonKind"] in KINDS and c["reasonText"] and c["evidence"] and c["qty"] > 0
    # Peyronnet refuses substitutions: only products she has bought herself
    assert {c["productId"] for c in out} <= await bought_last_year("cli_0001")


@seed
async def test_seed_blocked_client_gets_nothing():
    assert await suggested("cli_0005", "2026-11-26") == []


@seed
async def test_seed_leroy_refuses_substitutes():
    out = await suggested("cli_0024", "2026-11-26")
    assert {c["productId"] for c in out} <= await bought_last_year("cli_0024")


@seed
async def test_seed_zero_stock_is_never_suggested():
    # ris de veau and onglet are at zero; at Christmas Peyronnet takes 5× more ris de veau than the rest of the year
    for client_id, day in [("cli_0001", "2026-11-26"), ("cli_0001", "2026-12-22"), ("cli_0024", "2026-11-26"), ("cli_0008", "2026-11-26")]:
        ids = {c["productId"] for c in await suggested(client_id, day)}
        assert not ids & {"prd_0015", "prd_0038"}, (client_id, day, ids)


@seed
async def test_seed_sausage_promo_not_before_december():
    assert all(c["reasonKind"] != "promo" for c in await suggested("cli_0008", "2026-11-26"))
    dec = await suggested("cli_0008", "2026-12-03")
    assert ("prd_0047", "promo") in {(c["productId"], c["reasonKind"]) for c in dec}
