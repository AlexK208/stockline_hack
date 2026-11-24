# DECISIONS.md — team-06 · Chevillard du Limousin

Agent vocal de **prise de commande au téléphone** pour un chevillard (viande en gros) du Limousin.

Ce document est tenu au fil de l'eau : le problème choisi et pourquoi, nos choix techniques, nos mesures, et —
surtout — ce qui n'a pas marché. Les chiffres marqués **mesurés** viennent d'un passage réel enregistré dans
`evals/results/` et reproductible avec `make calls` ; tout le reste est signalé comme hypothèse.

---

## 1. Le problème choisi, et pourquoi

**Un client appelle, l'agent l'identifie, prend sa commande (y compris « comme d'habitude »), vérifie le prix, le
stock à la date de livraison et les délais, relit la commande et la confirme dans l'ERP.**

Pourquoi celui-là, parmi tout ce que l'ERP permet :

| Raison | Détail |
|---|---|
| C'est le vrai goulot d'étranglement | Chez un chevillard, les commandes arrivent par téléphone entre 5 h et 8 h, sur un créneau court, pendant que le commercial est déjà en tournée ou au désossage. C'est le moment où l'entreprise a le moins de bras disponibles et le plus d'appels. |
| C'est là que les données sont les plus riches | ~100 clients, 3 ans d'historique, des paniers habituels, des personas détaillés. « Comme d'habitude » et « la génisse de chez Dumontet » ne sont jouables que sur ce cas d'usage. |
| Les règles sont dures et vérifiables | Délais (2 jours pour les carcasses, 17 h pour le PAD, 3 jours pour les collectivités), ruptures, comptes bloqués, refus de substitution. On peut **prouver** qu'un appel s'est bien passé en regardant l'ERP, pas en jugeant le ton. C'est ce qui nous a permis d'écrire des tests de non-régression dès la 2ᵉ heure. |
| Le coût d'une erreur est réel | Une demi-carcasse acceptée pour mercredi alors que l'abattage est jeudi, c'est un client sans viande le jour de sa plus grosse vente. |

**Pièce de démonstration** (prévue seulement une fois le cœur au vert) : un client appelle pour une livraison
courte, l'agent lui lit le ticket de pesée — poids préparé contre poids commandé, numéro de lot.

Les six appels de référence sont décrits dans [`SCENARIOS.md`](SCENARIOS.md) (T1 à T6) : commande normale, client
ambigu, produit en rupture avec refus de substitution, changement d'avis en cours d'appel, compte bloqué pour
impayés, et « j'ai oublié un truc » sur un brouillon existant.

---

## 2. Nos choix techniques

### 2.1 Les règles métier restent dans le backend ; l'agent n'agit que par outils

Repris du kit et tenu jusqu'au bout. Le service IA ne recalcule jamais un prix, un stock ou un encours : il appelle
l'API. Conséquence concrète : quand on a rendu la disponibilité du stock sensible à la date de livraison, le
changement s'est fait une seule fois (`stock.availability_on`) et a profité à l'agent, à l'UI et aux tests.

### 2.2 Les outils d'écriture se vérifient eux-mêmes

**Le choix le plus rentable de la nuit.** Au départ, le modèle devait appeler `check_products` *puis* écrire. Deux
appels modèle par tour de commande, et rien n'empêchait le modèle de sauter la vérification.

Maintenant `create_draft_order`, `add_order_line` et `update_order_line` font eux-mêmes les contrôles (stock à la
date, délai, jour de livraison, pièces → kilos). En cas de problème, **ils n'écrivent rien** et renvoient
`problems`. Le modèle n'a plus de vérification à penser : il écrit, et l'outil refuse si c'est interdit.

- −1 étape modèle par tour de commande ;
- la règle ne peut plus être oubliée par le modèle, elle est dans le code ;
- `check_products` reste, pour les questions (« il vous reste de l'onglet ? »).

Visible dans la trace de T3 : `create_draft_order` renvoie `problems: ['Onglet de bœuf : rupture']`, rien n'est
écrit, le modèle réessaie sans l'onglet et enregistre la demande.

### 2.3 Identifier l'appelant dans le code, avant le modèle

Quand les premiers mots de l'appelant désignent **un seul** client, `identify_caller` est exécuté dans la boucle
(`agent/loop.py`), avant que le modèle tourne, et la fiche lui est donnée dans le tour. Le premier tour coûte une
étape modèle de moins. Si plusieurs clients collent, on ne devine pas : l'agent pose une question courte (c'est T2).

### 2.4 Un accusé de réception parlé immédiatement, choisi par du code

Le silence entre la fin de la phrase du client et le premier son est ce qui fait raccrocher. Un accusé court est
émis dès que l'appelant se tait (`services/call_prep.py`), choisi **dans le code** à partir du transcript, jamais
par le modèle — donc jamais une invention.

Les mots ont changé plusieurs fois à l'oreille. Aujourd'hui ils collent au tour : « Je note. » ou « Un instant. »
sur une commande, « Je regarde. » sur une question, « Très bien. » après un oui, « Je comprends. » sur un compte
bloqué, et **rien du tout** sur un au revoir ou une demande de relecture. Deux essais abandonnés : « D'accord. »,
qui avant un refus s'entend comme un oui ; puis « Alors… » et « Voyons… », qu'un testeur a trouvés agaçants. Ce
sont des erreurs invisibles dans l'ERP : elles ne s'entendent qu'à l'oreille.

### 2.5 Interdire d'affirmer sans outil

Règle de prompt : l'agent ne peut pas dire qu'un produit, une quantité ou une date est possible ou impossible de
mémoire — seulement à partir d'un résultat d'outil **du tour courant**. Et les informations internes (encours,
marge, dates de lot) ne se disent pas au client.

Ajoutée après avoir vu un modèle annoncer un délai correct… sans avoir rien vérifié. Juste cette fois-là.

### 2.6 Sonnet, pas Haiku

`claude-haiku-5-5` est nettement plus rapide (premier mot ~1,3–1,9 s contre ~2,9 s) et passe aussi les six
scénarios sur un passage. On reste pourtant sur `claude-sonnet-5-5` :

- Haiku a affirmé en T6 « je peux la rajouter pour mercredi » pour une demi-carcasse de porc, **sans appeler
  d'outil**. C'est faux (délai 2 jours), et aucun contrôle ERP ne pouvait le voir : rien n'avait été écrit.
- Au moment de décider, les contrôles capables d'attraper ça n'existaient pas encore. Ils existent maintenant
  (§ 2.7), donc Haiku est ré-évaluable — mais ce n'était pas défendable de changer de modèle « à l'aveugle » à
  quelques heures du gel.

**La décision est donc : Sonnet par défaut, Haiku à re-tester avec `make calls ARGS="--repeat 3"`.**

### 2.7 Des tests de non-régression automatiques, y compris sur ce que l'agent *dit*

`make calls` rejoue T1–T6 contre l'agent et vérifie l'ERP. Mais vérifier l'ERP ne suffit pas, et c'est le
raisonnement le plus important de ce document :

> Quand un outil refuse une écriture, **rien n'arrive dans l'ERP**. Une fausse promesse faite au client ne laisse
> donc aucune trace, et le scénario passe au vert.

T5 et T6 vérifient donc aussi les mots : en T6, la réponse à « et une demi-carcasse de porc » ne doit jamais
accepter mercredi et doit s'appuyer sur un outil du tour ; en T5, aucune fiche d'un autre client ne doit être
ouverte, aucun autre client nommé, aucun chiffre interne lu à l'appelant.

`make calls-test` (13 contrôles, sans modèle et sans crédits) vérifie que **chaque contrôle échoue bien quand il
doit échouer**. Un contrôle qui cesse silencieusement de mordre est pire que pas de contrôle.

**`make jury` : les cas du jury, rejoués.** Le jury teste en direct sur des scénarios que nous ne connaissons
pas. Nous en avons écrit 18 qui ressemblent à ce qu'il tentera (`evals/jury_calls.json`, 57 tours) : cinq Karim
dont deux bouchers à Limoges, un appelant qui se trompe de personne et se corrige, quelqu'un qui réclame la
commande d'un autre client par son numéro, un fournisseur, un faux patron qui réclame un encours.

Leur `expected` est en prose, et plusieurs ont plusieurs bonnes réponses défendables : les noter automatiquement
reviendrait à inventer un avis que le scénario ne donne pas. `make jury` sépare donc les rôles — deux invariants
durs (aucun chiffre interne dit, aucune écriture avant d'avoir identifié l'appelant), des indices signalés mais
non jugés (combien de fiches ouvertes, quels autres clients nommés), et la transcription imprimée en face de
`expected` pour qu'un humain tranche en quelques secondes.

La première version des invariants faisait échouer J1, J14 et J15 **pour du comportement correct** : J1 *doit*
citer Marty et Deschamps pour lever l'ambiguïté, le `client_id` de J14 est le propriétaire de la commande
réclamée à tort et non l'appelant, et dans J15 l'appelant corrige lui-même son identité. Un contrôle qui crie au
loup sur du bon comportement est pire que pas de contrôle : l'équipe cesse de le lire. Ces trois-là sont devenus
des signalements. **Résultat : 18/18 sur les invariants, aucun défaut trouvé par la couche automatique.**

### 2.8 Délai des carcasses : on suit les données, pas le document

Conflit assumé. `data/context/01-entreprise.md` dit que l'abattage est lundi et jeudi, donc qu'un veau commandé
mardi part vendredi au mieux. L'historique dit autre chose : sur 12 mois, **224** carcasses de veau et **123**
d'agneau ont été commandées un mardi pour le jeudi, et toute commande de carcasse est passée exactement 2 jours
avant.

Refuser un demi-veau mardi pour jeudi, ce serait refuser ce que l'entreprise fait chaque semaine. **On garde le
délai plat de 2 jours** sur la catégorie carcasses. Quand le veau ou l'agneau n'est pas en stock pour la date,
`check_products` le dit déjà avec le prochain arrivage.

### 2.9 Voix de synthèse : modèle changé, voix encore à trouver (lane B)

Lane A a signalé deux fois que la voix par défaut « parle français avec un rythme anglais et marque une pause
avant *kilos* ». C'est un défaut qui compte directement pour le prix « le plus naturel » et pour la démo live.
Mesures faites le 23/11 sur notre compte, même phrase française, 3 tirages, voix par défaut :

| Modèle | 1er octet (médiane) | Durée audio, texte identique |
|---|---|---|
| `eleven_flash_v2_5` *(ancien défaut)* | 163 ms | 8,18 s |
| **`eleven_v4_turbo`** *(nouveau défaut)* | **137 ms** | **7,89 s** |
| `eleven_turbo_v2_5` | 198 ms | 8,54 s |
| `eleven_multilingual_v2` | 520 ms | 7,89 s |

**Correction, faite après coup et elle nous concerne.** Nous avons d'abord écrit que `eleven_v4_turbo` gagnait
« sur les deux axes », 26 ms plus tôt et 0,3 s d'audio en moins. Les 26 ms (137 contre 163) sont **à l'intérieur
de la bande 123–160 ms que notre propre mesure sur huit voix appelle du bruit** : sur trois tirages, cet écart ne
prouve rien. Et un audio plus court veut dire qu'il parle plus vite, pas qu'il laisse moins de blancs.

**La vraie raison de garder `eleven_v4_turbo` est une oreille humaine** : le testeur de l'équipe, qui ne
comprenait pas le français de l'agent une heure plus tôt, a jugé cette voix bonne. C'est pour cela qu'elle est
gelée (§ 2.9 plus bas). Nous laissons l'erreur visible parce que c'est exactement le travers que nous reprochons
ailleurs dans ce document : lire un écart d'un seul tirage comme une preuve.

`eleven_multilingual_v2` est écarté : 3,8× plus lent au premier octet, rédhibitoire pour du téléphone.

**Changé dans le code, pas dans `.env`.** `.env` est ignoré par git et propre à chaque poste : un réglage local
n'aurait profité qu'à une machine. Le défaut est donc dans `clients/factory.py` (`DEFAULT_TTS`) et dans
`clients/elevenlabs.py`. `TTS_MODEL` dans `.env` continue de primer pour qui veut essayer autre chose.

**La voix, elle, n'est pas réglée.** La voix par défaut reste une voix *premade* multilingue, pas une voix
française native : c'est elle qui porte l'accent, pas le modèle. Deux impasses rencontrées :

- **On ne peut pas lister la bibliothèque de voix.** La clé ElevenLabs fournie n'a pas la permission
  `voices_read` (`401 missing_permissions`). Impossible de chercher une voix FR par API.
- **Les voix testables sont anglophones.** Huit voix *premade* accessibles par identifiant ont été essayées :
  toutes répondent, et **le choix de la voix ne change pas la latence** (123–160 ms, dans le bruit de mesure).
  C'est donc un choix purement auditif. Les échantillons sont générés et écoutables (même phrase, modèle
  `eleven_v4_turbo`) — il faut une oreille humaine pour trancher, pas une mesure.

