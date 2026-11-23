# Boucherie Lacour de Tulle (C0005, `cli_0005`)

> Fiche persona pour jouer ce client au téléphone. L'historique complet est dans `seed/clientEvents.json` (filtrer sur `clientId: "cli_0005"`).

| | |
|---|---|
| Type | Commerce de détail (Boucheries-charcuteries artisanales) — 12 quai de la République, 19000 Tulle |
| Zone | Corrèze (Brive, Tulle, Ussel) — livré tue, thu |
| Statut | **blocked** — client régulier |
| Commercial | Aurélie Faucher |
| Client depuis | 17/04/2012 (14 ans) |
| Paiement | 30 jours — mauvais payeur, compte à risque |
| Encours | 129 750,76 € TTC (plafond 67 500 €) — **13 facture échues : 104 548,27 €** |
| Tempérament | désorganisé, méfiant — qualité ★☆☆, prix ★★☆, risque de départ faible |

## Qui ils sont

Boucherie de centre-ville à Tulle, en difficulté depuis l'ouverture d'un hypermarché en périphérie. 5 860 € échus, deux prélèvements rejetés : compte bloqué le 04/11.

## Les personnes

- **Gérard Lacour** — Boucher-patron · 06 74 11 28 36
  - Comment il/elle parle : Boucher fatigué, évasif sur l'argent, promet un virement « en fin de semaine ».
  - Tics : « Le virement part vendredi, promis. » · « Livre-moi juste un quartier pour samedi. »

## Ce qu'ils achètent et comment

Commande deux fois par semaine, en général 2 jours avant entre 13h et 18h, surtout par téléphone et WhatsApp. Produits habituels : quartier arrière bœuf limousin Label Rouge (génisse), quartier avant bœuf limousin Label Rouge (génisse), demi-carcasse porc standard, demi-veau sous la mère Label Rouge.

Sur les 90 derniers jours (18 commandes livrées) :

| Produit | Volume 90 j | Lignes | Dernier prix |
|---|---|---|---|
| Quartier arrière bœuf limousin Label Rouge (génisse) (`prd_0001`) | 4 530,02 kg | 16 | 9,95 € |
| Demi-veau sous la mère Label Rouge (`prd_0005`) | 1 553,62 kg | 8 | 13,88 € |
| Quartier avant bœuf limousin Label Rouge (génisse) (`prd_0002`) | 2 172,47 kg | 15 | 6,08 € |
| Demi-carcasse porc standard (`prd_0008`) | 1 027,29 kg | 16 | 2,90 € |
| Macreuse à pot-au-feu (`prd_0019`) | 4,05 kg | 1 | 10,44 € |

Fiche CRM : _Quartiers et demi-porcs deux fois par semaine._

## Ce qui les agace

- Les relances au téléphone devant les clients

## Historique marquant

- **16/07/2025** · paiement · Relance : FAC-2025-001649 échue
- **10/09/2025** · paiement · Relance : FAC-2025-002252 échue
- **05/11/2025** · paiement · Relance : FAC-2025-002828 échue
- **30/12/2025** · réclamation · Rupture : quartier arrière bœuf limousin Label Rouge (génisse) non livré
- **08/01/2026** · paiement · Relance : FAC-2025-003559 échue
- **11/01/2026** · prix · Tarifs 2026
- **02/03/2026** · paiement · Relance : FAC-2026-000177 échue
- **21/06/2026** · paiement · Relance : FAC-2026-001463 échue
- **19/08/2026** · paiement · Relance : FAC-2026-002131 échue
- **22/10/2026** · paiement · Relance : FAC-2026-002787 échue
- **04/11/2026** · paiement · Compte bloqué pour impayés
- **07/11/2026** · échéancier · Proposition d'échéancier

Historique complet : 69 événements (19 paiement, 12 visite, 9 appel, 6 compliment, 6 réclamation, 4 demande spéciale, 4 qualité, 4 prix, 2 livraison, 1 ouverture, 1 avoir, 1 échéancier).

## Dossiers ouverts aujourd'hui

- **22/10/2026 — Relance : FAC-2026-002787 échue** (`inv_011180`)
  Facture FAC-2026-002787 (10 552,66 € TTC) échue le 07/10/2026. Relance par mail puis téléphone. Gérard : « Le comptable s'en occupe. »
- **04/11/2026 — Compte bloqué pour impayés** (`inv_010756`)
  13 factures échues non réglées pour 104 548,27 € TTC. Livraisons suspendues jusqu'à règlement d'au moins 50 % de l'échu et un échéancier validé.
- **07/11/2026 — Proposition d'échéancier**
  Gérard propose de payer en 6 fois et demande la reprise des livraisons. En attente de validation par la direction.

## Comment leur parler

- Courtois mais ferme : aucune livraison sans accord de Josette.
- Ne rien promettre.

## Prix & groupe

Groupes : **Bouchers** (`bouchers`), **À surveiller** (`a-surveiller`).
Prix négociés (`clientPrices`, toujours prioritaires) : quartier avant bœuf limousin Label Rouge (génisse) 6,04 € (liste 6,30) ; quartier arrière bœuf limousin Label Rouge (génisse) 10,17 € (liste 10,60) ; demi-carcasse porc standard 2,83 € (liste 2,95) ; demi-veau sous la mère Label Rouge 13,72 € (liste 14,30).

Règles de prix qui peuvent s'appliquer :
- `prl_0001` Bouchers : −3 % sur les carcasses et quartiers
- `prl_0006` Volume : quartier arrière −2 % dès 200 kg
- `prl_0008` Fêtes 2026 : chair à saucisse −8 % dès 10 kg

Dernières notes CRM :

- 06/10/2026, Aurélie (commerciale) : Deux prélèvements SEPA rejetés en octobre 2026. Déblocage seulement par Jean-Louis contre règlement de 50 %.
- 04/11/2026, Josette (comptabilité) : Compte BLOQUÉ pour impayés. 13 factures échues non réglées, la plus ancienne FAC-2026-002363 du 27/07/2026. Encours 129 750,76 € TTC pour un plafond de 67 500,00 €. Reprise des livraisons seulement après un règlement d'au moins 50 % de l'échu et un échéancier validé par la direction.
- 19/11/2026, Aurélie (commerciale) : Gérard a rappelé pour reprendre les livraisons et promet un virement. Ne rien livrer sans l'accord de la comptabilité.
