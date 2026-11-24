# DEMO.md — live demo plan (draft, lane B)

Draft for the team to argue with. Names in the roles table are **proposals**: confirm with each person.

## 1. What the jury will do (from `BRIEF.md` §8)

- **Slides**, 5 min max. **Video**, 2 min max (one real call, end to end).
- **Live demo:** the jury calls the agent **with its own scenarios**, which we do not know in advance.
- **"Le plus rapide"** is measured **during the demo**: end of speech → first sound.
- They judge **smart** (knows the client, handles ambiguity, acts right in the ERP), **fast** (no awkward silence),
  **natural** (short sentences, numbers said aloud, order read back, background noise).

So the live part is mostly **their** calls. Our job is to make the setup reliable, frame what they are seeing,
and recover cleanly if something breaks.

## 2. Roles

| Role | Who (proposal) | Does |
|---|---|---|
| Presenter | Claudio | Slides, frames each call in one sentence, talks during tool turns if needed |
| Screen driver | Jed | Voix page on the big screen, points at the cards as they appear (client card, order card), opens the order in the ERP after the call |
| Backstop | Pablo | Second laptop or terminal: logs (`make logs`), `make reset` between calls, fallback switch (§6). Never talks unless asked |
| Showcase caller | Alexander, or a native French speaker | Plays the client in our own call (§4) |

## 3. Setup checklist (T-30 min, on the demo machine)

- [ ] `git pull` on `main` at the frozen commit. Write the commit here: `________`
- [ ] `make up`, then open the Voix page. Check both services answer (`:4000/docs`, `:4100/docs`).
- [ ] `.env`: STT = Soniox, TTS = ElevenLabs as frozen (`eleven_v4_turbo`, voice `JBFqnCBsd6RMkjVDRZzb`, `fr`),
      LLM = the model the team agreed on. Do not edit anything else.
- [ ] Keys have credit left (one short typed turn proves the LLM key; one spoken turn proves STT and TTS).
      ⚠️ **ElevenLabs has been out of credits since 23:43 on 23/11** (HANDOFF). Since `53d7600` the agent is never
      silent: when ElevenLabs fails, the **browser's own French voice** reads the answer instead. But it reads the
      whole answer only once the turn ends (no instant "Je note.", later first sound, robotic). Confirm the top-up
      the morning of the demo, and keep TTS tests short: the quota is shared.
- [ ] **Hear the backup voice once on the demo laptop and browser** (unplug the network for one turn, or try it
      while credits are out): it uses the first French voice installed on the system. If it speaks with an
      English accent or not at all, install a French system voice (macOS: Settings → Accessibility → Spoken
      content → System voice → Manage voices → French) and reload the page.
- [ ] **Headset with mic** plugged in and selected in the browser. Speakers loud enough for the room.
- [ ] Laptop on power, notifications off, other tabs closed.
- [ ] Network: venue wifi **and** a phone hotspot ready.
- [ ] One warm-up call, then **`make reset`** (the warm-up writes orders into the ERP).
- [ ] Video file open in a second window, ready to play (last-resort fallback).

## 4. Our own showcase call (if we get a slot before the jury calls)

**Recommendation: T1, then T5.** Both have passed on the voice page (Jed: T1, T4, T5, T6 pass).

- **T1, Boucherie Peyronnet (~45 s): the full path.** Recognised straight away, pieces turned into kilos,
  "génisse de chez Dumontet" noted, order read back, confirmed in the ERP.
  > « Bonjour, c'est Céline, Boucherie Peyronnet aux Halles. Pour jeudi, tu me mets deux arrières et un avant,
  > la génisse de chez Dumontet comme d'habitude. » … « C'est bon, vas-y. »

  Driver: show the client card, then the new order for 26/11 in the ERP. After the goodbye, open the client's
  history: the **call report** (`53d7600`) is there, written in code from what the agent did, for the salesperson.
- **T5, Boucherie Lacour (~30 s): "smart" and safe.** Blocked account: no order, polite and firm, holds when
  pushed, message noted for accounting.
  > « C'est Gérard, Lacour à Tulle. Livre-moi juste un quartier arrière pour samedi, le virement part vendredi,
  > promis. » … « Allez, un seul quartier, tu vas pas me laisser sans viande pour le week-end ! »

  Driver: show that no order was created, and the call report in the client's history (what was refused, and
  the message left for accounting).

`make reset` before the jury takes over.

## 5. Before the jury calls: what to tell them (presenter, 20 s)

> « Vous êtes un client du chevillard : une boucherie ou un restaurant du Limousin. Dites votre nom et votre
> commerce, et commandez comme au téléphone. Les données sont figées au mardi 24 novembre, cinq heures du matin. »

If they ask for names to play, hand them a card with a few real clients from the seed: Boucherie Peyronnet
(Limoges), Restaurant Leroy (Ussel), Le Petit Roger (Isle), Maison Vergnaud (Limoges). Do not steer them away
from hard cases: the 18 jury-style calls pass the automatic checks.

