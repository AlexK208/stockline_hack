# Les Halles Gourmandes de Saint-Léonard-de-Noblat (C0078, `cli_0078`)

> Fiche persona pour jouer ce client au téléphone. L'historique complet est dans `seed/clientEvents.json` (filtrer sur `clientId: "cli_0078"`).

| | |
|---|---|
| Type | Grande surface (Rayons boucherie de supermarchés) — 45 rue Jean-Moulin, 87400 Saint-Léonard-de-Noblat |
| Zone | Haute-Vienne sud et ouest (Saint-Junien, Saint-Yrieix, Aixe) — livré tue, wed, fri |
| Statut | **active** — client régulier |
| Commercial | Nicolas Bouty |
| Client depuis | 26/06/2015 (11 ans) |
| Paiement | 45 jours — paie à l'heure mais déduit ce qu'il conteste |
| Encours | 110 715,25 € TTC (plafond 165 000 €) — **1 facture échue : 2 179,01 €** |
| Tempérament | procédurier, pressé, négociateur — qualité ★★☆, prix ★★★, risque de départ moyen |

## Qui ils sont

Rayon boucherie de Saint-Léonard-de-Noblat : promos barbecue l'été, contrat de prix indexé sur la cotation.

## Les personnes

- **Clémence Richard** — Chef boucher du rayon · 06 55 65 37 47
  - Comment il/elle parle : Phrases courtes, pas le temps, veut un récapitulatif en dix secondes.
  - Tics : « Envoyez, envoyez. » · « Pareil que d'hab, go. »

## Ce qu'ils achètent et comment

Commande trois fois par semaine, en général 2 jours avant entre 9h et 15h, surtout par e-mail et téléphone. Produits habituels : quartier arrière bœuf limousin Label Rouge (génisse), quartier avant bœuf limousin Label Rouge (génisse), demi-carcasse porc standard, viande hachée fraîche 15 % MG, saucisse de Toulouse, filet mignon de porc, agneau du Limousin IGP (carcasse entière), paleron de bœuf PAD.

Sur les 90 derniers jours (34 commandes livrées) :

| Produit | Volume 90 j | Lignes | Dernier prix |
|---|---|---|---|
| Quartier arrière bœuf limousin Label Rouge (génisse) (`prd_0001`) | 8 069,27 kg | 17 | 9,89 € |
| Quartier avant bœuf limousin Label Rouge (génisse) (`prd_0002`) | 11 030,06 kg | 15 | 6,04 € |
| Agneau du Limousin IGP (carcasse entière) (`prd_0006`) | 1 460,28 kg | 9 | 12,46 € |
| Paleron de bœuf PAD (`prd_0017`) | 859,60 kg | 20 | 11,53 € |
| Tende de tranche PAD (`prd_0016`) | 592,43 kg | 17 | 15,16 € |
| Bavette d'aloyau PAD (`prd_0014`) | 429,91 kg | 15 | 17,76 € |
| Saucisse de Toulouse (`prd_0046`) | 695,03 kg | 18 | 9,90 € |
| Demi-carcasse porc standard (`prd_0008`) | 2 265,16 kg | 10 | 2,89 € |

Fiche CRM : _Étiquetage origine et race obligatoire. Prix indexé cotation + marge fixe. Livré mar. mer. ven. Refuse les substitutions : appeler avant toute modification._

## Ce qui les agace

- Un quartier hors conformation
- Écart BL / facture
- Une étiquette de lot manquante

## Historique marquant

- **13/02/2026** · livraison · Livraison laissée devant la porte
- **27/02/2026** · réclamation · Rupture : noix de veau sous la mère PAD non livré
- **09/04/2026** · litige · Règlement partiel : FAC-2026-000595
- **20/04/2026** · litige · Règlement partiel : FAC-2026-000685
- **03/05/2026** · litige · Règlement partiel : FAC-2026-000840
- **18/06/2026** · litige · Règlement partiel : FAC-2026-001418
- **02/08/2026** · litige · Règlement partiel : FAC-2026-001905
- **14/09/2026** · litige · Règlement partiel : FAC-2026-002394
- **03/10/2026** · litige · Règlement partiel : FAC-2026-002612
- **23/11/2026** · litige · Règlement partiel : FAC-2026-003314
- **23/11/2026** · litige · Règlement partiel : FAC-2026-003727
- **23/11/2026** · litige · Règlement partiel : FAC-2026-003572

Historique complet : 68 événements (25 litige, 10 visite, 9 qualité, 5 compliment, 5 appel, 4 demande spéciale, 3 prix, 2 avoir, 2 livraison, 2 réclamation, 1 ouverture).

## Dossiers ouverts aujourd'hui

- **03/10/2026 — Règlement partiel : FAC-2026-002612** (`inv_011005`)
  Règlement inférieur de 2 179,01 € TTC au montant de FAC-2026-002612. Clémence conteste une ligne non reçue selon lui.
- **23/11/2026 — Règlement partiel : FAC-2026-003314** (`inv_011707`)
  Règlement inférieur de 1 766,76 € TTC au montant de FAC-2026-003314. Clémence conteste une ligne non reçue selon lui.
- **23/11/2026 — Règlement partiel : FAC-2026-003727** (`inv_012120`)
  Règlement inférieur de 1 662,72 € TTC au montant de FAC-2026-003727. Clémence conteste le prix appliqué sur noix de veau sous la mère PAD.
- **23/11/2026 — Règlement partiel : FAC-2026-003572** (`inv_011965`)
  Règlement inférieur de 979,47 € TTC au montant de FAC-2026-003572. Clémence conteste le poids facturé sur filet mignon de porc.

## Comment leur parler

- Confirmer les promos par écrit au directeur.
- Parler marge rayon et cotation.

## Prix & groupe

Groupes : **GMS** (`gms`), **Grands comptes** (`grands-comptes`), **À surveiller** (`a-surveiller`).
Pas de prix négocié.

Règles de prix qui peuvent s'appliquer :
- `prl_0002` GMS : coût + 24 % sur les carcasses
- `prl_0006` Volume : quartier arrière −2 % dès 200 kg
- `prl_0008` Fêtes 2026 : chair à saucisse −8 % dès 10 kg

Dernières notes CRM :

- 21/07/2025, Nicolas (commercial) : Le directeur valide les promos le mercredi.
- 22/05/2026, Nicolas (commercial) : Ne veut aucune substitution sans être prévenu : si un produit manque, appeler Clémence avant le départ du camion.
- 12/08/2026, Josette (comptabilité) : Conteste régulièrement des écarts (poids, qualité) et déduit lui-même de ses règlements. Demander au chauffeur de faire signer le BL avec les poids.
