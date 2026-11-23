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

Il est **neutre volontairement** (« Alors… », « Voyons… », ou « Bonjour Christian. » au premier tour). On a essayé
« D'accord. » : avant un refus, ça s'entend comme un oui. C'est une erreur qu'on ne pouvait pas voir dans l'ERP,
seulement à l'oreille.

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

`eleven_v4_turbo` gagne **sur les deux axes** : il commence à parler 26 ms plus tôt et dit le même texte en 0,3 s
de moins — donc moins de blancs, ce qui correspond à ce qu'Alexander entendait. Le commentaire du kit annonçait
« same latency, more expressive » : c'était vrai, et même un peu mieux que ça.

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

### 2.10 Reconnaissance vocale : vérifiée, et le silence du dépassement corrigé

Soniox a été testé sur la page Voix, 14 phrases avec vocabulaire métier et noms de clients : **14/14 en pièce
calme**, ratés occasionnels sur « onglet » (entendu « l'anglais ») et « BL ». Conclusion : la STT n'est pas le
goulot, la liste de vocabulaire d'entreprise fait son travail.

Un défaut latent a été trouvé en même temps : la liste approche son plafond (~5 922 caractères sur 6 000) et les
termes en trop étaient **supprimés en silence**. Un produit ajouté à l'ERP pouvait donc cesser d'être reconnu sans
que personne le sache, et le symptôme ressemble à une erreur du modèle. `clients/soniox.py` journalise maintenant
le nombre de termes abandonnés (une fois par changement, pas à chaque tour).

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

Le passage de 6/6 à T5 en échec n'est **pas une régression** : c'est un défaut présent depuis le début que les
contrôles ERP ne voyaient pas. Détail complet dans [`SCENARIOS.md`](SCENARIOS.md) et `evals/results/`.

### 3.2 Latence

**Mode texte** (même boucle agent que la voix, sans STT ni TTS), 18 tours par passage complet. C'est la part
« modèle + outils » de ce que le client attend ; la page Voix ajoute la transcription et la synthèse par-dessus.

| Commit | min | médiane | p90 | pire | étendue |
|---|---|---|---|---|---|
| `43573ec` (référence) | 563 ms | 3032 ms | 6811 ms | 7992 ms | 7429 ms |
| `99842b2` | 1182 ms | 3022 ms | 7052 ms | 7890 ms | 6708 ms |
| `be7eb4b` | 676 ms | **3445 ms** | **4700 ms** | **4709 ms** | **4033 ms** |

**La médiane a empiré de ~400 ms, et c'est quand même un gain.** Ce qui fait raccrocher un client au téléphone,
ce n'est pas le tour moyen, c'est le tour où la ligne a l'air morte : le p90 perd 2352 ms et le pire tour 3181 ms.
L'étendue est presque divisée par deux. On a optimisé la queue de distribution, pas le centre, et c'est délibéré.

**Mode vocal** (page Voix, fin de parole → premier son, premier tour Peyronnet) :

| Étape | Premier son |
|---|---|
| Kit de départ | 8,7 s |
| Après le filler avant outils | 5,0 s |
| Après l'accusé de réception parlé | 3,6 s |
| Mesure lane C sur `WS /voice`, T1 | **0,09 s** (premier mot), 5,4 s pour le tour complet |

L'accusé de réception immédiat est ce qui transforme l'expérience : le client entend une voix tout de suite, puis
la vraie réponse arrive. Les 2 à 5 s restantes sont le temps du modèle, pas du silence perçu.

### 3.3 Coût

Mesuré sur un passage complet des six scénarios, 18 tours :

| Commit | Entrée totale | dont lu en cache | Entrée **non** cachée | Sortie | Taux de cache |
|---|---|---|---|---|---|
| `43573ec` (référence) | 1 245 032 | 1 095 659 | 149 373 | 4 621 | 88,0 % |
| `be7eb4b` | **994 729** | 835 406 | **159 323** | 4 086 | 84,0 % |

**Par appel réussi** (`be7eb4b`, 6 appels) : ~165 800 jetons d'entrée, dont ~139 200 lus en cache et **~26 550
réellement facturés au plein tarif d'entrée**, plus ~680 jetons de sortie.

Soit **−20 % de jetons d'entrée par appel** par rapport à la référence, en ayant *ajouté* des fonctionnalités. Le
gain vient de la suppression de l'étape `check_products` avant chaque écriture (§ 2.2), pas d'un élagage de prompt.

**Le cache de prompt fait l'essentiel du travail : 84 à 88 % de l'entrée est servie depuis le cache.** C'est la
raison pour laquelle un prompt système volumineux et une liste d'outils stable sont un bon investissement ici : ils
sont écrits une fois par appel et relus à prix réduit à chaque tour. Nous n'avons donc **pas** cherché à raccourcir
le prompt système, contrairement à notre intuition de départ.

> **Honnêteté sur l'euro.** Nous donnons le coût en **jetons**, parce que c'est ce que nous avons mesuré. Les
> identifiants provisionnés par le kit (`claude-sonnet-5-5`, `claude-haiku-5-5`) ne figurent pas sur une grille
> tarifaire publique que nous ayons pu vérifier pendant le hackathon, et les lectures de cache sont facturées à un
> tarif réduit distinct. Convertir en euros demanderait d'inventer deux chiffres : nous ne l'avons pas fait. Les
> jetons ci-dessus sont comparables entre équipes ; la conversion est une multiplication que le jury peut appliquer
> avec la vraie grille.

---

## 4. Ce qui a marché

- **Écrire les six scénarios avant d'optimiser.** Dès la 2ᵉ heure, chaque changement se jugeait en une commande au
  lieu d'une discussion. C'est ce qui a rendu possible 5 passages mesurés en une soirée.
- **Déplacer les règles du prompt vers les outils** (§ 2.2) : plus rapide, moins cher, et surtout plus fiable — une
  règle dans le code ne s'oublie pas.
- **Optimiser la queue de latence plutôt que la médiane.** Contre-intuitif sur un tableau de chiffres, évident au
  téléphone.
- **L'accusé de réception choisi par du code.** 8,7 s → 0,09 s de premier son. Aucun risque d'invention puisque le
  modèle n'écrit pas cette phrase.
- **Tester les contrôles eux-mêmes** (`make calls-test`). Nous a évité au moins un contrôle qui passait au vert
  pour une mauvaise raison.
- **Un journal de passation partagé** (`HANDOFF.md`) entre quatre sessions d'agents de code sur quatre lanes. Tous
  les conflits de la nuit ont été sur ce fichier, jamais sur le code : le découpage par lane a tenu.

## 5. Ce qui n'a pas marché

### 5.1 `identify_caller` ouvre la fiche d'un autre client — non corrigé

Le défaut le plus sérieux que nous ayons trouvé, et nous le laissons visible plutôt que de le cacher.

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

**Correctif proposé, non appliqué faute de temps avant le gel** : une fois l'appelant identifié dans la session,
`identify_caller` ne doit pas pouvoir basculer sur un autre client sur une simple supposition textuelle — soit il
refuse, soit il demande une confirmation explicite.

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
| Scénarios | 6/6 sur `be7eb4b` ; T5 en échec depuis `2c052d5` à cause du défaut § 5.1, détecté et non corrigé |
| Latence texte | médiane 3445 ms, p90 4700 ms, pire 4709 ms |
| Latence voix | 0,09 s jusqu'au premier son, 8,7 s au départ |
| Coût | ~165 800 jetons d'entrée par appel, dont ~26 550 hors cache |
| Modèle | `claude-sonnet-5-5` ; Haiku ré-évaluable maintenant que les contrôles existent |
| Voix | `eleven_v4_turbo` (137 ms au 1er octet) ; voix encore anglophone, bloqué sur une clé Gradium — § 2.9 |
| Données | figées au **mardi 24/11/2026, 05:00** (`meta.today`) |

**Ce que nous ferions avec deux heures de plus, dans l'ordre :** le garde-fou de `identify_caller` (§ 5.1),
demander une clé Gradium pour une vraie voix française (§ 2.9), re-mesurer Haiku avec les nouveaux contrôles,
puis le ticket de pesée.
