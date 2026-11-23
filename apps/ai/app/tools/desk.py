"""
Order-desk tools: the two composite calls an inbound order call needs, so a turn costs one model round-trip
instead of three or four.

    identify_caller   who is calling → one client card (rules, open orders, last orders, usual basket), or the
                      candidates to choose from. Matching is done here, in code, not by the model: never a guess.
    check_products    for a delivery date: price for this client, date-aware stock, pieces → kilos, lead time,
                      delivery day. Everything needed before writing an order line.

Business rules stay in the ERP (stock by date: /api/stock/availability; prices: /api/prices/resolve). What lives
here is matching, formatting and the house lead times from data/context/02-journee-type.md.
"""

import asyncio
import math
import re
import time
import unicodedata
from datetime import date, timedelta

from pydantic import Field

from .erp import ErpClient, enc, pick
from .registry import ToolArgs, ToolContext, tool

WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]

# ───────────────────────── text matching ─────────────────────────


def norm(s: str) -> str:
    """lowercase, no accents, œ → oe, punctuation → spaces."""
    s = (s or "").lower().replace("œ", "oe").replace("æ", "ae")
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


# Words that say nothing about WHICH client: articles and fillers. Trade words (boucherie, restaurant…) are kept
# but weigh little because many clients share them (see idf below).
STOP = set(
    "a au aux c ce cest d de des du en et est ici il j je l la le les m me moi mon n on ou oui pour que qui s sa se "
    "son sur t te toi tu un une vous y bonjour bonsoir salut allo ouais bon alors donc euh ben voila merci svp "
    "chez comme dhabitude habitude dhab veux voudrais faut mets mettez met tu commande commander demain jeudi "
    "lundi mardi mercredi vendredi samedi dimanche kilo kilos kg".split()
)


def tokens(s: str) -> list[str]:
    return [t for t in norm(s).split() if len(t) > 1 and t not in STOP]


def lev(a: str, b: str) -> int:
    if a == b:
        return 0
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def same_word(said: str, ref: str) -> bool:
    """Exact, or one typo on a word of 5+ letters ("peyronet" = "peyronnet"). "leroy" is not "leroux"."""
    if said == ref:
        return True
    if min(len(said), len(ref)) < 5 or abs(len(said) - len(ref)) > 1:
        return False
    return lev(said, ref) <= 1 and said[0] == ref[0] and said[-1] == ref[-1]


# ───────────────────────── client directory (cached) ─────────────────────────

_dir: tuple[float, list[dict], dict[str, float]] | None = None
_dir_lock = asyncio.Lock()
DIR_TTL_S = 120


async def directory(erp: ErpClient) -> tuple[list[dict], dict[str, float]]:
    """All clients with their name tokens, contact names and city, plus how rare each name token is."""
    global _dir
    async with _dir_lock:
        if _dir and time.monotonic() - _dir[0] < DIR_TTL_S:
            return _dir[1], _dir[2]
        rows = await erp.get("/api/clients", {"limit": 500})
        clients = []
        for c in rows:
            contacts = [k.get("name", "") for k in c.get("contacts") or []]
            clients.append(
                {
                    **pick(c, "id", "code", "name", "city", "status"),
                    "contacts": contacts,
                    "_name": tokens(c["name"]),
                    "_first": [t for n in contacts for t in tokens(n)[:1]],
                    "_last": [t for n in contacts for t in tokens(n)[1:]],
                    "_city": tokens(c.get("city", "")),
                    "_code": norm(c.get("code", "")),
                }
            )
        df: dict[str, int] = {}
        for c in clients:
            for t in set(c["_name"]):
                df[t] = df.get(t, 0) + 1
        idf = {t: 1 + math.log(len(clients) / n) for t, n in df.items()}  # "peyronnet" ≈ 5.5, "boucherie" ≈ 2.2
        _dir = (time.monotonic(), clients, idf)
        return clients, idf


def reset_directory() -> None:
    global _dir
    _dir = None


