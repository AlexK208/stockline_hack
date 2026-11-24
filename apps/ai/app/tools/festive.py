"""Le carnet des fêtes: Christmas and New Year reservations by phone (lane B). The rules live in the ERP
(apps/backend/app/services/festive.py): the windows, the capacity of the scarce pieces, the guaranteed share, the
waiting list, the deadlines. These tools only read and write through /api/festive.

A reservation is not an order: no stock is touched and nothing here changes how orders are taken. One call = one
client still holds: every tool takes the caller's client_id, so call_guard (agent/loop.py) refuses any other.
"""

from pydantic import Field

from . import desk
from .erp import enc
from .history import without_none
from .registry import ToolArgs, ToolContext, tool

WINDOW_DAYS = {"noel": (19, 24), "nouvel_an": (26, 31)}
WAITLIST_RULE = (
    "La partie en liste d'attente N'EST PAS promise : dis-le clairement (« je vous mets X sur liste d'attente, on vous "
    "rappelle si ça se libère »), avec la raison (`reason`)."
)


class FestiveLine(ToolArgs):
    product_id: str
    qty: float | None = Field(None, description="Quantité en kilos (ou dans l'unité du produit)")
    pieces: float | None = Field(None, description="Nombre de pièces si l'appelant parle en pièces (« deux demi-veaux », « un agneau ») : converti en kilos")
    note: str | None = Field(None, description="ex. « génisse de chez Dumontet », « bien persillé »")


async def _delivery_dates(ctx: ToolContext, client_id: str, year: int) -> dict:
    """The client's delivery days inside each holiday window this year (what the agent can offer)."""
    client = await ctx.erp.get(f"/api/clients/{enc(client_id)}")
    days = client.get("deliveryDays") or []
    from datetime import date

    out = {}
    for w, (a, b) in WINDOW_DAYS.items():
        out[w] = [
            f"{desk.jour(f'{year}-12-{d:02d}')} {d}/12 ({year}-12-{d:02d})"
            for d in range(a, b + 1)
            if not days or desk.WEEKDAYS[date(year, 12, d).weekday()] in days
        ]
    return out


@tool
async def festive_history(ctx: ToolContext, client_id: str) -> dict:
    """
    CARNET DES FÊTES, à appeler dès que l'appelant parle des fêtes, de Noël, du réveillon, du Nouvel An, ou d'une livraison entre
    le 19 et le 31 décembre. Renvoie ce que CE client a pris l'an dernier pour Noël et pour le Nouvel An (produits, quantités, jours),
    ses jours de livraison possibles cette année dans ces deux périodes, et ce qu'il a déjà réservé. Sers-t'en pour proposer
    « comme l'an dernier » avec les vraies quantités, sans les inventer.
    """
    h = await ctx.erp.get(f"/api/festive/history/{enc(client_id)}")
    year = h["lastYear"] + 1
    products = {p["id"]: p for p in await ctx.erp.get("/api/products", {"limit": 500})} if any(w["lines"] for w in h["windows"]) else {}
    return {
        "client": h["clientName"],
        "lastYear": [
            {
                "window": w["label"],
                "deliveryDates": w["deliveryDates"],
                "main": [_line(l, products.get(l["productId"])) for l in w["lines"][:TOP]],
                **({"alsoTook": [l["productName"] for l in w["lines"][TOP:]]} if len(w["lines"]) > TOP else {}),
            }
            for w in h["windows"]
            if w["lines"]
        ],
        "deliveryDatesThisYear": await _delivery_dates(ctx, client_id, year),
        "alreadyReserved": [
            {k: r.get(k) for k in ("id", "productName", "deliveryDate", "qtyReserved", "qtyWaitlist", "unit")} for r in h["reservations"]
        ],
        "how": "Au téléphone, une phrase : seulement la période dont il parle (« les fêtes » sans précision : Noël), ses produits "
        "`main` avec `say`, puis demande le jour. Ne lis pas `alsoTook` sauf s'il demande le détail. Pour réserver « comme l'an "
        "dernier », passe les `qty` de `main` (et ce qu'il ajoute). Rien n'est réservé tant que festive_reserve n'a pas été appelé.",
    }


TOP = 4  # products read on the phone per window: the rest only if he asks


def _line(l: dict, product: dict | None) -> dict:
    """A line of last year's basket, with how a butcher says it: whole pieces for carcasses and quarters."""
    out = {k: l[k] for k in ("productId", "productName", "qty", "unit")}
    w = desk.piece_kg((product or {}).get("caliber"))
    if w and (w[0] + w[1]) / 2 >= 5:  # a piece big enough to count in pieces (quartier, demi-veau, agneau)
        n = max(1, round(l["qty"] / ((w[0] + w[1]) / 2)))
        out["say"] = f"environ {n} pièce(s) ({desk.fmt(l['qty'])} kg)"
    else:
        out["say"] = f"{desk.fmt(round(l['qty'] * 2) / 2)} {l.get('unit') or 'kg'}"
    return out


