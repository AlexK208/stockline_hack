"""Le cadran annoncé (tools/cotation.py): say the week's move once, record it, stay silent otherwise; one client per call."""

import pytest

from app.agent.loop import call_guard
from app.schemas import ToolCall
from app.tools import TOOLS, ToolContext, cotation


class FakeErp:
    def __init__(self, info):
        self.info, self.posted = info, []

    async def get(self, path, query=None):
        assert path == "/api/cotation/client/cli_0001"
        return self.info

    async def post(self, path, body=None):
        self.posted.append((path, body))
        return {"announced": True}


MOVED = {
    "announcedThisWeek": False,
    "say": "Cette semaine, l'arrière a pris 5 centimes, à 10 euros 20 le kilo : c'est la cotation de lundi au cadran de Limoges.",
    "ifAsked": "Sur un mois, l'arrière est passé de 9 euros 77 à 10 euros 20 le kilo…",
    "products": [
        {"productId": "prd_0001", "short": "l'arrière", "priceNow": 10.2, "lastWeekPrice": 10.15, "delta": 0.05},
        {"productId": "prd_0002", "short": "l'avant", "priceNow": 6.11, "lastWeekPrice": 6.11, "delta": 0.0},
    ],
}


def ctx(erp):
    return ToolContext(erp=erp, actor="voice_agent")


def test_registered():
    assert "cotation_semaine" in TOOLS


async def test_a_move_is_said_and_recorded_for_the_products_that_moved_only():
    erp = FakeErp(MOVED)
    out = await cotation.cotation_semaine.fn(ctx(erp), client_id="cli_0001", product_ids=["prd_0001", "prd_0002"])
    assert out["mustSay"].startswith("Cette semaine")
    assert erp.posted == [("/api/cotation/announce", {"clientId": "cli_0001", "productIds": ["prd_0001"]})]


async def test_nothing_to_say_records_nothing():
    erp = FakeErp({"announcedThisWeek": True, "products": MOVED["products"]})  # already told this week: no `say`
    out = await cotation.cotation_semaine.fn(ctx(erp), client_id="cli_0001", product_ids=["prd_0001"])
    assert "mustSay" not in out and erp.posted == []


class NoErp:
    async def get(self, path, query=None):
        raise LookupError(path)


async def test_guard_keeps_it_on_the_callers_account():
    c = ToolContext(erp=NoErp(), actor="voice_agent", on_call=True, caller="cli_0001", heard="deux arrières")
    await call_guard(ToolCall(id="c", name="cotation_semaine", arguments={"clientId": "cli_0001", "productIds": ["prd_0001"]}), c)
    with pytest.raises(PermissionError):
        await call_guard(ToolCall(id="c", name="cotation_semaine", arguments={"clientId": "cli_0002", "productIds": ["prd_0001"]}), c)
