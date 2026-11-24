"""
Outgoing calls « avant le camion » (services/truck_calls.py).

    GET /outbound/truck-calls   the morning's check, for the page: every weighed order of the day, the calls to make
                                (who, what is missing, how much, which truck, when it leaves), the gaps left alone and
                                why, what the calls already settled. Read-only, built in code from the ERP, no model.

To start one of these calls the page sends the call's `startWith` (« /appel ord_… ») as a `text` message on WS /voice:
the agent then speaks first (services/voice_session.py).
"""

from fastapi import APIRouter

from app.services import truck_calls
from app.tools.erp import ErpClient

router = APIRouter(prefix="/outbound", tags=["outbound"])


@router.get("/truck-calls")
async def truck_calls_board() -> dict:
    return await truck_calls.truck_board(ErpClient("voice_agent"))
