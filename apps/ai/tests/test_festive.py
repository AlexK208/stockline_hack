"""Le carnet des fêtes (tools/festive.py): what the agent says from last year's basket, and the one-client guard."""

import pytest

from app.agent.loop import call_guard
from app.schemas import ToolCall
from app.tools import TOOLS, ToolContext, festive


def test_the_four_festive_tools_are_registered():
    assert {"festive_history", "festive_availability", "festive_reserve", "festive_cancel"} <= set(TOOLS)


def test_big_pieces_are_said_in_pieces_small_ones_in_kilos():
    arriere = {"productId": "prd_0001", "productName": "Quartier arrière", "qty": 391.0, "unit": "kg"}
    assert festive._line(arriere, {"caliber": "quartier 90-110 kg"})["say"].startswith("environ 4 pièce")
    ris = {"productId": "prd_0038", "productName": "Ris de veau", "qty": 4.4, "unit": "kg"}
    assert festive._line(ris, {"caliber": None})["say"] == "4.5 kg"  # rounded to the half kilo, no piece weight
    filet = {"productId": "prd_0012", "productName": "Filet", "qty": 17.0, "unit": "kg"}
    assert festive._line(filet, {"caliber": "pièce 2-2,5 kg sous vide"})["say"] == "17 kg"  # a 2 kg piece: kilos


class NoErp:
    async def get(self, path, query=None):
        raise LookupError(path)


@pytest.mark.parametrize("tool", ["festive_history", "festive_availability", "festive_reserve", "festive_cancel"])
async def test_guard_keeps_festive_tools_on_the_callers_account(tool):
    ctx = ToolContext(erp=NoErp(), actor="voice_agent", on_call=True, caller="cli_0001", heard="Pour Noël")
    await call_guard(ToolCall(id="c", name=tool, arguments={"clientId": "cli_0001"}), ctx)  # his own: allowed
    with pytest.raises(PermissionError):
        await call_guard(ToolCall(id="c", name=tool, arguments={"clientId": "cli_0002"}), ctx)


async def test_guard_refuses_festive_tools_before_the_caller_is_identified():
    ctx = ToolContext(erp=NoErp(), actor="voice_agent", on_call=True, caller=None, heard="Pour Noël")
    with pytest.raises(PermissionError):
        await call_guard(ToolCall(id="c", name="festive_reserve", arguments={"clientId": "cli_0001"}), ctx)
