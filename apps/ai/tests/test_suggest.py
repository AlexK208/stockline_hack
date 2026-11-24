"""suggest_items (tools/suggest.py): the « forgotten from a repeated order » rule on crafted orders, then the whole
tool on the seed data (read-only; skipped when the ERP is not running)."""

import httpx
import pytest

from app.config import settings
from app.tools.erp import ErpClient
from app.tools.suggest import forgotten, suggest

A, B, C, D, E, F = "prd_A", "prd_B", "prd_C", "prd_D", "prd_E", "prd_F"


def orders(basket: dict, times: int, start: int = 1) -> list[dict]:
    return [{"date": f"2026-10-{start + i:02d}", "lines": dict(basket)} for i in range(times)]


USUAL = {A: 200, B: 110, C: 72}  # placed 3 times, identical


# ───────────────────────── the rule, on crafted orders ─────────────────────────


def test_one_forgotten_product_of_a_three_times_repeated_order_is_offered():
    got = forgotten(orders(USUAL, 3), {A, C})
    assert got["missing"] == [B] and got["times"] == 3 and got["qty"][B] == 110


def test_two_forgotten_products_are_offered_together():
    usual = {A: 1, B: 1, C: 1, D: 1, E: 1, F: 1}  # 2 of 6 missing = 33 %
    got = forgotten(orders(usual, 3), {A, B, C, D})
    assert got["missing"] == [E, F]


def test_not_repeated_three_times_gives_nothing():
    assert forgotten(orders(USUAL, 2), {A, C}) is None


def test_more_than_35_percent_missing_gives_nothing():
    assert forgotten(orders({A: 1, B: 1}, 5), {A}) is None  # 1 of 2 = 50 %
    assert forgotten(orders({A: 1, B: 1, C: 1, D: 1, E: 1}, 5), {A, B, C}) is None  # 2 of 5 = 40 %


def test_three_missing_gives_nothing_even_under_35_percent():
    usual = {f"p{i}": 1 for i in range(10)}
    assert forgotten(orders(usual, 3), {f"p{i}" for i in range(7)}) is None  # 3 of 10 = 30 %, but 3 missing


def test_more_than_two_extra_products_gives_nothing():
    assert forgotten(orders(USUAL, 3), {A, C, D, E, F}) is None  # 1 missing, 3 extra: another order


def test_more_than_three_differences_gives_nothing():
    usual = {A: 1, B: 1, C: 1, D: 1, E: 1, F: 1}
    assert forgotten(orders(usual, 3), {A, B, C, D, "x", "y"}) is None  # 2 missing + 2 extra = 4


def test_an_order_with_nothing_missing_gives_nothing():
    assert forgotten(orders(USUAL, 3), {A, B, C}) is None
    assert forgotten(orders(USUAL, 3), {A, B, C, D}) is None  # only an extra product: nothing forgotten


def test_an_empty_order_gives_nothing():
    assert forgotten(orders(USUAL, 3), set()) is None


def test_the_closest_repeated_order_wins():
    history = orders(USUAL, 3) + orders({A: 1, C: 1, D: 1, E: 1}, 4, start=10)
    got = forgotten(history, {A, C, D})  # missing B from USUAL (+1 extra D), or E from the other one (no extra)
    assert got["missing"] == [E] and got["times"] == 4


def test_the_usual_quantity_is_the_median_of_the_repeated_orders():
    history = [{"date": f"2026-10-0{i}", "lines": {A: 200, B: q, C: 70}} for i, q in enumerate((100, 110, 130), 1)]
    assert forgotten(history, {A, C})["qty"][B] == 110


# ───────────────────────── edge cases (common sense) ─────────────────────────


def test_a_product_removed_or_declined_during_the_call_is_never_offered_back():
    assert forgotten(orders(USUAL, 3), {A, C}, declined={B}) is None  # « enlève l'avant » / « pas d'avant cette semaine »
    usual = {A: 1, B: 1, C: 1, D: 1, E: 1, F: 1}
    assert forgotten(orders(usual, 3), {A, B, C, D}, declined={E})["missing"] == [F]  # only the other one


def test_a_swap_for_a_similar_product_is_not_forgotten():
    cat = {A: "carcasses", B: "porc", C: "veau", "prd_X": "porc"}
    assert forgotten(orders(USUAL, 3), {A, C, "prd_X"}, category=cat) is None  # B swapped for X (same category)
    cat_other = {**cat, "prd_X": "abats"}
    assert forgotten(orders(USUAL, 3), {A, C, "prd_X"}, category=cat_other)["missing"] == [B]  # not a swap


def test_equally_close_repeated_orders_pick_the_most_recent_one():
    older = orders({A: 1, B: 1, C: 1}, 3, start=1)
    newer = orders({A: 1, C: 1, D: 1}, 3, start=20)
    got = forgotten(older + newer, {A, C})
    assert got["missing"] == [D]  # same distance, same count: the most recent wins, every time


# ───────────────────────── suggest(): the seed data, through the ERP ─────────────────────────


def erp_up() -> bool:
    try:
        return httpx.get(f"{settings.erp_api_url}/api/meta", timeout=2).status_code == 200
    except httpx.HTTPError:
        return False


seed = pytest.mark.skipif(not erp_up(), reason="ERP not running")


async def suggested(client_id: str, day: str) -> list[dict]:
    return await suggest(ErpClient("voice_agent"), client_id, day)


@seed
async def test_seed_no_open_order_means_nothing_to_compare():
    # Peyronnet has no order yet for Thursday 26/11 in the seed: no current order, nothing can be « forgotten »
    assert await suggested("cli_0001", "2026-11-26") == []


@seed
async def test_seed_blocked_client_gets_nothing():
    assert await suggested("cli_0005", "2026-11-26") == []


@seed
async def test_seed_christmas_week_is_left_to_the_carnet_des_fetes():
    assert await suggested("cli_0001", "2026-12-22") == []
