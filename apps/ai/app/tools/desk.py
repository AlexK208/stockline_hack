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
    """Exact, or ONE missing/extra letter on a word of 5+ letters ("peyronet" = "peyronnet").
    A changed letter is another word: "leroy" is not "leroux", "julien" is not "junien"."""
    if said == ref:
        return True
    if min(len(said), len(ref)) < 5 or abs(len(said) - len(ref)) != 1:
        return False
    short, long = sorted((said, ref), key=len)
    if long.startswith(short):
        return True  # a silent last letter the transcriber dropped or added: "bistro" = "bistrot"
    return lev(said, ref) == 1 and said[0] == ref[0] and said[-1] == ref[-1]


# ───────────────────────── client directory (cached) ─────────────────────────

_dir: tuple[float, list[dict], dict] | None = None
_dir_lock = asyncio.Lock()
DIR_TTL_S = 120
# Words of a client's name that say nothing about who is calling when heard alone: places and street words.
# Product words ("viande", "bœuf", "agneau"…) are added from the catalogue when the directory is built.
GENERIC = set("place rue avenue boulevard route chemin impasse halles marche centre ville".split())


# The ERP's client types, in the words callers use for their own trade ("fishmonger" is the kit's generic word for
# the retail shop: here, the butcher's shop).
TRADE = {
    "fishmonger": ("boucherie", "boucher", "bouchere", "charcuterie", "charcutier"),
    "restaurant": ("restaurant", "resto", "restaurateur", "chef"),
    "brasserie": ("brasserie", "routier", "bistrot", "bistro"),
    "supermarket": ("supermarche", "magasin", "superette", "hyper", "grande", "surface", "rayon"),
    "canteen": ("cantine", "cuisine", "collectivite", "ehpad", "residence", "hopital", "hospitalier", "scolaire"),
    "caterer": ("traiteur",),
    "hotel": ("hotel", "auberge", "hostellerie", "gite", "gites", "relais"),
}
TRADE_LABEL = {
    "fishmonger": "boucherie (commerce de détail)", "restaurant": "restaurant", "brasserie": "brasserie", "supermarket": "grande surface",
    "canteen": "restauration collective", "caterer": "traiteur", "hotel": "hôtel / auberge",
}  # fmt: skip


def build_directory(rows: list[dict], products: list[dict]) -> tuple[list[dict], dict]:
    """Clients with their name words, contact names, town and street words; plus how rare each name word is and
    which name words belong to ONE client only (and are not everyday or product words)."""
    generic = set(GENERIC)
    for p in products:
        for text in [p.get("name", ""), *(p.get("aliases") or [])]:
            generic.update(tokens(text))
    clients = []
    for c in rows:
        contacts = [k.get("name", "") for k in c.get("contacts") or []]
        street = [t for t in tokens(re.sub(r"\d+", " ", c.get("address", "").split(",")[0])) if t not in generic]
        clients.append(
            {
                **pick(c, "id", "code", "name", "city", "status"),
                "kind": TRADE_LABEL.get(c.get("type"), c.get("type")),
                "contacts": contacts,
                "_trade": TRADE.get(c.get("type"), ()),
                "_name": tokens(c["name"]),
                "_first": [t for n in contacts for t in tokens(n.split()[0] if n.split() else "")],  # "Jean-Louis" → jean, louis
                "_last": [t for n in contacts for t in tokens(" ".join(n.split()[1:]))],
                "_city": tokens(c.get("city", "")),
                "_street": street,
                "_code": norm(c.get("code", "")),
            }
        )
    df: dict[str, int] = {}
    for c in clients:
        for t in set(c["_name"]):
            df[t] = df.get(t, 0) + 1
    idf = {t: 1 + math.log(len(clients) / n) for t, n in df.items()}  # "peyronnet" ≈ 5.5, "boucherie" ≈ 2.2
    firsts = {t for c in clients for t in c["_first"]}
    towns = {t for c in clients for t in c["_city"]}  # "la boucherie à Couzeix": a town is not a proof of identity
    unique = {t for t, n in df.items() if n == 1 and t not in generic and t not in firsts and t not in towns}
    rare = {t for t, n in df.items() if n <= 3 and t not in generic and t not in firsts and t not in towns}
    return clients, {"idf": idf, "unique": unique, "rare": rare}


