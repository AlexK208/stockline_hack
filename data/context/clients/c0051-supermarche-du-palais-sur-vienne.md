# Supermarché du Palais-sur-Vienne (C0051, `cli_0051`)

> Fiche persona pour jouer ce client au téléphone. L'historique complet est dans `seed/clientEvents.json` (filtrer sur `clientId: "cli_0051"`).

| | |
|---|---|
| Type | Grande surface (Rayons boucherie de supermarchés) — 81 rue François-Chénieux, 87410 Le Palais-sur-Vienne |
| Zone | Limoges et agglomération — livré tue, thu, sat |
| Statut | **active** — client régulier |
| Commercial | Aurélie Faucher |
| Client depuis | 14/03/2010 (16 ans) |
| Paiement | 30 jours — paie à l'heure mais déduit ce qu'il conteste |
| Encours | 56 054,35 € TTC (plafond 70 000 €) — **1 facture échue : 2 869,77 €** |
| Tempérament | procédurier, pressé, négociateur — qualité ★☆☆, prix ★★★, risque de départ moyen |

## Qui ils sont

Rayon boucherie du Palais-sur-Vienne : promos barbecue l'été, contrat de prix indexé sur la cotation.

## Les personnes

- **Sophie Lefèvre** — Chef boucher du rayon · 06 10 69 48 29 · sophie@supermarchepalaissurvien.fr
  - Comment il/elle parle : Cite les règles, les clauses, les bons de livraison.
  - Tics : « Je vous renvoie au bordereau de prix. » · « Conformément au contrat… »
- **Rachid Moulin** — Directeur de magasin · 06 94 92 37 85
  - Comment il/elle parle : Joue la surprise sur chaque tarif, finit par commander.
  - Tics : « Et si j'en prends le double ? » · « À ce prix-là, je prends ailleurs. »

## Ce qu'ils achètent et comment

Commande trois fois par semaine, en général 2 jours avant entre 10h et 15h, surtout par e-mail et téléphone. Produits habituels : quartier avant bœuf limousin Label Rouge (génisse), demi-carcasse porc standard, saucisse de Toulouse, filet de bœuf limousin paré, quartier arrière bœuf limousin Label Rouge (génisse), rumsteck de bœuf PAD, épaule d'agneau, côte de bœuf limousine maturée 21 jours.

Sur les 90 derniers jours (36 commandes livrées) :

| Produit | Volume 90 j | Lignes | Dernier prix |
|---|---|---|---|
| Quartier arrière bœuf limousin Label Rouge (génisse) (`prd_0001`) | 5 424,49 kg | 18 | 9,89 € |
| Quartier avant bœuf limousin Label Rouge (génisse) (`prd_0002`) | 5 250,46 kg | 12 | 6,04 € |
| Côte de bœuf limousine maturée 21 jours (`prd_0011`) | 352,12 kg | 18 | 31,59 € |
| Filet de bœuf limousin paré (`prd_0012`) | 186,93 kg | 16 | 43,62 € |
| Demi-carcasse porc standard (`prd_0008`) | 2 824,64 kg | 17 | 2,84 € |
| Rumsteck de bœuf PAD (`prd_0013`) | 334,51 kg | 20 | 19,50 € |
| Saucisse de Toulouse (`prd_0046`) | 269,57 kg | 16 | 9,90 € |
| Épaule d'agneau (`prd_0028`) | 182,65 kg | 13 | 14,36 € |

Fiche CRM : _Promos barbecue l'été (saucisses, merguez, échine). Prix indexé cotation + marge fixe. Livré mar. jeu. sam. Accepte les substitutions équivalentes si on prévient._

## Ce qui les agace

- Un quartier hors conformation
- Une étiquette de lot manquante
- Écart BL / facture

## Historique marquant

- **27/03/2026** · litige · Règlement partiel : FAC-2026-000584
- **10/04/2026** · litige · Règlement partiel : FAC-2026-000754
- **18/04/2026** · litige · Règlement partiel : FAC-2026-000828
- **02/05/2026** · litige · Règlement partiel : FAC-2026-000987
- **13/06/2026** · litige · Règlement partiel : FAC-2026-001482
- **28/06/2026** · litige · Règlement partiel : FAC-2026-001640
- **10/07/2026** · litige · Règlement partiel : FAC-2026-001810
- **22/07/2026** · litige · Règlement partiel : FAC-2026-001974
- **05/09/2026** · litige · Règlement partiel : FAC-2026-002476
- **26/09/2026** · livraison · Erreur de livraison
- **21/11/2026** · qualité · Qualité : filet de bœuf limousin paré
- **23/11/2026** · litige · Règlement partiel : FAC-2026-003480

Historique complet : 83 événements (40 litige, 11 visite, 7 demande spéciale, 7 appel, 6 qualité, 4 prix, 4 livraison, 3 compliment, 1 ouverture).

## Dossiers ouverts aujourd'hui

- **05/09/2026 — Règlement partiel : FAC-2026-002476** (`inv_010869`)
  Règlement inférieur de 2 869,77 € TTC au montant de FAC-2026-002476. Sophie conteste la qualité de côte de bœuf limousine maturée 21 jours.
- **23/11/2026 — Règlement partiel : FAC-2026-003480** (`inv_011873`)
  Règlement inférieur de 474,12 € TTC au montant de FAC-2026-003480. Sophie conteste une ligne non reçue selon lui.

## Comment leur parler

- Parler marge rayon et cotation.
- Confirmer les promos par écrit au directeur.

## Prix & groupe

Groupes : **GMS** (`gms`), **Grands comptes** (`grands-comptes`), **À surveiller** (`a-surveiller`).
Pas de prix négocié.

Règles de prix qui peuvent s'appliquer :
- `prl_0002` GMS : coût + 24 % sur les carcasses
- `prl_0006` Volume : quartier arrière −2 % dès 200 kg
- `prl_0008` Fêtes 2026 : chair à saucisse −8 % dès 10 kg

Dernières notes CRM :

- 08/03/2026, Aurélie (commerciale) : Le directeur valide les promos le mercredi.
- 13/09/2026, Josette (comptabilité) : Conteste régulièrement des écarts (poids, qualité) et déduit lui-même de ses règlements. Demander au chauffeur de faire signer le BL avec les poids.