def score_client(said: list[str], c: dict, idf: dict[str, float]) -> tuple[float, bool]:
    """(score, whole name said). Name words count by rarity; a contact's name or the town add to it."""
    name_hit = [t for t in c["_name"] if any(same_word(s, t) for s in said)]
    score = sum(idf.get(t, 1.0) for t in set(name_hit))
    if any(same_word(s, t) for s in said for t in c["_last"]):
        score += 3.0
    if any(s == t for s in said for t in c["_first"]):
        score += 2.5
    if c["_code"] and c["_code"] in said:
        score += 10
    city_only = [t for t in c["_city"] if t not in c["_name"]]
    if city_only and all(any(same_word(s, t) for s in said) for t in city_only):
        score += 2.0
    return score, bool(c["_name"]) and len(set(name_hit)) == len(set(c["_name"]))


def match_clients(said_text: str, clients: list[dict], idf: dict[str, float]) -> tuple[dict | None, list[dict]]:
    """→ (the one client, []) when there is no doubt, else (None, candidates best first). Never guesses:
    two clients as plausible as each other ("Hyper Frais Limoges" / "… Corgnac") are returned as candidates."""
    said = tokens(said_text)
    scored = []
    for c in clients:
        s, full = score_client(said, c, idf)
        if s >= 2.4:  # at least one fairly distinctive word, a contact's name, or the town with something else
            scored.append((s, full, c))
    if not scored:
        return None, []
    scored.sort(key=lambda x: (-x[0], x[2]["name"]))
    top, top_full, best = scored[0]
    rivals = [x for x in scored[1:] if x[0] >= top - 1.5]
    if top_full:  # the whole name was said: a rival that only shares part of it and scores lower is not a rival
        rivals = [x for x in rivals if x[1] or x[0] >= top - 1e-9]
    # A longer name that contains everything the caller said scores the same: as plausible as the short one → ask.
    distinctive = top >= 4.0
    if not rivals and distinctive:
        return best, []
    return None, [x[2] for x in scored[:5] if x[0] >= top - 3.0]


# ───────────────────────── identify_caller ─────────────────────────


def next_delivery_dates(today_iso: str, delivery_days: list[str], n: int = 4) -> list[dict]:
    d0 = date.fromisoformat(today_iso)
    out = []
    for i in range(1, 15):
        d = d0 + timedelta(days=i)
        if WEEKDAYS[d.weekday()] in (delivery_days or WEEKDAYS[:6]):
            out.append({"date": d.isoformat(), "jour": f"{JOURS[d.weekday()]} {d.day}"})
            if len(out) == n:
                break
    return out


def jour(iso: str) -> str:
    d = date.fromisoformat(iso[:10])
    return f"{JOURS[d.weekday()]} {d.day}"


def order_card(o: dict, editable: bool) -> dict:
    """Open orders keep their line ids (needed to edit them); past orders are one short string per line."""
    if editable:
        lines = [{"lineId": l["id"], **pick(l, "productId", "productName", "qty", "unit")} for l in o["lines"]]
    else:
        lines = [f"{l['productId']} {l['productName']} : {fmt(l['qty'])} {l.get('unit', '')}".strip() for l in o["lines"]]
    return {**pick(o, "id", "number", "status", "deliveryDate"), "jour": jour(o["deliveryDate"]), "lines": lines}


CONTEXT_TITLES = ("Les personnes et leur façon de parler", "Comment leur parler", "Ce qui les agace")


async def client_card(erp: ErpClient, client_id: str) -> dict:
    c, ctx_rows, meta, open_events = await asyncio.gather(
        erp.get(f"/api/clients/{enc(client_id)}"),
        erp.get("/api/context/for", {"entityType": "client", "id": client_id}),
        erp.get("/api/meta"),
        erp.get(f"/api/clients/{enc(client_id)}/events", {"status": "open", "limit": 4}),
    )
    recent = c.get("recentOrders") or []
    open_ids = [o["id"] for o in recent if o["status"] in ("draft", "confirmed") and o["deliveryDate"] > meta["today"]][:3]
    past_ids = [o["id"] for o in recent if o["status"] in ("prepared", "delivered", "invoiced")][:2]
    details = await asyncio.gather(*(erp.get(f"/api/orders/{enc(i)}") for i in open_ids + past_ids))
    by_id = {o["id"]: o for o in details}
    blocked = c["status"] == "blocked"
    how = {
        e["title"]: e["body"]
        for e in (ctx_rows.get("entries") or [])
        if e.get("title") in CONTEXT_TITLES and e.get("body")
    }
    card = {
        **pick(c, "id", "name", "city", "status", "salesRep", "preferences"),
        "contacts": [pick(k, "name", "role") for k in c.get("contacts") or []],
        "nextDeliveries": next_delivery_dates(meta["today"], c.get("deliveryDays") or []),
        "openOrders": [order_card(by_id[i], True) for i in open_ids],
        "lastOrders": [order_card(by_id[i], False) for i in past_ids],
        "usual": [f"{u['productId']} {u['productName']} : en moyenne {fmt(round(u['avgQty'], 1))} {u.get('unit', '')}" for u in (c.get("usual") or [])[:8]],
        "openIssues": [f"{e['type']} : {e['title']}" for e in (open_events or [])[:4]],
        "credit": pick(c, "creditLimit", "outstanding", "overdue"),
        "howToTalk": how,
    }
    if blocked:
        card["BLOCKED"] = (
            "Compte bloqué pour impayés. Ne prends AUCUNE commande et ne promets rien : explique poliment que le compte "
            "est bloqué, que la comptabilité (Josette) doit le lever, prends le message (log_client_event type call)."
        )
    if card["openOrders"]:
        card["note"] = "Ce client a déjà une commande en cours : modifie-la (lineId) au lieu d'en créer une autre pour le même jour."
    return card