async def directory(erp: ErpClient) -> tuple[list[dict], dict]:
    global _dir
    async with _dir_lock:
        if _dir and time.monotonic() - _dir[0] < DIR_TTL_S:
            return _dir[1], _dir[2]
        rows, products = await asyncio.gather(erp.get("/api/clients", {"limit": 500}), erp.get("/api/products", {"limit": 500}))
        clients, stats = build_directory(rows, products)
        _dir = (time.monotonic(), clients, stats)
        return clients, stats


def reset_directory() -> None:
    global _dir
    _dir = None


def explain(said: list[str], c: dict, stats: dict) -> dict:
    """How well a client accounts for what was said: a score, which said words it explains, and whether the
    evidence is strong enough to name it without asking (whole name, a name word only it has, a contact's surname)."""
    idf, unique = stats["idf"], stats["unique"]
    covered: set[str] = set()
    name_hit: set[str] = set()
    for t in set(c["_name"]):
        for w in said:
            if same_word(w, t):
                name_hit.add(t)
                covered.add(w)
    surname = {w for w in said for t in c["_last"] if same_word(w, t)}
    first = {w for w in said for t in c["_first"] if w == t}
    town_words = [t for t in c["_city"] if t not in c["_name"]]
    town = {w for w in said for t in town_words if same_word(w, t)}
    if len(town) < len(set(town_words)):
        town = set()  # the whole town or nothing ("saint" alone is not Saint-Junien)
    street = {w for w in said for t in c["_street"] if same_word(w, t)}
    code = {w for w in said if c["_code"] and w == c["_code"]}
    trade = {w for w in said if w in c.get("_trade", ()) and w not in covered}  # "le boucher à Limoges"
    score = sum(idf.get(t, 1.0) for t in name_hit) + (3.0 if surname else 0) + (2.5 if first else 0)
    score += (2.0 if town else 0) + (1.5 if street else 0) + (10 if code else 0) + (1.0 if trade else 0)
    full = bool(c["_name"]) and name_hit == set(c["_name"])
    return {
        "client": c,
        "score": score,
        "covered": covered | surname | first | town | street | code | trade,
        "people": surname | first,
        "name_hit": name_hit,
        # proof that belongs to this client only: a name word nobody else has, a contact's surname, its code
        "proof": bool(name_hit & unique) or bool(surname) or bool(code),
        # …or the whole name, or a contact's first name together with a rare word of the name ("Julien, Hyper Frais")
        "strong": full or bool(name_hit & unique) or bool(surname) or bool(code) or (bool(first) and bool(name_hit & stats["rare"])),
    }


def match_clients(said_text: str, clients: list[dict], stats: dict) -> tuple[dict | None, list[dict]]:
    """→ (the one client, []) when there is no doubt, else (None, candidates best first). It never guesses:
      - a first name alone, a town alone or a trade word alone names nobody: candidates, and the agent asks;
      - if another client explains every word the best one explains ("Hyper Frais Limoges" / "… Corgnac",
        "Peyrat" the chef / Peyrat Traiteur), both are returned and the agent asks which."""
    said = tokens(said_text)
    scored = [e for e in (explain(said, c, stats) for c in clients) if e["score"] >= 2.4]
    if not scored:
        return None, []
    scored.sort(key=lambda e: (-e["score"], e["client"]["name"]))
    best = scored[0]
    rivals = [e for e in scored[1:] if e["covered"] >= best["covered"] or e["score"] >= best["score"] - 1e-9]
    # Same family of names ("Charcuterie-Traiteur Esposito" / "Hostellerie Esposito") and the other one explains a word
    # the best one does not ("pour la charcuterie… non pardon, l'hostellerie") → both are in play: the agent settles it
    # from the whole sentence, or asks.
    rivals += [e for e in scored[1:] if (e["name_hit"] & best["name_hit"] & stats["rare"]) and (e["covered"] - best["covered"])]
    if not best["proof"]:
        # Named only by everyday words ("la boucherie à Couzeix" = La Boucherie de Couzeix?): if the caller also gave
        # a person's name that belongs to ANOTHER client, that client is just as plausible → ask.
        rivals += [e for e in scored[1:] if e["people"] - best["covered"]]
    if best["strong"] and not rivals:
        return best["client"], []
    out, seen = [], set()
    for e in [best, *rivals, *(e for e in scored if e["score"] >= best["score"] - 3.0)]:
        if e["client"]["id"] not in seen:
            seen.add(e["client"]["id"])
            out.append(e["client"])
    return None, out[:5]


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


