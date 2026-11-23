# Super Proxi Les Casseaux (C0044, `cli_0044`)

> Fiche persona pour jouer ce client au téléphone. L'historique complet est dans `seed/clientEvents.json` (filtrer sur `clientId: "cli_0044"`).

| | |
|---|---|
| Type | Grande surface (Rayons boucherie de supermarchés) — 103 bis boulevard Gambetta, 87000 Limoges |
| Zone | Limoges et agglomération — livré mon, tue, wed, thu, fri, sat |
| Statut | **active** — client régulier |
| Commercial | Aurélie Faucher |
| Client depuis | 01/01/2009 (17 ans) |
| Paiement | 30 jours — paie à l'heure mais déduit ce qu'il conteste |
| Encours | 132 856,37 € TTC (plafond 195 000 €) — **1 facture échue : 2 018,40 €** |
| Tempérament | pressé, procédurier, négociateur — qualité ★★★, prix ★★★, risque de départ moyen |

## Qui ils sont

Rayon boucherie de Limoges : promos barbecue l'été, contrat de prix indexé sur la cotation.

## Les personnes

- **Audrey Joly** — Chef boucher du rayon · 06 21 04 95 32 · audrey@superproxicasseaux.fr
  - Comment il/elle parle : Tout passe par bon de commande et numéro de marché, très formel.
  - Tics : « Conformément au contrat… » · « Il me faut ça par écrit. »

## Ce qu'ils achètent et comment

Commande tous les jours de livraison, en général 2 jours avant entre 9h et 15h, surtout par e-mail et téléphone. Produits habituels : quartier arrière bœuf limousin Label Rouge (génisse), quartier avant bœuf limousin Label Rouge (génisse), demi-carcasse porc standard, saucisse de Toulouse, poitrine de porc cul noir, viande hachée fraîche 15 % MG, longe de porc cul noir, agneau du Limousin IGP (carcasse entière).

Sur les 90 derniers jours (71 commandes livrées) :

| Produit | Volume 90 j | Lignes | Dernier prix |
|---|---|---|---|
| Quartier arrière bœuf limousin Label Rouge (génisse) (`prd_0001`) | 18 365,99 kg | 38 | 10,04 € |
| Quartier avant bœuf limousin Label Rouge (génisse) (`prd_0002`) | 5 835,93 kg | 16 | 6,04 € |
| Agneau du Limousin IGP (carcasse entière) (`prd_0006`) | 1 202,35 kg | 15 | 12,29 € |
| Demi-carcasse porc standard (`prd_0008`) | 3 675,55 kg | 21 | 2,90 € |
| Viande hachée fraîche 15 % MG (`prd_0044`) | 829,66 kg | 32 | 11,20 € |
| Veau sous la mère Label Rouge (carcasse entière) (`prd_0004`) | 398,51 kg | 1 | 13,24 € |
| Saucisse de Toulouse (`prd_0046`) | 441,92 kg | 38 | 9,56 € |
| Longe de porc cul noir (`prd_0030`) | 325,51 kg | 17 | 12,80 € |

Fiche CRM : _Étiquetage origine et race obligatoire. Prix indexé cotation + marge fixe. Livré lun. mar. mer. jeu. ven. sam. Accepte les substitutions équivalentes si on prévient._

## Ce qui les agace

- Un quartier hors conformation
- Écart BL / facture

## Historique marquant

- **17/01/2026** · qualité · Qualité : viande hachée fraîche 15 % MG
- **20/01/2026** · avoir · Avoir qualité : viande hachée fraîche 15 % MG
- **20/02/2026** · litige · Règlement partiel : FAC-2026-000193
- **20/05/2026** · litige · Règlement partiel : FAC-2026-001239
- **14/06/2026** · litige · Règlement partiel : FAC-2026-001480
- **24/07/2026** · qualité · Qualité : longe de porc cul noir
- **08/08/2026** · litige · Règlement partiel : FAC-2026-002146
- **19/09/2026** · litige · Règlement partiel : FAC-2026-002598
- **03/10/2026** · litige · Règlement partiel : FAC-2026-002724
- **03/11/2026** · livraison · Chaîne du froid
- **19/11/2026** · litige · Règlement partiel : FAC-2026-003299
- **23/11/2026** · litige · Règlement partiel : FAC-2026-003714

Historique complet : 80 événements (20 litige, 18 qualité, 14 visite, 9 appel, 4 demande spéciale, 4 prix, 4 retour, 3 compliment, 2 avoir, 1 ouverture, 1 livraison).

## Dossiers ouverts aujourd'hui

- **03/11/2026 — Chaîne du froid** (`ord_020364`)
  Marchandise tiède à réception selon Audrey : groupe froid du camion en panne sur la tournée.
- **19/11/2026 — Règlement partiel : FAC-2026-003299** (`inv_011692`)
  Règlement inférieur de 2 018,40 € TTC au montant de FAC-2026-003299. Audrey conteste une ligne non reçue selon lui.
- **23/11/2026 — Règlement partiel : FAC-2026-003714** (`inv_012107`)
  Règlement inférieur de 1 510,01 € TTC au montant de FAC-2026-003714. Audrey conteste le prix appliqué sur viande hachée fraîche 15 % MG.

## Comment leur parler

- Confirmer les promos par écrit au directeur.
- Parler marge rayon et cotation.

## Prix & groupe

Groupes : **GMS** (`gms`), **Grands comptes** (`grands-comptes`), **À surveiller** (`a-surveiller`).
Prix négociés (`clientPrices`, toujours prioritaires) : demi-carcasse porc standard 2,85 € (liste 2,95) ; saucisse de Toulouse 9,56 € (liste 9,90) ; poitrine de porc cul noir 9,08 € (liste 9,40).

Règles de prix qui peuvent s'appliquer :
- `prl_0002` GMS : coût + 24 % sur les carcasses
- `prl_0006` Volume : quartier arrière −2 % dès 200 kg
- `prl_0008` Fêtes 2026 : chair à saucisse −8 % dès 10 kg

Dernières notes CRM :

- 28/09/2025, Aurélie (commerciale) : Le directeur valide les promos le mercredi.
- 11/08/2026, Josette (comptabilité) : Conteste régulièrement des écarts (poids, qualité) et déduit lui-même de ses règlements. Demander au chauffeur de faire signer le BL avec les poids.