@tool
async def identify_caller(
    ctx: ToolContext,
    said: str = Field(description="Ce que l'appelant a dit pour se présenter, tel quel : nom du commerce, prénom, ville. Ex. « Christian de la Boucherie Peyronnet »"),
    client_id: str | None = Field(None, description="Seulement après que l'appelant a choisi parmi les candidats proposés : l'id retenu"),
) -> dict:
    """
    PREMIER outil d'un appel : identifie le client qui appelle et renvoie EN UN SEUL APPEL sa fiche complète (statut, compte bloqué,
    préférences et règle de substitution, prochains jours de livraison, commandes en cours avec leurs lignes, dernières commandes,
    panier habituel, problèmes ouverts, façon de lui parler). Remplace search + get_client + get_context.
    Si plusieurs clients sont plausibles, renvoie `candidates` : demande alors lequel (ville, nom du patron), ne devine jamais.
    """
    if client_id:
        return {"status": "found", "client": await client_card(ctx.erp, client_id)}
    clients, idf = await directory(ctx.erp)
    best, candidates = match_clients(said, clients, idf)
    if best:
        return {"status": "found", "client": await client_card(ctx.erp, best["id"])}
    if candidates:
        return {
            "status": "ambiguous",
            "instruction": "Plusieurs clients possibles : demande lequel en citant ce qui les distingue (ville, nom du contact). "
            "Puis rappelle identify_caller avec clientId.",
            "candidates": [pick(c, "id", "name", "city", "status", "contacts") for c in candidates],
        }
    return {"status": "unknown", "instruction": "Client non reconnu : demande le nom du commerce et la ville. N'invente rien."}


# ───────────────────────── check_products ─────────────────────────

# House lead times (data/context/02-journee-type.md): carcasses and quarters are ordered 2 days ahead (slaughter on
# Monday and Thursday), 21-day matured ribs a week ahead, everything else the day before.
LEAD_DAYS_BY_CATEGORY = {"carcasses": 2}
LEAD_DAYS_BY_PRODUCT = {"prd_0011": 7}
PIECE = re.compile(r"(\d+(?:[.,]\d+)?)\s*-\s*(\d+(?:[.,]\d+)?)\s*(kg|g)\b")


def piece_kg(caliber: str | None) -> tuple[float, float] | None:
    """"quartier 90-110 kg" → (90, 110); "pièce 300-350 g" → (0.3, 0.35); "carré 6 côtes" → None."""
    m = PIECE.search(caliber or "")
    if not m:
        return None
    lo, hi = (float(x.replace(",", ".")) for x in m.group(1, 2))
    k = 0.001 if m.group(3) == "g" else 1
    return lo * k, hi * k


class Item(ToolArgs):
    product_id: str = Field(description="id du produit (prd_…), lu dans le glossaire produits")
    qty: float | None = Field(None, description="Quantité en kilos (ou dans l'unité du produit) si l'appelant l'a donnée ainsi")
    pieces: float | None = Field(None, description="Nombre de pièces si l'appelant parle en pièces : « deux arrières », « un agneau », « un demi-veau »")