**Le vrai correctif est déjà dans le kit, il manque une clé.** Le provider **Gradium** est implémenté
(`clients/gradium.py`) et son défaut est **Armand, voix phare fr-FR native**. Il lit la même variable
`TTS_API_KEY`, donc il suffirait d'une clé Gradium pour basculer :

```
TTS_PROVIDER=gradium
TTS_API_KEY=<clé Gradium>      # remplace la clé ElevenLabs
TTS_VOICE=F7Iib4MAyHIRed0x     # Armand (défaut), inutile de l'écrire
```

Aucune clé Gradium ne nous a été fournie. **C'est la demande à faire à Stockline**, et c'est la seule voie vers
une voix réellement française : les voix *premade* d'ElevenLabs resteront des voix anglophones qui parlent
français.

**🔒 Mais la voix est gelée, et pour une bonne raison.** Après le changement de modèle et le raccourcissement des
phrases parlées, le testeur de l'équipe — qui ne comprenait pas le français de l'agent une heure plus tôt — a jugé
la voix bonne. Nous ne savons pas laquelle des deux modifications a fait la différence. Tout est donc figé en
l'état (fournisseur, modèle, voix, langue, découpage du texte, phrases d'ouverture) jusqu'à la démo, **y compris
la bascule Gradium** : si la clé arrive, elle s'essaie sur une branche et le testeur l'écoute avant quoi que ce
soit. Une meilleure voix sur le papier ne vaut pas une surprise à 18 h.

