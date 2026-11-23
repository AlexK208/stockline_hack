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

## 2026-11-23 22:33 · Pablo's session (lane B) · branch `b/stt-check`
**Done:** STT check with Soniox on the Voix page, results in `STT-TEST.md`. 14/14 correct in a quiet room;
occasional misses on "onglet" and "BL".
**Next:** nothing planned. STT is not a priority.
**Broken / open questions:** the STT vocabulary list is close to its 6,000-character cap (~5,922 used), so
adding many products or aliases could silently drop some.
## 2026-11-23 23:30 · Jed's session (lane C) · branch `c/live-cards`
**Done:** Pulled `a85646c` (lane A) and `DECISIONS.md` (lane D), with no conflicts. 91/91 AI tests pass on the
current code. The ai container only mounts `app/`, so its `tests/` folder is stale: a plain `pytest` inside the
container shows 2 false failures. Web typecheck passes. The ai service reloaded with the new code.

T1 again on `WS /voice` (typed turns, `make reset` first, claude-sonnet-5-5 / Soniox / ElevenLabs):

| Turn | Agent said | Tools | First word / total |
|---|---|---|---|
| 1 | "Bonjour Céline. Ta commande de jeudi est prête : deux arrières, soit environ deux cents kilos, et un avant, environ cent dix kilos, facturés au poids réel. L'éleveur Dumontet et la livraison avant six heures trente sont notés sur la commande, mais je ne peux pas te les garantir. Je la confirme ?" | caller lookup (code) 0.17 s, `create_draft_order` 0.35 s | 0.11 s / 5.3 s |
| 2 | "Très bien, c'est confirmé pour jeudi : deux arrières et un avant. Tu as besoin d'autre chose ?" | `confirm_order` 0.07 s | 2.9 s / 3.2 s |

ERP: **PASS**, same as before. CMD-2026-006259 confirmed for Thursday 26/11: 200 kg at 10.20 € + 110 kg at 6.11 €,
2 712,10 € excl. tax. Dumontet is on the order and on each line; CMD-2026-006219 is untouched.

**Fixed since my 23:00 entry:** the read-back now gives each line's weight, as T1 expects. `create_draft_order` went
from 1.2 s to 0.35 s.

**Correction to my 23:00 entry:** "the caller lookup before the model did not happen" is wrong for the current code.
The `identify_caller` with `said: "Boucherie Peyronnet"` is the code-side lookup in `agent/loop.py`, not the model,
and takes 0.17 s with no extra model step. I hadn't checked where that call came from in the first run either.

**Still open for lane A:**
- "mais je ne peux pas te les garantir" still sounds negative to a regular client.
- Turn 2: 2.9 s of silence after "C'est bon, vas-y." That follows the new "nothing after a yes" rule; your call
  whether it's worth it.
- **Forward `result` on `agent_tool`** (`voice_session.py` ~263-265: `case ToolResultEvent(name=name, ok=ok, ms=ms,
  result=result)` and `AgentToolMessage(..., result=result)`). The loop already has the client card 0.17 s into the
  turn. Without this, the Client en ligne card only appears at `create_draft_order`, about 4.5 s in.

**Next:** Jed checks the cards on screen and runs T4 and T5.

## 2026-11-23 23:15 · Claudio's session (lane D) · branch `d/decisions`
**Done:** Wrote **`DECISIONS.md`**. It did not exist, and it is a required deliverable in `BRIEF.md` — "le jury le
lira". Lane D owns it. It is in French, like `BRIEF.md` and `SCENARIOS.md`.

It covers what the brief asks for: the problem and why we chose it, our technical choices, what worked, what did
not, and the measurements (latency, cost, scenario pass rate). Everything is sourced from `evals/results/` and
reproducible with `make calls`; anything not measured is marked as such.

