"""Write tools: build and edit an order (draft → lines → confirm). Business rules live in the ERP API.

Two guards live here because the ERP only WARNS (TECH.md, piège 2) and a voice agent must not get it wrong:
  - no order is created or confirmed for a blocked account;
  - an order is not confirmed while it still has a line that cannot be delivered (stock at the delivery date)
    or a delivery day on which no truck serves the client.
"""

from pydantic import Field

from .erp import enc, pick
from .history import without_none
from .registry import ToolArgs, ToolContext, tool


class OrderLine(ToolArgs):
    product_id: str
    qty: float = Field(description="Quantité dans l'unité du produit (kg, pièce, caisse…)")
    note: str | None = Field(None, description="ex. « livrer avant 7 h », « bien mûr »")
    substitute_for: str | None = Field(None, description="productId remplacé, si c'est une substitution")

    def to_erp(self) -> dict:
        return self.model_dump(by_alias=True, exclude_none=True)


def summarize_order(o: dict) -> dict:
    """What the model gets back after any order operation: short, with line ids for later edits."""
    return {
        **pick(o, "id", "number", "status"),
        "client": (o.get("client") or {}).get("name"),
        **pick(o, "deliveryDate", "totalHt"),
        "lines": [
            {
                "lineId": line["id"],
                **pick(line, "productId", "productName", "qty", "unit", "unitPrice"),
                **({"note": line["note"]} if line.get("note") else {}),
            }
            for line in o["lines"]
        ],
        "warnings": o.get("warnings") or [],
    }


BLOCKING_WARNINGS = {"client_blocked", "insufficient_stock", "no_route"}


async def refuse_if_blocked(ctx: ToolContext, client_id: str) -> None:
    client = await ctx.erp.get(f"/api/clients/{enc(client_id)}")
    if client.get("status") == "blocked":
        raise ValueError(
            f"Compte bloqué ({client['name']}) : aucune commande tant que la comptabilité n'a pas levé le blocage. "
            "Prends le message (log_client_event), ne promets rien."
        )


@tool
async def create_draft_order(
    ctx: ToolContext,
    client_id: str,
    delivery_date: str | None = Field(None, description="YYYY-MM-DD, optionnel"),
    lines: list[OrderLine] | None = None,
    note: str | None = None,
) -> dict:
    """
    Crée une pré-commande (brouillon) pour un client, avec ou sans lignes. Prix résolus par l'ERP (prix client > catalogue).
    Create a draft order. Delivery date defaults to the client's next delivery day.
    """
    await refuse_if_blocked(ctx, client_id)
    body = {
        "clientId": client_id,
        "deliveryDate": delivery_date,
        "lines": [line.to_erp() for line in lines] if lines is not None else None,
        "note": note,
        "source": "voice_agent" if ctx.actor == "voice_agent" else "web",
    }
    return summarize_order(await ctx.erp.post("/api/orders", without_none(body)))


@tool
async def add_order_line(
    ctx: ToolContext,
    order_id: str,
    product_id: str,
    qty: float = Field(description="Quantité dans l'unité du produit (kg, pièce, caisse…)"),
    note: str | None = Field(None, description="ex. « livrer avant 7 h », « bien mûr »"),
    substitute_for: str | None = Field(None, description="productId remplacé, si c'est une substitution"),
) -> dict:
    """Ajoute une ligne à une commande brouillon ou confirmée. Add a line to an order."""
    line = OrderLine(product_id=product_id, qty=qty, note=note, substitute_for=substitute_for)
    return summarize_order(await ctx.erp.post(f"/api/orders/{enc(order_id)}/lines", line.to_erp()))


@tool
async def confirm_order(ctx: ToolContext, order_id: str) -> dict:
    """
    Confirme une commande : réserve le stock et l'affecte à une tournée. Renvoie des alertes (encours, stock…).
    Only after the caller explicitly agreed to the recap.
    """
    order = await ctx.erp.get(f"/api/orders/{enc(order_id)}")
    blocking = [w["message"] for w in order.get("warnings") or [] if w["code"] in BLOCKING_WARNINGS]
    if blocking:
        raise ValueError("Commande non confirmée, à régler d'abord avec le client : " + " ; ".join(blocking))
    return summarize_order(await ctx.erp.post(f"/api/orders/{enc(order_id)}/confirm"))


@tool
async def get_order(ctx: ToolContext, order_id: str) -> dict:
    """Détail d'une commande (lignes, statut, total, alertes). Order detail."""
    return summarize_order(await ctx.erp.get(f"/api/orders/{enc(order_id)}"))


@tool
async def update_order_line(
    ctx: ToolContext,
    order_id: str,
    line_id: str = Field(description="lineId renvoyé par l'ERP pour cette ligne"),
    qty: float | None = Field(None, description="Nouvelle quantité"),
    product_id: str | None = Field(None, description="Nouveau produit (le prix est recalculé)"),
    note: str | None = None,
    substitute_for: str | None = Field(None, description="productId remplacé, si c'est une substitution acceptée par le client"),
) -> dict:
    """
    Modifie une ligne d'une commande brouillon ou confirmée : quantité, produit, note. À utiliser quand l'appelant change d'avis
    (« finalement mets-en dix », « plutôt de la bavette ») au lieu d'ajouter une deuxième ligne. Change a line of an order.
    """
    body = {"qty": qty, "productId": product_id, "note": note, "substituteFor": substitute_for}
    return summarize_order(await ctx.erp.patch(f"/api/orders/{enc(order_id)}/lines/{enc(line_id)}", without_none(body)))


@tool
async def remove_order_line(ctx: ToolContext, order_id: str, line_id: str = Field(description="lineId de la ligne à retirer")) -> dict:
    """
    Retire une ligne d'une commande brouillon ou confirmée (« finalement non, enlève le… »). Remove a line.
    La dernière ligne d'une commande confirmée ne se retire pas : annule la commande (cancel_order).
    """
    return summarize_order(await ctx.erp.delete(f"/api/orders/{enc(order_id)}/lines/{enc(line_id)}"))


@tool
async def update_order(
    ctx: ToolContext,
    order_id: str,
    delivery_date: str | None = Field(None, description="Nouvelle date de livraison YYYY-MM-DD"),
    note: str | None = Field(None, description="Note de commande, ex. « livrer avant 6 h 30 »"),
) -> dict:
    """Change la date de livraison ou la note d'une commande brouillon ou confirmée. Change delivery date or note."""
    return summarize_order(await ctx.erp.patch(f"/api/orders/{enc(order_id)}", without_none({"deliveryDate": delivery_date, "note": note})))


@tool
async def cancel_order(ctx: ToolContext, order_id: str) -> dict:
    """
    Annule une commande (brouillon, confirmée ou préparée). Seulement si l'appelant le demande explicitement et après le lui avoir
    fait confirmer. Cancel an order, only on the caller's explicit request.
    """
    return summarize_order(await ctx.erp.post(f"/api/orders/{enc(order_id)}/cancel"))
