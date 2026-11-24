"""
Tools of the outgoing call « date courte » (services/short_dated.py has the logic and the checks).

    short_date_brief  the facts of the call: the product, its use-by date, the price a person approved, what this
                      client usually takes, his delivery days before the date
    take_offer        the only write of such a call: the line at the approved price, after the client's yes

Both work for the client on the phone only (they take no client id: the caller is the one the call identified), and
take_offer is refused unless the client's own last sentence is an agreement (agent/loop.py call_guard).
"""

from pydantic import Field

from app.services import short_dated

from .registry import ToolContext, tool

NO_CALLER = "Cet outil ne sert que pendant un appel d'offre date courte, pour le client en ligne."


@tool
async def short_date_brief(ctx: ToolContext, product_id: str = Field(description="Le produit de l'offre (prd_…)")) -> dict:
    """
    Appel SORTANT « date courte » : tout ce que tu as le droit de dire sur l'offre faite à ce client. Le produit, sa date
    limite, le prix approuvé par l'équipe, ce qu'il en prend d'habitude, ses jours de livraison avant la date. Il t'est
    fourni au début de l'appel : ne le rappelle que pour le relire. N'existe pas pour un appel entrant ordinaire.
    """
    if not ctx.caller:
        raise ValueError(NO_CALLER)
    return await short_dated.brief(ctx.erp, product_id, ctx.caller)


@tool
async def take_offer(
    ctx: ToolContext,
    product_id: str = Field(description="Le produit de l'offre (prd_…, celui du brief)"),
    qty: float = Field(description="La quantité que le client vient d'accepter (kilos, ou l'unité du produit)"),
    delivery_date: str = Field(description="YYYY-MM-DD : le jour de livraison accepté, un de deliveryOptions du brief"),
) -> dict:
    """
    Appel sortant date courte : écrit l'offre que le client vient d'accepter, au prix approuvé, sur sa commande de ce
    jour-là (créée et confirmée s'il n'en a pas). Un seul appel, pas de create_draft_order ni de confirm_order.
    Seulement après son OUI sur la quantité et le jour. Refusé par le code sans prix approuvé, au-delà de maxQty, ou
    pour un jour de livraison qui tombe après la date limite.
    """
    if not ctx.caller:
        raise ValueError(NO_CALLER)
    return await short_dated.take(ctx.erp, ctx.caller, product_id, qty, delivery_date)
