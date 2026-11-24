"""Le carnet des fêtes: Christmas and New Year reservations, taken by phone (lane B, 24/11/2026).

Why: Christmas is the peak of a chevillard's year and it falls on the scarcest pieces (2025 vs a normal fortnight:
carré de veau ×6.5, filet ×5.3, demi-carcasses ×3.7, ris ×2.9). Some pieces are limited by the animal itself (one
ris per veal, one onglet per beef, 21 days of maturation for the ribs). Until now the reservations were a paper list
("la liste est chez Damien") and the clients' requests free text in their history.

What this module does, all in plain rules (no model):
  - the two holiday windows of the year (Noël: 19–24/12, Nouvel An: 26–31/12), the same windows read in last year's
    deliveries;
  - each client's basket for those windows last year (`history`), so the agent can say "comme l'an dernier";
  - for the SCARCE pieces only, a capacity per window = the most the house delivered for that window last year:
    the one number the data can defend. Everything else is reserved without a cap;
  - a fair share when it gets tight: a client is guaranteed his own volume of last year (or 15 % of the window if
    that is more); beyond that, what is left, and the rest goes on a waiting list, never promised;
  - the order deadline per piece (whole veal and lamb, matured ribs: a week before; carcasses: 2 days; the rest:
    the day before), the client's delivery days, and no reservation on a blocked account.

A reservation is not an order: it is the promise of a volume for a date. The orders themselves are taken nearer the
date, as usual, so nothing here touches stock, orders or invoices.
"""

from __future__ import annotations

import math
from collections import defaultdict
from datetime import date, timedelta

from app import crud
from app.core.activity import Ctx, log_event, now, today
from app.core.db import Doc, per_data_version, transactional
from app.core.errors import HttpError, validation_error

WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]

# (first day, last day) in December, for this year and the same days of last year.
WINDOWS = {"noel": (19, 24), "nouvel_an": (26, 31)}
WINDOW_LABEL = {"noel": "Noël", "nouvel_an": "Nouvel An"}

# Pieces limited by the animal or by time: the only ones with a capacity. Reason = what the agent may say.
SCARCE: dict[str, str] = {
    "prd_0038": "un ris par veau",
    "prd_0039": "deux rognons par veau",
    "prd_0015": "un onglet par bête",
    "prd_0012": "deux filets par bœuf",
    "prd_0022": "un carré par côté de veau, et les veaux sous la mère sont comptés",
    "prd_0021": "deux quasis par veau",
    "prd_0011": "21 jours de maturation : ce qui n'est pas en chambre trois semaines avant ne sera pas prêt",
    "prd_0004": "veaux sous la mère réservés chez les éleveurs",
    "prd_0005": "veaux sous la mère réservés chez les éleveurs",
    "prd_0006": "agneaux réservés chez les éleveurs",
}
WEEK_BEFORE = {"prd_0004", "prd_0005", "prd_0006", "prd_0011"}  # house rules: veal/lamb, matured ribs
FAIR_SHARE = 0.15  # guaranteed to anyone, as a share of the window's capacity


def _year() -> int:
    return date.fromisoformat(today()).year


def window_of(day: date) -> str | None:
    if day.month != 12:
        return None
    return next((w for w, (a, b) in WINDOWS.items() if a <= day.day <= b), None)


def _window_dates(window: str, year: int) -> tuple[str, str]:
    a, b = WINDOWS[window]
    return f"{year}-12-{a:02d}", f"{year}-12-{b:02d}"


def _round_up(x: float) -> float:
    return math.ceil(x * 2) / 2  # to the half kilo / half unit


@per_data_version
def _last_year() -> dict:
    """{(window, clientId, productId): qty} and {(window, productId): qty} delivered last year in the windows."""
    year = _year() - 1
    ranges = {w: _window_dates(w, year) for w in WINDOWS}
    by_client: dict[tuple, float] = defaultdict(float)
    by_product: dict[tuple, float] = defaultdict(float)
    days: dict[tuple, set] = defaultdict(set)
    for o in crud.orders.all():
        d = (o.get("deliveryDate") or "")[:10]
        if not d.startswith(f"{year}-12") or o.get("status") == "cancelled":
            continue
        w = next((w for w, (a, b) in ranges.items() if a <= d <= b), None)
        if not w:
            continue
        days[(w, o["clientId"])].add(d)
        for ln in o.get("lines") or []:
            q = ln.get("qty") or 0
            by_client[(w, o["clientId"], ln["productId"])] += q
            by_product[(w, ln["productId"])] += q
    return {"by_client": by_client, "by_product": by_product, "days": days}


def capacity(window: str, product_id: str) -> float | None:
    """Scarce pieces only (None = no cap): the most the house delivered for that window last year."""
    if product_id not in SCARCE:
        return None
    return _round_up(_last_year()["by_product"].get((window, product_id), 0.0))