**Decisions I recorded on your behalf — please correct anything I got wrong, it is your work:**
- Alexander: self-checking write tools, caller pre-identification, the code-chosen acknowledgement ("D'accord."
  rejected because it reads as a yes before a refusal), the no-claim-without-a-tool rule, Sonnet over Haiku with
  the T6 reason, and the carcass lead time (doc says Monday/Thursday slaughter, 12 months of history says a flat
  2 days, 224 veal and 123 lamb — we follow the data). That last one you asked twice to have written down.
- Jed: the 0.09 s first word on `WS /voice` is in the latency table as the headline voice number.

**Three things worth knowing, because they shape how the numbers read:**
1. **The median latency got worse (3032 → 3445 ms) and I wrote it up as a win.** p90 −2352 ms, worst −3181 ms,
   spread nearly halved. On a phone call the tour where the line sounds dead is what loses the caller, not the
   average one. The document says this explicitly rather than hiding the median.
2. **Cost: 84–88 % of input tokens are cache reads.** So shortening the system prompt is the wrong lever — we
   recorded that as an abandoned idea. The real saving was removing a model step: −20 % input tokens per call
   versus the baseline, while adding features.
3. **No euro figure.** `claude-sonnet-5-5` and `claude-haiku-5-5` are not on a public rate card I could verify,
   and cache reads bill differently. I gave tokens per successful call instead and said plainly why. Inventing a
   €/MTok rate in a document the jury reads was not worth it. If anyone has the real grid, it is one multiplication.

**`identify_caller` is written up as an open, uncorrected defect (§ 5.1)**, with the suggested guard. I would rather
the jury see that we found it, measured it and said so, than discover it live. Alexander, it is still the highest
-value fix left.

**Next (lane D):** slides and video notes — the two remaining deliverables I own. Shout if you want the DECISIONS
wording changed first.

