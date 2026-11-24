# Pablo’s pitch guide — backstop and timekeeper

Exported 24/11 from the shared doc (https://claude.ai/artifact/RQyewyUMJ2G2dGQmygvSKV). Script for the slides: `SPEAKER-NOTES.md`.

## Your job

You are the backstop and the timekeeper. During the slides you keep Claudio on time. During the jury’s calls you keep the demo machine running: you reset the ERP between jurors, stage the “Cassez le matin” cards, watch the logs, and run the fallback if something breaks. You don’t speak unless someone asks you a question about speech, latency or cost.

**Three rules you never break**

1. **Never touch `.env` or the code during the demo.** Reload, `make reset` and `make chaos` are the only actions.
2. **Never run `make reset` in the middle of a call.** It wipes everything the agent has written, including the order the juror is placing. Only between jurors, and tell Claudio first (a nod is enough).
3. **Never run `make calls`, `make jury` or `make chaos-check` on the demo machine once we’re on.** They reset the ERP and use the shared API credits.

## Before we go on (T−30 min, on the demo machine)

Tick each box. Most of this comes from DEMO.md § 3.

- [ ] `git pull` on `main` at the frozen commit. Write it here: `________`
- [ ] `make up`. Check `http://localhost:4000/docs` and `http://localhost:4100/docs` both answer.
- [ ] Check `.env` without editing it: Soniox for speech-to-text, ElevenLabs `eleven_v4_turbo` with the frozen voice for TTS, the model the team agreed on.
- [ ] **ElevenLabs credit.** It ran out at 23:43 last night (HANDOFF). Confirm with Stockline that it was topped up. Then one short spoken turn proves speech-to-text and the voice; one typed turn proves the model.
- [ ] Hear the backup browser voice once (turn the network off for one turn). If it isn’t French, install a French system voice and reload the page.
- [ ] Headset mic plugged in and selected in the browser. Speakers loud enough for the room.
- [ ] Laptop on power, notifications off, other tabs closed.
- [ ] Phone hotspot ready, next to you, unlocked.
- [ ] Voix page open in demo mode: `http://localhost:5173/voice?demo=1` (Jed’s screen).
- [ ] One warm-up call, then **`make reset`**.
- [ ] The 2-minute video open in a second window, paused on its first frame.
- [ ] Two terminal tabs on your side: one running `make logs`, one at the repo folder for commands. The cheat sheet at the end of this guide open beside them.
- [ ] A visible timer for the 5 minutes (phone stopwatch), and the sabotage cards with their commands on the back.

## During the 5-minute slides

Start the stopwatch when Claudio says his first word. Sit where he can see you without turning his head. Agree the signals with him before we go on.

| Time | Claudio should be on | Your signal | If he is behind |
| --- | --- | --- | --- |
| 2:00 | Slide 4 (Smart) | Two fingers up | Still on slide 3: point at your watch. He skips the Stockline-agents sentence. |
| 4:00 | Slide 7 (How we know) | Four fingers up | Still on slide 6: point at your watch. He cuts the bug story to one sentence. |
| 4:40 | Slide 8 (Your turn) | Flat hand, “wrap up” | He reads the jury line and stops. |
| 5:00 | Done | Closed fist | — |

While he talks, watch the `make logs` tab: an error now means fix it before the jury calls (reload the page, check the network). On slide 8, have the sabotage cards ready to hand to Alexander, and the command tab focused.

## During the jury’s calls

**Between two jurors:** if the last call left the ERP in a state that would confuse the next one, run `make reset` (a few seconds). Nod to Claudio first. If nothing was written, skip it.

**When a juror picks a “Cassez le matin” card:**

1. Take the card. Read the reason the juror wrote. Keep it as one sentence a chef can hear; if it’s long, ask “On garde cette phrase ?” and use what they say.
2. Run `make reset` (only if a juror call has already written into the ERP).
3. Type the command from the back of the card, with the juror’s sentence between the quotes in `WHY`. Don’t use a straight double quote `"` inside the sentence.
4. Check the output ends with `Contrôle sans modèle : OK`. It also prints who gets called and the € at stake: read Claudio the number of calls.
5. Tell Jed “c’est prêt”. The “Avant le camion” panel updates without a reload; he clicks **Appeler** on a card and the juror plays that client.

| Card | Product | Suggested reason | Command |
| --- | --- | --- | --- |
| S1 | Côte de bœuf maturée 21 j | Chambre froide 2 en panne cette nuit : lot écarté par précaution | `make chaos PRODUCT=prd_0011 WHY="…"` |
| S2 | Train de côtes / entrecôte | La palette de lundi a cassé la chaîne du froid | `make chaos PRODUCT=prd_0010 WHY="…"` |
| S3 | Filet de bœuf paré | Filet saisi par les services vétérinaires ce matin | `make chaos PRODUCT=prd_0012 WHY="…"` |
| S4 | Foie de veau | Lot refusé au contrôle qualité de 3 h | `make chaos PRODUCT=prd_0037 WHY="…"` |
| S5 | Côte maturée, poids court | Une partie du lot n’a pas atteint ses 21 jours | `make chaos PRODUCT=prd_0011 WHY="…" ARGS="--short 30"` |

Only these five products. If a juror asks for another one, say: “On a vérifié ces cinq-là ; choisissez-en un, et la raison est la vôtre.” Never paleron (17 clients, too many for a live demo).

**Our own “Avant le camion” call (if we show it):** `make reset` first, so both onglet calls (Leroy, Le Bœuf Limousin) are back on the board.

## If something breaks

From DEMO.md § 6, with your part in each. Stay calm and act in this order: wait once, look at the logs, then the smallest fix.

| Symptom | You do | Who speaks |
| --- | --- | --- |
| Silence over ~5 s after the caller speaks | Wait once. Look at `make logs`. If there’s an error, tell Jed “recharge”. If not, the caller repeats the sentence. | Caller |
| Page error or the voice connection drops | Tell Jed to reload the Voix page and start a new call. | Jed |
| Caller not transcribed (speech-to-text down or out of credit) | Tell Jed: typed turns. The Voix page has a text box (“Ou tapez la phrase de l’appelant…”). | Claudio says so plainly |
| “TTS indisponible, voix de secours du navigateur” on screen | Nothing. The browser voice takes over and ElevenLabs is retried after 60 s. It answers later and sounds robotic. | Claudio, one sentence: “the voice provider failed, the agent switched to a backup voice” |
| Model errors in the logs, or no network | Switch the laptop to your phone hotspot. Still down: start the 2-minute video, then show the `make calls` and `make jury` results. | Claudio |
| `make chaos` doesn’t end with “OK” | `make reset`, then run the same command again. Still not OK: tell Claudio to move on to a normal call. | Claudio |
| A juror’s call left a mess (wrong client, half order) | After the call ends: `make reset`. Never mid-call. | — |

If you’re not sure what’s wrong, don’t guess in front of the jury: show Claudio a thumbs-down and switch to the video.

## Cheat sheet

Keep this open next to the terminal. Run everything from the repo folder.

| What | Command |
| --- | --- |
| Start the services | `make up` |
| Watch the logs (Ctrl-C to stop) | `make logs` |
| Reset the ERP to the data pack | `make reset` |
| Stage a sabotage card | `make chaos PRODUCT=prd_0011 WHY="…"` |
| Short-weight card (S5) | `make chaos PRODUCT=prd_0011 WHY="…" ARGS="--short 30"` |
| Products on today’s trucks | `python3 evals/break_morning.py --list` |
| Voix page, demo mode | `http://localhost:5173/voice?demo=1` |
| “Avant le camion” board | Header button **Avant le camion** on the Voix page (or `?camion=1`) |

**Not during the demo:** `make calls`, `make jury`, `make chaos-check` (they reset the ERP and use credits), `make clean` (deletes the database), anything in `.env`.