def first_delivery_from(earliest: date, delivery_days: list[str]) -> dict:
    """The first day, from `earliest` on, on which this client is delivered."""
    for i in range(0, 15):
        d = earliest + timedelta(days=i)
        if WEEKDAYS[d.weekday()] in (delivery_days or WEEKDAYS[:6]):
            return {"date": d.isoformat(), "jour": f"{JOURS[d.weekday()]} {d.day}"}
    return {"date": earliest.isoformat(), "jour": f"{JOURS[earliest.weekday()]} {earliest.day}"}


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
    clients, stats = await directory(ctx.erp)
    if client_id:
        # The model chose among the candidates: allowed only if what the caller said really singles this client out.
        # "Karim, le boucher, à Limoges" fits two butchers named Karim in Limoges: ask again rather than pick one.
        chosen = next((c for c in clients if c["id"] == client_id), None)
        if chosen:
            words = tokens(said)
            mine = explain(words, chosen, stats)
            if not mine["strong"]:
                twins = [e["client"] for e in (explain(words, c, stats) for c in clients if c["id"] != client_id) if e["score"] >= 2.4 and e["covered"] >= mine["covered"]]
                if twins:
                    return {
                        "status": "ambiguous",
                        "instruction": "Ce que l'appelant a dit correspond encore à plusieurs clients : ne choisis pas. Demande le nom du commerce "
                        "ou son nom de famille, puis rappelle identify_caller avec ce qu'il répond.",
                        "candidates": [pick(c, "id", "name", "kind", "city", "status", "contacts") for c in [chosen, *twins][:5]],
                    }
        return {"status": "found", "client": await client_card(ctx.erp, client_id)}
    best, candidates = match_clients(said, clients, stats)
    if best:
        return {"status": "found", "client": await client_card(ctx.erp, best["id"])}
    if candidates:
        return {
            "status": "ambiguous",
            "instruction": "Plusieurs clients possibles : demande lequel en citant ce qui les distingue (ville, nom du contact). "
            "Puis rappelle identify_caller avec clientId.",
            "candidates": [pick(c, "id", "name", "kind", "city", "status", "contacts") for c in candidates],
        }
    return {"status": "unknown", "instruction": "Client non reconnu : demande le nom du commerce et la ville. N'invente rien."}


# ───────────────────────── check_products ─────────────────────────

# House lead times (data/context/02-journee-type.md): carcasses and quarters are ordered 2 days ahead (slaughter on
# Monday and Thursday), 21-day matured ribs a week ahead, everything else the day before.
LEAD_DAYS_BY_CATEGORY = {"carcasses": 2}
# Canteens, hospitals and care homes order 3 days ahead (same file; every canteen order in the history does).
LEAD_DAYS_BY_CLIENT_TYPE = {"canteen": 3}
# 21-day matured ribs: "réservation une semaine à l'avance". The history shows them sold 1 to 3 days ahead when some
# are in the ageing room, so the week applies only when the stock at the date does not cover the request.
RESERVE_DAYS_WHEN_SHORT = {"prd_0011": 7}
PIECE = re.compile(r"(\d+(?:[.,]\d+)?)\s*-\s*(\d+(?:[.,]\d+)?)\s*(kg|g)\b")
PACK = re.compile(r"(\d+)\s*x\s*(\d+(?:[.,]\d+)?)\s*(kg|g)\b")
ONE = re.compile(r"(\d+(?:[.,]\d+)?)\s*(kg|g)\b")


def piece_kg(caliber: str | None) -> tuple[float, float] | None:
    """Weight of one piece or pack, in kilos, as (lightest, heaviest):
    "quartier 90-110 kg" → (90, 110); "pièce 300-350 g" → (0.3, 0.35); "carton 50 x 100 g" → (5, 5);
    "sachet 2,5 kg" → (2.5, 2.5); "carré 6 côtes" → None (no weight: ask for kilos)."""
    text = caliber or ""
    num = lambda x: float(x.replace(",", "."))  # noqa: E731
    if m := PIECE.search(text):
        k = 1000 if m.group(3) == "g" else 1
        return round(num(m.group(1)) / k, 4), round(num(m.group(2)) / k, 4)
    if m := PACK.search(text):
        w = round(int(m.group(1)) * num(m.group(2)) / (1000 if m.group(3) == "g" else 1), 4)
        return w, w
    if m := ONE.search(text):
        w = round(num(m.group(1)) / (1000 if m.group(2) == "g" else 1), 4)
        return w, w
    return None