@tool
async def festive_availability(
    ctx: ToolContext, client_id: str, product_ids: list[str] = Field(description="Les produits concernés, en un seul appel")
) -> dict:
    """
    CARNET DES FÊTES, pour RÉPONDRE sans rien réserver (« il vous restera du ris pour Noël ? ») : pour chaque produit et chaque
    période (Noël, Nouvel An), si c'est une pièce limitée (`scarce`), la capacité, ce qui est déjà réservé, ce qui reste, la raison
    (« un ris par veau ») et la part garantie à CE client. Les pièces non limitées se réservent sans plafond.
    """
    a = await ctx.erp.get("/api/festive/availability", {"productIds": ",".join(product_ids), "clientId": client_id})
    return {"products": a["products"]}


@tool
async def festive_reserve(
    ctx: ToolContext,
    client_id: str,
    delivery_date: str = Field(description="YYYY-MM-DD, un jour de livraison du client entre le 19 et le 24/12 ou le 26 et le 31/12"),
    lines: list[FestiveLine] = Field(description="Toutes les pièces pour cette date, en un seul appel"),
    replace: bool = Field(False, description="True quand le client CHANGE une quantité déjà réservée (« finalement cinq au lieu de neuf ») : qty devient le nouveau total. Par défaut la quantité s'ajoute."),
) -> dict:
    """
    CARNET DES FÊTES : réserve des volumes pour une date de fêtes, une fois que le client a dit ce qu'il veut (pas avant). Ce n'est
    PAS une commande : la commande se passe plus près de la date, comme d'habitude. L'ERP vérifie tout (période, jour de livraison,
    date limite, compte bloqué) et n'écrit rien s'il y a un problème. Pour les pièces limitées (ris, filet, carré de veau, côte
    maturée, veaux et agneaux entiers…), le client a sa part garantie (son volume de l'an dernier, ou une part équitable) ; le reste
    va en LISTE D'ATTENTE. Relis au client ce qui est réservé et ce qui est en attente.
    """
    erp_lines, said = [], []
    for line in lines:
        qty = line.qty
        if qty is None and line.pieces:
            product = await ctx.erp.get(f"/api/products/{enc(line.product_id)}")
            w = desk.piece_kg(product.get("caliber"))
            if not w:
                raise ValueError(f"{product['name']} : pas de poids par pièce, demande la quantité en kilos")
            qty = round(line.pieces * (w[0] + w[1]) / 2, 1)
            said.append(f"{desk.fmt(line.pieces)} pièce(s) de {product['name']} ≈ {desk.fmt(qty)} kg")
        if not qty:
            raise ValueError(f"{line.product_id} : quantité manquante, demande-la au client")
        erp_lines.append(without_none({"productId": line.product_id, "qty": qty, "note": line.note}))
    r = await ctx.erp.post("/api/festive/reservations", {"clientId": client_id, "deliveryDate": delivery_date, "lines": erp_lines, "replace": replace})
    waiting = any(l["qtyWaitlist"] for l in r["lines"])
    return {
        "reserved": True,
        "label": r["label"],
        "deliveryDate": r["deliveryDate"],
        "lines": [
            {k: l[k] for k in ("reservationId", "productName", "unit", "qtyReserved", "qtyWaitlist", "deadline") if k in l}
            | ({"reason": l["reason"]} if l.get("qtyWaitlist") and l.get("reason") else {})
            for l in r["lines"]
        ],
        **({"estimatedFromPieces": said, "say": "poids estimé, facturé au poids réel"} if said else {}),
        **({"waitlistRule": WAITLIST_RULE} if waiting else {}),
    }


@tool
async def festive_cancel(ctx: ToolContext, client_id: str, reservation_id: str = Field(description="id de la réservation (fet_…), lu dans festive_history")) -> dict:
    """CARNET DES FÊTES : annule une réservation de CE client (il ne veut plus ce produit pour les fêtes). Pour changer une quantité,
    utilise plutôt festive_reserve avec replace=True."""
    mine = await ctx.erp.get("/api/festive/reservations", {"clientId": client_id})
    if reservation_id not in {r["id"] for r in mine}:
        raise ValueError("Réservation introuvable sur le compte de ce client : relis festive_history.")
    r = await ctx.erp.post(f"/api/festive/reservations/{enc(reservation_id)}/cancel")
    c = r["cancelled"]
    return {"cancelled": True, "productName": c.get("productName"), "deliveryDate": c.get("deliveryDate")}