def _active() -> list[Doc]:
    return [r for r in crud.festive_reservations.all() if r.get("status") == "active"]


def _booked(window: str, product_id: str, exclude: str | None = None) -> tuple[float, float]:
    """(reserved, waitlisted) for a window and a piece, all clients."""
    rs = [r for r in _active() if r["window"] == window and r["productId"] == product_id and r["id"] != exclude]
    return sum(r["qtyReserved"] for r in rs), sum(r["qtyWaitlist"] for r in rs)


def guaranteed(window: str, client_id: str, product_id: str) -> float | None:
    cap = capacity(window, product_id)
    if cap is None:
        return None
    last = _last_year()["by_client"].get((window, client_id, product_id), 0.0)
    return _round_up(max(last, FAIR_SHARE * cap))


def deadline(product_id: str, day: date) -> date:
    """Last day to reserve for that delivery day (house rules, see 02-journee-type.md)."""
    product = crud.products.require(product_id)
    if product_id in WEEK_BEFORE:
        return day - timedelta(days=7)
    if product.get("category") == "carcasses":
        return day - timedelta(days=2)
    return day - timedelta(days=1)


def _product_view(p: Doc) -> Doc:
    return {"productId": p["id"], "productName": p["name"], "unit": p.get("unit")}


def _reservation_view(r: Doc) -> Doc:
    p = crud.products.table.rows.get(r["productId"])
    return {**r, "productName": (p or {}).get("name"), "windowLabel": WINDOW_LABEL[r["window"]]}


# ───────── Reads ─────────


def history(client_id: str) -> Doc:
    """The client's holiday basket last year, per window, biggest first, and his reservations this year."""
    client = crud.clients.require(client_id)
    ly = _last_year()
    year = _year() - 1
    windows = []
    for w in WINDOWS:
        lines = [
            {**_product_view(crud.products.require(pid)), "qty": round(q, 2), "scarce": pid in SCARCE}
            for (win, cid, pid), q in ly["by_client"].items()
            if win == w and cid == client_id and q > 0
        ]
        lines.sort(key=lambda x: -x["qty"] * (crud.products.require(x["productId"]).get("price") or 0))
        windows.append({"window": w, "label": WINDOW_LABEL[w], "deliveryDates": sorted(ly["days"].get((w, client_id), set())), "lines": lines})
    return {
        "clientId": client_id,
        "clientName": client["name"],
        "lastYear": year,
        "windows": windows,
        "reservations": [_reservation_view(r) for r in _active() if r["clientId"] == client_id],
    }


def availability(product_ids: list[str], client_id: str | None = None) -> Doc:
    """For each piece and window: capacity (scarce only), reserved, waitlist, left, the client's guaranteed share."""
    out = []
    for pid in product_ids:
        p = crud.products.require(pid)
        for w in WINDOWS:
            cap = capacity(w, pid)
            reserved, waitlist = _booked(w, pid)
            row = {**_product_view(p), "window": w, "label": WINDOW_LABEL[w], "scarce": cap is not None}
            if cap is not None:
                row.update(capacity=cap, reserved=round(reserved, 2), waitlist=round(waitlist, 2),
                           left=round(max(cap - reserved, 0), 2), reason=SCARCE[pid])  # fmt: skip
                if client_id:
                    row["guaranteedForClient"] = guaranteed(w, client_id, pid)
            out.append(row)
    return {"today": today(), "products": out}


def list_reservations(client_id: str | None = None, window: str | None = None) -> list[Doc]:
    rs = [r for r in _active() if (not client_id or r["clientId"] == client_id) and (not window or r["window"] == window)]
    return [_reservation_view(r) for r in sorted(rs, key=lambda r: r["createdAt"])]


