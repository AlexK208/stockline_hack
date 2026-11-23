# Le Relais du Lac de Vassivière (C0006, `cli_0006`)

> Fiche persona pour jouer ce client au téléphone. L'historique complet est dans `seed/clientEvents.json` (filtrer sur `clientId: "cli_0006"`).

| | |
|---|---|
| Type | Hôtel (Hôtels, auberges et restaurants touristiques) — Auphelle, 87470 Peyrat-le-Château |
| Zone | Creuse (Guéret, Aubusson, La Souterraine) — livré wed, sat |
| Statut | **blocked** — client régulier |
| Commercial | Nicolas Bouty |
| Client depuis | 02/05/2019 (7 ans) |
| Paiement | 30 jours — mauvais payeur, compte à risque |
| Encours | 54 740,87 € TTC (plafond 34 000 €) — **3 facture échues : 49 496,43 €** |
| Tempérament | désorganisé, râleur — qualité ★★☆, prix ★★★, risque de départ moyen |

## Qui ils sont

Hôtel-restaurant au bord du lac de Vassivière, ouvert d'avril à octobre. Conteste 1 450 € de livraisons d'août (côtes de bœuf « jamais reçues ») et n'a réglé que la moitié de son encours de saison : compte bloqué le 20/10 en attendant le règlement.

## Les personnes

- **Yannick Morel** — Gérant · 06 85 40 22 17
  - Comment il/elle parle : Saisonnier débordé, conteste les factures de l'été.
  - Tics : « J'ai jamais reçu ces côtes de bœuf ! » · « On règle tout en octobre, comme chaque année. »

## Ce qu'ils achètent et comment

Commande en saison seulement, en général 2 jours avant entre 11h et 17h, surtout par téléphone et e-mail. Produits habituels : côte de bœuf limousine maturée 21 jours, faux-filet de bœuf limousin PAD, gigot d'agneau du Limousin, longe de porc cul noir, jambon sec du Limousin (désossé), saucisse de Toulouse.

Sur les 90 derniers jours (13 commandes livrées) :

| Produit | Volume 90 j | Lignes | Dernier prix |
|---|---|---|---|
| Côte de bœuf limousine maturée 21 jours (`prd_0011`) | 331,63 kg | 10 | 31,75 € |
| Faux-filet de bœuf limousin PAD (`prd_0009`) | 171,30 kg | 10 | 25,51 € |
| Gigot d'agneau du Limousin (`prd_0026`) | 217,75 kg | 10 | 18,00 € |
| Saucisse de Toulouse (`prd_0046`) | 173,83 kg | 8 | 9,90 € |
| Longe de porc cul noir (`prd_0030`) | 65,33 kg | 4 | 12,85 € |
| Jambon sec du Limousin (désossé) (`prd_0052`) | 38,16 kg | 6 | 19,80 € |

Fiche CRM : _Côtes de bœuf et menu terroir en saison._

## Ce qui les agace

- Les relances de paiement
- Les BL non signés

## Historique marquant

- **19/09/2024** · carte · Carte d'automne
- **14/10/2024** · paiement · Relance : FAC-2024-002665 échue
- **13/01/2025** · prix · Tarifs 2025
- **26/07/2025** · réclamation · Rupture : gigot d'agneau du Limousin non livré
- **12/10/2025** · paiement · Relance : FAC-2025-002607 échue
- **09/01/2026** · prix · Tarifs 2026
- **14/06/2026** · paiement · Relance : FAC-2026-001368 échue
- **15/08/2026** · qualité · Qualité : jambon sec du Limousin (désossé)
- **13/09/2026** · paiement · Relance : FAC-2026-002438 échue
- **20/10/2026** · paiement · Compte bloqué pour impayés
- **26/10/2026** · échéancier · Proposition d'échéancier
- **15/11/2026** · paiement · Relance : FAC-2026-003085 échue

Historique complet : 36 événements (7 appel, 6 paiement, 5 visite, 4 prix, 3 qualité, 2 compliment, 2 note, 2 carte, 1 ouverture, 1 retour, 1 livraison, 1 réclamation, 1 échéancier).

## Dossiers ouverts aujourd'hui

- **13/09/2026 — Relance : FAC-2026-002438 échue** (`inv_010831`)
  Facture FAC-2026-002438 (26 361,70 € TTC) échue le 31/08/2026. Relance par mail. Yannick : « Le comptable s'en occupe. »
- **20/10/2026 — Compte bloqué pour impayés** (`inv_010831`)
  3 factures échues non réglées pour 49 496,43 € TTC. Livraisons suspendues jusqu'à règlement d'au moins 50 % de l'échu et un échéancier validé.
- **26/10/2026 — Proposition d'échéancier**
  Yannick propose de payer en 6 fois et demande la reprise des livraisons. En attente de validation par la direction.
- **15/11/2026 — Relance : FAC-2026-003085 échue** (`inv_011478`)
  Facture FAC-2026-003085 (10 448,94 € TTC) échue le 31/10/2026. Relance par mail puis téléphone. Yannick : « J'ai eu un trou de trésorerie, je régularise. »

## Comment leur parler

- Rester factuel : BL signés et photos du chauffeur.
- Renvoyer vers Josette pour le litige.

## Prix & groupe

Groupes : **Auberges** (`auberges`), **À surveiller** (`a-surveiller`).
Pas de prix négocié.

Règles de prix qui peuvent s'appliquer :
- `prl_0006` Volume : quartier arrière −2 % dès 200 kg
- `prl_0008` Fêtes 2026 : chair à saucisse −8 % dès 10 kg

Dernières notes CRM :

- 29/09/2026, Nicolas (commercial) : Litige sur trois livraisons d'août : Josette a envoyé les BL signés le 28/10.
- 20/10/2026, Josette (comptabilité) : Compte BLOQUÉ pour impayés. 3 factures échues non réglées, la plus ancienne FAC-2026-002438 du 01/08/2026. Encours 54 740,87 € TTC pour un plafond de 34 000,00 €. Reprise des livraisons seulement après un règlement d'au moins 50 % de l'échu et un échéancier validé par la direction.
- 22/11/2026, Nicolas (commercial) : Yannick a rappelé pour reprendre les livraisons et promet un virement. Ne rien livrer sans l'accord de la comptabilité.
