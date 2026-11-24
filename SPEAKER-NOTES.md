# Speaker notes — team 06 pitch (English)

Exported 24/11 from the shared doc (https://claude.ai/artifact/HJHPHYkCNCwyVZnnbbsfXa). Slides: French deck https://claude.ai/artifact/L9iK2jTLZrHpcgzjLqPWPt, English copy https://claude.ai/artifact/3GjiWAGp5Ue7wjAnGJFoy2.

## How to use this

The talk is 8 slides in 4 min 55 s. Each slide below has three parts: **Say** (the script, about the right length for its time slot), **What each detail means** (so you can answer if a juror digs in), and **If asked** (short honest answers).

Present in French if the jury is French: the English script is for rehearsing and understanding. The agent itself only speaks French, so jurors must call it in French either way.

| # | Slide | Time | Length |
| --- | --- | --- | --- |
| 1 | 04:38 (hook) | 0:00–0:25 | 25 s |
| 2 | The problem | 0:25–1:05 | 40 s |
| 3 | The agent | 1:05–2:00 | 55 s |
| 4 | Smart | 2:00–2:45 | 45 s |
| 5 | Fast | 2:45–3:25 | 40 s |
| 6 | Natural · Cheap | 3:25–4:00 | 35 s |
| 7 | How we know | 4:00–4:40 | 40 s |
| 8 | Your turn | 4:40–4:55 | 15 s |

Pablo signals at 2:00 (you should be starting slide 4) and 4:00 (starting slide 7). Behind at 2:00: skip the Stockline-agents sentence on slide 3. Behind at 4:00: drop the bug story on slide 7 to one sentence.

Numbers come from `PITCH.md` and `DECISIONS.md` on `main` at `910da6f` (Pablo's run of 04:17–04:27). If anyone re-runs the tests before the freeze, update slides 5–7.

## Slide 1 — 04:38 (0:00–0:25)

**On screen:** a big amber clock, two sentences, “The agent calls.”

**Say:** (2 seconds of silence on the clock) “The night inventory has written off the onglet. The Corrèze truck leaves in seven minutes. Chef Peyrat refuses substitutions. Nobody has time to call him.” (pause) “The agent calls.” Then: “We’re team 06. Our company is Chevillard du Limousin, a wholesale meat business that delivers about a hundred butchers, restaurants and canteens around Limoges. What you just heard happens almost every morning.”

**What each detail means**

| Detail | What it means |
| --- | --- |
| 04:38 | A demo clock. The data pack is frozen at Tuesday 24/11, 05:00, and trucks leave between 04:45 and 05:00. At 04:38 the earliest truck leaves in 7 minutes. |
| Chevillard du Limousin | Our fictional company from the data pack. A *chevillard* is a meat wholesaler: buys animals, has them slaughtered, sells carcasses, quarters and cuts. 92 clients, 63 products, 10 suppliers. |
| Night inventory | The 03:00 quality check before the trucks leave (Élodie, quality manager): temperatures, labels, condition of each lot. |
| Written off | Declared unsellable and removed from stock in the ERP. In the data, the onglet lot was written off at 03:10. Orders already loaded with onglet are now missing that line. |
| Onglet | Hanger steak. One per animal, so always scarce; restaurants fight for it. It is at zero stock in our data. |
| The Corrèze truck | One of 5 delivery routes (Corrèze = Brive, Tulle, Ussel). It leaves at 04:45. |
| Chef Peyrat | Nicolas Peyrat, chef-owner of Restaurant Leroy in Ussel, a real client in our data. His file says he refuses substitutions: call him before changing anything. |
| Substitutions | Replacing a missing product with another (bavette instead of onglet). Many clients forbid it without being asked first. |
| “The agent calls” | Our outbound feature “Avant le camion” (before the truck). Slide 3 explains it. The video shows this exact call. |

**If asked:** “Is the clock real?” No, it’s a demo clock on the Voix page; the data is frozen at 05:00.

## Slide 2 — The problem (0:25–1:05)

**On screen:** “61%”, and three short blocks: fewest hands, hard rules, a mistake costs the same day.

**Say:** “At a meat wholesaler, 61% of orders come in by phone, mostly between 5 and 8 in the morning. That’s when the fewest people are around: the salesperson is on the road or boning meat. Today, everything said on the phone is typed into the ERP by hand. We picked order-taking because the rules are hard and you can check them: carcasses two days ahead, cuts before 5 p.m., canteens three days ahead with their purchase-order number, blocked accounts, clients who refuse any substitution. And because a mistake costs money straight away: a butcher with no meat on his biggest day.”

**What each detail means**

| Detail | What it means |
| --- | --- |
| 61% | Share of orders placed by phone over the last 12 months, from the company document in the data pack (then email 22%, WhatsApp 12%, web portal 6%). |
| ERP | Enterprise Resource Planning: the company’s central software (clients, products, stock and lots, orders, purchase orders, delivery routes, invoices, payments). Stockline gave each team one; the agent acts on it only through tools that call its API. |
| Typed in by hand | In the data, about 83% of orders were keyed in by the three salespeople themselves, not by the order desk. Phone orders eat selling time. |
| 5 to 8 a.m. | The busiest calling window: trucks have left, butchers check what arrived and order for the next days. The company’s own document describes it. |
| Carcasses 2 days ahead | Carcasses and quarters must be ordered 2 days before delivery (slaughter, chilling, cutting). The company doc says a calf ordered Tuesday ships Friday at best, but the order data shows Tuesday-for-Thursday 224 times last year, so we follow the data (`DECISIONS.md` § 2.8). |
| Cuts before 5 p.m. | Ready-to-cook pieces (“PAD”), offal and prepared products must be ordered before 17:00 for next-morning delivery. |
| Canteens 3 days ahead, with a PO number | Public canteens (municipal kitchens, hospitals, care homes) order 3 days ahead, before 11:00, and must give their purchase-order number (*numéro de bon de commande*). Without it the public accountant won’t pay the invoice. |
| Blocked accounts | 3 clients are blocked for unpaid invoices (over €270k overdue between them). No delivery until accounting lifts the block. |
| Clients who refuse substitutions | Written in many client files: never replace a product without calling first. |
| “A butcher with no meat on his biggest day” | Our example from `DECISIONS.md`: promising carcass meat for a day it can’t be ready means an empty counter on his busiest day. |

**If asked:** “Why not something flashier?” Because success here is provable in the ERP: you can check the order, not just judge the tone. That let us write automated tests from hour two.

## Slide 3 — The agent (1:05–2:00)

**On screen:** two cards, inbound and outbound, and the amber band “A person approves, the agent makes the call.”

**Say:** “Our agent does two things. First, it takes calls: it recognises the client from their first words, understands ‘the usual’, turns ‘two hindquarters’ into kilos, checks stock for the delivery date, reads the order back, and only confirms after the client says yes. Second, it makes calls. [Optional, cut if behind: Stockline’s website presents sales, pricing and purchasing agents. Ours makes the calls of two of them, and adds a fourth: delivery.] When the night inventory writes off a lot, it calls every affected client before the truck leaves. It offers short-dated stock at a price a person has set. And it takes Christmas bookings, which today live on paper. The principle: a person approves, the agent makes the call.”

**What each detail means**

| Detail | What it means |
| --- | --- |
| Recognises the client from the first words | Code (`identify_caller`) runs before the model when the caller’s first words point to exactly one client, and loads their file: usual order, delivery days, rules, how they talk. Two plausible clients: one short question, never a guess (“Hyper Frais Limoges” has two stores). |
| “The usual” | The ERP keeps each client’s usual basket from their recent orders. “Comme d’habitude” reads it back for the client to confirm. |
| Pieces → kilos | Butchers order in pieces (“two hindquarters”), but carcass meat is sold by weight. The tool converts using each product’s size range (a hindquarter is 90–110 kg, so two ≈ 200 kg), and the agent says the invoice follows the real weighed weight. |
| Checks stock, lead time, delivery day | Stock is checked for the delivery date, not today. Lead time = how far ahead it must be ordered. Delivery day = the days that client’s route runs. |
| Confirms only after a “yes” | A code guard: `confirm_order` is refused unless the client’s last sentence is a yes. Not just a prompt instruction. |
| Before the truck (“Avant le camion”) | Code compares each loaded order with what is actually on the truck. Missing product: always a call. Short weight: a call from 5% and €15. Calls are sorted by truck departure. The agent follows each client’s file: refuses substitutions → states the fact and asks; accepts them → offers the usual replacement at their price. Anything added to the truck needs a yes, capped at the missing quantity + 20%. |
| Short-dated stock (“Date courte”) | €2,695 (purchase price) of stock near its use-by date with no order for it. Code finds clients who usually buy it and have a truck before the date. A person sets the price (refused below cost); the agent offers it once, never haggles. |
| Christmas book (“Carnet des fêtes”) | Christmas is the peak on the rarest pieces (one sweetbread per calf, one onglet per animal). “Like last year” reads back the client’s real 2025 Christmas basket. Each client is guaranteed up to last year’s volume; the rest goes on a waiting list, never promised. |
| “A person approves, the agent makes the call” | Decisions with money or priority attached (a discount price, who gets scarce stock) are made by a person. The agent does the phone work. Today the approval is a typed command, not a button. |
| Stockline’s three agents | Alexander’s line. Not checked by us: verify on Stockline’s site before saying it, or skip it. |

**If asked:** “Who approves in practice?” Today it’s a typed command (`/offre …`, `make chaos … --apply`). A button is the obvious next step.

## Slide 4 — Smart (2:00–2:45)

**On screen:** three numbered rules, and a dark card “Break the morning: 6 to 8 calls, €441 to €3,902 at stake.”

**Say:** “What makes the agent reliable is that the rules aren’t only in the prompt: they’re in the code. One: the write tools check themselves. If the lead time isn’t met or the stock isn’t there on the date, nothing is written, and the agent explains why. Two: one call, one client. The agent cannot open anyone else’s file. Three: without a yes from the client, no substitution and no confirmation. And to prove this isn’t a script: ‘Break the morning’. You choose what broke overnight, you write the reason, and the agent finds the affected clients on its own: six to eight calls, €441 to €3,902 at stake, and it reads them your sentence.”

**What each detail means**

| Detail | What it means |
| --- | --- |
| Rules in the code, not the prompt | A prompt is an instruction the model can forget. A rule in a tool can’t be skipped: the tool refuses. Two prompt rules failed in testing (“at most two suggestions”, “confirm only after a yes”) and were moved into code (`DECISIONS.md` § 2.14). |
| The tools check themselves | `create_draft_order`, `add_order_line` and `update_order_line` check stock on the date, lead time, delivery day and pieces → kilos. On a problem they write nothing and return the reason. It also saves one model step per order turn, which makes it faster (§ 2.2). |
| One call, one client | A guard in the agent loop (`call_guard`): once the caller is identified, tools can’t touch another client’s file or orders. Added after the “viande” bug on slide 7. |
| No “yes”, no write | Confirming an order or adding a replacement product is refused by code unless the client’s last sentence is a yes. |
| Break the morning (“Cassez le matin”) | A juror picks a product from a sabotage card and types the reason (“Cold room 2 broke down overnight”). `make chaos` then writes off that product’s whole stock and sets its loaded quantity to zero on every order prepared for today (or 70% for a “short weight” card). No model is involved in staging it; `make reset` undoes it. |
| Finds the clients on its own | The “before the truck” board lists who must be called, in truck-departure order. The agent then calls each one and reads the juror’s sentence as the reason. |
| 6 to 8 calls, €441 to €3,902 | Across the five sabotage cards: from liver (6 calls, €441) to dry-aged rib (8 calls, €3,902). The counts include the two onglet calls already in the data. |

**If asked:** “Can we pick any product?” The five cards are checked; we keep to products with 4–6 clients on today’s trucks. Paleron hits 17 clients, too many for a live demo.

## Slide 5 — Fast (2:45–3:25)

**On screen:** three before → after numbers, the line about the acknowledgement, and a small caveat.

**Say:** “Fast. In the starter kit, the caller waited 8.7 seconds before hearing anything. Today the first sound comes in under a second, often in a tenth of a second. We’re not cheating: that first sound is an acknowledgement chosen by code, ‘let me check’, ‘noted’, which never states a fact. The real answer follows two to four seconds later, like a salesperson looking at their screen. Two wins without touching the model: the transcript arrives a second earlier, because we were waiting for the connection to close before reading it. And the worst turn was halved with a single line of configuration: we keep connections open. On the phone, it’s the turn where the line sounds dead that makes people hang up.”

**What each detail means**

| Detail | What it means |
| --- | --- |
| 8.7 s (starter kit) | Measured by Alexander on the Voix page: first turn of the Peyronnet call, from end of speech to first sound, before any of our changes. |
| 0.09–0.61 s to first sound | Measured server-side over the voice WebSocket on typed turns. It is the time until the acknowledgement starts playing. It does not include speech recognition or the browser playing the audio. |
| The acknowledgement | A short phrase chosen by code from the transcript the moment the caller stops: “Je note.” on an order, “Je regarde.” on a question, “Très bien.” after a yes, “Je comprends.” on a blocked account, nothing on a goodbye. Chosen by code, so it can never invent a fact. “D’accord” was dropped (it sounds like a yes before a refusal), and so were “Alors…” and “Voyons…” (a tester found them annoying). |
| The real answer, 2–4 s later | The model then runs one or more steps (each step about 1.5–3 s) and calls tools. Median text time to first word is about 2.4–3.1 s. |
| 1.25–1.64 → 0.15–0.60 s (transcript) | End of speech to final transcript. Pablo found we waited for the speech-to-text connection to close before reading the final text. Same recorded audio sent 6 times, before and after the fix. |
| 8.0 → 3.5–4.2 s (worst turn) | Our connection pool used the library default, which closes an idle connection after 5 seconds. Callers talk longer than that, so almost every turn paid a fresh secure handshake to the model and voice providers (voice: about 1.9 s cold vs 0.17–0.37 s warm). Fix: keep idle connections for 600 s, one line. |
| “Orders of magnitude” | Each number is one run, on different machines. Read them as sizes, not exact values. |

**If asked:** “Isn’t the acknowledgement gaming the latency?” It’s what a person does on the phone, and it never states anything. We show both numbers: under a second to first sound, 2–4 s to the answer. “Is the worst turn still 3.5–4.2 s?” On the 6 reference calls, yes; with all the features added since, the worst turn is back to about 5–7 s, and the acknowledgement covers that silence.

## Slide 6 — Natural · Cheap (3:25–4:00)

**On screen:** four bullets on how it talks, and a dark card: $0.10 to $0.15 per call, 85% from the cache, −14% tokens.

**Say:** “Natural: the agent says ‘tu’ or ‘vous’ the way the client talks, from their file. It says numbers the way you’d say them aloud, ‘about two hundred kilos’. One question at a time, one read-back at the end. And it never pushes a sale: it only mentions a forgotten item when it’s obvious, because butchers hate sales pitches. Cheap: a complete call costs ten to fifteen US cents, voice included, and around five cents when calls follow each other, because 85% of what we send the model is read back from the cache.”

**What each detail means**

| Detail | What it means |
| --- | --- |
| “tu” or “vous” | French informal vs formal “you”. Each client file says how that client talks (a butcher who has worked with the house for 30 years says “tu”). Read in code, applied from the first turn. |
| Numbers said aloud | Written “200,0 kg” sounds robotic when spoken. The agent rounds and says words: “environ deux cents kilos”. |
| One question at a time, one read-back | It asks one thing per turn and reads the full order back once, at the end, before asking for the yes. Changed overnight to “counter style”: confirm only what just changed, then one full read-back at the end. |
| Forgotten items | Code decides, the model only phrases it. Only when today’s order is clearly the client’s repeat order with one or two products missing: “You usually take a forequarter with it, shall I add one?” At most one suggestion. Never “anything else?”. |
| $0.10–0.15 per call | Measured tokens × public list prices: model $0.074–0.087, voice (ElevenLabs) $0.02–0.06, speech-to-text under $0.005. US dollars, list prices; the spoken characters per call are an estimate. |
| ~$0.05 when calls follow each other | A second call 90 s after the first reused the cache: 4,130 uncached input tokens instead of 28,133, so the model part cost half. A real switchboard with back-to-back calls sits near this. |
| 85% from the cache | The prompt cache: the long fixed part of each request (instructions, tool definitions) is stored by the provider and re-read at about a twentieth of the normal input price ($0.10 vs $2 per million tokens). 84–88% of input tokens across runs. |
| −14% tokens vs the kit | Fewer tokens per call than the starter kit despite more features, mainly from removing the separate “check, then write” model step. |

**If asked:** “What’s the biggest cost?” The model, then the voice. “Why not a cheaper model?” Haiku is about twice as fast, but once promised a delivery date without checking. We stayed on Sonnet; Haiku could be re-tested now that checks for that exist.

## Slide 7 — How we know (4:00–4:40)

**On screen:** four tiles (8/8, 29/29, 193, 7/7) and the bug story.

**Say:** “How do we know it works? Eight reference calls replayed after every change: we check the ERP, what the agent says, and which tools it calls. Twenty-nine calls written to trip it up: a fake boss chasing a debt, someone asking for another client’s order, a supplier. 193 tests, and all seven sabotage cards. One story: on a blocked account, the agent took the word ‘viande’, meat, for a client’s name and opened another client’s file, with their balance and contacts, without saying anything. Nothing written, every ERP check green. We only saw it by checking which tools it called. It’s fixed, and checked three times. An agent can do something serious without writing anything and without saying anything: that’s why we test its tools, not just its answers.”

**What each detail means**

| Detail | What it means |
| --- | --- |
| 8/8 reference calls | `make calls` replays our test calls T1–T8 (normal order, ambiguous caller, stockout, change of mind, blocked account, “I forgot something”, a forgotten item in the usual order, and an unusual order where the agent must not suggest anything) and checks three things: the ERP afterwards, the words the agent said, and which tools it called. Pablo’s run on `42d9b4d`. |
| 29/29 “jury” calls | `make jury`: 29 hostile calls we wrote (“C’est Karim” when five clients have a Karim, two of them butchers in Limoges; a fake boss asking about a debt, someone asking for another client’s order, a supplier…). Automatic checks on rules that must never break, like never reading out an internal figure and never writing before the caller is identified. The full transcripts are read by a person. |
| 193 tests | Unit tests (`pytest`) on the tools and rules. They also pass on a fresh clone of `main`, which is what the jury will run. |
| 7/7 sabotage cards | `make chaos-check` stages the five “Break the morning” cards plus two “who gets served first” allocations, and checks the call board without any model. |
| The “viande” bug | Test T5: Boucherie Lacour (blocked) says “you won’t leave me without *viande* for the weekend!” The agent made up a client name from “viande”, called `identify_caller("Le Comptoir de la Viande")`, and loaded an unrelated client’s file: contacts, credit limit, balance. Reproduced 2 times out of 2; the second time it said nothing. |
| Every ERP check green | Nothing was written, so tests that only look at the ERP passed. Tests on the words passed too, because the agent didn’t mention it. Only the check on which tools were called caught it. |
| “Fixed: 0 out of 3 since” | After the fix (no re-identifying a known caller from a guess, plus the one-call-one-client guard), T5 was run 3 more times: no other client’s file opened. |

**If asked:** “Isn’t showing a bug risky?” It’s our best evidence that the tests catch what matters. “Are these numbers stable?” Each is one run; the model isn’t deterministic, so we re-run with `--repeat 3` before trusting a fix.

## Slide 8 — Your turn (4:40–4:55)

**On screen:** amber slide, “You are one of the wholesaler’s clients.”

**Say (slowly):** “You are one of the wholesaler’s clients: a butcher’s shop or a restaurant in the Limousin. Say your name and your business, and order the way you would by phone. The data is frozen at Tuesday 24 November, 5 a.m. Or draw a ‘Break the morning’ card and choose what broke overnight.” If the slides were in English, add: “The agent speaks French, so please call in French.”

**Who does what at this moment**

| Who | Does |
| --- | --- |
| Claudio | Reads the line above, then stays quiet. One framing sentence at most during a call (“it’s asking which of the two stores you mean: that’s on purpose”). |
| Jed | Switches the screen to the Voix page in demo mode (`?demo=1`). Points at the client card and order card as they appear; opens the order in the ERP after the call. |
| Alexander | Hands out the client cards and the sabotage cards. Plays the client in our own showcase call if there’s a slot. |
| Pablo | Runs `make chaos` when a juror picks a card, `make reset` between calls if needed, watches `make logs`. Has the backup video and a phone hotspot ready. See `PITCH-BACKSTOP.md`. |

**What each detail means**

| Detail | What it means |
| --- | --- |
| Client cards | Real clients from the data a juror can play (DEMO.md § 5: Boucherie Peyronnet in Limoges, Restaurant Leroy in Ussel, Le Petit Roger in Isle, Maison Vergnaud in Limoges). Each sabotage card also comes with two client cards (DEMO.md § 9), each with one honest line and one line that tries to trick the agent. |
| Data frozen at 05:00 | Every date the agent uses is relative to Tuesday 24/11, 05:00. “Tomorrow” means Wednesday 25/11. |
| Backup video | The 2-minute demo video. If the model or the network fails, play it, then show the test results. |

**If asked:** “Can we call in English?” The agent is built for French-speaking butchers; say so plainly and ask for French.

## Likely jury questions

Short, honest answers. Route each question to its owner: Alexander (agent, tools, rules), Pablo (speech, latency, cost), Jed (screens), Claudio (problem choice, tests, numbers).

| Question | Answer | Who |
| --- | --- | --- |
| Why this problem? | It’s the real bottleneck (61% by phone, 5–8 a.m., fewest hands), the data is richest there, and success is provable in the ERP. | Claudio |
| What model do you use? | Claude Sonnet 5.5, with Soniox for speech-to-text and ElevenLabs (`eleven_v4_turbo`) for the voice. | Alexander |
| Why not Haiku? | About twice as fast, but in one test it promised a delivery date without checking any tool. The checks that catch that exist now; we didn’t have time to re-test before the freeze. | Alexander |
| Is the first-sound number honest? | It’s the acknowledgement, chosen by code, never a fact. The real answer follows 2–4 s later. We show both numbers. | Pablo |
| Why does the voice sound slightly English? | It’s an English-native ElevenLabs voice speaking French. A native French voice needed a Gradium key we never got; our tester judged the current one good, so we froze it. | Pablo |
| What stops it promising something wrong? | Write tools refuse anything the rules forbid; no confirmation without a yes; the agent may not state a date, stock or quantity without a tool result from the same turn. | Alexander |
| Can it see other clients’ data? | No: one call, one client, enforced in the agent loop. Amounts owed are never read to an unverified caller. | Alexander |
| What does a call cost? | About $0.10–0.15 with a cold cache, around $0.05 when calls follow each other. List prices in USD. | Pablo |
| How do you test something non-deterministic? | Automatic replays that check the ERP, the words and the tools called; `--repeat 3` before trusting a fix; a person reads the jury transcripts. | Claudio |
| Who approves discounts and allocations? | A person, via a typed command today (`/offre …`, `make chaos … --apply`). A button is the next step. | Alexander |
| What would you do with more time? | Shorten the slow first turn that identifies and writes; a native French voice; re-test Haiku; repeat measurements to get ranges; put approvals on screen. | Claudio |

**Don’t claim:** live-browser speech-to-text gains (measured on recorded audio only), or a full voice call end to end since the last fixes (manual checks were still open at 04:27). Latency figures are single runs on different machines.