### 2.10 Reconnaissance vocale : vérifiée, et le silence du dépassement corrigé

Soniox a été testé sur la page Voix, 14 phrases avec vocabulaire métier et noms de clients : **14/14 en pièce
calme**, ratés occasionnels sur « onglet » (entendu « l'anglais ») et « BL ». Conclusion : la STT n'est pas le
goulot, la liste de vocabulaire d'entreprise fait son travail.

Un défaut latent a été trouvé en même temps : la liste approche son plafond (~5 922 caractères sur 6 000) et les
termes en trop étaient **supprimés en silence**. Un produit ajouté à l'ERP pouvait donc cesser d'être reconnu sans
que personne le sache, et le symptôme ressemble à une erreur du modèle. `clients/soniox.py` journalise maintenant
le nombre de termes abandonnés (une fois par changement, pas à chaque tour).

### 2.11 Connexions gardées ouvertes : le gain le plus rentable de la nuit

**Une ligne de configuration, le pire tour passe de 4,5–8,0 s à 3,5–4,2 s.**

`clients/http.py` partage un pool de connexions entre tous les fournisseurs (Anthropic, ElevenLabs, Deepgram…).
Il était construit avec les réglages httpx par défaut — et **httpx ferme une connexion inactive au bout de
5 secondes**. Au téléphone, l'appelant parle plus de 5 secondes entre deux tours. Le pool était donc vide à
presque chaque tour, et nous repayions une poignée de main TLS complète vers Anthropic et ElevenLabs à chaque
fois. `GUIDE-VOIX.md` § 4.9 avait mesuré le côté TTS : **≈ 1,9 s à froid contre 170–370 ms à chaud**.

Le correctif est `keepalive_expiry = 600 s` sur le pool partagé. Rien d'autre ne change : si le fournisseur ferme
la connexion de son côté, httpx se reconnecte.

| | pire tour | médiane |
|---|---|---|
| Avant (6 passages complets) | 4526 – 7992 ms | 3032 – 3446 ms |
| Après (2 passages) | **3513 – 4157 ms** | **2696 – 2756 ms** |

**Les deux plages de « pire tour » ne se recouvrent pas**, ce qui est l'argument : sur six passages antérieurs,
aucun n'était descendu sous 4526 ms, et les deux passages suivants sont tous les deux en dessous. Le nombre de
jetons est inchangé au jeton près entre les deux nouveaux passages (175 402 puis 175 418 par appel) — la
modification est purement transport, elle ne change pas ce que le modèle fait.

**Ce que la mesure sous-estime, et ce qu'elle ne couvre pas.** `make calls` enchaîne les tours sans attendre ; un
vrai appel laisse l'appelant parler plusieurs secondes entre deux tours, donc la connexion y était encore plus
souvent froide : le gain réel au téléphone devrait dépasser ce tableau. Mais `make calls` passe par `POST /chat`,
**sans TTS ni STT** : ce que nous avons mesuré ici est uniquement la réutilisation de la connexion vers Anthropic.
La moitié ElevenLabs du gain est déduite de la mesure de `GUIDE-VOIX.md` § 4.9, pas mesurée par nous — les crédits
TTS sont épuisés depuis 23 h 43 et personne ne peut plus chronométrer un tour vocal complet.

**Ce correctif ne touche pas la reconnaissance vocale.** Le flux Soniox est un WebSocket séparé (`clients/ws.py`),
pas le pool httpx. Mesuré de son côté : ouverture du socket 300–950 ms, et `finalize` → mots définitifs seulement
95–375 ms — donc Soniox n'est pas le poste coûteux que nous croyions, et le reste du délai de transcription est
dans notre propre code, pas chez le fournisseur. **Pablo l'a trouvé ensuite (`4ac4348`) : nous attendions la
fermeture du socket Soniox, qui met 1,1 à 1,3 s à être acquittée, avant de rendre la transcription finale.** Le
socket se ferme maintenant en arrière-plan : fin de parole → transcription finale **1,25–1,64 s → 0,15–0,60 s**
(même enregistrement envoyé 6 fois par `WS /voice`, avant et après). Détail en § 3.2.

---

## 3. Mesures

### 3.1 Taux de réussite des scénarios

| Passage | Commit | Résultat | Ce qui a changé |
|---|---|---|---|
| 21:40 | `43573ec` | **5/6** | Référence. T3 échoue : la demande d'onglet n'est pas enregistrée comme événement client. |
| 22:02 | `99842b2` | **5/6** | Accusé de réception + pré-identification. T3 échoue toujours. |
| 22:07 | `7166485` | **3/3** sur T3 | Outils auto-vérifiants + règle d'enregistrement. T3 corrigé, confirmé sur 3 passages. |
| 22:12 | `be7eb4b` | **6/6** | Premier passage complet au vert. |
| 22:25 | `2c052d5` | **T5 ✗, T6 ✓** | Les contrôles sur la parole entrent en service. T5 échoue — voir § 5.1. |
| 22:59 | `38633a7` | **3/3** sur T5 | Garde-fou `identify_caller`. Défaut § 5.1 corrigé, confirmé sur 3 passages. |
| 23:04 | `93fc71b` | **6/6** | Tous contrôles actifs. |
| 23:29 | `8a2d158` | **6/6** | Audit lane A, gel de la voix, `make jury`. |
| 00:02 | `31400b7` | **6/6** | **Passage de référence final** : déroulé « façon comptoir » (confirmer ce qui vient de changer, une seule relecture à la fin). |

Le passage de 6/6 à T5 en échec n'est **pas une régression** : c'est un défaut présent depuis le début que les
contrôles ERP ne voyaient pas. Il a été corrigé, puis revérifié (§ 5.1).

**Le 6/6 final compte plus que le premier : il est obtenu avec davantage de contrôles.** Le 6/6 de `be7eb4b`
ne vérifiait que l'ERP. Celui de `93fc71b` passe en plus les trois contrôles sur la parole et le contrôle sur
les outils appelés — c'est-à-dire exactement les contrôles qui avaient fait tomber T5. Détail complet dans
[`SCENARIOS.md`](SCENARIOS.md) et `evals/results/`.

### 3.2 Latence

**Mode texte** (même boucle agent que la voix, sans STT ni TTS), 18 tours par passage complet. C'est la part
« modèle + outils » de ce que le client attend ; la page Voix ajoute la transcription et la synthèse par-dessus.

| Commit | Réussite | min | médiane | p90 | pire | étendue |
|---|---|---|---|---|---|---|
| `43573ec` (référence) | 5/6 | 563 ms | 3032 ms | 6811 ms | 7992 ms | 7429 ms |
| `99842b2` | 5/6 | 1182 ms | 3022 ms | 7052 ms | 7890 ms | 6708 ms |
| `be7eb4b` | 6/6 | 676 ms | 3446 ms | 4700 ms | 4709 ms | 4033 ms |
| `93fc71b` | 6/6 | 1091 ms | 2764 ms | 5517 ms | 7023 ms | 5932 ms |
| `8a2d158` | 6/6 | 591 ms | 3124 ms | **4286 ms** | **4526 ms** | **3935 ms** |
| `31400b7` | 6/6 | 605 ms | 3192 ms | 5263 ms | 6451 ms | 5846 ms |
| **`608a233` (final), passage 1** | **6/6** | 561 ms | **2756 ms** | 3777 ms | 4157 ms | 3596 ms |
| **`608a233` (final), passage 2** | **6/6** | 583 ms | **2696 ms** | **3498 ms** | **3513 ms** | **2930 ms** |

**Ce n'est pas la médiane qui a bougé, c'est la queue, et c'est ce que nous visions.** Par rapport à la référence,
le passage final garde une médiane quasi identique (3032 → 3124 ms) mais **le p90 perd 2525 ms et le pire tour
3466 ms** ; l'étendue passe de 7429 à 3935 ms. Au téléphone, ce qui fait raccrocher n'est pas le tour moyen, c'est
le tour où la ligne a l'air morte. Le pire tour de tout le passage final est à 4,5 s, contre 8,0 s au départ — et
ce avec un scénario de plus au vert et des contrôles plus stricts.

**Le pire tour est toujours un PREMIER tour d'appel.** Sur les six passages complets, sans exception, le tour le
plus lent est le tour 1 d'un scénario (T1, T3, T4 ou T5) : celui qui identifie l'appelant *et* écrit la commande,
avec le cache de prompt encore froid. Les tours suivants sont systématiquement rapides. C'est une bonne nouvelle
pour un appel téléphonique : le client n'attend longtemps qu'une seule fois, au tout début — précisément là où
l'accusé de réception parlé (§ 2.4) couvre l'attente avec un son immédiat.

**Réserve de méthode, et elle est visible dans le tableau.** Ces chiffres viennent d'**un** passage par commit et
le modèle n'est pas déterministe. `93fc71b`, `8a2d158` et `31400b7` sont du code très proche : la médiane y va de
2764 à 3192 ms et le pire tour de 4526 à 7023 ms. **Cet écart est du bruit de tirage, pas un effet du code.**
La médiane sur 18 tours est raisonnablement robuste ; le « pire tour » est un seul tour et doit se lire comme un
ordre de grandeur. Donner un intervalle demanderait `--repeat 3`, que nous n'avons pas eu le temps de passer sur
chaque commit.

**Mode vocal** (page Voix, fin de parole → premier son, premier tour Peyronnet) :

| Étape | Premier son |
|---|---|
| Kit de départ | 8,7 s |
| Après le filler avant outils | 5,0 s |
| Après l'accusé de réception parlé | 3,6 s |
| Mesure lane C sur `WS /voice` (tours tapés, mesuré côté serveur, sans STT) | **0,09 à 0,61 s** jusqu'au premier son sur une demande |

L'accusé de réception immédiat est ce qui transforme l'expérience : le client entend une voix tout de suite, puis
la vraie réponse arrive. Les 2 à 5 s restantes sont le temps du modèle, pas du silence perçu.

**Après un « oui », l'agent ne se tait plus.** Une mesure plus ancienne donnait 2,5 à 3,5 s de silence volontaire
sur ce tour. Depuis `401765f`, un « oui » reçoit « Très bien. » tout de suite, et depuis `7b72a6c` « c'est tout » et
« oui, valide, au revoir » aussi. Ce tour n'a pas été rechronométré depuis.

**Reconnaissance vocale : une seconde gagnée à chaque tour, sans toucher au modèle** (lane B, `4ac4348`) :

| Même enregistrement envoyé par `WS /voice` (6 fois) | Fin de parole → transcription finale |
|---|---|
| Avant | 1 250 – 1 640 ms |
| **Après** | **146 – 595 ms** |

La cause n'était ni Soniox ni la liste de vocabulaire (vérifié avec et sans, et avec un audio coupé net sur le
dernier mot) : `clients/ws.py` attendait la fermeture du socket, que Soniox met 1,1 à 1,3 s à acquitter, avant de
rendre le texte. Le socket se ferme maintenant en arrière-plan. Le gain est mesuré avec un audio enregistré
passé par notre vrai socket, **pas encore avec un micro de navigateur** : un appel parlé sur la page Voix doit le
confirmer.

