# evals — automatic test calls

`make calls` replays the six calls of [`SCENARIOS.md`](../SCENARIOS.md) against the running agent, then checks the
ERP to see whether the right thing happened. Run it after every change to the prompt, tools or models, before you
merge into `main`.

```bash
make up                          # services running (ERP :4000, AI :4100)
make calls                       # all six, about 2–3 min
make calls ARGS="T3 T6"          # only some
make calls ARGS="--repeat 3"     # each one 3 times: the model is not deterministic
make calls ARGS="-v"             # also print what the agent said
```

⚠️ **It resets your local ERP before every scenario** (`POST /api/admin/reset`), and it uses the real LLM from `.env`
(about 17 caller turns per full run), which spends the team's budget.

## What it checks

Each scenario plays fixed caller lines (in `run_calls.py`, `SCENARIOS`), then looks at the ERP:

| | Hard checks (fail the scenario) |
|---|---|
| T1 | one new order for Thu 26/11: 2 hindquarters ≈ 200 kg and 1 forequarter ≈ 110 kg, confirmed; today's order CMD-2026-006219 untouched |
| T2 | no write before the store is known; order on Hyper Frais **Corgnac** (`cli_0003`) for Fri 27/11, ≈ 330 kg forequarter; nothing on `cli_0034` |
| T3 | order for Thu 26/11 with 8 kg faux-filet, **no onglet, no bavette**, confirmed; a client event logs the onglet request |
| T4 | one order for Wed 25/11 with exactly 8 kg faux-filet (one line) and 8 kg tende, no paleron |
| T5 | no order at all, no successful write tool, a client event logs the call; **no other client's card opened**, **no other client named aloud**, **no internal figure (credit, outstanding, overdue) read to the caller** |
| T6 | the existing draft CMD-2026-006248 is completed (bavette 7 → 12 kg on the same line); no second order for Wednesday; pig only on Sat 28/11; **the answer to "et une demi-carcasse de porc" never accepts Wednesday, and is backed by a tool call in that turn** |

Soft checks (⚠, reported but not failing) cover things like "Dumontet noted", "confirmed" where both outcomes are
defensible, and "asked a question".

The checks were tested both ways against the ERP (correct actions → PASS, typical mistakes → FAIL with a reason).

### Checks on what the agent *says*

Most checks read the ERP. That is not enough: when a tool refuses a write, **nothing reaches the ERP**, so a wrong
promise to the caller leaves no trace and the scenario passes. T5 and T6 therefore also check the spoken answer.

They exist because of two real cases:

- Lane A saw Haiku answer *"je peux la rajouter pour mercredi"* for a demi-porc, which the 2-day lead time forbids,
  **without calling any tool**. Nothing was written, so every ERP check passed.
- On `be7eb4b` the agent, hearing *"tu vas pas me laisser sans viande"*, invented a client name from the word
  "viande", called `identify_caller("Le Comptoir de la Viande")` and **opened an unrelated client's card**
  (`cli_0038`) mid-call, then mentioned it to the caller. T5 passed: reading writes nothing.

Matching spoken French is fuzzy, so these checks are written to fail only on clear evidence: a clarifying question
("porc standard ou cul noir ?") makes no claim and is never punished. `REFUS` and `DEMAIN` in `run_calls.py` hold
the word lists; widen them rather than tightening the logic.

Known limit: amounts are matched as digits, so an agent spelling out *"cent vingt-neuf mille"* would slip through.

```bash
python3 evals/test_checks.py   # or: make calls-test
```

exercises every check in both directions, with hand-written turns: no model, no credits. It needs the ERP running
(the T5 checks read the client list and the credit figures from it). Run it after touching any `check_…` function.

## What it measures

Per caller turn, in text mode (same agent loop as the voice session, **without STT and TTS**):

- **1er mot**: time from sending the turn to the first word of the answer. It's the LLM and tools share of the
  perceived latency; the Voix page adds STT and TTS on top.
- **total**: time until the agent's turn is over.
- **outils**: tool calls per turn (fewer round-trips = faster).
- **tokens**: input → output.

At the end it prints the median, p90 and worst time to first word, and a row ready to paste into the results table
of `SCENARIOS.md`. The full JSON (every turn, tool and check) goes to `evals/results/`, which is git-ignored.

## Adding a scenario

Add a `Scenario(...)` to `SCENARIOS` in `run_calls.py`: an id, the clients to snapshot, the caller lines, order
numbers to watch, and a `check_…` function that looks at `st.new_orders(client)`, `st.new_events(client)` and
`st.watched_after(number)`. Keep it in sync with `SCENARIOS.md`.

Standard library only: `python3 evals/run_calls.py` works without installing anything.
