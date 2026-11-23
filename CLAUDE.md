# CLAUDE.md — team-06 · Chevillard du Limousin

Shared instructions for every teammate's Claude session. The kit's own guide for coding agents is imported below.

@AGENTS.md

## Start of every session

1. Run **`git pull`** before reading or creating anything. Another session may have pushed since.
2. Read **`HANDOFF.md`** (the latest entries first) to see who is doing what.
3. Check the lane table below and only edit files your lane owns. For anything else, write a note in
   `HANDOFF.md` or ask the owner.

## Use case (decided)

**Inbound phone order-taking for butchers and restaurants.** A client calls, the agent identifies them, takes the
order (including "the usual"), checks price, stock and lead times for the delivery date, reads the order back and
confirms it in the ERP.

**Showpiece, only once the core passes all six test calls in `SCENARIOS.md`:** a client calls about a short
delivery, and the agent reads them the weigh ticket (prepared vs ordered weight, lot number).

## Already built and tested against the seed data: do not redo or rewrite

- `apps/ai/app/tools/desk.py`:
  - `identify_caller`: one call returns the full client card, and asks when two clients are plausible.
  - `check_products`: price, stock at the delivery date, pieces → kilos, lead time and delivery day.
- `apps/ai/app/tools/orders.py`:
  - `update_order_line`, `remove_order_line`, `update_order`, `cancel_order`.
  - No order can be created for a blocked account.
  - No confirmation while a line cannot be delivered.
- Backend: `GET /api/stock/availability?date=&productIds=` and the `insufficient_stock` warning are date-aware
  (`stock.availability_on`).
- `apps/ai/app/agent/prompts.py`: `BASE_RULES` and `VOICE_RULES` were rewritten around those tools.

## Lanes and file ownership

| Lane | Owner | Owns |
|---|---|---|
| A · Agent + tools | Alexander's session | `apps/ai/app/tools/`, `apps/ai/app/agent/`, `apps/ai/app/services/voice_session.py` |
| D · Tests + docs | Claudio's session | `SCENARIOS.md`, `DECISIONS.md`, `HANDOFF.md` structure, slides and video notes |
| B · Speech (STT/TTS) | Pablo's session | `apps/ai/app/clients/` (speech providers), STT checks, TTS voice and latency |
| C · Frontend (Voix page) | Jed's session | `apps/web/` (live call cards: `apps/web/src/pages/voice/`) |

Lane A is working on next:
- an instant spoken acknowledgement;
- looking up the caller before the model runs.

## Testing

- **`make calls`** replays T1–T6 automatically and checks the ERP (see `evals/README.md`). It resets the local ERP and
  uses real LLM credits. Run it before merging anything that touches the agent.
- **`SCENARIOS.md`** holds the six regression calls (T1–T6). Run `make reset` before each series, replay them after
  every significant change, and add a row to its results table.
- `make chat` talks to the agent in the terminal and shows tools, time and tokens. The **Voix** page runs a real
  voice turn with latency.
- If a test call fails because of a file you don't own, write the failure in `HANDOFF.md` for the owner rather than
  fixing it yourself.

## Facts the agent must get right

- The data is frozen at **Tuesday 24/11/2026, 05:00**.
- Carcasses and quarters are ordered **2 days ahead**. Slaughter is on Monday and Thursday: a calf or lamb ordered on
  Tuesday ships Friday at best.
- PAD pieces, offal and prepared products must be ordered **before 17:00** for the next morning.
- Canteens order **3 days ahead, before 11:00**, with a purchase-order number.
- Pieces are converted to kilos for the order, but the invoice follows the real weight.
- Out of stock: onglet (`prd_0015`) and ris de veau (`prd_0038`).
- Blocked accounts: `cli_0005`, `cli_0006`, `cli_0046`.
- Many clients refuse substitutions: never substitute without an explicit yes.

## Git rules

- Use short branches named `<lane>/<topic>` (e.g. `d/scenarios`). Pull before pushing; keep merges small and frequent.
- **Before every push, add an entry to `HANDOFF.md`.**
- Never commit `.env` or `data/seed/`.
- `main` must always start with `make setup`.
- Code freeze is Tuesday 13:00. Submission is **Tuesday 17:30**.