**Dernier passage complet** (`dbcc191`, mode texte, sans STT ni TTS, machine de Pablo) : T1–T6 **6/6**, premier mot
médiane **2,9 s**, p90 3,9 s, **pire 6,4 s** ; appels jury **18/18** sur les invariants, médiane 2,6 s. Ce pire tour
est au-dessus de la plage de `608a233` : c'est un seul passage, sur une autre machine (§ 5.3), à lire comme du
bruit de tirage tant qu'un second passage ne le confirme pas.

### 3.3 Coût

Mesuré sur un passage complet des six scénarios, 18 tours :

| Commit | Entrée / appel | dont lu en cache | Entrée **non** cachée / appel | Taux de cache |
|---|---|---|---|---|
| `43573ec` (référence) | 207 505 | 182 610 | 24 896 | 88,0 % |
| `be7eb4b` | **165 788** | 139 234 | 26 554 | 84,0 % |
| `93fc71b` | 181 476 | 158 694 | **22 782** | 87,4 % |
| **`8a2d158` (final)** | 177 422 | 150 938 | 26 484 | 85,1 % |

**Par appel réussi** (passage final, 6 appels) : ~177 400 jetons d'entrée, dont ~150 900 lus en cache et
**~26 500 réellement facturés au plein tarif d'entrée**, plus ~610 jetons de sortie.

