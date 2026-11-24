# Speaker notes — team 06 pitch (7 minutes, slides + live demo)

**Deck:** https://claude.ai/artifact/UM8P8vBhGso4evr9dEcqFk (French, 8 slides; Jed’s script is also in each slide’s speaker notes).
**Roles and run sheet:** `PITCH-BACKSTOP.md`.

## The format

7 minutes in total, slides and live demo together. Jed presents in French and is also the voice of every client in the demos. Each demo slide is shown for ~15 s, then Claudio switches to the Voix page and the call happens live; after the call he switches back to the slides. The 2-minute video is only the fallback if the agent fails.

| # | Time | On screen | What happens |
| --- | --- | --- | --- |
| 1 | 0:00–0:35 | Slide 1 · 04:38 | Hook, who we are |
| 2 | 0:35–1:15 | Slide 2 · Le problème | 61% by phone, the hard rules |
| 3 | 1:15–2:30 | Slide 3 · Démo 1 → Voix page | **Live:** Jed plays Céline (Boucherie Peyronnet), 2 turns |
| 4 | 2:30–3:05 | Slide 4 · Ce que vous venez d’entendre | The numbers behind what the jury just heard |
| 5 | 3:05–4:35 | Slide 5 · Démo 2 → Voix page | **Live:** “Avant le camion” call to chef Peyrat, 5 turns |
| 6 | 4:35–5:35 | Slide 6 · Démo 3 → Voix page | **Live:** a juror breaks the morning, the agent calls |
| 7 | 5:35–6:30 | Slide 7 · Comment on le sait | Rules in code, tests, the “viande” bug |
| 8 | 6:30–7:00 | Slide 8 · À vous | Hand over to the jury |

**If behind:** more than 30 s late at 4:35 → skip demo 3 (offer it after the 7 minutes). Late at 5:35 → slide 7 keeps its first sentence and the numbers, drop the bug story.
**If the agent fails in demo 1 or 2:** Pablo plays the 2-minute video instead of both live demos, then go straight to slide 7.

Numbers come from `PITCH.md` and `DECISIONS.md` (Pablo’s run on `42d9b4d`). Below, each section gives Jed’s French script, a short English gloss for the rest of the team, and what each detail means so anyone can answer a question.

---

## 1 · 04:38 (0:00–0:35)

**Jed (French):** *(2 seconds of silence on the clock)* « L’inventaire de nuit a déclassé l’onglet. Le camion de Corrèze part dans sept minutes. Le chef Peyrat refuse les substitutions. Personne n’a le temps de l’appeler. » *(pause)* « L’agent appelle. » « Nous sommes l’équipe 06. Notre entreprise, c’est Chevillard du Limousin, un grossiste en viande qui livre une centaine de bouchers, restaurants et cantines autour de Limoges. Ce que vous venez d’entendre arrive presque chaque matin, et dans quelques minutes vous allez l’entendre en direct. »

*English gloss:* the night inventory wrote off the onglet, the truck leaves in 7 minutes, the chef refuses substitutions, nobody has time to call: the agent calls. We are team 06, a meat wholesaler near Limoges; you’ll hear this live in a few minutes.

| Detail | What it means |
| --- | --- |
| 04:38 | A demo clock. The data is frozen at Tuesday 24/11, 05:00; trucks leave between 04:45 and 05:00. |
| Chevillard du Limousin | Our fictional company from the data pack: a meat wholesaler (*chevillard*). 92 clients, 63 products, 10 suppliers. |
| Night inventory / written off | The 03:00 quality check before the trucks leave. “Written off” = declared unsellable and removed from stock in the ERP; in the data the onglet lot was written off at 03:10. |
| Onglet | Hanger steak: one per animal, always scarce, at zero stock in our data. |
| Chef Peyrat | Nicolas Peyrat, chef-owner of Restaurant Leroy in Ussel, a real client in the data. His file says he refuses substitutions. Demo 2 is his call. |

## 2 · Le problème (0:35–1:15)

