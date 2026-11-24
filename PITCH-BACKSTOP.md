# Pitch run sheet — roles, timing and backstop

7 minutes, slides and live demo together. Deck: https://claude.ai/artifact/UM8P8vBhGso4evr9dEcqFk. What Jed says, word for word, and what every detail means: `SPEAKER-NOTES.md`.

## Roles

| Who | Role | In one line |
| --- | --- | --- |
| **Jed** | Presenter and the voice of every client | The only native French speaker: he presents in French and speaks to the agent in all three demos. Headset on the whole time. |
| **Claudio** | Laptop (*régie*) | Runs the demo laptop, silently: slides, switching to the Voix page, the buttons, typing if voice fails. |
| **Pablo** | Timekeeper and backstop | Keeps Jed on time, stages the “Cassez le matin” card, watches the logs, runs every fallback. |
| **Alexander** | Jury contact and technical questions | Runs the juror moment in demo 3, then takes agent and tool questions and hands the headset to jurors. |

### Jed — presenter and client voice
- Presents every slide in French (script in `SPEAKER-NOTES.md` and in the deck’s speaker notes).
- Before each demo says who he plays (« Je joue Céline… », « Je joue le chef… »), then speaks to the agent with the exact lines below.
- During a live call: no narration. If the agent mishears, correct it like a real caller (« Non, Peyronnet, P-E-Y… »).
- Watches Pablo’s signals; skips the optional lines when Pablo points at his watch.

### Claudio — laptop
- Two full-screen windows: the deck in Present mode, and the Voix page in demo mode (`http://localhost:5173/voice?demo=1`). Switch with Cmd-Tab. Rehearse the switch.
- Advances the slides on Jed’s cue (a nod, or “slide suivante”).
- Demo 1: switches to the Voix page and points at the client card, then the new order for Thursday 26/11.
- Demo 2: clicks **Avant le camion**, then **Appeler** on Leroy; points at the card turning “fait”, « Récupéré 77 € », and « remplace Onglet de bœuf » on the order.
- Demo 3: when Pablo says “c’est prêt”, clicks **Appeler** on the first new card.
- If speech recognition fails: types Jed’s lines in the text box (« Ou tapez la phrase de l’appelant… ») so the call carries on.
- Never touches `.env` or the code.

### Pablo — timekeeper and backstop
- Starts the stopwatch on Jed’s first word; gives the signals in the run of show below.
- Runs `make reset` right before we start (not between demos 1 and 2).
- Demo 3: stages the juror’s card (procedure below), ~10 s.
- Keeps `make logs` open, the phone hotspot ready, and the 2-minute video paused on its first frame.
- Runs the fallbacks (table below).

### Alexander — jury contact and technical questions
- Demo 3: points the juror to the numbered options on slide 6, asks « Lequel ? Et qu’est-ce qui s’est passé cette nuit ? », writes the number and the sentence on paper or his phone, and hands it to Pablo. Keeps it to one short sentence a chef can hear.
- After the 7 minutes: hands the headset to jurors who want to call; answers questions on the agent, tools and rules (Jed relays in French if needed).

## Run of show

| Time | On screen | Jed | Claudio | Pablo | Alexander |
| --- | --- | --- | --- | --- | --- |
| 0:00–0:35 | Slide 1 · 04:38 | Hook, who we are | Slides | Stopwatch on | — |
| 0:35–1:15 | Slide 2 · Le problème | 61%, the rules | Slides | **Signal at 1:15** | — |
| 1:15–2:30 | Slide 3 → Voix page | Intro 15 s, then plays Céline (2 turns) | Switch to Voix, point at cards; type if needed | Watch logs | — |
| 2:30–3:05 | Slide 4 · Ce que vous venez d’entendre | The numbers | Back to slides | **Signal at 3:05** | — |
| 3:05–4:35 | Slide 5 → Voix page | Intro 15 s, then plays chef Peyrat (5 turns) | Avant le camion → Appeler Leroy | Watch logs; **signal at 4:35** | Get ready for the juror |
| 4:35–5:35 | Slide 6 → Voix page | Asks a juror to pick | Appeler on the first new card | `make chaos …` | Takes the juror’s number and sentence |
| 5:35–6:30 | Slide 7 · Comment on le sait | Rules, tests, the bug | Slides | **Signal at 6:30** | — |
| 6:30–7:00 | Slide 8 · À vous | Hands over to the jury | Back to the Voix page | `make reset` only if needed | Hands the headset over |

**Signals (Pablo → Jed):** one finger up = “start the next demo now”; pointing at the watch = “you’re behind, skip the optional line”; flat hand = “wrap up”.
- More than 30 s behind at 4:35: skip demo 3, go to slide 7, offer it after the 7 minutes.
- Behind at 5:35: Jed keeps the first sentence and the numbers on slide 7, drops the bug story.

## The live lines

**Demo 1 — Jed as Céline, Boucherie Peyronnet**
1. « Bonjour, c’est Céline, Boucherie Peyronnet aux Halles. Pour jeudi, tu me mets deux arrières et un avant, la génisse de chez Dumontet comme d’habitude. »
2. After the read-back: « C’est bon, vas-y. »

