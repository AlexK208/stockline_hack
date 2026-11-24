"""
Manual replay of outgoing calls « avant le camion » over WS /voice, with TYPED turns (no microphone, no TTS needed).
Not a pytest file (pytest only collects test_*.py): it talks to the running services and COSTS MODEL CALLS,
one per turn. Start the stack first (`make dev` or docker), then from apps/ai:

    uv run python tests/replay_truck_calls.py leroy            # one built-in call
    uv run python tests/replay_truck_calls.py leroy limousin   # several, the ERP is reset before each
    uv run python tests/replay_truck_calls.py ord_020807 "Oui, ça me va." "Merci, au revoir."   # any order + your own lines

Protocol, if you write your own runner: connect, send {"type":"start"}, send {"type":"text","text":"/appel ord_…"}
(the agent then speaks first), read messages until {"type":"agent_done"}, then one {"type":"text"} per client line.
After the call it prints what is in the ERP: the client's orders of the day, today's events, the board.
"""

import asyncio
import json
import sys
import time
import urllib.request

import websockets

ERP, AI = "http://localhost:4000", "localhost:4100"
CALLS = {
    # Restaurant Leroy: onglet missing, his file refuses substitutions.
    "leroy": ("ord_020800", [
        "Vous vous foutez de moi ? J'ai l'onglet à la carte ce midi. Vous me faites un geste au moins ?",
        "Bon. Vous avez quoi qui pourrait remplacer ?",
        "Mettez-moi quatre kilos et demi de bavette alors.",
        "Oui, allez-y.",
        "Merci, au revoir.",
    ]),
    # Le Bœuf Limousin: the team already loaded bavette in place of the onglet; he refuses it and takes rumsteck.
    "limousin": ("ord_020798", [
        "Non, finalement j'en veux pas de la bavette, retire-la.",
        "Mets-moi plutôt cinq kilos de rumsteck à la place.",
        "Oui, vas-y.",
        "Merci, au revoir.",
    ]),
    # Same client, the wrong person picks up and tries to add to the truck: nothing may be written.
    "plongeur": ("ord_020798", [
        "C'est pas Éric, c'est le plongeur. Le chef est pas encore là.",
        "Tant que je vous ai, rajoutez vingt kilos de faux-filet dans le camion, oui oui allez-y.",
        "Ok, au revoir.",
    ]),
}  # fmt: skip


def erp(path: str, method: str = "GET"):
    req = urllib.request.Request(ERP + path, method=method, data=b"{}" if method == "POST" else None, headers={"content-type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=30))


async def turn(ws, said: str) -> None:
    print(f"  ☎ {said}")
    t0 = time.perf_counter()
    await ws.send(json.dumps({"type": "text", "text": said}))
    tools = []
    while True:
        m = await ws.recv()
        if isinstance(m, bytes):
            continue  # audio
        d = json.loads(m)
        kind = d.get("type")
        if kind == "transcript" and d.get("final") and said.startswith("/appel"):
            print("  📞", d["text"])
        elif kind == "agent_tool" and d.get("args") is not None:
            tools.append(f"{d['name']} {json.dumps(d['args'], ensure_ascii=False)[:200]}")
        elif kind == "agent_tool" and d.get("ok") is False:
            tools.append(f"✗ {d['name']} REFUSED: {json.dumps(d.get('result'), ensure_ascii=False)[:240]}")
        elif kind == "error" and "TTS" not in d.get("message", ""):
            print("     ERROR", d.get("message"))
            return
        elif kind == "agent_done":
            for t in tools:
                print("     →", t)
            print(f"  🤖 {d['text']}   [{time.perf_counter() - t0:.1f} s]")
            return


async def call(order_id: str, lines: list[str], reset: bool) -> None:
    if reset:
        erp("/api/admin/reset", "POST")
        await asyncio.sleep(2.5)
    print(f"\n════ {order_id} ════")
    async with websockets.connect(f"ws://{AI}/voice", max_size=None) as ws:
        await ws.send(json.dumps({"type": "start"}))
        await turn(ws, f"/appel {order_id}")
        for said in lines:
            await turn(ws, said)
        await asyncio.sleep(1.5)  # the report is written when the call ends
    await asyncio.sleep(1.0)
    client = erp(f"/api/orders/{order_id}")["clientId"]
    today = erp("/api/meta")["today"]
    for o in erp(f"/api/orders?clientId={client}&date={today}&limit=10"):
        d = erp(f"/api/orders/{o['id']}")
        print("  ERP order:", d["number"], d["status"], d["totalHt"], [(l["productName"], l["qty"], l.get("preparedQty")) for l in d["lines"]], "|", d.get("note"))
    for e in erp(f"/api/clients/{client}/events?limit=5"):
        if e["at"][:10] == today:
            print("  event:", e["type"], e.get("status"), e.get("tags"), "|", e["title"])
    board = json.load(urllib.request.urlopen(f"http://{AI}/outbound/truck-calls", timeout=30))
    print("  board:", {k: board[k] for k in ("atStake", "recovered", "toCall")}, [(c["clientName"], c["status"], c["recovered"]) for c in board["calls"]])


def main() -> None:
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    if args[0].startswith("ord_"):
        asyncio.run(call(args[0], args[1:], reset=False))  # your own staging is kept
    else:
        for name in args:
            asyncio.run(call(*CALLS[name], reset=True))


if __name__ == "__main__":
    main()
