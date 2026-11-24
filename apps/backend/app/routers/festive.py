"""/api/festive: le carnet des fêtes (Christmas and New Year reservations). Rules in services/festive.py."""

from typing import Any

from fastapi import APIRouter, Query
from pydantic import Field

from app.dependencies import CtxDep
from app.schemas.base import Input
from app.services import festive

router = APIRouter(prefix="/api/festive", tags=["festive"])


class FestiveLineInput(Input):
    product_id: str
    qty: float | int = Field(description="Quantité dans l'unité du produit (kilos le plus souvent)")
    note: str | None = None


class FestiveReservationInput(Input):
    client_id: str
    delivery_date: str = Field(description="YYYY-MM-DD, entre le 19 et le 24/12 (Noël) ou le 26 et le 31/12 (Nouvel An)")
    lines: list[FestiveLineInput]
    replace: bool = Field(False, description="True: each line's qty is the new total for that piece (default: added to it)")


@router.get("/history/{client_id}")
async def festive_history(client_id: str) -> dict[str, Any]:
    """The client's holiday basket last year (per window, biggest first) and his reservations this year."""
    return festive.history(client_id)


@router.get("/availability")
async def festive_availability(
    product_ids: str = Query(alias="productIds", description="Comma list of product ids"),
    client_id: str | None = Query(None, alias="clientId"),
) -> dict[str, Any]:
    """Per piece and window: capacity (scarce pieces only), reserved, waitlist, left, the client's guaranteed share."""
    return festive.availability([p for p in product_ids.split(",") if p], client_id or None)


@router.get("/reservations")
async def festive_reservations(
    client_id: str | None = Query(None, alias="clientId"), window: str | None = Query(None, description="noel | nouvel_an")
) -> list[dict[str, Any]]:
    return festive.list_reservations(client_id or None, window or None)


@router.post("/reservations")
async def festive_reserve(body: FestiveReservationInput, ctx: CtxDep) -> dict[str, Any]:
    """Reserve volumes for one delivery date. All lines are checked first: on a problem nothing is written.
    Scarce pieces: up to the client's guaranteed share or what is left; the rest goes on the waiting list."""
    return festive.reserve(ctx, body.data())


@router.post("/reservations/{id}/cancel")
async def festive_cancel(id: str, ctx: CtxDep) -> dict[str, Any]:
    """Cancel; the freed volume goes to the waiting list, oldest first."""
    return festive.cancel(ctx, id)


@router.get("/board")
async def festive_board() -> dict[str, Any]:
    """Damien's view: scarce pieces per window (capacity, reserved, waitlist, who), other reserved pieces, and the
    holiday requests still only written as text in a client's history."""
    return festive.board()