Soit **−14 % de jetons d'entrée par appel** par rapport à la référence, en ayant ajouté des fonctionnalités et des
garde-fous. Le gain vient de la suppression de l'étape `check_products` avant chaque écriture (§ 2.2), pas d'un
élagage de prompt.

Honnêtement : `be7eb4b` reste le passage le moins cher (165 800 par appel). L'audit de sécurité ajouté ensuite
coûte des appels d'outils supplémentaires sur certains tours. Nous gardons l'arbitrage : un appel 7 % plus cher
vaut mieux qu'un appel qui ouvre la fiche du mauvais client.

**Le cache de prompt fait l'essentiel du travail : 84 à 88 % de l'entrée est servie depuis le cache.** C'est la
raison pour laquelle un prompt système volumineux et une liste d'outils stable sont un bon investissement ici : ils
sont écrits une fois par appel et relus à prix réduit à chaque tour. Nous n'avons donc **pas** cherché à raccourcir
le prompt système, contrairement à notre intuition de départ.

### Coût en argent

Nous avions d'abord refusé de convertir en dollars faute de grille vérifiable. Pablo a trouvé la page de tarifs
d'Anthropic : **Sonnet 5.5, $2 /M en entrée, $0,10 /M pour une lecture de cache, $2,50 /M pour une écriture de
cache, $10 /M en sortie** (prix publics catalogue, en USD ; la clé fournie par Stockline peut être facturée
autrement). Pour la voix, ElevenLabs v4 Turbo est à $0,04 pour 1 000 caractères.