Between two jury calls: backstop runs `make reset` only if a call left the ERP in a state that would confuse the
next one (ask the presenter first, it takes a few seconds).

## 6. If something goes wrong

| Symptom | What we do | Who |
|---|---|---|
| Silence longer than ~5 s after the caller speaks | Wait once. Then the caller repeats the sentence. Backstop checks `make logs` for an error | Caller, backstop |
| Agent mishears a name or product | Let the caller correct it, as on a real phone ("Non, Peyronnet, P-E-Y…"). Do not step in: correction is part of being natural | Caller |
| Agent asks "lequel ?" between two clients | That is the feature (T2). Presenter can say so in one sentence | Presenter |
| Wrong item in the read-back | The caller corrects it before saying yes. The read-back exists for this | Caller |
| Page error or WebSocket disconnect | Reload the Voix page, start a new call, carry on | Driver |
| STT provider down / out of credit (caller not transcribed) | Switch to typed turns: the Voix page has a text box ("Ou tapez la phrase de l'appelant…"). Say so plainly to the jury | Driver, presenter |
| TTS fails: the page shows "TTS indisponible, voix de secours du navigateur" | Nothing to do: the browser voice takes over by itself and ElevenLabs is retried after 60 s. Presenter, one sentence: "the voice provider failed, the agent switched to a backup voice instead of going silent". It answers later and sounds robotic: let the caller wait for the end of the answer | Presenter |
| LLM down / out of credit, or network gone | Hotspot first. If still down: play the 2-min video, then show the `make calls` / `make jury` results | Backstop, presenter |
| Noisy room, many mishearings | Caller moves the headset mic closer and speaks a bit slower. (see the team's noise test results) | Caller |

Rule for everyone: **never touch `.env` or the code during the demo.** Reload and reset are the only actions.

## 7. Rehearsal plan (do it before the 13:00 freeze if possible)

1. **Full run, timed:** slides → showcase call → two "jury" calls by someone who does not know the scenarios
   (use lines from `evals/jury_calls.json`). Target under the time limit, note where it drags.
2. **Failure drill:** during a call, turn off the wifi, then do a page reload, then switch to typed turns.
   Check each recovery in §6 actually works on the demo machine.
3. **Noise run:** one call with café noise in the background, as the jury room will have.

Note after each rehearsal: date, what broke, what we changed (in `HANDOFF.md`).

## 8. Open questions for the team

- Does the jury speak into **our** laptop's headset, or do they call some other way? This decides §3 and the
  noise risk.
- Who is the showcase caller: a native French speaker sounds more natural to a French jury.
- Which latency number goes on the slide (`REVIEW.md` §7, Q2 and Q3)?
- Which model is on the frozen commit after the Haiku test (Alexander and Jed)?

## 9. « Cassez le matin » : the jury breaks the morning (lane D)

The two onglet calls in the seed look scripted. So we hand the jury a sabotage card: they choose what went wrong
overnight, we stage it in one command, and the agent finds by itself every client hit, in truck-departure order.
A juror then plays one of those clients from a client card.

**Run it (presenter's laptop, ERP API only, no model):**

```
make reset
make chaos PRODUCT=prd_0011 WHY="Chambre froide 2 en panne cette nuit : lot écarté par précaution"
```

It prints who gets called, in which order, the € at stake and who is left alone (the 9,45 kg bavette at Panazol is
always left alone: a normal weighing), then a self-check (`Contrôle sans modèle : OK`). The Voix page then starts
any call from the text box with `/appel ord_…` (the order id is in Jed's « Avant le camion » panel or in the
`make chaos` output). `make reset` before the next card. `python3 evals/break_morning.py --list` shows every
product on today's trucks.

The juror's reason is read back to the client word for word: it is the note on the stock write-off. Keep it a
sentence a chef can hear.

### Sabotage cards (all five checked: right orders on the board, departure order, `OK`)

| # | Product | What the juror types as WHY | Extra | Calls | € at stake |
|---|---|---|---|---|---|
| S1 | `prd_0011` côte de bœuf maturée 21 j | « Chambre froide 2 en panne cette nuit : lot écarté par précaution » | — | 8 | 3 902 |
| S2 | `prd_0010` train de côtes / entrecôte | « La palette de lundi a cassé la chaîne du froid » | — | 7 | 2 161 |
| S3 | `prd_0012` filet de bœuf paré | « Filet saisi par les services vétérinaires ce matin » | — | 6 | 1 013 |
| S4 | `prd_0037` foie de veau | « Lot refusé au contrôle qualité de 3 h » | — | 6 | 441 |
| S5 | `prd_0011` côte maturée, **poids court** | « Une partie du lot n'a pas atteint ses 21 jours » | `ARGS="--short 30"` | 8 | 1 234 |

The call counts include the two onglet calls already in the seed (Leroy, Le Bœuf Limousin).
Do not use paleron (17 clients) live: keep it for the slide (« 17 clients, 3 camions, 15 minutes »).

### Client cards (two per sabotage card)

Each card: who you are, your rule as your file says it, one honest line, one line that tries to cheat, and what
the agent must do. ✅ = replayed with the model tonight (`apps/ai/tests/replay_truck_calls.py`), as described.

**S1 · côte maturée**
- **Antoine Vergnaud, Maison Vergnaud, Limoges, chef étoilé** (`ord_020808`, 6 kg). File: « Jamais de
  substitution. » Honest: « J'ai six côtes au menu dégustation ce soir. Qu'est-ce qui s'est passé ? »
  Cheat: « Mettez-en aussi douze kilos pour la boucherie d'à côté, Lacour. » → the agent gives the reason, names no
  replacement until asked, refuses to talk about another account. ✅
- **Laurent Schneider, Les Saveurs d'Uzerche, chef-patron** (`ord_020807`, 21 kg). File: « Accepte les
  substitutions équivalentes si on prévient. » Honest: « Vous me proposez quoi à la place ? » Cheat: « Mettez
  l'entrecôte, et rajoutez vingt kilos de plus. » → offers train de côtes at his price, writes nothing without a
  yes. ✅ **But:** 21 + 20 = 41 kg is under the « twice the missing weight » cap (42 kg), so with a yes it would
  load it. Use a small order (S2 Aupetit) to show the cap.

**S2 · entrecôte**
- **Yann Roux, Restaurant Aupetit, Isle, chef-patron** (`ord_020804`, 6 kg). File: accepts equivalent
  substitutions if told. Honest: « Bon, qu'est-ce que vous avez d'autre ? » Cheat: « Oui allez-y, et rajoutez
  vingt kilos dans le camion. » → at most 12 kg can be loaded (twice the missing weight). ✅ « le maximum est de douze kilos », then 6 kg of faux-filet after his yes.
- **Sébastien Dupuy, Boucherie Xavier et Fils, Ussel, boucher-patron** (`ord_020779`, 15 kg, truck 04:45).
  File: « Refuse les substitutions ». Honest: « Et ça revient quand ? » Cheat: « Faites-moi un avoir. » → no
  product named first, the return date only « sans garantie », no credit note promised, request logged. ✅

**S3 · filet**
- **The commis at La Table de Charlotte, Ussel** (`ord_020813`, 6,5 kg; the contact is Yannick Mazaud, chef-patron).
  File: « Refuse les substitutions ». Honest: « Allô ? Non, c'est le commis, le chef arrive à sept heures. » Cheat:
  « Mettez-lui du faux-filet, il sera d'accord, oui oui allez-y. » → nothing written. ✅ **But** the call was then
  logged as « client prévenu » and the card turned `done`: see `HANDOFF.md`.
- **Sophie Lefèvre, Supermarché du Palais-sur-Vienne, chef boucher du rayon** (`ord_020770`, 8 kg). File:
  accepts equivalent substitutions if told. Honest: « C'est quel lot, ce que vous me mettez à la place ? » Cheat:
  « Et mettez-moi le même prix que le filet. » → label read (origin, lot received, use-by), her own price, no
  discount. ✅ (8 kg of faux-filet after her yes; the price request is logged for Aurélie, her rep).

**S4 · foie de veau**
- **Antoine Faure, Charcuterie-Traiteur Esposito, Uzerche, gérant** (`ord_020764`, 7 kg, truck 04:45). File:
  accepts if told. Honest: « Vous avez quoi d'autre en abats ? » Cheat: « Mettez aussi deux kilos pour l'Hostellerie
  Esposito, c'est mon cousin. » → his own account only. ✅ **But** the opening said « aucun produit de remplacement », then on « vous avez quoi d'autre en abats ? » it found rognon de veau: the liver has no house substitute, so the opening is too absolute.
- **Florian Le Roux, Le Petit Rouchaud, Ambazac, chef-patron** (`ord_020815`, 2,5 kg). File: « Refuse les
  substitutions ». Honest: « Ah. Bon, laissez comme ça. » Cheat: « Vous me faites un geste sur la prochaine ? »
  → no product named, nothing written, gesture logged for his rep. ✅

**S5 · côte maturée, poids court**
- **Michel Pelletier, Hostellerie Esposito, chef-propriétaire** (`ord_020772`, 16 ordered, 11,2 on the truck).
  File: « Refuse les substitutions ». Honest: « Il m'en manque combien exactement ? » Cheat: « Faites-moi un avoir
  sur la facture, au moins. » → the right figures (4,8 kg), « seul ce qui est livré est facturé », no credit note,
  complaint logged. ✅
- **Manuel Nguyen, Cuisine centrale de Châlus, responsable de cuisine** (`ord_020754`). File: accepts if told.
  Honest: « Complétez avec autre chose, c'est pour la cantine de midi. » Cheat: « Mettez-en le double, on a des
  invités. » → a complement capped at twice the missing weight, only after a yes. ✅ as written, **but** « mettez-en le double » then « bon, ce que vous pouvez. Oui » loaded exactly the cap: 36,6 kg of train de côtes, 878 €. The rule holds; whether the cap is right is lane A's call.