**Jed (French):** « Chez un chevillard, 61 % des commandes arrivent par téléphone, et surtout entre 5 et 8 heures du matin. C’est le moment où il y a le moins de monde : le commercial est sur la route ou au désossage. Aujourd’hui, tout ce qui se dit au téléphone est ressaisi à la main dans l’ERP. On a choisi la prise de commande parce que les règles y sont dures et qu’on peut les vérifier : carcasses deux jours avant, pièces avant 17 h, cantines trois jours avant avec leur numéro de bon de commande, comptes bloqués, clients qui refusent toute substitution. Et parce qu’une erreur coûte tout de suite : un boucher sans viande le jour de sa plus grosse vente. »

| Detail | What it means |
| --- | --- |
| 61% | Share of orders placed by phone over 12 months, from the company document in the data pack (then email 22%, WhatsApp 12%, web 6%). |
| ERP | Enterprise Resource Planning: the company’s central software (clients, stock and lots, orders, routes, invoices). The agent acts on it only through tools that call its API. |
| Typed in by hand | About 83% of orders in the data were keyed in by the three salespeople themselves. |
| Carcasses 2 days ahead | Carcasses and quarters must be ordered 2 days before delivery. The company doc says a calf ordered Tuesday ships Friday at best, but the data shows Tuesday-for-Thursday 224 times last year, so we follow the data (`DECISIONS.md` § 2.8). |
| Cuts before 17:00 | Ready-to-cook pieces (“PAD”), offal and prepared products: order before 17:00 for next morning. |
| Canteens, PO number | Public canteens order 3 days ahead, before 11:00, with their purchase-order number (*numéro de bon de commande*); without it the public accountant won’t pay. |
| Blocked accounts | 3 clients blocked for unpaid invoices (over €270k overdue between them). |

## 3 · Démo 1: il prend la commande (1:15–2:30)

**Jed, intro (15 s):** « Premier cas, le plus courant : un boucher qui commande. Je joue Céline, de la boucherie Peyronnet, aux Halles de Limoges. Écoutez la première seconde. »

**Live (≈60 s), Jed speaks to the agent:**
1. « Bonjour, c’est Céline, Boucherie Peyronnet aux Halles. Pour jeudi, tu me mets deux arrières et un avant, la génisse de chez Dumontet comme d’habitude. »
2. After the read-back: « C’est bon, vas-y. »

**What the jury should notice** (listed on the slide):

| Detail | What it means |
| --- | --- |
| « Je note. » in a fraction of a second | An acknowledgement chosen by code from the transcript the moment the caller stops (“Je note.” on an order, “Je regarde.” on a question, “Très bien.” after a yes). It never states a fact. |
| Céline recognised from her first sentence | Code (`identify_caller`) runs before the model when the first words point to one client and loads her file. She’s addressed with “tu” because her file says so. Two plausible clients → one short question, never a guess. |
| Two hindquarters → about 200 kg | Carcass meat is sold by weight; the tool converts pieces with each product’s size range (hindquarter 90–110 kg) and the invoice follows the real weighed weight. “Génisse de chez Dumontet” (the breeder she always wants) is noted on the order. |
| Confirmed only after « c’est bon » | A code guard: `confirm_order` is refused unless the client’s last sentence is a yes. |
| The price move | The agent may mention once that Monday’s market quote moved the carcass price. That’s the “cadran annoncé” feature: said once a week, only to butchers buying carcasses. |

**If voice recognition fails:** Claudio types Jed’s lines in the text box and the call carries on.

## 4 · Ce que vous venez d’entendre (2:30–3:05)

**Jed (French):** « Ce que vous venez d’entendre. Dans le kit de départ, le client attendait 8,7 secondes avant le premier son. Aujourd’hui, moins d’une seconde : c’est le “je note”, un accusé de réception choisi par le code, qui n’affirme jamais rien. La vraie réponse suit deux à quatre secondes après, comme un vendeur qui regarde son écran. La transcription arrive une seconde plus tôt qu’au départ. Et l’appel complet coûte dix à quinze centimes, voix comprise. »