Appliqué à nos deux passages finaux, **par appel réussi** :

| | lectures de cache | entrée non cachée | sortie | **modèle** |
|---|---|---|---|---|
| Passage 1 | 147 268 | 28 133 | 543 | **$0,076 – 0,090** |
| Passage 2 | 171 288 | 4 130 | 555 | **$0,031 – 0,033** |

La fourchette vient de ce que notre instrumentation ne sépare pas une *écriture* de cache ($2,50) d'une entrée
fraîche ($2) : nous donnons les deux bornes plutôt que d'en choisir une.

**L'écart entre les deux passages est le chiffre intéressant, et il n'est pas du bruit.** Le second passage a
tourné une minute et demie après le premier et a réutilisé son cache : 4 130 jetons non cachés au lieu de 28 133,
soit **moitié moins cher**. Autrement dit, le coût d'un appel dépend surtout de la *fraîcheur du cache*, pas de la
longueur de l'appel. Dans un vrai standard téléphonique, où les appels s'enchaînent, on serait près du passage 2 ;
le premier appel de la journée coûte le double.

**Avec la voix** : +$0,02 à $0,06 par appel (500 à 1 500 caractères parlés, estimation d'après les tours mesurés
par Jed). La reconnaissance vocale (Soniox) coûte **moins de $0,005** par appel. Soit **$0,05 à $0,15 l'appel
complet**, de la reconnaissance à la réponse parlée : **≈ $0,10 à 0,15 avec un cache froid** (modèle $0,074–0,087,
voix $0,02–0,06, STT < $0,005), autour de $0,05 quand les appels s'enchaînent. **Le premier poste est le modèle,
puis la voix.** Les caractères parlés par appel sont une estimation (500 à 1 500), et ce sont les prix catalogue en USD.

