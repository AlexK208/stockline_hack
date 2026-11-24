"""
Tools of the outgoing call « avant le camion » (services/truck_calls.py has the logic and the checks).

    truck_call_brief  the facts of the call: what is missing on today's delivery and why, where the truck is, the
                      client's substitution rule, what can still be loaded (real stock, his price, the lot)
    add_to_truck      a complement on today's truck, after the client's yes
    take_off_truck    a replacement the client does not want leaves the truck (not delivered, not invoiced)

On a call both only work for the caller's own order (agent/loop.py call_guard), and add_to_truck is refused unless
the client's own last sentence is an agreement.
"""

from pydantic import Field

from app.services import truck_calls

from .registry import ToolArgs, ToolContext, tool


class TruckLine(ToolArgs):
    product_id: str = Field(description="id du produit de remplacement accepté par le client (prd_…), lu dans les options du brief")
    qty: float = Field(description="Quantité en kilos acceptée par le client")


@tool
async def truck_call_brief(ctx: ToolContext, order_id: str = Field(description="La commande du jour concernée (ord_…)")) -> dict:
    """
    Appel SORTANT avant le départ du camion : tout ce que tu as le droit de dire sur la livraison de ce matin de ce client.
    Ce qui manque et pourquoi, l'heure de passage prévue, sa règle de substitution, ce qu'on peut encore charger (stock réel,
    son prix, le lot), quand le produit revient. Il t'est fourni au début de l'appel sortant : ne le rappelle que pour le relire.
    N'existe pas pour un appel entrant ordinaire.
    """
    return await truck_calls.truck_brief(ctx.erp, order_id)


@tool
async def add_to_truck(
    ctx: ToolContext,
    order_id: str = Field(description="La commande du jour sur laquelle il manque quelque chose (celle du brief, ord_…)"),
    lines: list[TruckLine] = Field(description="Le ou les produits de remplacement que le client vient d'accepter, avec la quantité"),
) -> dict:
    """
    Appel sortant avant camion : ajoute au camion DE CE MATIN le remplacement que le client vient d'accepter (produit en
    stock, quantité). Crée et confirme le complément en un seul appel : pas de create_draft_order ni de confirm_order.
    Seulement après son OUI sur le produit et la quantité. Refusé par le code si le produit n'est pas en stock aujourd'hui,
    si la quantité dépasse ce qui manque (plus une petite marge, maxComplementKg du brief), ou si un complément existe déjà.
    """
    return await truck_calls.add_complement(ctx.erp, order_id, [{"productId": l.product_id, "qty": l.qty} for l in lines])


@tool
async def take_off_truck(
    ctx: ToolContext,
    order_id: str = Field(description="La commande du jour (celle du brief, ord_…)"),
    product_id: str = Field(description="Le produit de REMPLACEMENT à retirer (replacedBy.productId du brief)"),
) -> dict:
    """
    Appel sortant avant camion : retire du camion de ce matin un produit de remplacement dont le client ne veut pas
    (il ne sera ni livré ni facturé). Ne retire que ce qui a été mis à la place d'un produit manquant, jamais ce que le
    client a commandé lui-même. Seulement quand le client vient de dire qu'il n'en veut pas.
    """
    return await truck_calls.take_off(ctx.erp, order_id, product_id)
