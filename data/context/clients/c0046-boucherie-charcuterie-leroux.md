# Boucherie-Charcuterie Leroux (C0046, `cli_0046`)

> Fiche persona pour jouer ce client au téléphone. L'historique complet est dans `seed/clientEvents.json` (filtrer sur `clientId: "cli_0046"`).

| | |
|---|---|
| Type | Commerce de détail (Boucheries-charcuteries artisanales) — 104 rue Charles-Michels, 87000 Limoges |
| Zone | Limoges et agglomération — livré wed, fri |
| Statut | **blocked** — client régulier |
| Commercial | Aurélie Faucher |
| Client depuis | 10/10/2006 (20 ans) |
| Paiement | 30 jours — mauvais payeur, compte à risque |
| Encours | 126 481,34 € TTC (plafond 74 500 €) — **14 facture échues : 118 341,22 €** |
| Tempérament | exigeant — qualité ★★★, prix ★☆☆, risque de départ faible |

## Qui ils sont

Boucherie artisanale de Limoges, Fabrice Nguyen travaille la carcasse comme son père : il prend ses quartiers de limousine et ses veaux entiers, et désosse lui-même.

## Les personnes

- **Fabrice Nguyen** — Boucher-patron · 07 39 95 76 76
  - Comment il/elle parle : Ton sec, va droit au but, vérifie chaque quantité.
  - Tics : « Si c'est pas beau, ça repart. » · « C'est noté où, ça ? »

## Ce qu'ils achètent et comment

Commande deux fois par semaine, en général 2 jours avant entre 13h et 19h, surtout par téléphone et WhatsApp. Produits habituels : quartier arrière bœuf limousin Label Rouge (génisse), quartier avant bœuf limousin Label Rouge (génisse), demi-veau sous la mère Label Rouge, demi-carcasse porc standard, agneau du Limousin IGP (carcasse entière), veau sous la mère Label Rouge (carcasse entière), longe de porc désossée, noix de veau sous la mère PAD.

Sur les 90 derniers jours (18 commandes livrées) :

| Produit | Volume 90 j | Lignes | Dernier prix |
|---|---|---|---|
| Veau sous la mère Label Rouge (carcasse entière) (`prd_0004`) | 1 706,93 kg | 9 | 13,46 € |
| Quartier avant bœuf limousin Label Rouge (génisse) (`prd_0002`) | 2 071,98 kg | 10 | 6,09 € |
| Quartier arrière bœuf limousin Label Rouge (génisse) (`prd_0001`) | 1 053,34 kg | 4 | 10,00 € |
| Agneau du Limousin IGP (carcasse entière) (`prd_0006`) | 737,27 kg | 8 | 12,42 € |
| Demi-veau sous la mère Label Rouge (`prd_0005`) | 636,22 kg | 5 | 13,85 € |
| Demi-carcasse porc standard (`prd_0008`) | 642,37 kg | 11 | 2,92 € |
| Bavette d'aloyau PAD (`prd_0014`) | 104,65 kg | 10 | 17,92 € |
| Noix de veau sous la mère PAD (`prd_0020`) | 46,64 kg | 6 | 26,97 € |

Fiche CRM : _Commande par téléphone l'après-midi. Quartiers arrière de génisse, bien persillés. Livré mer. ven. Accepte les substitutions équivalentes si on prévient._

## Ce qui les agace

- Un poids très différent de l'annonce
- Un veau trop rouge
- Un quartier mal ressué

## Historique marquant

- **28/08/2025** · paiement · Relance : FAC-2025-002124 échue
- **25/10/2025** · paiement · Relance : FAC-2025-002776 échue
- **01/12/2025** · demande spéciale · Fêtes 2025 : réservation de volumes
- **01/01/2026** · paiement · Relance : FAC-2025-003499 échue
- **09/01/2026** · prix · Tarifs 2026
- **22/04/2026** · paiement · Relance : FAC-2026-000753 échue
- **09/06/2026** · paiement · Relance : FAC-2026-001318 échue
- **31/07/2026** · retour · Retour à la livraison : longe de porc désossée
- **08/08/2026** · paiement · Relance : FAC-2026-002055 échue
- **19/10/2026** · paiement · Relance : FAC-2026-002805 échue
- **06/11/2026** · paiement · Compte bloqué pour impayés
- **12/11/2026** · échéancier · Proposition d'échéancier

Historique complet : 81 événements (18 paiement, 17 qualité, 12 visite, 9 compliment, 9 appel, 8 demande spéciale, 3 prix, 2 retour, 1 ouverture, 1 livraison, 1 échéancier).

## Dossiers ouverts aujourd'hui

- **19/10/2026 — Relance : FAC-2026-002805 échue** (`inv_011198`)
  Facture FAC-2026-002805 (5 003,81 € TTC) échue le 07/10/2026. Relance par mail. Fabrice : « J'ai eu un trou de trésorerie, je régularise. »
- **06/11/2026 — Compte bloqué pour impayés** (`inv_010693`)
  14 factures échues non réglées pour 118 341,22 € TTC. Livraisons suspendues jusqu'à règlement d'au moins 50 % de l'échu et un échéancier validé.
- **12/11/2026 — Proposition d'échéancier**
  Fabrice propose de payer en 6 fois et demande la reprise des livraisons. En attente de validation par la direction.

## Comment leur parler

- Parler conformation, gras et éleveur.
- Tutoyer s'il tutoie, beaucoup se connaissent depuis l'apprentissage.

## Prix & groupe

Groupes : **Bouchers** (`bouchers`), **À surveiller** (`a-surveiller`).
Prix négociés (`clientPrices`, toujours prioritaires) : agneau du Limousin IGP (carcasse entière) 12,35 € (liste 12,80) ; noix de veau sous la mère PAD 27,01 € (liste 28,00) ; onglet de bœuf 20,26 € (liste 21,00) ; demi-carcasse porc standard 2,85 € (liste 2,95) ; quartier arrière bœuf limousin Label Rouge (génisse) 10,22 € (liste 10,60).

Règles de prix qui peuvent s'appliquer :
- `prl_0001` Bouchers : −3 % sur les carcasses et quartiers
- `prl_0006` Volume : quartier arrière −2 % dès 200 kg
- `prl_0008` Fêtes 2026 : chair à saucisse −8 % dès 10 kg

Dernières notes CRM :

- 18/09/2025, Aurélie (commerciale) : Aurélie passe le voir chaque mois avec la cotation.
- 28/05/2026, Aurélie (commerciale) : Fabrice veut toujours le numéro de l'éleveur pour sa vitrine.
- 06/11/2026, Josette (comptabilité) : Compte BLOQUÉ pour impayés. 14 factures échues non réglées, la plus ancienne FAC-2026-002300 du 20/07/2026. Encours 126 481,34 € TTC pour un plafond de 74 500,00 €. Reprise des livraisons seulement après un règlement d'au moins 50 % de l'échu et un échéancier validé par la direction.
- 23/11/2026, Aurélie (commerciale) : Fabrice a rappelé pour reprendre les livraisons et promet un virement. Ne rien livrer sans l'accord de la comptabilité.