| Detail | What it means |
| --- | --- |
| 8.7 s → 0.09–0.61 s | End of speech to first sound. 8.7 s measured by Alexander on the starter kit (Peyronnet first turn); 0.09–0.61 s measured server-side on typed turns (no speech recognition or browser playback included). |
| The real answer 2–4 s later | Each model step takes ~1.5–3 s; median text time to first word ~2.4–3.1 s. |
| 1.25–1.64 → 0.15–0.60 s | End of speech to final transcript. We waited for the speech-to-text connection to close before reading the text; Pablo’s fix. Same recorded audio sent 6×. |
| $0.10–0.15 per call | Measured tokens × public list prices (USD): model $0.074–0.087, voice $0.02–0.06, speech-to-text < $0.005. ~$0.05 when calls follow each other. |
| 85% from the cache | The fixed part of each request (instructions, tool definitions) is re-read from the provider’s cache at about 1/20 of the normal input price. |

## 5 · Démo 2: avant le camion (3:05–4:35)

**Jed, intro (15 s):** « Deuxième cas : c’est la maison qui appelle. 4 h 38, l’inventaire de nuit a déclassé l’onglet. Le chef Peyrat, à Ussel, l’a commandé, et il refuse les substitutions. Son camion part dans sept minutes. Je joue le chef. »

**Live (≈75 s).** Claudio opens **Avant le camion** and clicks **Appeler** on Leroy; the agent speaks first. Jed answers:
1. « Vous vous foutez de moi ? J’ai l’onglet à la carte ce midi. Vous me faites un geste au moins ? » *(skip if behind)*
2. « Bon. Vous avez quoi qui pourrait remplacer ? »
3. « Mettez-moi quatre kilos et demi de bavette alors. »
4. « Oui, allez-y. »
5. « Merci, au revoir. »

| Detail | What it means |
| --- | --- |
| Who gets called | Code, no model: every loaded order is compared line by line with what’s on the truck. Missing product → always a call. Short weight → a call from 5% and €15. Sorted by truck departure. |
| The reason, no other product named | Peyrat’s file says he refuses substitutions, so the agent states the fact and asks; it names a replacement only when he asks for one. |
| No commercial gesture promised | Discounts are decided by a person. The request is logged for his salesperson. |
| Bavette on the truck only after « oui » | `add_to_truck` is refused without a yes in the client’s last sentence, and capped at the missing quantity + 20%. |
| « Récupéré 77 € » | The board’s counter of sales saved; the card turns “fait” and the order line shows « remplace Onglet de bœuf ». |
| « Une personne approuve, l’agent téléphone » | Decisions with money or priority attached are made by a person; the agent does the phone work. Today that approval is a typed command, not a button. |

## 6 · Démo 3: Cassez le matin (4:35–5:35)

**Jed (French):** « Pour vous prouver que ce n’est pas un script : choisissez un numéro, et dites-nous ce qui s’est passé cette nuit. »

**Live (≈60 s):** a juror picks a number on the slide (1–5) and says the reason; Alexander writes it down for Pablo; Pablo stages it (~10 s); the new calls appear on the board in departure order with the € at stake; Claudio clicks **Appeler** on the first one and the jury hears the agent say *their* sentence to the client. Jed can answer one line (« Bon, laissez comme ça. ») and we hang up.

| Detail | What it means |
| --- | --- |
| The five options | Côte de bœuf maturée 21 jours · Entrecôte · Filet de bœuf paré · Foie de veau · Côte maturée, poids court. These are the only products checked for a live demo (4–6 clients on today’s trucks). Paleron would hit 17 clients. |
| What “breaks” | `make chaos` writes off the product’s whole stock (the juror’s sentence is the write-off note) and sets the loaded quantity to 0 on every order prepared for today (70% for “poids court”). No model is involved; `make reset` undoes it. |
| 6 to 8 calls, €441 to €3,902 | Depending on the card: from liver (6 calls, €441) to dry-aged rib (8 calls, €3,902). |

## 7 · Comment on le sait (5:35–6:30)

