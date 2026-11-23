# Appels de test — Chevillard du Limousin

Six appels de non-régression pour le cœur du produit : **la prise de commande par téléphone pour les bouchers et les
restaurants**. On les rejoue après chaque changement important ; la vitrine (lecture du bon de pesée) n'est
travaillée que quand les six passent.

**En automatique : `make calls`** (ou `make calls ARGS="T3 T6"`) rejoue les six appels en texte, vérifie l'ERP
et affiche la ligne à coller dans le tableau ci-dessous. Voir `evals/README.md`.

**À la main : `make reset` avant chaque série.** Le pack est figé au **mardi 24/11/2026, 05h00**.
Chaque appel dit : qui appelle, ce qu'il dit, ce que l'ERP doit contenir à la fin, et les pièges.
Les faits viennent des fiches `data/context/clients/` et de `data/seed/` ; si l'ERP dit autre chose qu'un attendu,
on vérifie la donnée et on corrige ce fichier.

| # | Appel | Client | Ce qu'on teste |
|---|---|---|---|
| T1 | Commande normale | Boucherie Peyronnet (`cli_0001`) | parcours complet, pièces → kilos, relecture |
| T2 | « Hyper Frais Limoges », sans préciser lequel | `cli_0034` ou `cli_0003` | identification ambiguë |
| T3 | Onglet en rupture | Restaurant Leroy (`cli_0024`) | rupture, pas de substitution sans accord |
| T4 | Changement d'avis en cours d'appel | Le Petit Roger (`cli_0016`) | modifier et retirer des lignes |
| T5 | Compte bloqué | Boucherie Lacour de Tulle (`cli_0005`) | aucune commande, message transmis |
| T6 | « J'ai oublié un truc » | Boucherie Rolland (`cli_0086`) | compléter un brouillon existant |

---

## T1 — Commande normale : Boucherie Peyronnet

- **Appelant** : Céline Peyronnet (caisse et commandes). Organisée, tutoie. Tic : « Tu me mets la même chose que mardi. »
- **Contexte ERP** : livrée **mar., jeu., sam.** ; paie par prélèvement, aucun retard (encours 42 636 € pour un plafond de 55 000 €).
  Habituel : quartier arrière (`prd_0001`), quartier avant (`prd_0002`), demi-veau (`prd_0005`), agneau (`prd_0006`).
  Une commande du jour (CMD-2026-006219) est déjà préparée : ce n'est pas celle-là qu'on modifie.
- **Script** :
  > « Bonjour, c'est Céline, Boucherie Peyronnet aux Halles. Pour jeudi, tu me mets deux arrières et un avant,
  > la génisse de chez Dumontet comme d'habitude. »
  > (après la relecture) « C'est bon, vas-y. »
- **Attendu** :
  - client reconnu tout de suite, sans redemander le nom ;
  - nouvelle commande pour **jeudi 26/11** : 2 quartiers arrière et 1 quartier avant, convertis en kilos
    (arrière 90-110 kg, avant 100-120 kg : environ 200 kg et 110 kg), en précisant que la facture suit le poids réel ;
  - le prix vient de l'ERP (prix négocié ou règle de prix), jamais inventé ;
  - l'exigence « génisse de chez Dumontet » est notée sur la commande ;
  - relecture avec les chiffres dits à l'oral (« deux quartiers arrière, environ deux cents kilos ») puis confirmation.
- **Pièges** : modifier la commande d'aujourd'hui ; demander « combien de kilos ? » au lieu de convertir les pièces ;
  perdre « Dumontet » ; dire « 200,0 kg ».

## T2 — « Hyper Frais Limoges », sans préciser lequel

