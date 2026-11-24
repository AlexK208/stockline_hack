"""
Outgoing calls: « avant le camion » (services/truck_calls.py) and « date courte » (services/short_dated.py).

    GET /outbound/truck-calls   the morning's check, for the page: every weighed order of the day, the calls to make
                                (who, what is missing, how much, which truck, when it leaves), the gaps left alone and
                                why, what the calls already settled. Read-only, built in code from the ERP, no model.

To start one of these calls the page sends the call's `startWith` (« /appel ord_… ») as a `text` message on WS /voice:
the agent then speaks first (services/voice_session.py).
"""

from fastapi import APIRouter

from pydantic import BaseModel

from app.services import short_dated, truck_calls
from app.tools.erp import ErpClient

router = APIRouter(prefix="/outbound", tags=["outbound"])


@router.get("/truck-calls")
async def truck_calls_board() -> dict:
    return await truck_calls.truck_board(ErpClient("voice_agent"))


@router.get("/short-dated")
async def short_dated_board() -> dict:
    """Stock that will expire unsold, the price a person approved, who to call, what the calls sold (read-only, no model).
    To call a candidate the page sends his `startWith` (« /appel prd_… cli_… ») as a `text` message on WS /voice."""
    return await short_dated.board(ErpClient("voice_agent"))


class OfferPrice(BaseModel):
    price: float


@router.post("/short-dated/{product_id}/offer")
async def approve_short_dated_offer(product_id: str, body: OfferPrice) -> dict:
    """THE HUMAN STEP: a person sets the price of the offer. Refused below the purchase cost. No call starts without it.
    (Same as typing « /offre prd_… 6,90 » in the Voix page.)"""
    erp = ErpClient("voice_agent")
    erp.headers.pop("x-actor", None)  # recorded as a person's decision, not the agent's
    try:
        return await short_dated.approve(erp, product_id, body.price)
    except ValueError as e:
        from fastapi import HTTPException

        raise HTTPException(status_code=409, detail=str(e)) from None
