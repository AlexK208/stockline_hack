"""Le cadran annoncé (lane B): this week's carcass price move, told once to the butcher, recorded in the ERP.
The numbers and the sentence come from the ERP (apps/backend/app/services/cotation.py); this tool only reads them and,
when there is something to say, records that it was said. No price, order or rule is changed.
One call = one client: the tool takes the caller's client_id, so call_guard (agent/loop.py) refuses any other.
"""

from pydantic import Field

from .erp import enc
from .registry import ToolContext, tool


@tool
async def cotation_semaine(
    ctx: ToolContext,
    client_id: str,
    product_ids: list[str] = Field(description="Les carcasses ou quartiers de sa commande ou de sa question (arrière, avant, demi-carcasse, veau, demi-veau, agneau, demi-porc)"),
) -> dict:
    """
    LA COTATION DE LA SEMAINE. Les carcasses et quartiers suivent la cotation du lundi au cadran de Limoges : leur prix bouge chaque
    semaine, et les bouchers veulent être prévenus. Appelle cet outil UNE fois par appel, dans la même étape que l'écriture de la
    commande (ou que la réponse à sa question de prix), dès qu'il y a une carcasse ou un quartier. S'il renvoie `mustSay`, dis cette
    phrase une fois, avec tes mots et les nombres en toutes lettres : c'est enregistré comme annoncé. Sans `mustSay`, ne dis rien
    sur la cotation (pas de variation, ou déjà annoncée cette semaine). `ifAsked` sert seulement s'il réagit (« encore une hausse ? ») :
    réponds avec, sans remise (seul son commercial peut en parler), et enregistre sa réaction avec log_client_event
    (type price_negotiation, le concurrent cité s'il y en a un).
    """
    info = await ctx.erp.get(f"/api/cotation/client/{enc(client_id)}", {"productIds": ",".join(product_ids)})
    out: dict = {"announcedThisWeek": info["announcedThisWeek"]}
    if info.get("say"):
        moved = [p["productId"] for p in info["products"] if abs(p["delta"]) >= 0.01]
        await ctx.erp.post("/api/cotation/announce", {"clientId": client_id, "productIds": moved})
        out["mustSay"] = info["say"]
    if info.get("ifAsked"):
        out["ifAsked"] = info["ifAsked"]
    out["prices"] = [{k: p[k] for k in ("short", "priceNow", "lastWeekPrice") if k in p} for p in info["products"]]
    return out
