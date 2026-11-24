"""
« Qui est servi d'abord » (services/allocation.py), for the Voix page or any screen a person approves from.

    GET  /outbound/allocation?productId=prd_0011&available=20   both plans (priority, prorata), read-only, no model
    POST /outbound/allocation/apply {"productId", "available", "mode": "priority" | "prorata", "why"}
                                                                 writes the plan a person chose; the quantities are
                                                                 recomputed from the ERP, never taken from the page

After apply, GET /outbound/truck-calls lists the clients who got less than they ordered.
"""

from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services import allocation
from app.services.truck_calls import _board_cache
from app.tools.erp import ErpClient

router = APIRouter(prefix="/outbound", tags=["outbound"])


class ApplyBody(BaseModel):
    productId: str
    available: float
    mode: Literal["priority", "prorata"] = "priority"
    why: str = ""


@router.get("/allocation")
async def allocation_plans(productId: str, available: float) -> dict:
    try:
        return await allocation.propose(ErpClient("voice_agent"), productId, available)
    except ValueError as ex:
        raise HTTPException(400, str(ex)) from ex


@router.post("/allocation/apply")
async def allocation_apply(body: ApplyBody) -> dict:
    try:
        # actor "user": a person approved this plan on screen; the ERP shows it as theirs, not the agent's.
        out = await allocation.apply(ErpClient("user", "Répartition approuvée"), body.productId, body.available, body.mode, body.why)
    except ValueError as ex:
        raise HTTPException(400, str(ex)) from ex
    _board_cache.clear()  # the truck board must show the new loaded quantities at once
    return out