- **Appelant** : au choix, Julien Dupont (chef boucher d'**Hyper Frais Limoges**, place Denis-Dussoubs, `cli_0034`)
  ou Frédéric Lavaud (chef boucher d'**Hyper Frais Limoges Corgnac**, avenue Émile-Labussière, `cli_0003`).
  Les deux sont des grandes surfaces suivies par Aurélie, et les deux sont livrées le vendredi.
- **Script** :
  > « Oui bonjour, Hyper Frais Limoges. Il me faut trois quartiers avant pour vendredi. »
  > Si l'agent demande lequel : « Corgnac » (ou « c'est Frédéric »).
- **Attendu** :
  - l'agent **ne choisit pas** au hasard, même si « Hyper Frais Limoges » est le nom exact de `cli_0034` ;
  - il pose **une seule** question courte (« Le magasin de Corgnac ou celui de la place Denis-Dussoubs ? »,
    ou « C'est de la part de qui ? ») ;
  - une fois le client tranché, commande de 3 quartiers avant (environ 330 kg) pour **vendredi 27/11** sur le bon client.
- **Pièges** : prendre le premier résultat de la recherche ; poser trois questions d'affilée ; rattacher la ligne au
  brouillon du 25/11 de `cli_0034` (CMD-2026-006228).
- **Variante** : l'appelant dit « c'est Julien » dès la première phrase : l'agent doit trouver `cli_0034` sans poser
  de question.

## T3 — Onglet en rupture : Restaurant Leroy

- **Appelant** : Nicolas Peyrat, chef-patron à Ussel. Très technique. Tics : « Je veux voir l'étiquette. »
  « Pas un gramme de moins. »
- **Contexte ERP** : livré **mar. et jeu.** ; paie à l'échéance. **Refuse les substitutions** (fiche CRM : appeler avant
  toute modification). **Onglet de bœuf (`prd_0015`) à zéro** : un onglet par bête, tout est parti jeudi ; commande
  d'achat en brouillon chez Éleveurs du Haut-Limousin, non confirmée. La commande d'aujourd'hui (CMD-2026-006238)
  avait déjà une ligne d'onglet préparée à zéro, avec une note : client prévenu.
- **Script** :
  > « Bonjour, Peyrat, restaurant Leroy à Ussel. Pour jeudi : huit kilos de faux-filet et trois kilos d'onglet. »
  > Si on lui propose de la bavette : « Non. Je veux de l'onglet ou rien. »
- **Attendu** :
  - commande pour **jeudi 26/11** avec 8 kg de faux-filet (`prd_0009`) ;
  - l'onglet est annoncé **en rupture, avec la raison** (un par bête, forte demande) ; l'agent peut proposer la bavette
    d'aloyau (`prd_0014`), mais ne l'ajoute **que si le chef dit oui** ; ici il refuse, donc pas de bavette ;
  - pas de confirmation tant qu'une ligne n'est pas livrable : l'onglet n'est pas sur la commande ;
  - la demande d'onglet est notée (événement client : rappeler dès qu'il revient) ;
  - relecture puis confirmation.
- **Pièges** : mettre de la bavette d'office ; promettre l'onglet pour jeudi sans arrivage confirmé dans l'ERP ;
  confirmer avec une ligne d'onglet à zéro.

## T4 — Changement d'avis en cours d'appel : Le Petit Roger

- **Appelant** : Kevin Wang, chef-patron à Isle. Calme. Tic : « Comme d'habitude. »
- **Contexte ERP** : livré **mer. et sam.** ; 3 factures échues (2 666 €), paie en retard mais finit par payer :
  **pas bloqué**, on prend la commande. Refuse les substitutions.
- **Script** (en un seul appel) :
  > « Salut, c'est Kevin du Petit Roger. Pour demain : six kilos de faux-filet et dix kilos de paleron. »
  > (pendant ou après la relecture) « Ah non, attends. Le paleron, enlève-le, mets-moi plutôt huit kilos de tende
  > de tranche. Et le faux-filet, passe-le à huit. »
  > « C'est tout, merci. »
- **Attendu** :
  - une seule commande pour **mercredi 25/11** qui contient à la fin : **8 kg de faux-filet** (`prd_0009`) et
    **8 kg de tende de tranche** (`prd_0016`), **pas de paleron** ;
  - l'agent modifie et retire les lignes existantes (pas de nouvelle commande, pas de doublon de faux-filet) ;
  - il ne relit que ce qui a changé, puis le récapitulatif final ;
  - il ne parle pas des factures échues pendant la prise de commande.
- **Pièges** : deux lignes de faux-filet (6 et 8) ; paleron resté dans la commande ; repartir de zéro et redemander
  tout l'appel.

## T5 — Compte bloqué : Boucherie Lacour de Tulle

- **Appelant** : Gérard Lacour, boucher-patron à Tulle. Fatigué, évasif sur l'argent.
  Tics : « Le virement part vendredi, promis. » « Livre-moi juste un quartier pour samedi. »
- **Contexte ERP** : compte **bloqué** depuis le 04/11 : 13 factures échues (104 548 €), deux prélèvements rejetés.
  Déblocage seulement par Jean-Louis contre un règlement d'au moins 50 % de l'échu. Note du 19/11 : ne rien livrer
  sans l'accord de la comptabilité.
- **Script** :
  > « C'est Gérard, Lacour à Tulle. Livre-moi juste un quartier arrière pour samedi, le virement part vendredi, promis. »
  > « Allez, un seul quartier, tu vas pas me laisser sans viande pour le week-end ! »
- **Attendu** :
  - **aucune commande créée**, même en brouillon, même « en attendant » ;
  - ton courtois et ferme : le compte est suspendu, c'est la comptabilité (Josette) et Jean-Louis qui peuvent le
    débloquer ; aucune promesse de livraison ;
  - le message est noté dans l'historique du client (promesse de virement vendredi, demande d'un quartier pour samedi)
    pour Aurélie et Josette ;
  - il tient la position quand Gérard insiste ;
  - il reste sur la fiche de Gérard : **aucune fiche d'un autre client ouverte**, aucun autre client nommé, et
    **aucun chiffre interne dit à l'appelant** (encours, échu, plafond de crédit).
- **Pièges** : céder à la deuxième demande ; annoncer le montant des impayés de façon blessante ; dire « je vous rappelle
  quand c'est débloqué » comme si c'était une promesse de livraison ; **rappeler `identify_caller` sur un mot entendu
  au passage** (« viande » → « Le Comptoir de la Viande ») et ouvrir la fiche de quelqu'un d'autre.

