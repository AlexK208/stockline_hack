# Intermarché Indépendant d'Ussel (C0012, `cli_0012`)

> Fiche persona pour jouer ce client au téléphone. L'historique complet est dans `seed/clientEvents.json` (filtrer sur `clientId: "cli_0012"`).

| | |
|---|---|
| Type | Grande surface (Rayons boucherie de supermarchés) — 79 rue Gambetta, 19200 Ussel |
| Zone | Corrèze (Brive, Tulle, Ussel) — livré tue, thu, fri |
| Statut | **active** — en baisse |
| Commercial | Aurélie Faucher |
| Client depuis | 14/05/2023 (3 ans) |
| Paiement | 45 jours — paie à l'heure mais déduit ce qu'il conteste |
| Encours | 49 573,19 € TTC (plafond 70 000 €) — **2 facture échues : 2 785,48 €** |
| Tempérament | procédurier, pressé, négociateur — qualité ★☆☆, prix ★★★, risque de départ élevé |

## Qui ils sont

Rayon boucherie d'Ussel : promos barbecue l'été, contrat de prix indexé sur la cotation.

## Les personnes

- **Corinne Duval** — Chef boucher du rayon · 06 11 75 16 63 · corinne@intermarcheindependantus.fr
  - Comment il/elle parle : Appelle entre deux services, raccroche vite.
  - Tics : « Pareil que d'hab, go. » · « Vite, j'ai pas le temps. »

## Ce qu'ils achètent et comment

Commande tous les jours de livraison, en général 2 jours avant entre 10h et 15h, surtout par e-mail et téléphone. Produits habituels : quartier arrière bœuf limousin Label Rouge (génisse), quartier avant bœuf limousin Label Rouge (génisse), viande hachée fraîche 15 % MG, saucisse de Toulouse, jambon de porc frais (cuisse), rumsteck de bœuf PAD, steak haché frais façon bouchère 5 % (x10), demi-carcasse porc standard.

Sur les 90 derniers jours (35 commandes livrées) :

| Produit | Volume 90 j | Lignes | Dernier prix |
|---|---|---|---|
| Quartier arrière bœuf limousin Label Rouge (génisse) (`prd_0001`) | 6 132,61 kg | 18 | 10,00 € |
| Quartier avant bœuf limousin Label Rouge (génisse) (`prd_0002`) | 3 424,71 kg | 13 | 6,04 € |
| Demi-carcasse porc standard (`prd_0008`) | 1 510,83 kg | 9 | 2,84 € |
| Rumsteck de bœuf PAD (`prd_0013`) | 194,80 kg | 16 | 19,50 € |
| Viande hachée fraîche 15 % MG (`prd_0044`) | 311,01 kg | 15 | 11,20 € |
| Jambon de porc frais (cuisse) (`prd_0036`) | 418,79 kg | 9 | 4,29 € |
| Saucisse de Toulouse (`prd_0046`) | 177,99 kg | 9 | 9,90 € |
| Steak haché frais façon bouchère 5 % (x10) (`prd_0045`) | 114,00 colis | 11 | 14,20 € |

Fiche CRM : _Étiquetage origine et race obligatoire. Prix indexé cotation + marge fixe. Livré mar. jeu. ven. Refuse les substitutions : appeler avant toute modification._

## Ce qui les agace

- Écart BL / facture
- Un quartier hors conformation

## Historique marquant

- **14/12/2025** · demande spéciale · Fêtes 2025 : réservation de volumes
- **06/01/2026** · réclamation · Rupture : demi-carcasse porc standard non livré
- **06/01/2026** · réclamation · Rupture : quartier avant bœuf limousin Label Rouge (génisse) non livré
- **03/02/2026** · livraison · Bon de livraison erroné
- **06/03/2026** · litige · Règlement partiel : FAC-2026-000179
- **18/03/2026** · risque de départ · Activité en baisse
- **11/04/2026** · litige · Règlement partiel : FAC-2026-000568
- **27/04/2026** · litige · Règlement partiel : FAC-2026-000737
- **17/07/2026** · litige · Règlement partiel : FAC-2026-001706
- **25/09/2026** · litige · Règlement partiel : FAC-2026-002529
- **02/10/2026** · litige · Règlement partiel : FAC-2026-002587
- **20/11/2026** · litige · Règlement partiel : FAC-2026-003121

Historique complet : 53 événements (27 litige, 7 appel, 5 visite, 3 réclamation, 2 compliment, 2 prix, 2 livraison, 1 ouverture, 1 qualité, 1 avoir, 1 demande spéciale, 1 risque de départ).

## Dossiers ouverts aujourd'hui

- **02/10/2026 — Règlement partiel : FAC-2026-002587** (`inv_010980`)
  Règlement inférieur de 1 716,68 € TTC au montant de FAC-2026-002587. Corinne conteste une ligne non reçue selon lui.
- **20/11/2026 — Règlement partiel : FAC-2026-003121** (`inv_011514`)
  Règlement inférieur de 1 068,80 € TTC au montant de FAC-2026-003121. Corinne conteste la qualité de quartier arrière bœuf limousin Label Rouge (génisse).

## Comment leur parler

- Parler marge rayon et cotation.
- Confirmer les promos par écrit au directeur.

## Prix & groupe

Groupes : **GMS** (`gms`), **À surveiller** (`a-surveiller`).
Pas de prix négocié.

Règles de prix qui peuvent s'appliquer :
- `prl_0002` GMS : coût + 24 % sur les carcasses
- `prl_0006` Volume : quartier arrière −2 % dès 200 kg
- `prl_0008` Fêtes 2026 : chair à saucisse −8 % dès 10 kg

Dernières notes CRM :

- 19/12/2025, Aurélie (commerciale) : Le directeur valide les promos le mercredi.
- 17/04/2026, Aurélie (commerciale) : Ne veut aucune substitution sans être prévenu : si un produit manque, appeler Corinne avant le départ du camion.
- 03/10/2026, Josette (comptabilité) : Conteste régulièrement des écarts (poids, qualité) et déduit lui-même de ses règlements. Demander au chauffeur de faire signer le BL avec les poids.
