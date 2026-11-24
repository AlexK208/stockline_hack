"""/api/cotation: le cadran annoncé (this week's carcass price moves, told to the butchers). Rules in services/cotation.py."""

from typing import Any

from fastapi import APIRouter, Query
from pydantic import Field

from app.dependencies import CtxDep
from app.schemas.base import Input
from app.services import cotation

router = APIRouter(prefix="/api/cotation", tags=["cotation"])


class AnnounceInput(Input):
    client_id: str
    product_ids: list[str] | None = None
    reaction: str | None = Field(None, description="What the client said back (« encore une hausse ? », a competitor's price…)")


@router.get("/client/{client_id}")
async def cotation_for_client(client_id: str, product_ids: str | None = Query(None, alias="productIds")) -> dict[str, Any]:
    """This week's move on each carcass product the client buys: today's price for him, last week's, a month ago,
    the sentence to say (only if it moved and he was not told yet this week)."""
    return cotation.for_client(client_id, [p for p in (product_ids or "").split(",") if p] or None)


@router.post("/announce")
async def cotation_announce(body: AnnounceInput, ctx: CtxDep) -> dict[str, Any]:
    """Record that the client was told this week's move (one client event tagged cotation-annoncee), with his reaction."""
    return cotation.announce(ctx, body.data())


@router.get("/board")
async def cotation_board() -> dict[str, Any]:
    """The week: every client who bought carcasses in the last 60 days, told or not yet, with his move."""
    return cotation.board()