**Demo 2 — Jed as chef Peyrat, Restaurant Leroy** (the agent speaks first after **Appeler**)
1. « Vous vous foutez de moi ? J’ai l’onglet à la carte ce midi. Vous me faites un geste au moins ? » *(skip if behind)*
2. « Bon. Vous avez quoi qui pourrait remplacer ? »
3. « Mettez-moi quatre kilos et demi de bavette alors. »
4. « Oui, allez-y. »
5. « Merci, au revoir. »

**Demo 3 — Jed as whichever client the agent calls:** one line (« Bon, laissez comme ça. »), then hang up.

## Demo 3: staging the juror’s card (Pablo)

1. Take the number and sentence from Alexander. No straight double quote `"` inside the sentence.
2. Type the command for that number, the juror’s sentence between the quotes in `WHY`. No `make reset` here: the earlier demos don’t interfere.
3. Check the output ends with `Contrôle sans modèle : OK`; say the number of calls to Jed if he wants it.
4. Tell Claudio “c’est prêt”: the Avant le camion panel updates without a reload.

| # on the slide | Product | Command |
| --- | --- | --- |
| 1 | Côte de bœuf maturée 21 jours | `make chaos PRODUCT=prd_0011 WHY="…"` |
| 2 | Entrecôte | `make chaos PRODUCT=prd_0010 WHY="…"` |
| 3 | Filet de bœuf paré | `make chaos PRODUCT=prd_0012 WHY="…"` |
| 4 | Foie de veau | `make chaos PRODUCT=prd_0037 WHY="…"` |
| 5 | Côte maturée, poids court | `make chaos PRODUCT=prd_0011 WHY="…" ARGS="--short 30"` |

If a juror wants another product: « On a vérifié ces cinq-là ; choisissez-en un, et la raison est la vôtre. » Never paleron (17 clients).

## Before we go on (T−30 min, on the demo machine)

| ✓ | Check | Who |
| --- | --- | --- |
| [ ] | `git pull` on `main`, then `make up`; `http://localhost:4000/docs` and `http://localhost:4100/docs` both answer | Pablo |
| [ ] | `.env` checked, not edited: Soniox, ElevenLabs `eleven_v4_turbo` with the frozen voice, the agreed model | Pablo |
| [ ] | ElevenLabs credit topped up (it ran out last night): one short spoken turn proves voice and transcription | Pablo |
| [ ] | Jed’s voice through the headset: one test call, speech recognised | Jed + Claudio |
| [ ] | Headset selected in the browser; room speakers loud enough | Claudio |
| [ ] | Deck in Present mode + Voix page `?demo=1`, both full screen; Cmd-Tab rehearsed | Claudio |
| [ ] | Laptop on power, notifications off, other tabs closed | Claudio |
| [ ] | Phone hotspot ready and unlocked | Pablo |
| [ ] | The 2-minute video open, paused on its first frame | Pablo |
| [ ] | `make logs` in one terminal tab, the repo folder in another | Pablo |
| [ ] | One full timed rehearsal, then **`make reset`** | Everyone |

## If something breaks

Act in this order: wait once, look at the logs, then the smallest fix. Never touch `.env` or the code.

| Symptom | What we do | Who |
| --- | --- | --- |
| Silence over ~5 s after Jed speaks | Wait once. Pablo checks `make logs`. Error → Claudio reloads the Voix page; none → Jed repeats the sentence. | Pablo, Claudio, Jed |
| Agent mishears | Jed corrects it like a real caller. Nobody steps in. | Jed |
| Speech not transcribed | Claudio types Jed’s lines in the text box; Jed says so in one sentence. | Claudio, Jed |
| « TTS indisponible, voix de secours du navigateur » | Nothing: the browser voice takes over (robotic, later). Jed: « le fournisseur de voix a lâché, l’agent est passé sur une voix de secours ». | Jed |
| Page error or socket drops | Claudio reloads the Voix page and restarts the call. | Claudio |
| Model errors or no network | Pablo switches to the hotspot. Still down: Pablo plays the 2-minute video instead of demos 1–2, then slide 7. | Pablo |
| `make chaos` not OK | `make reset`, same command again. Still not OK: skip demo 3. | Pablo |
| A call left a mess | `make reset` after the call, never during. | Pablo |

Not sure what’s wrong? Pablo gives Jed a thumbs-down and plays the video. Don’t debug in front of the jury.

## Cheat sheet (Pablo’s terminal)

| What | Command |
| --- | --- |
| Start the services | `make up` |
| Watch the logs | `make logs` |
| Reset the ERP to the data pack | `make reset` |
| Stage a sabotage card | `make chaos PRODUCT=prd_0011 WHY="…"` |
| Short-weight card | `make chaos PRODUCT=prd_0011 WHY="…" ARGS="--short 30"` |
| Products on today’s trucks | `python3 evals/break_morning.py --list` |
| Voix page, demo mode | `http://localhost:5173/voice?demo=1` |

**Never during the pitch:** `make calls`, `make jury`, `make chaos-check` (they reset the ERP and use credits), `make clean`, anything in `.env`.
