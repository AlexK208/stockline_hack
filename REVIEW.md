# REVIEW.md — where team-06 stands, and what to do with the time left

Written 2026-11-24 ~01:10 on `53bc540`, by lane D. **Code freeze 13:00, submission 17:30** — about 12 hours of
building time left.

This file is a working document for planning and brainstorming, not a deliverable. The deliverable that the jury
reads is [`DECISIONS.md`](DECISIONS.md). Everything factual below is measured and reproducible; anything that is a
judgement call says so.

---

## 1. Snapshot

| | State | Evidence |
|---|---|---|
| Scenarios T1–T6 | **6/6** on `8a2d158` | `make calls`, 18 turns, `evals/results/` |
| Jury calls J1–J18 | **18/18** on the automatic invariants | `make jury`, 57 turns |
| Unit tests | **97 pass** | `make test` |
| Check-the-checks | green | `make calls-test` |
| Text latency | median 3124 ms, p90 4286 ms, worst 4526 ms | 18 turns, one run |
| Voice latency | **0,09–0,61 s to first audio** on a request (8,7 s in the kit); **2,5–3,5 s after a « oui »** (no acknowledgement there, by design). ⚠️ Typed turns, measured in the server: no STT, no browser playback. Spoken end-to-end not measured yet | lane C, `WS /voice`, T1 T4 T5 T6 |
| Cost | ~177 400 input tokens per call, ~26 500 outside cache (85 % cache) | same run |
| Model | `claude-sonnet-5-5` | `.env` |
| Voice | 🔒 **FROZEN** on `401765f` — ElevenLabs `eleven_v4_turbo`, voice `JBFqnCBsd6RMkjVDRZzb`, fr | HANDOFF 23:20 |

### Deliverables (`BRIEF.md` §8)

- [x] Repo that runs from `make setup`
- [x] `DECISIONS.md`
- [ ] **Slides (5 min)** — not started
- [ ] **Demo video (2 min)** — not started
- [ ] **Live demo rehearsal** — not done

**The two missing deliverables are worth more than any remaining code.** A 6/6 agent that the jury never sees
properly scores worse than a 5/6 agent with a clean demo. Treat §5 as the default plan and §4 as optional.

---

## 2. What is strong — do not break it

Know what you are risking before changing anything.

1. **Write tools verify themselves.** `create_draft_order`, `add_order_line`, `update_order_line` check stock,
   lead time, delivery day and pieces→kilos, and write nothing when there is a problem. The model cannot forget
   a rule that lives in the tool.
2. **One call = one client** (`call_guard` in `agent/loop.py`). The agent cannot touch another client's file or
   order. This fixed a real defect where the agent invented a client name from a stray word.
3. **No credit figures on the phone.** Removed from the card and the voice prompt, not just forbidden by prompt.
4. **The eval harness.** `make calls` (ERP + spoken + tool checks), `make jury` (18 hostile calls),
   `make calls-test` (tests the checks themselves, no credits).
5. **The voice.** The tester who could not understand it an hour before now says it is good. **Frozen.**

---

## 3. What needs improving most, ranked

### 3.1 The demo story is untold — highest value, lowest risk

Nothing in the repo explains, in 5 minutes, what we built and why it is good. All the material exists
(`DECISIONS.md`, the measurement tables, the jury transcripts); none of it is in a form a jury sees. **This is the
single biggest gap.**

### 3.2 The live demo is unrehearsed — highest risk

The jury will call the agent live on scenarios we do not know. We have never done a full run-through under
demo conditions: who talks, which scenario, what happens when it goes wrong. An untested demo path is how a
6/6 agent looks broken on stage.

### 3.3 The jury transcripts were never human-graded

`make jury` gives 18/18 on the **invariants** (no internal figure spoken, no write before identification). Each
scenario's `expected` is prose and was deliberately left for a human. **Nobody has read them.** The transcripts are
in `evals/results/jury-*.json` and printed by `make jury ARGS="-v"`. This is cheap (no credits, just reading) and
is the most likely place to find a real behavioural defect before the jury does.

Known unresolved from lane A: **J10, matured ribs** — accepted from stock with the one-week rule stated; nobody
decided whether that is right.