class Item(ToolArgs):
    product_id: str = Field(description="id du produit (prd_…), lu dans le glossaire produits")
    qty: float | None = Field(None, description="Quantité en kilos (ou dans l'unité du produit) si l'appelant l'a donnée ainsi")
    pieces: float | None = Field(None, description="Nombre de pièces si l'appelant parle en pièces : « deux arrières », « un agneau », « un demi-veau »")


async def check_items(erp: ErpClient, client_id: str, delivery_date: str, items: list[Item]) -> dict:
    """Everything to know before writing order lines, for one delivery date (shared by check_products and the write
    tools of orders.py, which refuse to write while `problems_of` finds something)."""
    meta, client = await asyncio.gather(erp.get("/api/meta"), erp.get(f"/api/clients/{enc(client_id)}"))
    today = date.fromisoformat(meta["today"])
    day = date.fromisoformat(delivery_date)
    ids = list(dict.fromkeys(i.product_id for i in items))
    products, levels = await asyncio.gather(
        asyncio.gather(*(erp.get(f"/api/products/{enc(i)}") for i in ids)),
        erp.get("/api/stock/availability", {"date": delivery_date, "productIds": ",".join(ids)}),
    )
    product = {p["id"]: p for p in products}
    level = {r["productId"]: r for r in levels}
    days = client.get("deliveryDays") or []

    async def one(it: Item) -> dict:
        p = product[it.product_id]
        row: dict = {"productId": p["id"], "name": p["name"], "unit": p["unit"], **({"packaging": p["caliber"]} if p.get("caliber") else {})}
        qty = it.qty
        rng = piece_kg(p.get("caliber")) if p["unit"] == "kg" else None
        if qty is None and it.pieces and rng:
            qty = round(it.pieces * (rng[0] + rng[1]) / 2, 1)
            if rng[0] == rng[1]:
                row["estimatedFromPieces"] = f"{fmt(it.pieces)} × {fmt(rng[0])} kg = {fmt(qty)} kg"
            else:
                row["estimatedFromPieces"] = f"{fmt(it.pieces)} pièce(s) ≈ {fmt(qty)} kg (pièce de {fmt(rng[0])} à {fmt(rng[1])} kg, facturé au poids réel)"
        elif qty is None and it.pieces and p["unit"] != "kg":
            row["needQty"] = f"Ce produit se vend par « {p['unit']} » ({p.get('caliber') or 'voir le nom'}) : convertis toi-même ce que dit le client en nombre de {p['unit']} et passe-le dans qty."
        elif qty is None:
            row["needQty"] = "Pas de poids par pièce connu pour ce produit : demande la quantité en kilos, n'invente pas un poids."
        if qty is not None:
            row["qty"] = qty
            price = await erp.get("/api/prices/resolve", {"clientId": client_id, "productId": p["id"], "qty": fmt(qty)})
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
            alts = await erp.get(f"/api/products/{enc(p['id'])}/alternatives")
            row["alternatives"] = [pick(a, "id", "name") for a in alts[:3]]
        lead = max(LEAD_DAYS_BY_CATEGORY.get(p.get("category"), 1), LEAD_DAYS_BY_CLIENT_TYPE.get(client.get("type"), 1))
        why = f"ce produit se commande {lead} jours avant" if lead == LEAD_DAYS_BY_CATEGORY.get(p.get("category"), 1) else f"ce client commande {lead} jours avant"
        if row["stock"] != "ok" and p["id"] in RESERVE_DAYS_WHEN_SHORT:
            lead = RESERVE_DAYS_WHEN_SHORT[p["id"]]
            why = "ce produit se réserve une semaine à l'avance quand il n'y en a pas assez en maturation"
        if (day - today).days < lead:
            first = first_delivery_from(today + timedelta(days=lead), days)
            row["leadTime"] = f"Trop tard pour cette date : {why}. Première livraison possible : {first['jour']} ({first['date']})."
        elif p["id"] in RESERVE_DAYS_WHEN_SHORT and (day - today).days < RESERVE_DAYS_WHEN_SHORT[p["id"]]:
            row["say"] = "Ce produit se réserve normalement une semaine à l'avance ; il y en a assez en maturation pour cette date, donc c'est possible : dis-le ainsi."
        return row

    result: dict = {"deliveryDate": delivery_date, "jour": jour(delivery_date), "items": list(await asyncio.gather(*(one(it) for it in items)))}
    if day <= today:
        result["deliveryDay"] = "Date passée ou aujourd'hui : les camions sont partis. Propose un des prochains jours."
        result["nextDeliveries"] = next_delivery_dates(meta["today"], days)
    elif days and WEEKDAYS[day.weekday()] not in days:
        result["deliveryDay"] = "Ce client n'est pas livré ce jour-là. Propose un des prochains jours de livraison."
        result["nextDeliveries"] = next_delivery_dates(meta["today"], days)
    return result


