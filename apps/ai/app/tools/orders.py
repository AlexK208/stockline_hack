"""Write tools: build and edit an order (draft → lines → confirm). Business rules live in the ERP API.

Two guards live here because the ERP only WARNS (TECH.md, piège 2) and a voice agent must not get it wrong:
  - no order is created or confirmed for a blocked account;
  - an order is not confirmed while it still has a line that cannot be delivered (stock at the delivery date)
    or a delivery day on which no truck serves the client.
"""

from pydantic import Field

from . import desk
from .erp import enc, pick
from .history import without_none
from .registry import ToolArgs, ToolContext, tool


class OrderLine(ToolArgs):
    product_id: str
    qty: float | None = Field(None, description="Quantité en kilos (ou dans l'unité du produit)")
    pieces: float | None = Field(None, description="Nombre de pièces si l'appelant parle en pièces (« deux arrières », « un agneau ») : converti en kilos")
    note: str | None = Field(None, description="ex. « génisse de chez Dumontet », « livrer avant 7 h »")
    substitute_for: str | None = Field(None, description="productId remplacé, si c'est une substitution acceptée par le client")

    def to_erp(self, qty: float) -> dict:
        return without_none({"productId": self.product_id, "qty": qty, "note": self.note, "substituteFor": self.substitute_for})


NOT_WRITTEN = "Rien n'a été écrit dans l'ERP. Explique ces points au client, puis rappelle l'outil avec ce qu'il décide."


async def checked_lines(ctx: ToolContext, client_id: str, delivery_date: str, lines: list[OrderLine]) -> tuple[list[dict], dict | None]:
    """Check the lines for that client and date (stock at the date, lead time, delivery day, pieces → kilos).
    → (ERP lines ready to write, None) when all is fine, else ([], what to tell the model: nothing is written)."""
    items = [desk.Item(product_id=l.product_id, qty=l.qty, pieces=l.pieces) for l in lines]
    checked = await desk.check_items(ctx.erp, client_id, delivery_date, items)
    problems = desk.problems_of(checked)
    if problems:
        return [], {"written": False, "problems": problems, "instruction": NOT_WRITTEN, **checked}
    return [l.to_erp(row["qty"]) for l, row in zip(lines, checked["items"])], None


def estimates(order: dict, erp_lines: list[dict], lines: list[OrderLine]) -> dict:
    """Adds, for lines given in pieces, the reminder that the weight is an estimate."""
    said = [f"{desk.fmt(l.pieces)} pièce(s) ≈ {desk.fmt(e['qty'])} kg" for l, e in zip(lines, erp_lines) if l.pieces and l.qty is None]
    return {**order, **({"estimatedFromPieces": said, "say": "poids estimé, facturé au poids réel"} if said else {})}


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
    Crée une pré-commande (brouillon) pour un client, avec toutes ses lignes d'un coup. L'outil vérifie lui-même, pour la date de
    livraison : stock à la date (arrivages compris), délai de commande, jour de livraison du client, et convertit les pièces en kilos.
    S'il y a un problème il N'ÉCRIT RIEN et renvoie `problems` : explique-les au client. Sinon il renvoie la commande (prix du client).
    Inutile d'appeler check_products avant. Delivery date defaults to the client's next delivery day.
    """
    await refuse_if_blocked(ctx, client_id)
    erp_lines: list[dict] = []
    if lines:
        delivery_date = delivery_date or await desk.default_delivery_date(ctx.erp, client_id)
        erp_lines, refusal = await checked_lines(ctx, client_id, delivery_date, lines)
        if refusal:
            return refusal
    body = {
        "clientId": client_id,
        "deliveryDate": delivery_date,
        "lines": erp_lines if lines is not None else None,
        "note": note,
        "source": "voice_agent" if ctx.actor == "voice_agent" else "web",
    }
    order = summarize_order(await ctx.erp.post("/api/orders", without_none(body)))
    return estimates(order, erp_lines, lines or [])


@tool
async def add_order_line(
    ctx: ToolContext,
    order_id: str,
    product_id: str,
    qty: float | None = Field(None, description="Quantité en kilos (ou dans l'unité du produit)"),
    pieces: float | None = Field(None, description="Nombre de pièces si l'appelant parle en pièces : converti en kilos"),
    note: str | None = Field(None, description="ex. « livrer avant 7 h », « bien mûr »"),
    substitute_for: str | None = Field(None, description="productId remplacé, si c'est une substitution acceptée par le client"),
) -> dict:
    """
    Ajoute une ligne à une commande brouillon ou confirmée. Vérifie lui-même stock à la date de la commande, délai et conversion
    pièces → kilos : en cas de problème il n'écrit rien et renvoie `problems`. Add a line to an order.
    """
    order = await ctx.erp.get(f"/api/orders/{enc(order_id)}")
    line = OrderLine(product_id=product_id, qty=qty, pieces=pieces, note=note, substitute_for=substitute_for)
    erp_lines, refusal = await checked_lines(ctx, order["clientId"], order["deliveryDate"], [line])
    if refusal:
        return refusal
    updated = summarize_order(await ctx.erp.post(f"/api/orders/{enc(order_id)}/lines", erp_lines[0]))
    return estimates(updated, erp_lines, [line])


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
    qty: float | None = Field(None, description="Nouvelle quantité TOTALE de la ligne (pas la quantité ajoutée) : « rajoute cinq kilos » sur une ligne de sept = 12"),
    pieces: float | None = Field(None, description="Nouvelle quantité en pièces, si l'appelant parle en pièces"),
    product_id: str | None = Field(None, description="Nouveau produit (le prix est recalculé)"),
    note: str | None = None,
    substitute_for: str | None = Field(None, description="productId remplacé, si c'est une substitution acceptée par le client"),
) -> dict:
    """
    Modifie une ligne d'une commande brouillon ou confirmée : quantité, produit, note. À utiliser quand l'appelant change d'avis
    (« finalement mets-en dix », « plutôt de la bavette ») au lieu d'ajouter une deuxième ligne. Vérifie lui-même le stock à la date
    et le délai pour la nouvelle quantité ou le nouveau produit : en cas de problème il n'écrit rien et renvoie `problems`.
    """
    if qty is not None or pieces is not None or product_id is not None:
        order = await ctx.erp.get(f"/api/orders/{enc(order_id)}")
        current = next((l for l in order["lines"] if l["id"] == line_id), None)
        if current is None:
            raise ValueError(f"Ligne {line_id} introuvable sur cette commande : relis ses lignes avec get_order.")
        wanted = OrderLine(product_id=product_id or current["productId"], qty=qty if (qty is not None or pieces is not None) else current["qty"], pieces=pieces)
        erp_lines, refusal = await checked_lines(ctx, order["clientId"], order["deliveryDate"], [wanted])
        if refusal:
            return refusal
        qty = erp_lines[0]["qty"]
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