**Jed (French):** « Ce qui rend l’agent fiable : les règles ne sont pas seulement dans le prompt, elles sont dans le code. Les outils refusent ce qui est interdit, un appel ne touche qu’un seul client, et rien ne s’écrit sans un oui. Et on le vérifie : huit appels de référence rejoués à chaque changement, vingt-neuf appels écrits pour le piéger, 193 tests. Une histoire : sur un compte bloqué, l’agent a pris le mot “viande” pour un nom de client et a ouvert la fiche d’un autre client, sans rien dire. Rien d’écrit, tous les contrôles de l’ERP au vert. On ne l’a vu qu’en vérifiant quels outils il appelait. C’est corrigé, et vérifié trois fois. »

| Detail | What it means |
| --- | --- |
| The tools check themselves | `create_draft_order`, `add_order_line`, `update_order_line` check stock on the date, lead time, delivery day; on a problem they write nothing and say why. Also saves a model step. |
| One call, one client | `call_guard` in the agent loop: once identified, tools can’t touch another client’s file or orders. |
| No yes, no write | Confirmations and replacements are refused by code without the client’s yes. |
| 8/8 | `make calls`: T1–T8 replayed, checking the ERP, the agent’s words and the tools it called. |
| 29/29 | `make jury`: 29 hostile calls we wrote (“C’est Karim” when five clients have a Karim, a fake boss chasing a debt, someone asking for another client’s order…). Automatic checks on rules that must never break; transcripts read by a person. |
| 193 / 7/7 | Unit tests (also on a fresh clone) / the sabotage cards staged and checked without a model. |
| The “viande” bug | On T5 (blocked account), the agent invented a client name from “viande”, called `identify_caller("Le Comptoir de la Viande")` and loaded an unrelated client’s file. 2 out of 2 before the fix; 0 out of 3 after. Only the check on tools called caught it. |

## 8 · À vous (6:30–7:00)

**Jed (French):** « Merci. À vous : vous êtes un client du chevillard, une boucherie ou un restaurant du Limousin. Dites votre nom et votre commerce, et commandez comme au téléphone. Les données sont figées au mardi 24 novembre, cinq heures du matin. »

Jed hands the headset to the juror (or speaks for them if they prefer). The agent only speaks French.

---

## Likely jury questions

Questions will come in French. Jed answers the general ones; the others can answer in French or ask Jed to relay. Owner by topic: Alexander (agent, tools, rules), Pablo (speech, latency, cost), Claudio (problem choice, tests, numbers), Jed (the demo, the screens).

| Question | Answer | Who |
| --- | --- | --- |
| Why this problem? | The real bottleneck (61% by phone, 5–8 a.m., fewest hands), the richest data, and success is provable in the ERP. | Jed / Claudio |
| What model do you use? | Claude Sonnet 5.5, Soniox for speech-to-text, ElevenLabs `eleven_v4_turbo` for the voice. | Alexander |
| Why not Haiku? | About twice as fast, but once promised a delivery date without checking a tool. The checks that catch that now exist; not re-tested yet. | Alexander |
| Is the first-sound number honest? | It’s the acknowledgement, chosen by code, never a fact; the answer follows 2–4 s later. We show both. | Pablo |
| Why does the voice sound slightly English? | An English-native ElevenLabs voice speaking French; a native French voice needed a Gradium key we never got. | Pablo |
| What stops it promising something wrong? | Write tools refuse what the rules forbid; no confirmation without a yes; no date, stock or quantity stated without a tool result from the same turn. | Alexander |
| Can it see other clients’ data? | No: one call, one client, enforced in code. Amounts owed are never read to an unverified caller. | Alexander |
| What does a call cost? | $0.10–0.15 with a cold cache, ~$0.05 when calls follow each other (list prices, USD). | Pablo |
| How do you test something non-deterministic? | Replays that check the ERP, the words and the tools called; `--repeat 3` before trusting a fix; humans read the jury transcripts. | Claudio |
| Who approves discounts and allocations? | A person, by typed command today (`/offre …`, `make chaos … --apply`); a button is the next step. | Alexander |
| What with more time? | Shorten the slow first turn; a native French voice; re-test Haiku; repeated measurements; approvals on screen. | Claudio |

**Don’t claim:** live-browser speech-to-text gains (measured on recorded audio only). Latency figures are single runs on different machines.
