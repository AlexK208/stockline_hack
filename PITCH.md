# PITCH.md — everything needed to build the slides and the video (lane D)

One file to brainstorm from, with the team or with Claude. Written on `main` at `910da6f` (24/11, after Pablo's 04:27
« development is finished » entry). Every number below gives where it comes from; anything we cannot defend in a
question is marked. Lines in « » are in French because the jury, the agent and the clients speak French.

Sources, if you need more: `BRIEF.md` § 3 and § 8 (what is judged), `DECISIONS.md` (the jury reads it),
`DEMO.md` (live demo plan, sabotage cards, cheat sheet § 10), `SCENARIOS.md` (test calls), `HANDOFF.md`.

---

## 1. The constraints

| Deliverable | Limit | Note |
|---|---|---|
| **Slides** | **5 min max** | Presented by Claudio (`DEMO.md` § 2) |
| **Video** | **2 min max**, « un vrai appel de bout en bout » | Also our last-resort fallback if the live demo breaks |
| Live demo | Jurors call the agent with **their own** scenarios | « Le plus rapide » is measured live: end of speech → first sound |
| Submission | Tuesday **17:30** · code freeze **13:00** | |

**Judged on:** **Smart** (knows the client, handles ambiguity, acts right in the ERP), **Fast** (no awkward silence,
round trips, cost per call), **Natural** (short sentences, numbers said aloud, read-back, interruptions, noise),
**plus the relevance of the problem chosen**. Special prizes: fastest, cheapest, most natural, smartest.

So the slides must do two things the live demo can't: **justify the problem** and **prove the numbers**.

---

## 2. Who we are, in one breath

- **The company (fictional, from our data pack):** *Chevillard du Limousin*, a wholesale meat business (carcasses,
  quarters, cuts, offal) delivering ~100 butchers, restaurants, canteens and supermarkets around Limoges.
- **Data frozen at Tuesday 24/11/2026, 05:00.** Trucks leave between 04:45 and 05:00. That date and hour are the
  backdrop of every demo moment.
- **Team:** Alexander (agent and tools), Pablo (speech, latency), Jed (frontend, Voix page), Claudio (tests, docs,
  presenting). Four coding-agent sessions, one per lane, coordinated through `HANDOFF.md`. 188 commits overnight.

---

## 3. The problem, and why this one (the « pertinence » axis)