---

## 4. Ce qui a marché

- **Écrire les six scénarios avant d'optimiser.** Dès la 2ᵉ heure, chaque changement se jugeait en une commande au
  lieu d'une discussion. C'est ce qui a rendu possible 5 passages mesurés en une soirée.
- **Déplacer les règles du prompt vers les outils** (§ 2.2) : plus rapide, moins cher, et surtout plus fiable — une
  règle dans le code ne s'oublie pas.
- **Optimiser la queue de latence plutôt que la médiane.** Contre-intuitif sur un tableau de chiffres, évident au
  téléphone.
- **L'accusé de réception choisi par du code.** Sur une demande, le premier son tombe à **0,09–0,61 s** contre
  8,7 s au départ. Aucun risque d'invention puisque le modèle n'écrit pas cette phrase. À nuancer : sur une phrase
  courte (« Oui. ») le transcript en direct est trop court pour choisir le mot, qui part alors avec le transcript
  final — 1,2 à 1,7 s. Ce transcript final arrive maintenant ~1 s plus tôt (`4ac4348`, § 3.2), donc ce cas devrait
  gagner autant ; pas encore re-mesuré à la voix.
- **Tester les contrôles eux-mêmes** (`make calls-test`). Nous a évité au moins un contrôle qui passait au vert
  pour une mauvaise raison.
- **Un journal de passation partagé** (`HANDOFF.md`) entre quatre sessions d'agents de code sur quatre lanes. Tous
  les conflits de la nuit ont été sur ce fichier, jamais sur le code : le découpage par lane a tenu.

## 5. Ce qui n'a pas marché

### 5.1 `identify_caller` ouvrait la fiche d'un autre client — trouvé par nos contrôles, corrigé, vérifié

Le défaut le plus sérieux de la nuit. Nous le laissons raconté en entier : c'est la meilleure preuve que le
harnais sert à quelque chose, puisque aucun contrôle ERP ne pouvait le voir.

En T5, l'appelant (compte bloqué) dit : *« Allez, un seul quartier, tu vas pas me laisser sans viande pour le
week-end ! »* L'agent a fabriqué un nom de client à partir du mot « viande », appelé
`identify_caller("Le Comptoir de la Viande")`, et **ouvert la fiche d'un client sans rapport** (`cli_0038`).

- **Reproduit 2 fois sur 2.**
- La première fois, il l'a dit à l'appelant (« Pardon, je viens d'ouvrir une fiche qui n'était pas la vôtre »).
  La seconde fois, **il n'a rien dit** : la réponse était parfaitement correcte.
- Aucune écriture, donc **tous les contrôles ERP passaient au vert**. Les contrôles sur la parole ne le voient pas
  non plus quand le modèle n'en parle pas. Seul le contrôle au niveau des outils l'attrape.
- Le risque est réel : `identify_caller` renvoie contacts, téléphones, plafond, encours et échu. C'est la donnée
  commerciale d'un autre client, chargée pendant l'appel d'un client en impayé.

**Corrigé** (`a85646c`, « identification sans devinette ») : l'agent n'a plus le droit de ré-identifier un
appelant déjà connu à partir d'une supposition textuelle.