### 3.4 Latency is measured as a point, not an interval

Every latency number is **one run**. `93fc71b` and `8a2d158` are near-identical code, yet median moved
2764 → 3124 ms and the worst turn 7023 → 4526 ms. That spread is sampling noise. Any claim of the form "this
change made it faster" based on one run is unsupported. `make calls ARGS="--repeat 3"` would fix it.

### 3.5 The voice: settled, frozen

~~The voice speaks French with an English accent.~~ **Out of date** (correction by lane B, 24/11 ~03:40): since
`401765f` the tester who could not understand the French says the voice is good, and the team agrees by ear. It is
frozen as it is (ElevenLabs `eleven_v4_turbo`, voice `JBFqnCBsd6RMkjVDRZzb`, fr). Gradium stays an option only on a
branch, with the tester's OK, and is not needed to win.

### 3.6 Smaller open items

- Agent wording gaps in T5 (not `identify_caller`, which works there): Jean-Louis is not named; the agent answers "vous" to a caller who says "tu".
- Haiku was rejected before the spoken checks existed. It is now re-evaluable and is ~2× faster. Nobody has retried.
- `Jev` (the fast decision model) has a key in `.env` and is **not used at all** — only `agent/jev_examples.py`
  references it.

---

## 4. What could be added (optional — only if §5 is on track)

Ranked by impact per hour. **None of these is worth missing the slides or the video.**

| Idea | Why it would land | Cost | Risk |
|---|---|---|---|
| **Weigh-ticket showpiece** | The use case we chose it for, from `CLAUDE.md`: a client calls about a short delivery, the agent reads the weigh ticket. **The data is already there** — `order_history` returns ordered vs `weighed` (`preparedQty`), and `/api/stock` returns lots with id, supplier, received and expiry dates. Mostly a prompt + one small tool. | 1–2 h | Low; touches lane A files |
| **Haiku re-evaluation** | A 2× latency win would be the "le plus rapide" prize. The checks that caught its failure now exist. One `.env` line + `make calls ARGS="--repeat 3"` + `make jury`. | ~45 min, credits | Low — measurement only, no code change |
| **`--repeat 3` on the final commit** | Turns every latency claim from a point into an interval. Strengthens `DECISIONS.md` for the jury. | ~15 min, credits | None |
| **Jev for one yes/no decision** | `BRIEF.md` explicitly lists it as a technique. Would show model-tiering. | 1–2 h | Medium — new code near the freeze, low payoff |

**Recommendation: weigh ticket only if lane A finishes early.** Everything else is measurement, which is cheap and
safe. Do not start Jev.

---

## 5. Task split — four people, no clashes

Ownership is by **file path**. If you need to change a file you do not own, write it in `HANDOFF.md` and let the
owner do it. This has held all night; the only conflicts we have had are in `HANDOFF.md` itself.

| Lane | Who | Owns (do not edit outside this) |
|---|---|---|
| **A** | Alexander | `apps/ai/app/tools/`, `apps/ai/app/agent/`, `apps/ai/app/services/voice_session.py`, `call_prep.py` |
| **B** | Pablo | `apps/ai/app/clients/` (speech providers), STT/TTS checks |
| **C** | Jed | `apps/web/` |
| **D** | Claudio | `SCENARIOS.md`, `DECISIONS.md`, `REVIEW.md`, `HANDOFF.md`, `evals/`, slides and video |

### Proposed assignment for the remaining hours

**Lane D (Claudio) — deliverables. Start now, nothing else matters more.**
1. Slides, 5 minutes. Outline: the problem and why → the demo → three technical choices (self-checking tools,
   one call = one client, code-chosen acknowledgement) → the measurements → what we would do next.
2. Demo video, 2 minutes: one real end-to-end call.
3. Keep `DECISIONS.md` in step with any new measurement.
4. If time: `make calls ARGS="--repeat 3"` for a latency interval.

**Lane C (Jed) — own the demo, you have the screen.**
1. Finish checking the cards on screen (T1, T4, T5, T6).
2. **Drive the live-demo rehearsal.** Decide the scenario, who speaks, what we do if the agent stalls. This is
   §3.2 and it is nobody's lane today, so take it.