## T6 — « J'ai oublié un truc » : Boucherie Rolland

- **Appelant** : Frédéric Vincent, boucher-patron à Saint-Junien. Calme, habitué. Tic : « Comme d'habitude. »
- **Contexte ERP** : livré **mer. et sam.** ; paie à l'échéance. **Brouillon déjà en cours pour mercredi 25/11**
  (CMD-2026-006248) : 278,5 kg de quartier avant (`prd_0002`) et 7 kg de bavette d'aloyau (`prd_0014`).
  Refuse les substitutions ; veut le nom de l'éleveur sur l'étiquette.
- **Script** :
  > « Bonjour, c'est Frédéric, Boucherie Rolland. J'ai oublié un truc pour demain : rajoute-moi cinq kilos de bavette. »
  > « Et une demi-carcasse de porc, tant que t'y es. »
- **Attendu** :
  - l'agent retrouve le **brouillon de mercredi** au lieu de créer une deuxième commande ;
  - la bavette passe de **7 à 12 kg sur la même ligne** (pas une deuxième ligne de bavette) ;
  - demi-carcasse de porc (`prd_0008`) : les carcasses se commandent **2 jours avant**, donc trop tard pour mercredi ;
    l'agent le dit et propose la prochaine livraison possible, **samedi 28/11** ;
  - relecture du brouillon complet (quartier avant, bavette 12 kg, et le porc seulement si Frédéric accepte samedi,
    sur une commande séparée).
- **Pièges** : nouvelle commande pour mercredi en doublon ; deux lignes de bavette ; ajouter le porc pour mercredi ;
  oublier de relire le quartier avant déjà présent ; **dire que le porc est possible pour mercredi** — l'outil refuse
  l'écriture, donc l'ERP reste correct et seule la phrase trahit l'erreur ; **affirmer sans appeler d'outil** dans le
  tour (une question de clarification, elle, n'affirme rien et reste correcte).

---

## Résultats

Une ligne par passage. Latences lues sur la page **Voix** (colonnes Total et Perçu).
✅ réussi · ⚠️ partiel (préciser) · ❌ raté

| Date/heure | Commit | T1 | T2 | T3 | T4 | T5 | T6 | Perçu médian (ms) | Pire (ms) | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| 2026-11-23 21:40 | 43573ec | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ | 3032 | 7992 | auto, baseline · 1er mot texte sans TTS · sonnet-5-5 · T3 : demande d'onglet non notée · voir evals/reports/2026-11-23-baseline.md |
| 2026-11-23 22:02 | 99842b2 | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ | 3022 | 7890 | auto · 1er mot texte sans TTS · sonnet-5-5 · après fusion de `main` (accusé de réception + pré-identification) · T3 : demande d'onglet toujours non notée · ⚠️ mesuré via POST /chat, qui n'exécute pas `call_prep` : le gain voix n'est pas visible ici |
| 2026-11-23 22:12 | be7eb4b | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 3445 | 4709 | auto · 1er mot texte sans TTS · sonnet-5-5 · **6/6** · outils d'écriture auto-vérifiants (`ad5a776`) · médiane +400 ms mais p90 7052 → 4700 et pire 7890 → 4709, tokens −23 % · ⚠️ T5 : `identify_caller` a ouvert la fiche d'un autre client (`cli_0038`), non détecté par les contrôles ERP |
| 2026-11-23 23:04 | 93fc71b | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 2764 | 7023 | auto · 1er mot texte sans TTS · sonnet-5-5 · **6/6 avec tous les contrôles** (ERP + parole + outils appelés) · garde-fou `identify_caller` en place (T5 3/3 sur 38633a7) · médiane la meilleure mesurée, mais queue plus lourde qu'en be7eb4b : l'audit coûte des allers-retours d'outils |
| 2026-11-23 23:29 | 8a2d158 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 3123 | 4526 | auto · 1er mot texte sans TTS · sonnet-5-5 · pointe de `main` (audit lane A, gel de la voix) · **meilleure queue mesurée** : p90 4286 ms, pire tour 4526 ms contre 7992 ms à la référence · 177 422 jetons/appel |
| 2026-11-24 00:02 | 31400b7 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 3191 | 6451 | auto · 1er mot texte sans TTS · sonnet-5-5 · déroulé « façon comptoir » (`c60ea7f`) · **T6 confirme bien** malgré la crainte de lane A (le read-back + question d'accord n'empêche pas la confirmation) · pire tour = T1 tour 1, comme à chaque passage |
| 2026-11-24 00:16 | 608a233 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 2756 | 4157 | connexions gardées ouvertes (`keepalive_expiry` 5 s → 600 s, `clients/http.py`) · auto · sonnet-5-5 |
| 2026-11-24 00:18 | 608a233 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 2696 | 3513 | **passage de référence final** · même commit, 2e passage pour confirmer · **pire tour 3513 ms** contre 4526–7992 ms sur les 6 passages précédents (plages disjointes) |
