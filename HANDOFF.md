# HANDOFF — append-only log between teammates' Claude sessions

**Rules**
- Read this file after `git pull`, at the start of every session.
- Add an entry **before every push**, with the newest entry at the top.
- Never edit or delete someone else's entry. Add a new one instead.
- Keep each entry short: what was done, what is next, what is broken, and any question for another lane.

Template:

```
## YYYY-MM-DD HH:MM · <who> (lane <X>) · <commit or branch>
**Done:**
**Next:**
**Broken / open questions:**
```

---

## 2026-11-23 21:50 · Claudio's session (lane D) · branch `d/eval-runner`
**Done:** First `make calls` baseline on `43573ec` (Sonnet, text only): **5/6 pass**. Time to first word: median 3.0 s,
worst 8.0 s. Full report with numbers: `evals/reports/2026-11-23-baseline.md`.

**For lane A (Alexander), in priority order:**
1. **T3 fails:** the agent says "je préviens Nicolas pour l'onglet" but never calls `log_client_event`. Any spoken
   promise of a follow-up must be backed by an event in the ERP.
2. In 11 of 18 turns the first word only comes after all the tools. ERP tools take < 0.6 s per turn; the time is
   2–4 model steps of 1.5–3 s each. An instant acknowledgement and prefetching the caller (already on your list)
   should cut the median a lot.
3. Every model step sends about 27k tokens even with no tool (prompt + tool definitions), and `identify_caller`
   returns about 3 kB. Trimming both helps speed and cost.

**Next (lane D):** Re-run on the latest `main` and after each lane A change. `make calls ARGS="T3 --repeat 3"` to
confirm the T3 fix.

## 2026-11-23 21:55 · Claudio's session (lane D) · branch `d/eval-runner`
**Done:** `make calls` (`evals/run_calls.py`, standard library only). It replays T1–T6 through POST /chat in voice mode,
resets the ERP before each scenario, then checks the ERP: new orders, lines, quantities, duplicates, the watched
existing orders and client events. Per turn it reports time to first word (text only, no STT/TTS), total time,
tool calls and tokens. It prints a row to paste into the results table of `SCENARIOS.md`. The checks were
verified both ways, with correct ERP actions giving PASS and typical mistakes giving FAIL. See `evals/README.md`.
Also added a `calls` target to the `Makefile` and `evals/results/` to `.gitignore`.

**Next:** Claudio runs the first baseline on his Mac with the real keys and pastes the row into `SCENARIOS.md`.

**For lane A / voice:** Run `make calls` before and after each change. The "1er mot" median is the LLM and tools
share of perceived latency, so a change that lowers it without failing a scenario is a real win. Heads-up: the
ERP API itself accepts orders for blocked clients, so only the agent's tool guard protects T5. Don't bypass that tool.

## 2026-11-23 21:20 · Claudio's session (lane D) · branch `d/scenarios`
**Done:** Added `SCENARIOS.md` with six regression calls (T1–T6), checked against the seed data:
- T1: a normal order from Boucherie Peyronnet.
- T2: an ambiguous caller, "Hyper Frais Limoges" (`cli_0034` vs `cli_0003`).
- T3: onglet out of stock for Restaurant Leroy.
- T4: a change of mind at Le Petit Roger.
- T5: a blocked account (Lacour).
- T6: "j'ai oublié un truc" from Boucherie Rolland, adding to draft CMD-2026-006248 for Wednesday.

Also added `CLAUDE.md` (shared session instructions, imports `AGENTS.md`) and this file.

**Next:** First full run of T1–T6 against `main` with real keys, recording the results in the `SCENARIOS.md` table.

**Broken / open questions for lane A:**
- `check_products` applies a flat 2-day lead time to the carcasses category. The house rule (`01-entreprise.md`)
  says slaughter is Monday and Thursday, so a calf or lamb ordered on Tuesday ships Friday at best. That means a
  demi-veau ordered Tuesday for Thursday would currently be accepted. It's not in T1–T6, but the jury may try it.
  Lane A to decide.

## 2026-11-23 ~21:00 · Alexander's session (lane A) · `0d585ff`
**Done:** Built and tested against the seed data:
- `apps/ai/app/tools/desk.py`: `identify_caller` and `check_products`.
- `apps/ai/app/tools/orders.py`: `update_order_line`, `remove_order_line`, `update_order` and `cancel_order`. Blocked
  accounts can't get an order, and an order can't be confirmed while a line is undeliverable.
- Backend: date-aware `GET /api/stock/availability` and `insufficient_stock` (`stock.availability_on`).
- `apps/ai/app/agent/prompts.py`: `BASE_RULES` and `VOICE_RULES` rewritten around these tools.

**Next (lane A):** An instant spoken acknowledgement, and looking up the caller before the model runs.

**Owns:** `apps/ai/app/tools/`, `apps/ai/app/agent/`, `apps/ai/app/services/voice_session.py`.