## 2026-11-23 23:00 · Jed's session (lane C) · branch `c/live-cards`
**Done:** T1 on the Voix WebSocket (`/ai/voice`, typed turns like the page's text box), after `make reset`, with
anthropic:claude-sonnet-5-5, Soniox and ElevenLabs. No browser was used, so the cards were checked against the data
they read, not on screen.

| Turn | Agent said | Tools | First word / total |
|---|---|---|---|
| 1 | "Bonjour Céline. Ta commande de jeudi est prête : deux arrières et un avant, soit environ trois cent dix kilos, facturés au poids réel. La génisse de chez Dumontet et la livraison avant six heures trente sont notées sur la commande, je ne peux pas te les garantir moi-même. Je te la confirme ?" | `identify_caller` 0.5 s, `create_draft_order` 1.2 s | 0.09 s / 5.4 s (LLM 4.6 s) |
| 2 | "Voyons… C'est confirmé pour jeudi : deux arrières et un avant, avec les demandes notées sur la commande. Je peux faire autre chose pour toi ?" | `confirm_order` 0.07 s | ~0 s / 2.5 s (LLM 2.0 s) |

ERP: **PASS.** CMD-2026-006259, confirmed, Thursday 26/11, source `voice_agent`. Hindquarter (`prd_0001`) 200 kg at
10.20 € (negotiated price), forequarter (`prd_0002`) 110 kg at 6.11 €, total 2 712,10 € excl. tax. "Génisse de chez
Dumontet" is on the order and on each line. Today's order CMD-2026-006219 is untouched (still "prepared").

Cards (from their data): Client en ligne = Boucherie Peyronnet, Limoges, account OK, Aurélie Faucher, delivered
Tuesday, Thursday and Saturday, "Refuse les substitutions" in red, usual order led by hindquarter ~113 kg. Commande
en cours = 200 kg and 110 kg, both "En stock" for 26/11 (3 884 kg and 5 702 kg left), Confirmée, 2 712,10 €.

**For lane A:**
- The read-back gives one combined total ("environ trois cent dix kilos"). T1 expects each line's weight
  ("deux quartiers arrière, environ deux cents kilos").
- "je ne peux pas te les garantir moi-même" sounds negative to a regular client.
- The caller lookup before the model did not happen: the model called `identify_caller` itself (+0.5 s and a model
  step).
- Still open from my previous entry: forward `result` on `agent_tool`. Until then the client card appears on
  `create_draft_order`, not on `identify_caller`.

**Next:** Jed checks the cards on screen (Voix page, same two lines) and runs T4 and T5.

## 2026-11-23 22:45 · Claudio's session (lane D) · branch `d/spoken-checks`
**Done:** The spoken-output checks lane A asked for. `make calls` now checks what the agent *says* on T5 and T6,
not only what reaches the ERP. Merged `origin/main` (`c954a9e`, lane C's call cards): 87 tests pass.

**Why these exist:** when a tool refuses a write, nothing reaches the ERP, so a false promise to the caller leaves
no trace and the scenario passes. The ERP checks are blind to it by construction.

- **T6** — the answer to "et une demi-carcasse de porc" must not accept mercredi, and must be backed by a tool call
  in that turn. A clarifying question ("porc standard ou cul noir ?") asserts nothing and is never punished.
  This is the exact case Alexander saw Haiku fail.
- **T5** — no other client's card may be opened, no other client named aloud, no internal figure (plafond, encours,
  échu) read to the caller.
- **`make calls-test`** (`evals/test_checks.py`, no model, no credits) exercises all 13 checks in both directions
  with hand-written turns. Run it after touching any `check_…`. Word lists are `REFUS` and `DEMAIN` in
  `run_calls.py`: widen them rather than tightening the logic.

**Validated against a real run (`2c052d5`, T5 + T6):** T6 passed all three new checks on the real Sonnet wording —
no false failures. Known limit: amounts are matched as digits, so "cent vingt-neuf mille" spelled out would slip through.

**⚠️ Alexander: the `identify_caller` defect is reproducible, and it is silent. 2 runs out of 2.**
On the second run the agent said nothing wrong — the spoken answer was courteous and correct — but it still called
`identify_caller("Le Comptoir de la Viande")` on turn 2 and opened `cli_0038`'s card. The caller never heard about
it this time. So:

- the ERP checks cannot see it (reading writes nothing);
- the spoken checks cannot see it either, when the model happens not to mention it;
- **only the tool-level check catches it**, which is why it is there.

It surfaces at random: first run it leaked into speech, second run it did not. Treat it as a live confidentiality
risk, not a cosmetic bug — `identify_caller` returns contacts, phone numbers, plafond, encours and échu.
Suggested guard unchanged (lane A, `tools/desk.py` / `agent/loop.py`): once the caller is identified, do not let
`identify_caller` switch to another client on a free-text guess.

**T5 therefore fails now (suite reads 5/6).** That is a newly *detected* real defect, not a new regression: the
agent behaved the same way on `be7eb4b` when the suite still said 6/6.

**Next (lane D):** once the guard lands, re-run the full set and record the row. Haiku can then be evaluated with
`make calls ARGS="--repeat 3"` — the checks that would have caught its T6 claim now exist.

**Lane C (Jed):** noted you have the Voix page; the voice replay of T1–T6 is yours, so I am not touching it.

## 2026-11-23 22:40 · Jed's session (lane C) · branch `c/live-cards`
**Done:** Jed takes lane C (frontend). On the Voix page, two cards above "ERP en direct" (`pages/voice/call-cards.tsx`):
- **Client en ligne**: name, town, account OK or blocked, sales rep, delivery days, overdue amount, the substitution
  rule (red when the client refuses them) and the usual order. Shows the candidates when the caller is ambiguous.
- **Commande en cours**: the order the voice agent is writing, line by line, with a stock badge for the delivery date
  (`GET /api/stock/availability`). Removed lines stay crossed out, a changed quantity shows the old one crossed out,
  and the status goes from draft to confirmed.
- Plumbing: optional `result` field on the `agent_tool` message (`schemas/voice.py`, `packages/shared/src/ai.ts`),
  kept by `useVoiceSession`; `api.stock.availability` + `useStockAvailability`; `StockAvailability` type.

**For lane A (2 small changes in `voice_session.py`, which you own):**
1. Line ~242: `case ToolResultEvent(name=name, ok=ok, ms=ms, result=result)` and send
   `AgentToolMessage(name=name, ok=ok, ms=ms, result=result)`. The client card then shows on the `identify_caller`
   result and the candidates on an ambiguous call.
2. When `prefetch_caller` finds the caller, send `AgentToolMessage(name="identify_caller", ok=True,
   result={"status": "found", "client": {"id": client_id}})` so the card appears before the model even answers.
Until then the client card shows as soon as any tool runs with a `clientId` (`check_products`, `create_draft_order`)
or the order exists.

**Next:** Jed tests on the Voix page (T1, T3, T4, T5, T6).
**Broken / open questions:** none known. Lane B still has no owner.
## 2026-11-23 22:20 · Claudio's session (lane D) · branch `d/eval-runner`
**Done:** Merged `origin/main` (`7208081` then `ad5a776`) into `d/eval-runner`. 87 tests pass. Full `make calls`
on the merged tree (`be7eb4b`): **6/6 confirmed on my Mac**, your fixes hold. Row added to `SCENARIOS.md`.
Earlier I also ran `make calls ARGS="T3 --repeat 3"` on `7166485`: 3/3, the client-event fix is solid.

**Latency, the honest reading — the median is not the story.** Median first word went 3022 → 3445 ms (worse),
but the tail collapsed:

| commit | min | médiane | p90 | pire | étendue | tokens entrée (18 tours) |
|---|---|---|---|---|---|---|
| 43573ec (baseline) | 563 | 3032 | 6811 | 7992 | 7429 | 1 245 032 |
| 99842b2 | 1182 | 3022 | 7052 | 7890 | 6708 | 1 295 948 |
| be7eb4b (now) | 676 | 3445 | 4700 | 4709 | 4033 | 994 729 |

p90 −2352 ms, worst −3181 ms, spread almost halved, input tokens −23 %. On a phone call the worst wait is what
makes a caller think the line is dead, so I read this as a clear win even though the median moved the wrong way.
My numbers run slower than yours (you had 2855 ms median) — different machine, so compare shapes, not absolutes.

**Your self-checking write tools work exactly as intended.** T3 turn 1: `create_draft_order` returned
`problems: ['Onglet de bœuf : rupture']` and wrote nothing, the model retried without the onglet and logged the
event. That is the behaviour you designed, visible in the trace.

**T6, the Haiku worry you raised — Sonnet is clean on `ad5a776`.** Turn 2 ("et une demi-carcasse de porc") the
agent called `add_order_line`, the tool refused on lead time, and it said: *"Pour demain c'est trop tard. La
demi-carcasse de porc se commande deux jours avant. Je peux te la mettre pour samedi."* Tool-backed and correct.
Your new prompt rule holds here.

**⚠️ But a new problem, and it is the best argument yet for your spoken-output request. T5, turn 2.**
The caller said only: *"Allez, un seul quartier, tu vas pas me laisser sans viande pour le week-end !"*
The agent invented a client name out of the word "viande", called `identify_caller(said="Le Comptoir de la
Viande")`, and **opened a different real client's card, `cli_0038`** — then told Gérard about it:
*"Pardon, je viens aussi d'ouvrir une fiche qui n'était pas la vôtre par erreur. Je n'y ai rien modifié."*

- **T5 still passed every hard check**, because nothing was written. The ERP-only checks are blind to this.
- Nothing was written and nothing confidential was read aloud, so no damage in this run.
- The risk is real though: `identify_caller` returns the full card — contacts, phone numbers, credit limit,
  outstanding and overdue amounts. That is another customer's commercial data pulled into a call with a blocked,
  hostile caller. One sentence further and it is a confidentiality problem.
- This is **not** your `loop.py` pre-identification: that matches the caller's opening words on turn 1, and turn 1
  resolved `cli_0005` correctly. The bad call came from the model on turn 2.
- **Suggested guard (lane A, `tools/desk.py` / `agent/loop.py`, your call):** once a caller is identified in a
  session, `identify_caller` should not silently switch to another client on a free-text guess — either refuse,
  or require an explicit confirmation step.

**Your request accepted (lane D):** I will add checks on what the agent *says*, not only on the ERP, starting with
T6 ("demi-carcasse de porc" must not be accepted for Wednesday) and T5 (must not mention another client, must not
read internal figures). The T5 case above is exactly why.

**On Haiku:** I would not switch yet. T5 shows Sonnet already inventing a client name from a stray word; a faster,
less careful model on the same tool surface is a bad trade until the spoken-output checks exist to catch it.
Happy to run `make calls ARGS="--repeat 3"` on Haiku once they are in.

**Next (lane D):** spoken-output checks, then re-run. The voice replay of T1–T6 on the Voix page is being handled
by someone else, so the perceived-latency columns are not blocked on me.

## 2026-11-23 22:41 · Alexander's session (lane A) · not yet committed
Three agents ran against the core: a code audit, a research pass on spoken French, and a "juror" who wrote 12 new
calls (`evals/jury_calls.json`, J1 to J12, with expected ERP state and what the agent must or must not say).

**Audit findings fixed (the first one was serious):**
- `tools/desk.py` matcher picked a WRONG client on a bare first name, a surname shared with another account, or an
  everyday word ("c'est Julien" → the hospital, "Peyrat" → Peyrat Traiteur, "de la viande hachée" → Le Comptoir de
  la Viande, an unknown butcher in Tulle → Lacour). My earlier "never wrong" claim only covered full names. Now: a
  first name, a town or a trade word alone never names a client; two accounts that explain the same words are both
  returned; a changed letter is another word. Replayed on 1,176 introductions built from the seed: 0 wrong.
- `identify_caller` with `clientId`: refused when what the caller said still fits several clients ("Karim, le
  boucher, à Limoges" fits two). Candidates now show each client's trade.
- `agent/loop.py`: the code-side lookup runs only before `identify_caller` has been called at all (it was also
  running on the caller's answer to "lequel ?").
- `tools/orders.py`: `update_order` re-checks every line for a new date; lowering a quantity is never refused;
  `create_draft_order` refuses a second open order for the same client and day; blocked accounts are refused on
  every write tool.
- Canteens: 3 days ahead (`check_items`). Lead-time messages now give the client's first possible delivery day.
- `voice_session.py`: the client card is kept for the whole call (was dropped after about 10 turns); a technical
  error is spoken; the page shows only what is spoken.

**Opening words (the "Alors…" complaint), rebuilt from the research:** a request gets "Je regarde." / "Un instant."
/ "Je vérifie." (never "d'accord": in French it accepts the request), a change of mind "Je corrige.", a plea "Je
comprends."; nothing after a yes, on a goodbye, or two turns in a row. `VOICE_ACK=smart|greeting|off` in `.env`.
Sources are in the research report (ask lane A): they belong in `DECISIONS.md`.

**New tool:** `order_history` (ordered vs weighed per line): "pareil que samedi", "il manquait un kilo".

**Results on lane A's copy:** `make calls` 6/6. J1 to J12 replayed through `WS /voice` and read one by one: 11 as
the juror expected. **J10 differs on purpose:** matured ribs asked 4 days ahead are ACCEPTED when the ageing room
covers the request, and the agent says the one-week rule aloud. Reason: 692 rib lines in 12 months were all ordered
1 to 3 days ahead. To make the rule strict, set `LEAD_DAYS_BY_PRODUCT`-style behaviour in `tools/desk.py`
(`RESERVE_DAYS_WHEN_SHORT`). **Team decision needed.**

**Lane D:** please wire `evals/jury_calls.json` into the runner (the `expected` lists are written to be checked).

## 2026-11-23 22:12 · Alexander's session (lane A) · not yet committed
**Baseline on Alexander's Mac (`7208081`, Sonnet 5.5):** `make calls` 6/6, médiane 2855 ms, pire 6165 ms.

**Haiku 5.5 tried on lane A's copy (`LLM_MODEL=claude-haiku-5-5`, same code):** 6/6 on one full run, then 4/4 and
4/4 on repeats of T1/T3/T4/T6. First word: median about 1.3 to 1.9 s, worst about 3 s (Sonnet: 2.9 s and 6.2 s).
But in T6 it once answered "je peux la rajouter pour mercredi" for a demi-porc WITHOUT calling a tool, which is
false (2-day lead time). The hard checks did not catch it because nothing was written. It also asks more
clarifying questions (porc standard ou cul noir ?).

**Done after that:**
- `prompts.py`: the agent may not say a product, quantity or date is possible or impossible from memory, only from
  a tool result of the current turn. Internal information (credit, margin, lot dates) is not said to the client.
- `tools/orders.py`: `expiring_soon` and `price_below_cost` warnings are no longer passed to the model (Haiku read
  a lot expiry date to the caller).
- With the rule, Haiku stopped making the claim in 2 more T6 runs. Not enough runs to trust it yet.

**Decision for now:** Sonnet stays the default. **Lane D, a request:** add a check on what the agent SAYS, not
only on the ERP: in T6, the answer to "et une demi-carcasse de porc" must not accept Wednesday. Then
`make calls ARGS="--repeat 3"` on Haiku tells us whether we can switch.

## 2026-11-23 22:05 · Claudio's session (lane D) · branch `d/eval-runner`
**Done:** Merged `origin/d/eval-runner` then `origin/main` (`d2abbd6`) into `d/eval-runner`. The only conflict was
this file; every entry from both sides was kept. `uv run pytest`: 87 pass. Re-ran `make calls` on the merged tree
(`99842b2`): **5/6**, 1er mot médiane 3022 ms, p90 6191 ms, pire 7890 ms (18 tours). Row added to `SCENARIOS.md`.

**Important for lane A (Alexander) — the run does not measure your latency work.** `make calls` drives
`POST /chat`, and `call_prep.py` is imported only by `voice_session.py`. So neither the instant acknowledgement
nor the pre-identification runs on the path I measured: `identify_caller` is still the first tool call in all six
scenarios, and the median is unchanged from the baseline (3032 → 3022 ms). That is **not** evidence your work
didn't help — it means this harness can't see it. Your Voix-page numbers (8.7 → 3.6 s first sound) remain the
measurement that counts for those two changes.

**T3 still fails, same check as before:** the agent handles the stockout correctly (8 kg faux-filet, no onglet, no
bavette, confirmed) but still does not log the onglet request as a client event. In this run it put the request in
the order note instead, which matches the wrinkle you already listed.

**Next (lane D):** replay T1–T6 by voice on the Voix page, as you asked, and fill the perceived-latency columns —
that is the only way to capture the acknowledgement and pre-identification gains. Then `make calls ARGS="T3 --repeat 3"`
once the client-event fix lands.

**Open question for lane A:** would it be worth having `POST /chat` share `call_prep` with the voice session? Today
the two paths differ, so an eval through `/chat` will keep under-reporting voice work. Your call — `voice_session.py`
is yours.

## 2026-11-23 22:03 · Alexander's session (lane A) · not yet committed
**Done (after the first `make calls` run: 5/6, médiane 2859 ms, pire 7567 ms):**
- `tools/orders.py`: `create_draft_order`, `add_order_line` and `update_order_line` now run the checks themselves
  (stock at the delivery date, lead time, delivery day, pieces → kilos). On a problem they write nothing and return
  `problems`. The model no longer calls `check_products` before writing: one model step less per order turn.
  `check_products` stays for questions ("il vous reste de l'onglet ?").
- `agent/loop.py`: when the caller's first words match exactly one client, `identify_caller` is run in code before
  the model (it shows as a normal tool row, about 50 ms). Works for `/chat` and `make calls` too.
- `prompts.py`: a product asked for but not served (stockout, no substitute) is logged with `log_client_event`
  (`special_request`). This was the T3 failure.

**`make calls` on lane A's copy, same commit of the runner:** 6/6. T1 first turn 7.0 s → 3.3 s; worst turn
7.6 s → 5.9 s; input tokens per call about 216k → 165k. Median first word about 3.0 s (was 2.9 s): the floor is now
two model calls on any turn that writes. Lane D: please rerun `make calls` after pulling and paste the row.

**Next (lane A):** try `LLM_MODEL=claude-haiku-5-5` against `make calls`; keep it only at 6/6.

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

## 2026-11-23 21:47 · Alexander's session (lane A) · not yet committed
**Done:**
- `apps/ai/app/services/call_prep.py` (new) + `voice_session.py`:
  - instant acknowledgement spoken the moment the caller stops ("Bonjour Christian." on the first turn, then a
    neutral "Alors…" / "Voyons…"), chosen in code from the live transcript. Neutral on purpose: "D'accord." before a
    refusal sounded like a yes.
  - caller identified in code before the model runs (same matcher as `identify_caller`); the client card is handed
    to the model inside the turn, so the first turn costs one model step less.
- `prompts.py`: requirements such as "génisse de chez Dumontet" go into the order or line note; the agent may not
  say "je transmets / je note / je vous rappelle" unless it wrote it with a tool.
- Tests: `tests/test_call_prep.py` added (87 pass).

**T1–T6 replayed as typed turns through `WS /voice` (real model, mock speech), after `make reset`:** all six end
with the expected ERP state (T2 asks which Hyper Frais; T5 creates no order and logs the call; T4 ends with one
order, 8 kg faux-filet + 8 kg tende de tranche; T6 edits the existing draft, bavette 7 → 12). Not yet replayed by
voice. Lane D: please run them by voice and fill the `SCENARIOS.md` table.

**Known wrinkles:**
- T3: the agent does not give the reason for the onglet stockout ("un par bête") and puts the request in the order
  note, not in a client event.
- The model sometimes repeats the caller's first name right after the acknowledgement.
- The real answer still takes 2 to 5 s after the acknowledgement (one model call per tool step).
- `TTS_MODEL=eleven_v4_turbo` in `.env` sounds more French (Alexander's ear). `.env` is not in git: each teammate
  sets it locally. A French `TTS_VOICE` id is still needed from Stockline (our key cannot list voices).

**Next (lane A):** cut the 2–5 s (fewer tool steps, try Haiku against T1–T6).

## 2026-11-23 21:35 · Alexander's session (lane A) · `d3b7aac`
**Done:**
- `voice_session.py`: the model's waiting phrase ("Je regarde.") is now spoken before the tools run, not after.
- `prompts.py`: spoken style (no unprompted full read-back, fewer commas, short product names) and a rule to write
  exactly the quantities the agent proposed.
- Voice page, Peyronnet first turn: first sound 8.7 s (kit) → 5.0 s → 3.6 s.

**Answer to lane D (lead time for veal and lamb):** keeping the flat 2 days for the whole carcasses category.
The order history disagrees with the "ordered Tuesday, ships Friday at best" line in `01-entreprise.md`: over the
last 12 months, veal carcasses were ordered on a Tuesday for Thursday 224 times and lamb 123 times, and every carcass
order is placed exactly 2 days ahead. Refusing a Tuesday → Thursday demi-veau would refuse what the company does
every week. When veal or lamb is not in stock for the date, `check_products` already reports it with the next
arrival. Worth one line in `DECISIONS.md` (doc and data disagree; we follow the data).

**Next (lane A):** instant spoken acknowledgement at end of speech; caller lookup before the model runs.

**Broken / open questions:**
- Voice (lane B/C, unassigned): the default ElevenLabs voice speaks French with an English rhythm and pauses
  before "kilos". Needs a French `TTS_VOICE` id from Stockline, or try `TTS_MODEL=eleven_v4_turbo` in `.env`.
- T3 expects the stockout reason ("un onglet par bête") and a logged client event for the onglet request: not
  checked yet with the model.

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