def board() -> Doc:
    """Damien's view: per window, every scarce piece with capacity, reserved, waitlist and who; the other pieces
    reserved (no cap); and the holiday requests still only written as text in a client's history."""
    clients = crud.clients.table.rows
    windows = []
    for w in WINDOWS:
        scarce = []
        for pid in SCARCE:
            p = crud.products.table.rows.get(pid)
            if not p:
                continue
            cap = capacity(w, pid) or 0.0
            rs = [r for r in _active() if r["window"] == w and r["productId"] == pid]
            reserved = sum(r["qtyReserved"] for r in rs)
            waitlist = sum(r["qtyWaitlist"] for r in rs)
            scarce.append({
                **_product_view(p), "reason": SCARCE[pid], "capacity": cap, "reserved": round(reserved, 2),
                "waitlist": round(waitlist, 2), "left": round(max(cap - reserved, 0), 2),
                "shortfall": round(max(reserved + waitlist - cap, 0), 2),
                "clients": [{"clientId": r["clientId"], "clientName": (clients.get(r["clientId"]) or {}).get("name"),
                             "qtyReserved": r["qtyReserved"], "qtyWaitlist": r["qtyWaitlist"], "deliveryDate": r["deliveryDate"],
                             "reservationId": r["id"], "createdBy": r.get("createdBy")} for r in rs],
            })  # fmt: skip
        other: dict[str, float] = defaultdict(float)
        for r in _active():
            if r["window"] == w and r["productId"] not in SCARCE:
                other[r["productId"]] += r["qtyReserved"]
        windows.append({
            "window": w, "label": WINDOW_LABEL[w], "dates": list(_window_dates(w, _year())),
            "scarce": scarce,
            "other": [{**_product_view(crud.products.require(pid)), "reserved": round(q, 2)} for pid, q in other.items()],
        })  # fmt: skip
    booked = {r["clientId"] for r in _active()}
    requests = [
        {"eventId": e["id"], "clientId": e["clientId"], "clientName": (clients.get(e["clientId"]) or {}).get("name"),
         "at": e["at"], "title": e["title"], "description": e.get("description")}
        for e in crud.client_events.all()
        if e.get("type") == "special_request" and "fêtes" in (e.get("title") or "").lower()
        and (e.get("at") or "")[:4] == str(_year()) and e["clientId"] not in booked
    ]  # fmt: skip
    requests.sort(key=lambda x: x["at"], reverse=True)
    return {"today": today(), "windows": windows, "pendingRequests": requests}


# ───────── Writes ─────────


def _check_line(client: Doc, day: date, product_id: str, qty: float) -> Doc:
    p = crud.products.require(product_id)
    if not p.get("active", True):
        raise validation_error(f"{p['name']} n'est plus au catalogue")
    if qty <= 0:
        raise validation_error("quantité attendue > 0")
    last = deadline(product_id, day)
    if date.fromisoformat(today()) > last:
        raise HttpError(400, "too_late", f"{p['name']} pour le {day.day}/12 : réservation possible jusqu'au {last:%d/%m}, c'est passé")
    return p


@transactional
def reserve(ctx: Ctx, input: Doc) -> Doc:
    """Reserve volumes for one delivery date. All the lines are checked first: on a problem nothing is written.
    Scarce pieces: up to the client's guaranteed share or what is left, the rest on the waiting list."""
    client = crud.clients.require(input["clientId"])
    if client.get("status") == "blocked":
        raise HttpError(400, "client_blocked", f"Compte bloqué ({client['name']}) : pas de réservation tant que la comptabilité n'a pas levé le blocage")
    try:
        day = date.fromisoformat(input["deliveryDate"])
    except (ValueError, TypeError):
        raise validation_error("deliveryDate : format AAAA-MM-JJ attendu") from None
    window = window_of(day)
    if not window or day.year != _year():
        a, b = (_window_dates(w, _year()) for w in WINDOWS)
        raise validation_error(f"Le carnet des fêtes couvre Noël ({a[0][8:]}–{a[1][8:]}/12) et le Nouvel An ({b[0][8:]}–{b[1][8:]}/12)")
    days = client.get("deliveryDays") or []
    if days and WEEKDAYS[day.weekday()] not in days:
        raise HttpError(400, "not_a_delivery_day",
                        f"{client['name']} n'est pas livré le {JOURS[day.weekday()]} ; jours de livraison : "
                        + ", ".join(JOURS[WEEKDAYS.index(d)] for d in days if d in WEEKDAYS))  # fmt: skip
    lines = input.get("lines") or []
    if not lines:
        raise validation_error("au moins une ligne")
    checked = [(_check_line(client, day, ln["productId"], float(ln["qty"])), ln) for ln in lines]

    results = []
    for p, ln in checked:
        qty = float(ln["qty"])
        pid = p["id"]
        # One active reservation per client, window and piece: a second call adds to it.
        prev = next((r for r in _active() if r["clientId"] == client["id"] and r["window"] == window and r["productId"] == pid), None)
        # By default a second call adds to the reservation ("rajoutez-moi deux kilos"); replace=True sets the new total
        # ("finalement cinq au lieu de neuf").
        wanted = qty if input.get("replace") else qty + (prev["qtyRequested"] if prev else 0)
        cap = capacity(window, pid)
        if cap is None:
            got, wait = wanted, 0.0
        else:
            reserved_others, _ = _booked(window, pid, exclude=prev["id"] if prev else None)
            left = max(cap - reserved_others, 0)
            # 1. His guaranteed share (his volume of last year, or 15 % of the window), within what is left.
            got = min(wanted, guaranteed(window, client["id"], pid) or 0, left)
            # 2. Beyond it, only what nobody is owed: last year's buyers keep their volume until they reserve it.
            if got < wanted:
                spare = max(left - _owed_to_others(window, pid, client["id"]) - got, 0)
                got = min(wanted, got + spare)
            got = round(got, 2)
            wait = round(wanted - got, 2)
        doc = {
            "id": prev["id"] if prev else crud.festive_reservations.next_id("fet_"),
            "clientId": client["id"],
            "productId": pid,
            "unit": p.get("unit"),
            "window": window,
            "deliveryDate": day.isoformat(),
            "qtyRequested": round(wanted, 2),
            "qtyReserved": got,
            "qtyWaitlist": wait,
            "status": "active",
            "note": ln.get("note") or (prev or {}).get("note"),
            "createdAt": (prev or {}).get("createdAt") or now(),
            "updatedAt": now(),
            "createdBy": ctx.actor,
        }
        doc = {k: v for k, v in doc.items() if v is not None}
        crud.festive_reservations.put(doc)
        results.append(_line_result(doc, p, window, cap))
    log_event(ctx, "festive.reserved", "client", client["id"],
              f"Carnet des fêtes : {client['name']} réserve pour le {day.day}/12 — "
              + ", ".join(f"{r['productName']} {r['qtyReserved']:g}" + (f" (+{r['qtyWaitlist']:g} en attente)" if r["qtyWaitlist"] else "") for r in results))  # fmt: skip
    return {"clientId": client["id"], "clientName": client["name"], "deliveryDate": day.isoformat(), "window": window,
            "label": WINDOW_LABEL[window], "lines": results}  # fmt: skip