3. Help film the video — you know what looks good on the page.

**Lane A (Alexander) — correctness, then the showpiece.**
1. **Read the 18 jury transcripts against their `expected`** (`make jury ARGS="-v"`, or
   `evals/results/jury-*.json`). Free, and the likeliest place to find a real defect. Decide J10 (matured ribs).
2. Fix the small T5 wording gaps (Jean-Louis not named, "tu"/"vous").
3. **Only if 1 and 2 are done:** the weigh-ticket showpiece (§4).
4. ⚠️ You own the voice freeze. Nobody lifts it but you.

**Lane B (Pablo) — measurement, no new code.**
1. **Haiku re-evaluation** (§4). `.env` only, no code change: `make calls ARGS="--repeat 3"` then `make jury`.
   Report numbers to lane D for `DECISIONS.md`. Recommend a switch **only** at full green, and it is Alexander's
   call because of the voice freeze.
2. Chase Stockline for a Gradium key. If it arrives: branch only, tester listens, nothing to `main` without
   Alexander.
3. Voice samples for a human to pick from are in `~/Downloads/tts-samples/`.

### Why these do not clash

- D writes docs and `evals/`; nobody else touches those.
- C writes `apps/web/`; nobody else touches that.
- A writes `apps/ai/app/{tools,agent,services}/`; nobody else touches those.
- B changes **`.env` only** (local, git-ignored) and `apps/ai/app/clients/` if anything.
- A's reading task and B's measuring task both use the ERP. **`make calls`, `make jury` and `make reset` wipe the
  local ERP**, so two people running them at once on the same machine will corrupt each other's results. Agree
  who runs evals, or run on different machines.

---

## 6. Merge discipline

Everything merges through small branches named `<lane>/<topic>`. Two lessons from tonight, both learned the hard
way:

1. **`HANDOFF.md` is where every conflict happens.** Two entries were silently lost in one merge tonight (lane C's
   23:30 and lane B's STT entry, both in PR #4, mine) and had to be restored by their authors. Git auto-merges
   this file happily and wrongly. Before committing a resolution, check the union:
   ```bash
   comm -23 <(git show origin/main:HANDOFF.md | grep '^## 2026' | sort) \
            <(grep '^## 2026' HANDOFF.md | sort)      # must print nothing
   ```
2. **Conflict markers have been committed to `main` at least once.** `grep -n '^<<<<<<<\|^>>>>>>>' HANDOFF.md`
   before every push.

Before every push: add a `HANDOFF.md` entry, run `make test`, and for anything touching `evals/` also
`make calls-test`.

---

## 7. Questions worth arguing about

Open questions for whoever brainstorms with this file. None has an obvious answer.

1. **Do we show the jury a failure?** `DECISIONS.md` tells the story of a real defect we found, measured and
   fixed (`identify_caller` opening another client's file). It is our strongest evidence that the eval harness
   works. Does that read as rigour, or as an admission? We currently lead with it.
2. **Median vs tail.** Our median latency is ordinary (~3,1 s); our tail is excellent (worst turn 4,5 s, from
   8,0 s). The "fastest" prize is measured on end-of-speech → first sound. On typed turns we measured
   **0,09–0,61 s** thanks to the spoken acknowledgement, but that skips speech-to-text and browser playback, and a
   turn after a « oui » gets no acknowledgement (2,5–3,5 s). Only a spoken measurement on the Voix page (its latency
   chips) gives the number a jury would hear. Which number do we put on the slide?
3. **Is the acknowledgement cheating?** The agent says "Je regarde." / "Un instant." / "Je corrige." instantly
   (nothing after a yes), then thinks for 2–4 s. It is honest
   (it never states a fact) and it is what a human does on the phone. But a jury measuring "first sound" gets
   well under a second while the real answer takes longer. Do we explain this on the slide, or let the number speak?
4. **Haiku.** 2× faster, and it once claimed a delivery date without calling a tool. The checks that catch that
   now exist. Is a measured, fully green Haiku worth switching to 12 hours before the demo?
5. **Weigh ticket or polish?** A new showpiece the jury has not seen before, versus a demo we have rehearsed
   three times. We think rehearsal wins, but it is close.
