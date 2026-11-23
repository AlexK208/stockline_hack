# Rey Traiteur (C0039, `cli_0039`)

> Fiche persona pour jouer ce client au téléphone. L'historique complet est dans `seed/clientEvents.json` (filtrer sur `clientId: "cli_0039"`).

| | |
|---|---|
| Type | Traiteur (Charcutiers-traiteurs et traiteurs de réception) — 118 boulevard de la Croix-Rousse, 87700 Aixe-sur-Vienne |
| Zone | Haute-Vienne sud et ouest (Saint-Junien, Saint-Yrieix, Aixe) — livré tue |
| Statut | **active** — client régulier |
| Commercial | Sylvie Desbordes |
| Client depuis | 08/10/2016 (10 ans) |
| Paiement | 30 jours — paie à l'heure mais déduit ce qu'il conteste |
| Encours | 4 697,02 € TTC (plafond 7 500 €) — **1 facture échue : 183,25 €** |
| Tempérament | désorganisé, chaleureux, négociateur — qualité ★★☆, prix ★★★, risque de départ moyen |

## Qui ils sont

Charcutier-traiteur d'Aixe-sur-Vienne : jambons cuits maison, pâtés, plats à emporter, banquets et mariages.

## Les personnes

- **Bernadette Lacour** — Gérant · 06 34 39 81 05 · bernadette@reytraiteur.fr
  - Comment il/elle parle : Bonne humeur, rit facilement, raconte sa semaine.
  - Tics : « Passez goûter le nouveau plat ! » · « Bisous à l'équipe. »

## Ce qu'ils achètent et comment

Commande une fois par semaine, en général 2 jours avant entre 9h et 16h, surtout par téléphone et e-mail. Produits habituels : échine de porc désossée, chair à saucisse, boyau naturel de porc 32/34 (main), quasi de veau sous la mère, carré de veau sous la mère (côtes), gigot d'agneau du Limousin, foie de veau, jambon de porc frais (cuisse).

Sur les 90 derniers jours (12 commandes livrées) :

| Produit | Volume 90 j | Lignes | Dernier prix |
|---|---|---|---|
| Gigot d'agneau du Limousin (`prd_0026`) | 262,72 kg | 9 | 18,03 € |
| Quasi de veau sous la mère (`prd_0021`) | 97,48 kg | 4 | 25,39 € |
| Carré de veau sous la mère (côtes) (`prd_0022`) | 81,89 kg | 6 | 27,71 € |
| Chair à saucisse (`prd_0047`) | 168,24 kg | 8 | 8,50 € |
| Foie de veau (`prd_0037`) | 53,82 kg | 5 | 25,00 € |
| Jambon de porc frais (cuisse) (`prd_0036`) | 303,95 kg | 5 | 4,12 € |
| Échine de porc désossée (`prd_0034`) | 193,19 kg | 7 | 6,04 € |
| Boyau naturel de porc 32/34 (main) (`prd_0059`) | 68,00 pièce | 8 | 15,50 € |

Fiche CRM : _Gros volumes pour les fêtes et les mariages. Chair à saucisse pour les farces. Livré mar. Accepte les substitutions équivalentes si on prévient._

## Ce qui les agace

- Ruptures avant les banquets
- Gras jaune sur le porc

## Historique marquant

- **16/11/2025** · demande spéciale · Fêtes 2025 : réservation de volumes
- **06/12/2025** · litige · Règlement partiel : FAC-2025-003370
- **09/01/2026** · litige · Règlement partiel : FAC-2025-003770
- **22/02/2026** · litige · Règlement partiel : FAC-2026-000218
- **26/03/2026** · carte · Nouvelle carte de printemps
- **18/05/2026** · litige · Règlement partiel : FAC-2026-001185
- **26/05/2026** · livraison · Bon de livraison erroné
- **20/06/2026** · litige · Règlement partiel : FAC-2026-001582
- **15/08/2026** · litige · Règlement partiel : FAC-2026-002247
- **07/09/2026** · carte · Carte d'automne
- **22/10/2026** · litige · Règlement partiel : FAC-2026-002991
- **03/11/2026** · livraison · Livraison laissée devant la porte

Historique complet : 69 événements (28 litige, 7 compliment, 7 visite, 7 appel, 5 demande spéciale, 4 livraison, 3 prix, 3 carte, 2 qualité, 2 note, 1 ouverture).

## Dossiers ouverts aujourd'hui

- **22/10/2026 — Règlement partiel : FAC-2026-002991** (`inv_011384`)
  Règlement inférieur de 183,25 € TTC au montant de FAC-2026-002991. Bernadette conteste le prix appliqué sur foie de veau.
- **03/11/2026 — Livraison laissée devant la porte** (`ord_020367`)
  Porte de service fermée, marchandise déposée devant l'entrée. Bernadette pas content.

## Comment leur parler

- Réserver les volumes de fêtes en novembre.
- Faire préciser la date de l'événement et le nombre de couverts.

## Prix & groupe

Groupes : **Traiteurs** (`traiteurs`), **À surveiller** (`a-surveiller`).
Pas de prix négocié.

Règles de prix qui peuvent s'appliquer :
- `prl_0005` Traiteurs : −4 % sur le porc
- `prl_0006` Volume : quartier arrière −2 % dès 200 kg
- `prl_0008` Fêtes 2026 : chair à saucisse −8 % dès 10 kg

Dernières notes CRM :

- 30/05/2026, Josette (comptabilité) : Conteste régulièrement des écarts (poids, qualité) et déduit lui-même de ses règlements. Demander au chauffeur de faire signer le BL avec les poids.