**Vérifié, pas supposé** — `make calls ARGS="T5 --repeat 3"` sur `38633a7` :

| | avant (`be7eb4b`, `2c052d5`) | après (`38633a7`) |
|---|---|---|
| Fiches d'un autre client ouvertes | **2 sur 2 passages** | **0 sur 3 passages** (9 tours) |
| Outils au tour 2 (la phrase piège) | `identify_caller("Le Comptoir de la Viande")` | **aucun outil** |
| T5 | ✗ | **✓ 3/3** |

Au tour 1, `identify_caller` est appelé une fois avec le vrai nom et rend bien `cli_0005` ; les tours suivants
n'appellent plus rien. Effet de bord mesuré : T5 descend à **118 300 jetons par appel** (contre ~165 800) et
**1139 ms** de médiane au premier mot, parce que deux tours sur trois n'appellent plus aucun outil.

**Ce que nous en retenons** : le contrôle qui a attrapé ce défaut n'est pas un contrôle ERP ni un contrôle sur les
mots, c'est un contrôle sur **les outils appelés**. Un agent peut faire quelque chose de grave sans rien écrire et
sans rien dire.

### 5.2 Ce que nous avons essayé et abandonné

| Essayé | Pourquoi abandonné |
|---|---|
| Haiku comme modèle par défaut | Plus rapide, mais a affirmé une disponibilité fausse sans appeler d'outil (§ 2.6). Repoussé, pas écarté. |
| « D'accord. » comme accusé de réception | Avant un refus, s'entend comme un accord. Remplacé par des formules neutres. |
| Faire vérifier le stock par le modèle avant d'écrire | Une étape modèle de plus par tour, et une règle que le modèle pouvait sauter. Déplacé dans les outils. |
| Raccourcir le prompt système pour réduire le coût | Mauvaise cible : 84–88 % de l'entrée est lue en cache. Le gain réel était dans le nombre d'étapes modèle. |
| La voix ElevenLabs par défaut | Rythme anglais sur du français, pause avant « kilos ». Le **modèle** est corrigé (§ 2.9) ; la **voix** reste anglophone, et la clé fournie ne peut pas lister la bibliothèque. Correctif connu : une clé Gradium. |

### 5.3 Limites connues de nos mesures

- `make calls` passe par `POST /chat`, pas par `WS /voice`. L'accusé de réception parlé vit dans la session vocale :
  **le harnais ne peut pas le mesurer.** Les gains voix ont été relevés à la main sur la page Voix. Nous l'avons
  découvert en voyant une médiane qui ne bougeait pas alors que l'oreille entendait une grosse différence.
- Les montants sont cherchés en chiffres : un agent qui épellerait « cent vingt-neuf mille » passerait au travers.
- Les latences sont mesurées sur des machines différentes selon la lane. Les **formes** de distribution sont
  comparables, pas les valeurs absolues.
- Le modèle n'est pas déterministe. Un passage unique ne prouve pas une amélioration de latence : nous avons utilisé
  `--repeat` pour les affirmations qui comptent (T3 corrigé : 3/3).

---

## 6. État à l'heure du gel

| | |
|---|---|
| Scénarios | **6/6 sur `608a233`**, deux passages, tous contrôles actifs (ERP + parole + outils appelés) · **18/18** sur les invariants des appels jury |
| Latence texte | médiane **2696–2756 ms**, p90 3498–3777 ms, **pire 3513–4157 ms** (2 × 18 tours) — pire tour 8,0 s → 3,5 s depuis la référence |
| Latence voix | **0,09 à 0,61 s** jusqu'au premier son sur une demande (8,7 s au départ) ; 1,2 à 1,7 s sur une phrase courte (avant `4ac4348`, devrait gagner ~1 s, non re-mesuré) ; « Très bien. » tout de suite après un « oui » ; STT fin de parole → transcription finale **0,15–0,60 s** (1,25–1,64 s avant `4ac4348`) |
| Coût | ~175 400 jetons d'entrée par appel, dont ~26 000 hors cache · **≈ $0,10–0,15 l'appel complet** (cache froid), ~$0,05 quand les appels s'enchaînent |
| Modèle | `claude-sonnet-5-5` ; Haiku ré-évaluable maintenant que les contrôles existent |
| Voix | `eleven_v4_turbo` (137 ms au 1er octet) ; voix encore anglophone, bloqué sur une clé Gradium — § 2.9 |
| Données | figées au **mardi 24/11/2026, 05:00** (`meta.today`) |

**Ce que nous ferions avec deux heures de plus, dans l'ordre :** demander une clé Gradium pour une vraie voix
française (§ 2.9), re-mesurer Haiku avec les nouveaux contrôles, rejouer T1–T6 en `--repeat 3` pour donner un
intervalle plutôt qu'un point sur la latence, puis le ticket de pesée.