def problems_of(checked: dict) -> list[str]:
    """What stops these lines from being written as asked ([] = all good)."""
    out = [checked["deliveryDay"]] if checked.get("deliveryDay") else []
    for row in checked["items"]:
        if row.get("needQty"):
            out.append(f"{row['name']} : quantité à demander")
        if row["stock"] != "ok":
            out.append(f"{row['name']} : {row['stock']} ({fmt(row.get('availableQty', 0))} {row['unit']} possibles à cette date)")
        if row.get("leadTime"):
            out.append(f"{row['name']} : {row['leadTime']}")
    return out


async def default_delivery_date(erp: ErpClient, client_id: str) -> str:
    """The client's next delivery day (what the ERP would pick for an order without a date)."""
    meta, client = await asyncio.gather(erp.get("/api/meta"), erp.get(f"/api/clients/{enc(client_id)}"))
    return next_delivery_dates(meta["today"], client.get("deliveryDays") or [], 1)[0]["date"]


@tool
async def check_products(
    ctx: ToolContext,
    client_id: str,
    delivery_date: str = Field(description="Date de livraison visée, YYYY-MM-DD"),
    items: list[Item] = Field(description="Tous les produits concernés, en un seul appel"),
) -> dict:
    """
    Pour RÉPONDRE À UNE QUESTION sans rien écrire (« il vous reste de l'onglet ? », « c'est combien la bavette ? », « je peux avoir
    un arrière pour mercredi ? ») : pour chaque produit et pour la date, prix de CE client, disponibilité À LA DATE (compte les
    arrivages prévus avant la livraison), conversion pièces → kilos, délai de commande, jour de livraison, et si ça manque : quantité
    possible, prochain arrivage, produits de remplacement. Inutile avant create_draft_order, add_order_line ou update_order_line :
    ces outils font eux-mêmes ces vérifications.
    """
    return await check_items(ctx.erp, client_id, delivery_date, items)


def fmt(n: float) -> str:
    return str(int(n)) if float(n).is_integer() else str(n)


async def prefetch_identify(said_text: str, erp: ErpClient) -> tuple[str, dict] | None:
    """What identify_caller would return for this utterance, when exactly ONE client matches it; else None (the model
    then calls the tool itself and asks). Used by the agent loop to skip a model round-trip at the start of a call."""
    try:
        clients, stats = await asyncio.wait_for(directory(erp), 1.5)
        best, _ = match_clients(said_text, clients, stats)
        if not best:
            return None
        card = await asyncio.wait_for(client_card(erp, best["id"]), 2.0)
    except Exception:  # ERP slow or down: let the model use the tool and report the problem
        return None
    return best["name"], {"status": "found", "client": card}


@tool
async def order_history(
    ctx: ToolContext,
    client_id: str,
    delivery_date: str | None = Field(None, description="YYYY-MM-DD : la livraison dont parle le client (« ma livraison de mardi dernier »). Sans date : ses dernières commandes"),
    limit: int | None = Field(None, description="Nombre de commandes (défaut 3, max 6)"),
) -> list[dict]:
    """
    Commandes passées d'un client avec, pour chaque ligne, la quantité COMMANDÉE et la quantité réellement PESÉE au départ (c'est le poids
    pesé qui est facturé). À utiliser quand le client parle d'une livraison passée : « pareil que samedi », « il manquait un kilo »,
    « c'était quoi la dernière fois ». Ne donne que ces chiffres : n'en invente aucun, et ne promets ni avoir ni remise.
    """
    query = {"clientId": client_id, "date": delivery_date, "status": "prepared,delivered,invoiced", "limit": min(limit or 3, 6)}
    orders = await ctx.erp.get("/api/orders", query)
    details = await asyncio.gather(*(ctx.erp.get(f"/api/orders/{enc(o['id'])}") for o in orders[: min(limit or 3, 6)]))
    out = []
    for o in details:
        lines = []
        for l in o["lines"]:
            row = {**pick(l, "productId", "productName", "unit"), "ordered": l["qty"]}
            if l.get("preparedQty") is not None:
                row["weighed"] = l["preparedQty"]
            lines.append(row)
        out.append({**pick(o, "id", "number", "status", "deliveryDate"), "jour": jour(o["deliveryDate"]), "lines": lines})
    return out
