#!/usr/bin/env python3
"""
« Cassez le matin » : the jury breaks the morning, the agent finds every client hit and calls them.

    make chaos PRODUCT=prd_0011 WHY="Chambre froide 2 en panne cette nuit : lot écarté par précaution"
    make chaos PRODUCT=prd_0012 WHY="…" ARGS="--short 30"     # 70 % loaded instead of 0 (« poids court »)
    python3 evals/break_morning.py --list                     # products on today's trucks, clients hit by each
    make chaos-check                                          # the five cards of DEMO.md § 9, reset before each

« Qui est servi d'abord » (services/allocation.py): part of the lot survives, a person decides who gets it.
    make chaos PRODUCT=prd_0011 WHY="…" ARGS="--keep 20"                  # prints both plans, writes NOTHING
    make chaos PRODUCT=prd_0011 WHY="…" ARGS="--keep 20 --apply"          # writes the priority plan, then the board
    make chaos PRODUCT=prd_0011 WHY="…" ARGS="--keep 20 --apply --mode prorata"

What it does, through the ERP API only (no model, no credits):
  1. writes the product's whole stock off (POST /api/stock/adjust, reason "adjustment", note = WHY: the agent says
     that note to the client as the reason);
  2. on every prepared order of today, sets each line of that product (not a substitute line) to preparedQty 0,
     or to (100 − short) % of the ordered quantity with --short;
  3. prints GET /outbound/truck-calls and checks, without a model, that the board calls exactly the orders broken
     here (plus those already on it) in truck-departure order.

`make reset` undoes everything. Keep to products with 4–6 clients on today's trucks (prd_0011, prd_0010, prd_0012,
prd_0037). Never stage an overweight: the call has no tool to fix it yet.
Standard library only.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request

ERP, AI = "http://localhost:4000", "http://localhost:4100"

# The five sabotage cards of DEMO.md § 9: (product, reason the juror types, percent short).
CARDS = [
    ("prd_0011", "Chambre froide 2 en panne cette nuit : lot écarté par précaution", 0),
    ("prd_0010", "La palette de lundi a cassé la chaîne du froid", 0),
    ("prd_0012", "Filet saisi par les services vétérinaires ce matin", 0),
    ("prd_0037", "Lot refusé au contrôle qualité de 3 h", 0),
    ("prd_0011", "Une partie du lot n'a pas atteint ses 21 jours", 30),
]
# « Qui est servi d'abord »: (product, reason, kg left, plan applied).
ALLOCATION_CARDS = [
    ("prd_0011", "Chambre froide 2 en panne : il ne reste que 20 kg de côtes saines", 20, "priority"),
    ("prd_0010", "La palette de lundi a cassé la chaîne du froid : 30 kg sauvés", 30, "prorata"),
]


def call(base: str, path: str, method: str = "GET", body: dict | None = None, params: dict | None = None):
    url = base + path + ("?" + urllib.parse.urlencode(params) if params else "")
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, method=method, data=data, headers={"content-type": "application/json", "x-actor": "user"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def items(x):
    return x.get("items", x) if isinstance(x, dict) else x


def today_orders() -> list[dict]:
    today = call(ERP, "/api/meta")["today"][:10]
    rows = items(call(ERP, "/api/orders", params={"status": "prepared", "date": today, "limit": 500}))
    return [call(ERP, f"/api/orders/{o['id']}") for o in rows]


def list_products(orders: list[dict]) -> None:
    hit: dict[str, tuple[str, set]] = {}
    for o in orders:
        for l in o.get("lines") or []:
            if not l.get("substituteFor"):
                hit.setdefault(l["productId"], (l.get("productName") or "", set()))[1].add(o["clientId"])
    for pid, (name, clients) in sorted(hit.items(), key=lambda kv: -len(kv[1][1])):
        mark = "  ← bon candidat" if 4 <= len(clients) <= 6 else ""
        print(f"  {pid}  {len(clients):>2} client(s)  {name}{mark}")


def stage(product_id: str, why: str, short: int, orders: list[dict]) -> list[str]:
    product = call(ERP, f"/api/products/{product_id}")
    on_hand = float(product.get("onHand") or 0)
    if on_hand > 0:
        call(ERP, "/api/stock/adjust", "POST", {"productId": product_id, "qty": -on_hand, "reason": "adjustment", "note": why})
        print(f"Stock de {product['name']} : {on_hand:g} {product.get('unit')} déclassés — « {why} »")
    else:
        print(f"Stock de {product['name']} déjà à 0 : rien à déclasser (la raison dite sera celle déjà notée dans l'ERP)")
    broken = []
    for o in orders:
        for l in o.get("lines") or []:
            if l["productId"] != product_id or l.get("substituteFor"):
                continue
            loaded = round(float(l["qty"]) * (100 - short) / 100, 2) if short else 0
            call(ERP, f"/api/orders/{o['id']}/lines/{l['id']}", "PATCH", {"preparedQty": loaded})
            broken.append(o["id"])
            print(f"  {o.get('number')} {o.get('clientName') or o['clientId']} : {l['qty']:g} commandé → {loaded:g} dans le camion")
    return broken


def print_plans(p: dict) -> None:
    print(f"{p['productName']} : {p['available']:g} {p['unit']} pour {p['clients']} client(s) qui en ont commandé {p['ordered']:g}")
    print("  règles : " + " · ".join(p["rules"]))
    for mode, plan in p["plans"].items():
        label = "PRIORITÉ (recommandé)" if mode == p["recommended"] else "MÊME PART POUR TOUS"
        print(f"\n  {label} — servis en entier {plan['fullyServed']}, en partie {plan['partly']}, rien {plan['nothing']} · "
              f"{plan['toCall']} appel(s) · {plan['notDelivered']:.2f} € non livrés")
        for l in plan["lines"]:
            mark = "☎" if l["call"] else " "
            print(f"   {mark} {l['clientName'][:30]:<30} {l['ordered']:>6g} → {l['loaded']:>6g}  {l['reason']}")


def check_plan(p: dict) -> bool:
    ok = True
    for mode, plan in p["plans"].items():
        over = [l["clientName"] for l in plan["lines"] if l["loaded"] > l["ordered"] + 1e-9 or l["loaded"] < 0]
        total = round(sum(l["loaded"] for l in plan["lines"]), 2)
        if over or total > p["available"] + 1e-9:
            print(f"  ÉCHEC {mode} : plus que commandé {over} ou plus que disponible ({total} > {p['available']})")
            ok = False
    return ok


def allocate(product: str, keep: float, why: str, apply: bool, mode: str, before: set[str]) -> bool:
    p = call(AI, "/outbound/allocation", params={"productId": product, "available": keep})
    print_plans(p)
    ok = check_plan(p)
    if not apply:
        print("\nRien n'est écrit. Pour appliquer ce plan après l'avoir lu : ajoutez --apply (et --mode prorata pour l'autre).")
        return ok
    out = call(AI, "/outbound/allocation/apply", "POST", {"productId": product, "available": keep, "mode": mode, "why": why})
    print(f"\nPlan « {out['applied']} » appliqué : stock ramené à {keep:g} {p['unit']}, {len(out['lines'])} ligne(s) chargées.")
    should_call = [l["orderId"] for l in out["lines"] if l["call"]]
    full = [l["orderId"] for l in out["lines"] if l["missing"] <= 0]
    ok = show_and_check(should_call, before) and ok
    time.sleep(0.2)
    ids = {c["orderId"] for c in call(AI, "/outbound/truck-calls")["calls"]}
    wrongly = [o for o in full if o in ids]
    if wrongly:
        print("  ÉCHEC : servis en entier mais appelés :", ", ".join(wrongly))
    return ok and not wrongly


def show_and_check(broken: list[str], before: set[str]) -> bool:
    time.sleep(3.2)  # the board is cached 3 s (services/truck_calls.py BOARD_TTL_S)
    board = call(AI, "/outbound/truck-calls")
    print(f"\nTableau « Avant le camion » : {board['toCall']} appel(s), {board['atStake']:.2f} € en jeu")
    for c in board["calls"]:
        t = c.get("truck") or {}
        probs = ", ".join(f"{p['productName']} ({p['kind']})" for p in c["problems"])
        print(f"  {t.get('departure')} {t.get('route') or '':<14} {c['clientName']:<32} {c['substitution']:<6} {probs}")
    for t in board.get("tolerated") or []:
        print(f"  laissé tranquille : {t['clientName']} — {t['productName']} ({t['why']})")

    ids = [c["orderId"] for c in board["calls"]]
    deps = [((c.get("truck") or {}).get("departure") or "99") for c in board["calls"]]
    missing = [o for o in broken if o not in ids]
    extra = [o for o in ids if o not in broken and o not in before]
    ok = not missing and not extra and deps == sorted(deps)
    print("\nContrôle sans modèle :", "OK" if ok else "ÉCHEC")
    if missing:
        print("  commandes cassées absentes du tableau (poids court sous le seuil 5 % / 15 € ?) :", ", ".join(missing))
    if extra:
        print("  appels inattendus :", ", ".join(extra))
    if deps != sorted(deps):
        print("  appels pas triés par départ du camion :", deps)
    return ok


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("product", nargs="?")
    ap.add_argument("--why", default="Lot écarté cette nuit par précaution")
    ap.add_argument("--short", type=int, default=0, help="percent missing (0 = absent from the truck)")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--cards", action="store_true", help="run the five sabotage cards, ERP reset before and after each")
    ap.add_argument("--keep", type=float, help="kg (or units) of the lot that survive: propose who gets them")
    ap.add_argument("--apply", action="store_true", help="with --keep: write the plan (after a person has read it)")
    ap.add_argument("--mode", choices=["priority", "prorata"], default="priority")
    a = ap.parse_args()
    if a.cards:
        results = []
        for product, why, short in CARDS:
            print(f"\n════ {product} {'--short ' + str(short) if short else ''} · {why}")
            call(ERP, "/api/admin/reset", "POST", {})
            orders = today_orders()
            time.sleep(3.2)
            before = {c["orderId"] for c in call(AI, "/outbound/truck-calls")["calls"]}
            broken = stage(product, why, short, orders)
            results.append(bool(broken) and show_and_check(broken, before))
        for product, why, keep, mode in ALLOCATION_CARDS:
            print(f"\n════ {product} --keep {keep:g} --apply --mode {mode} · {why}")
            call(ERP, "/api/admin/reset", "POST", {})
            time.sleep(3.2)
            before = {c["orderId"] for c in call(AI, "/outbound/truck-calls")["calls"]}
            results.append(allocate(product, keep, why, True, mode, before))
        call(ERP, "/api/admin/reset", "POST", {})
        print(f"\nCartes sabotage : {sum(results)}/{len(results)} OK (ERP remis à zéro)")
        return 0 if all(results) else 1
    orders = today_orders()
    if a.list or not a.product:
        list_products(orders)
        return 0
    if not 0 <= a.short < 100:
        ap.error("--short must be between 0 and 99")
    time.sleep(3.2)
    before = {c["orderId"] for c in call(AI, "/outbound/truck-calls")["calls"]}
    if a.keep is not None:
        return 0 if allocate(a.product, a.keep, a.why, a.apply, a.mode, before) else 1
    broken = stage(a.product, a.why, a.short, orders)
    if not broken:
        print("Aucune commande du jour ne contient ce produit : rien à casser.")
        return 1
    return 0 if show_and_check(broken, before) else 1


if __name__ == "__main__":
    sys.exit(main())