@tool
async def check_products(
    ctx: ToolContext,
    client_id: str,
    delivery_date: str = Field(description="Date de livraison visée, YYYY-MM-DD"),
    items: list[Item] = Field(description="Tous les produits demandés dans ce tour, en un seul appel"),
) -> dict:
    """
    À appeler AVANT d'écrire des lignes de commande, une seule fois pour tous les produits du tour. Pour chaque produit et pour la date
    de livraison : quantité en kilos (convertit les pièces : « deux arrières » → kilos estimés), prix de CE client, disponibilité À LA
    DATE (compte les arrivages prévus avant la livraison : seule vérité sur le stock), délai de commande respecté ou non, et si ça
    manque : quantité possible, date du prochain arrivage, produits de remplacement. Dit aussi si le client est livré ce jour-là.
    Ne propose un remplacement que si les préférences du client l'autorisent.
    """
    meta, client = await asyncio.gather(ctx.erp.get("/api/meta"), ctx.erp.get(f"/api/clients/{enc(client_id)}"))
    today = date.fromisoformat(meta["today"])
    day = date.fromisoformat(delivery_date)
    ids = list(dict.fromkeys(i.product_id for i in items))
    products, levels = await asyncio.gather(
        asyncio.gather(*(ctx.erp.get(f"/api/products/{enc(i)}") for i in ids)),
        ctx.erp.get("/api/stock/availability", {"date": delivery_date, "productIds": ",".join(ids)}),
    )
    product = {p["id"]: p for p in products}
    level = {r["productId"]: r for r in levels}

    out_items = []
    for it in items:
        p = product[it.product_id]
        row: dict = {"productId": p["id"], "name": p["name"], "unit": p["unit"]}
        qty = it.qty
        rng = piece_kg(p.get("caliber"))
        if qty is None and it.pieces and rng:
            qty = round(it.pieces * (rng[0] + rng[1]) / 2, 1)
            row["estimatedFromPieces"] = f"{fmt(it.pieces)} pièce(s) ≈ {fmt(qty)} kg (pièce de {fmt(rng[0])} à {fmt(rng[1])} kg, facturé au poids réel)"
        elif qty is None and it.pieces:
            row["needQty"] = "Pas de poids par pièce connu : demande la quantité en kilos."
        if qty is not None:
            row["qty"] = qty
            price = await ctx.erp.get("/api/prices/resolve", {"clientId": client_id, "productId": p["id"], "qty": fmt(qty)})
            row["unitPrice"] = price["price"]
        lv = level.get(p["id"], {})
        available = max(0.0, lv.get("availableOn", 0.0))
        if qty is None or available >= qty:
            row["stock"] = "ok" if available > 0 else "rupture"
        else:
            row["stock"] = "rupture" if available <= 0 else "insuffisant"
        if row["stock"] != "ok":
            row["availableQty"] = round(available, 1)
            if lv.get("nextArrival") and lv["nextArrival"]["date"] > delivery_date:
                row["nextArrival"] = {"date": lv["nextArrival"]["date"], "jour": jour(lv["nextArrival"]["date"])}
            else:
                row["nextArrival"] = "aucun arrivage confirmé"
            alts = await ctx.erp.get(f"/api/products/{enc(p['id'])}/alternatives")
            row["alternatives"] = [pick(a, "id", "name") for a in alts[:3]]
        lead = LEAD_DAYS_BY_PRODUCT.get(p["id"], LEAD_DAYS_BY_CATEGORY.get(p.get("category"), 1))
        if (day - today).days < lead:
            earliest = today + timedelta(days=lead)
            row["leadTime"] = f"Trop tard pour cette date : ce produit se commande {lead} jours avant. Au plus tôt le {earliest.isoformat()}."
        out_items.append(row)

    days = client.get("deliveryDays") or []
    result: dict = {"deliveryDate": delivery_date, "jour": jour(delivery_date), "items": out_items}
    if day <= today:
        result["deliveryDay"] = "Date passée ou aujourd'hui : les camions sont partis. Propose un des prochains jours."
        result["nextDeliveries"] = next_delivery_dates(meta["today"], days)
    elif days and WEEKDAYS[day.weekday()] not in days:
        result["deliveryDay"] = "Ce client n'est pas livré ce jour-là. Propose un des prochains jours de livraison."
        result["nextDeliveries"] = next_delivery_dates(meta["today"], days)
    return result


def fmt(n: float) -> str:
    return str(int(n)) if float(n).is_integer() else str(n)