def _owed_to_others(window: str, product_id: str, client_id: str) -> float:
    """What last year's buyers of this piece are still owed (their volume of last year, not yet reserved)."""
    ly = _last_year()["by_client"]
    owed = 0.0
    for (w, cid, pid), q in ly.items():
        if w != window or pid != product_id or cid == client_id or q <= 0:
            continue
        mine = sum(r["qtyReserved"] for r in _active() if r["clientId"] == cid and r["window"] == w and r["productId"] == pid)
        owed += max(q - mine, 0)
    return owed


def _line_result(doc: Doc, p: Doc, window: str, cap: float | None) -> Doc:
    out = {"reservationId": doc["id"], "productId": p["id"], "productName": p["name"], "unit": p.get("unit"),
           "qtyRequested": doc["qtyRequested"], "qtyReserved": doc["qtyReserved"], "qtyWaitlist": doc["qtyWaitlist"],
           "deadline": deadline(p["id"], date.fromisoformat(doc["deliveryDate"])).isoformat()}  # fmt: skip
    if cap is not None:
        reserved, _ = _booked(window, p["id"])
        out.update(scarce=True, reason=SCARCE[p["id"]], left=round(max(cap - reserved, 0), 2))
    return out


@transactional
def cancel(ctx: Ctx, reservation_id: str) -> Doc:
    """Cancel a reservation; the freed volume goes to the waiting list, oldest first."""
    r = crud.festive_reservations.require(reservation_id)
    if r.get("status") != "active":
        raise HttpError(409, "invalid_state", "Réservation déjà annulée")
    crud.festive_reservations.put({**r, "status": "cancelled", "updatedAt": now()})
    client = crud.clients.require(r["clientId"])
    log_event(ctx, "festive.cancelled", "client", r["clientId"], f"Carnet des fêtes : {client['name']} annule sa réservation ({r['productId']}, {r['qtyReserved']:g})")
    promoted = _promote(ctx, r["window"], r["productId"])
    return {"cancelled": _reservation_view(crud.festive_reservations.require(reservation_id)), "promoted": promoted}


def _promote(ctx: Ctx, window: str, product_id: str) -> list[Doc]:
    cap = capacity(window, product_id)
    if cap is None:
        return []
    reserved, _ = _booked(window, product_id)
    left = cap - reserved
    promoted = []
    for r in sorted((r for r in _active() if r["window"] == window and r["productId"] == product_id and r["qtyWaitlist"] > 0),
                    key=lambda r: r["createdAt"]):  # fmt: skip
        if left <= 0:
            break
        take = round(min(left, r["qtyWaitlist"]), 2)
        crud.festive_reservations.put({**r, "qtyReserved": round(r["qtyReserved"] + take, 2), "qtyWaitlist": round(r["qtyWaitlist"] - take, 2), "updatedAt": now()})
        left -= take
        name = crud.clients.require(r["clientId"])["name"]
        log_event(ctx, "festive.promoted", "client", r["clientId"], f"Carnet des fêtes : {take:g} de la liste d'attente confirmés pour {name} — à le prévenir")
        promoted.append({"reservationId": r["id"], "clientId": r["clientId"], "clientName": name, "qty": take})
    return promoted