**Core use case: inbound phone order-taking.** A client calls, the agent identifies them, takes the order
(including « comme d'habitude »), checks price, stock at the delivery date and lead times, reads the order back and
confirms it in the ERP.

Why this one (`DECISIONS.md` § 1), the four reasons for one slide:
1. **The real bottleneck.** Orders arrive by phone between 5 and 8 a.m., when the salesperson is on the road or
   boning meat: the fewest hands, the most calls.
2. **The richest data.** ~100 clients, 3 years of history, usual baskets, detailed personas. « Comme d'habitude » and
   « la génisse de chez Dumontet » only work on this use case.
3. **Hard, checkable rules.** Carcasses 2 days ahead, PAD (ready-to-cook pieces) before 17:00, canteens 3 days
   ahead with a PO number, out-of-stock items, blocked accounts, clients who refuse substitutions. Success is proven
   **in the ERP**, not by judging the tone.
4. **An error costs real money.** Half a carcass promised for Wednesday when slaughter is Thursday means a butcher
   without meat on his biggest day.

**Then we went past order-taking: the agent also places calls.** Alexander's line for the pitch:
> « Le site de Stockline liste trois agents : vente, prix, achats. Le nôtre passe les appels de deux d'entre eux, et en
> ajoute un quatrième : la livraison. Une personne approuve, l'agent téléphone. »

---

## 4. What it does: the feature list

Each feature: what it is, why a wholesaler cares, and how to show it (`DEMO.md` § 10 has the exact commands).

### 4.1 Inbound order-taking (the core)
- Recognises the caller from their first words. Two plausible clients: **one** short question, never a guess (T2:
  « Hyper Frais Limoges », two stores).
- Pieces → kilos (« deux arrières » ≈ 200 kg), with « la facture suit le poids réel ».
- Write tools **check themselves**: stock at the date, lead time, delivery day. If it is forbidden, nothing is
  written and the agent says why (on screen: the « Refusé pendant l'appel » list on the order card).
- Out of stock + client refuses substitutions: says so with the reason and **never substitutes without a yes**.
  Accepted substitution: the line is written as « remplace Onglet de bœuf ».
- Blocked account: no order, polite and firm under pressure, message logged for accounting.
- Reads the order back, numbers said aloud, confirms **only after a yes** (guarded in code, not just in the prompt).
- « tu » or « vous » depending on how this client talks (read from the client file).
- **Weigh ticket:** « commandé vingt-cinq, pesé vingt-quatre, la facture suit le poids pesé », complaint logged,
  no credit note promised.
- After the call, a **call report** is written to the client's history for the salesperson.

### 4.2 « Avant le camion »: outbound calls before the truck leaves (the story)
- The night inventory wrote off a lot. Code (no model) reads every loaded order line by line and decides who must
  be called: missing always; short weight from 5 % **and** 15 €. Sorted by truck departure.
- Each call follows the client's own file word for word: « refuse les substitutions » → state the fact, ask, name
  no product; « accepte si on prévient » → offer the house's usual replacement from real stock at their price.
- Guards in code: nothing added to the truck without a yes in the client's last sentence, capped at missing + 20 %;
  wrong person answers (the dishwasher) → nothing written, call stays « à rappeler ».
- **Voix page board:** clock starting at 04:38, « part dans 7 min » in red, € « Reste en jeu », « Récupéré »
  going up as calls succeed.

### 4.3 « Cassez le matin »: proof it is not a script
- A **juror** picks what broke overnight and types the reason; one command stages it; the agent finds every client
  hit (6–8 calls, 441 € to 3 902 € at stake) and says the juror's own sentence to each client.
- Five sabotage cards + ten client cards (honest line, cheating line) in `DEMO.md` § 9, all replayed with the model.
- Slide line kept for this: paleron hits **17 clients**: « 17 clients, 3 camions, 15 minutes : un commercial n'y
  arrive pas, l'agent passe les appels. »

### 4.4 « Qui est servi d'abord »: when part of the lot survives
- 20 kg of côtes left for 6 clients who ordered 123. Code proposes two plans with reasons in words: **priority**
  (no-substitution clients first, then earliest truck, then regulars) or **equal share**. Priority = 5 calls; equal
  share = 6 calls and 0,89 kg for someone who needed 5,5.
- **A person approves before anything is written.** Then each call tells the client their real share.
> « Il reste 20 kilos pour six clients qui en ont commandé 123. L'agent propose qui est servi, une personne
> approuve, et chaque client apprend sa part avant le départ du camion. »

### 4.5 « Date courte »: selling stock before its use-by date
- 2 695 € (purchase price) of short-dated stock with no order for it. Code finds the clients who usually buy it and
  have a truck before the date.
- **The agent never decides a discount**: a person sets the price (refused below cost or at list price), the agent
  offers it once, no haggling (« le prix est fixé par la maison »), writes only after a yes.

### 4.6 Carnet des fêtes: booking Christmas by phone
- Christmas is a chevillard's peak, on the rarest pieces: veal rack ×6,5, fillet ×5,3, sweetbreads ×2,9 vs a normal
  fortnight. A sweetbread per calf, one onglet per animal. Today the list is on paper.
- « Comme l'an dernier » reads back the client's real 2025 Christmas basket. Each client is guaranteed up to last
  year's volume; the rest goes on a **waiting list, never promised**, said with the reason.
- The « Carnet des fêtes » page fills live during the call.

### 4.7 Le cadran annoncé: the weekly price quote, said once
- Carcass prices follow Monday's quote at the Limoges market; **16 client files** cite unannounced price rises as a
  risk. When a butcher orders carcasses, the agent says the move once, from **his** prices (« l'arrière a pris cinq
  centimes, à dix euros vingt »), drops included, never twice in the week. Restaurants ordering cuts don't hear it.

### 4.8 End-of-order « oublis »
- Only when today's order is clearly the client's repeated order with one or two products missing: one question
  (« D'habitude tu prends aussi un avant avec, je te le mets ? »). Otherwise never « vous n'oubliez rien ? ».
  Decided by code, said by the model. Why so strict: « les bouchers détestent la relance commerciale ».

### 4.9 Under the hood (one slide at most)
- Sonnet 5.5 · Soniox (speech-to-text) · ElevenLabs `eleven_v4_turbo` (voice) · FastAPI ERP + AI service · React.
- **34 tools.** Business rules live in the backend; the agent acts through tools only; every ERP write is tagged
  with who made it (shown live on screen).
- An **instant spoken acknowledgement** chosen by code, not the model (« Je note. », « Je regarde. », « Très
  bien. »), so it can never invent anything.
- Caller identified in code before the model runs when the first words point to one client.

---

## 5. The numbers (only defensible ones)

Latest full run: Pablo, `42d9b4d`, 04:17–04:27 (`HANDOFF.md` 04:27).

| What | Number | How it was measured | Caveat if asked |
|---|---|---|---|
| Regression calls | **8/8** (T1–T8) | `make calls`: replays and checks the ERP, what the agent **said**, and which tools it called | One run; the model isn't deterministic |
| Jury-style calls | **29/29** invariants | `make jury`: 29 hard calls we wrote (5 Karims, a fake boss asking for a debt, someone asking for another client's order, a supplier…) | Invariants are automatic; the full transcripts are read by a human |
| Unit tests | **193** pass, also on a fresh clone | `pytest` | |
| Sabotage cards | **7/7** | `make chaos-check`, no model | |
| First **sound** on a request | **0,09–0,61 s** (kit: **8,7 s**) | Server side over `WS /voice`, typed turns | It's the acknowledgement; the real answer follows 2–4 s later. Skips STT and browser playback |
| End of speech → final transcript | **1,25–1,64 s → 0,15–0,60 s** | Same audio sent 6× through our socket, before/after Pablo's fix | Recorded audio, not yet a live browser mic |
| Worst turn (text) | **4,5–8,0 s → 3,5–4,2 s** | `make calls`, before/after keeping connections open (one config line) | Measured with 6 scenarios; at the freeze with more features the worst turn is 5,3–7,3 s |
| First word, median (text) | **~2,4–3,1 s** | `make jury` 2 409 ms, `make calls` 3 074 ms on `42d9b4d` | Model + tools only, no speech |
| Cost per call | **≈ $0,10–0,15** cold cache, **~$0,05** when calls follow each other | Measured tokens × public list prices (model $0,074–0,087, voice $0,02–0,06, STT < $0,005) | List prices in USD; spoken characters estimated |
| Prompt cache | **84–88 %** of input read from cache | Token counts per run | |
| Tokens per call | **−14 %** vs the kit, with more features | Removing the « check, then write » step | |

Voice-over lines Pablo proposed:
- « Une seconde gagnée à chaque tour, sans toucher au modèle : on attendait que la socket se ferme avant de lire
  la transcription. »
- « Le cache de prompt rend la partie modèle 4 à 5 fois moins chère : 85 % de l'entrée est relue depuis le cache. »
- « Un appel coûte une dizaine de centimes. Le poste principal est le modèle, puis la voix. »

---

## 6. The stories worth telling (pick for slides or video)

1. **« 04:38 » (the single story agreed overnight, `HANDOFF.md`):**
   « 04:38. L'inventaire de nuit a déclassé l'onglet. Le camion de Corrèze part dans 7 minutes. Le chef Peyrat
   refuse les substitutions et a l'onglet à la carte ce midi. Personne n'a le temps de l'appeler. L'agent appelle. »
   Then the call, then the ERP: complement on the route, issue closed, report in the history.
2. **A defect our tests found that no ERP check could see** (`DECISIONS.md` § 5.1). On a blocked-account call, the
   agent turned the word « viande » into a client name and **opened another client's file** (credit, contacts)
   without saying anything. Nothing written, every ERP check green. Caught only by checking **which tools were
   called**; fixed; 0 out of 3 after. Lesson: « un agent peut faire quelque chose de grave sans rien écrire et sans
   rien dire ».
3. **Rules moved from the prompt into code** (§ 2.2, § 2.14). Rules the prompt didn't hold (« max two
   suggestions », « confirm only after a yes ») now live in the tools. Faster, cheaper, can't be forgotten.
4. **We optimised the tail, not the median.** On the phone, what makes people hang up is the turn where the line
   sounds dead. Worst turn 8,0 → 3,5–4,2 s with one config line (httpx closed idle connections after 5 s; callers
   talk longer than that).
5. **Follow the data, not the document** (§ 2.8). The company doc says veal ordered Tuesday ships Friday; 224 veal
   carcasses were ordered on a Tuesday for Thursday last year. We follow what the business actually does.
6. **Honesty points** we kept visible on purpose: a TTS claim we had to correct (a 26 ms gap inside measurement
   noise); the voice is still an English-native voice speaking French (a French voice needs a Gradium key we never
   got).

---

## 7. The video (2 min max, one real call end to end)

Material that already works:

**Option A: the « 04:38 » call (recommended overnight, our most original feature).** Voix page, Mode démo
(`?demo=1`), « Avant le camion » open (`?camion=1`). Script replayed many times (Alexander's, `HANDOFF.md`):
- **Appeler** on Restaurant Leroy (the agent opens with the onglet, the reason, the 04:45 truck)
- « Vous vous foutez de moi ? J'ai l'onglet à la carte ce midi. Vous me faites un geste au moins ? »
  (no discount promised, the request is logged)
- « Bon. Vous avez quoi qui pourrait remplacer ? »
- « Mettez-moi quatre kilos et demi de bavette alors. »
- « Oui, allez-y. »  → the bavette is written onto the 04:45 truck
- « Merci, au revoir. »  → card turns « fait », « Récupéré 77 € », report in the client's history

**Option B: what the arena juror asked for (`HANDOFF.md` 00:56):** open on a fast, natural inbound order, then the
weigh-ticket call.
- T1, Céline Peyronnet (~45 s): « Bonjour, c'est Céline, Boucherie Peyronnet aux Halles. Pour jeudi, tu me mets
  deux arrières et un avant, la génisse de chez Dumontet comme d'habitude. » … « C'est bon, vas-y. »
  Show: client card, the quote said once, kilos, « génisse de chez Dumontet » noted, order confirmed.
- Weigh ticket: « Anh Boucher, le Relais des Monts. Sur ma livraison de mardi dernier, il manquait un kilo
  d'entrecôte. »

**Option C: a hybrid.** 10 s of the T1 order (fast, natural) → cut to 04:38 and the board → the Leroy call → 10 s of
the ERP after. Risky to fit in 2 min; the brief says « un vrai appel », so check that cuts are acceptable.

Practical notes:
- **Mode démo** hides latency figures and tool rows, bigger text. The board's clock starts at 04:38 when the page
  opens (click to reset): say it's a demo clock (the ERP is frozen at 05:00).
- `make reset` before each take (calls write into the ERP; `make reset` brings both onglet calls back).
- Use real voice if possible (the brief wants a real call); typed turns are the fallback. A native French speaker
  sounds better as the client.
- ElevenLabs quota is shared: keep takes short. If it fails, a browser voice takes over (robotic): redo the take.
- Show the ERP updating live: the order card, « remplace Onglet de bœuf », the client history.

---

## 8. A starting slide outline (5 min, to argue with)

1. **Hook (20 s):** « 04:38. Le camion part dans 7 minutes… » (story 1), or a short clip.
2. **The problem (40 s):** who calls whom, when, what it costs today (§ 3, four reasons).
3. **What the agent does (60 s):** inbound order-taking + it places calls: before the truck, short-dated stock,
   Christmas. « Une personne approuve, l'agent téléphone. »
4. **Smart (40 s):** follows each client's file, refuses what the rules forbid, never substitutes without a yes;
   « Cassez le matin »: the jury chooses what breaks.
5. **Fast (40 s):** 8,7 s → under 1 s to first sound; worst turn halved; one second gained on every transcript.
6. **Natural (30 s):** acknowledgement chosen by code, tu/vous, numbers said aloud, read-back, one question at most.
7. **Cheap (20 s):** ≈ $0,10 per call, 85 % cached.
8. **How we know (40 s):** 8/8, 29/29, 193 tests, and the defect only the tool check could see (story 2).
9. **Invite the jury (10 s):** « Vous êtes un client du chevillard… »; hand out the sabotage cards.

---

## 9. Questions to settle in the brainstorm (from `REVIEW.md` § 7 and `DEMO.md` § 8)

1. **Which latency number goes on the slide?** 0,09–0,61 s is first sound (the acknowledgement); the real answer is
   2–4 s later. Explain it, or let the number speak? It is honest (the acknowledgement never states a fact).
2. **Do we show a failure?** The § 5.1 defect is our best evidence that the tests work. Rigour or admission?
3. **Video: A, B or C?** Original (truck) vs what a juror expects first (a fast inbound order).
4. **Who plays the client** in the video and the showcase call? A native French speaker sounds more natural.
5. **How do jurors call?** Into our laptop's headset? That decides the noise risk.
6. **How much « beyond order-taking » to show?** Seven features in 5 min risks a list; one story + « and also… »
   might land better.

---

## 10. What to avoid saying (or say carefully)

- **Haiku:** we use Sonnet. Haiku was faster but once promised a delivery date without checking. It could be
  re-tested now that the checks exist; we didn't.
- **The voice:** an English-native ElevenLabs voice speaking French, frozen because our tester judged it good. A
  native French voice needs a Gradium key we never got.
- **Not yet confirmed:** the STT gain from a live browser mic; a full voice call end to end since the last fixes
  (manual checks are still open in `HANDOFF.md`, Pablo's 04:27 list).
- **Not on screen:** approving a « date courte » price and choosing a « Qui est servi d'abord » plan are typed
  commands (`/offre …`, `make chaos … --apply`), not buttons.
- **Latency figures are single runs on different machines:** read them as orders of magnitude, not exact values.
- **Left out on purpose:** amounts owed are never read to an unverified caller; no invoices by phone.
