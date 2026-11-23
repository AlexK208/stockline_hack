# Le Comptoir de la Viande (C0038, `cli_0038`)

> Fiche persona pour jouer ce client au téléphone. L'historique complet est dans `seed/clientEvents.json` (filtrer sur `clientId: "cli_0038"`).

| | |
|---|---|
| Type | Commerce de détail (Boucheries-charcuteries artisanales) — 67 rue du Château, 19140 Uzerche |
| Zone | Corrèze (Brive, Tulle, Ussel) — livré tue |
| Statut | **active** — en croissance |
| Commercial | Aurélie Faucher |
| Client depuis | 08/09/2010 (16 ans) |
| Paiement | 15 jours — paie à l'échéance, sans histoire |
| Encours | 14 766,27 € TTC (plafond 18 000 €) |
| Tempérament | méfiant, fidèle — qualité ★★★, prix ★☆☆, risque de départ faible |

## Qui ils sont

Boucherie artisanale d'Uzerche, Théo Plazanet travaille la carcasse comme son père : il prend ses quartiers de limousine et ses veaux entiers, et désosse lui-même.

## Les personnes

- **Théo Plazanet** — Boucher-patron · 06 35 16 75 41 · theo@comptoirviande.fr
  - Comment il/elle parle : Prudent, redemande les prix deux fois, veut tout par écrit.
  - Tics : « La dernière fois, c'était pas ce qui était prévu. » · « Ça vient d'où exactement ? »
- **Maxime Rey** — Associé · 06 75 52 59 33
  - Comment il/elle parle : Voix posée, tutoie le commercial depuis des années, commande toujours la même chose.
  - Tics : « Tu me mets la même chose que mardi. » · « Je te fais confiance. »
- **Franck Perrin** — Apprenti · 06 41 99 70 54
  - Comment il/elle parle : Calme, habitué, appelle à heure fixe.
  - Tics : « Tu me mets la même chose que mardi. » · « Je te fais confiance. »

## Ce qu'ils achètent et comment

Commande une fois par semaine, en général 2 jours avant entre 13h et 19h, surtout par téléphone et WhatsApp. Produits habituels : quartier arrière bœuf limousin Label Rouge (génisse), quartier avant bœuf limousin Label Rouge (génisse), demi-veau sous la mère Label Rouge, demi-carcasse porc standard, agneau du Limousin IGP (carcasse entière).

Sur les 90 derniers jours (12 commandes livrées) :

| Produit | Volume 90 j | Lignes | Dernier prix |
|---|---|---|---|
| Quartier arrière bœuf limousin Label Rouge (génisse) (`prd_0001`) | 2 006,25 kg | 5 | 10,23 € |
| Quartier avant bœuf limousin Label Rouge (génisse) (`prd_0002`) | 2 990,66 kg | 8 | 6,14 € |
| Demi-veau sous la mère Label Rouge (`prd_0005`) | 1 322,10 kg | 6 | 13,87 € |
| Agneau du Limousin IGP (carcasse entière) (`prd_0006`) | 632,33 kg | 4 | 12,48 € |
| Ris de veau (pomme) (`prd_0038`) | 0,97 kg | 1 | 50,27 € |

Fiche CRM : _Un veau sous la mère pour les fêtes. Commande par téléphone l'après-midi. Livré mar. Refuse les substitutions : appeler avant toute modification._

## Ce qui les agace

- Être livré après l'ouverture
- Un quartier mal ressué

## Historique marquant

- **03/06/2025** · qualité · Qualité : quartier avant bœuf limousin Label Rouge (génisse)
- **08/07/2025** · qualité · Qualité : demi-veau sous la mère Label Rouge
- **11/07/2025** · avoir · Avoir qualité : demi-veau sous la mère Label Rouge
- **30/09/2025** · qualité · Qualité : quartier arrière bœuf limousin Label Rouge (génisse)
- **14/12/2025** · demande spéciale · Fêtes 2025 : réservation de volumes
- **30/12/2025** · réclamation · Rupture : quartier avant bœuf limousin Label Rouge (génisse) non livré
- **06/01/2026** · réclamation · Rupture : demi-veau sous la mère Label Rouge non livré
- **06/01/2026** · réclamation · Rupture : quartier avant bœuf limousin Label Rouge (génisse) non livré
- **15/01/2026** · prix · Tarifs 2026
- **14/04/2026** · livraison · Erreur de livraison
- **25/08/2026** · livraison · Colis manquant
- **10/11/2026** · qualité · Qualité : demi-veau sous la mère Label Rouge

Historique complet : 55 événements (19 qualité, 8 demande spéciale, 7 visite, 5 appel, 5 réclamation, 3 prix, 3 livraison, 2 compliment, 2 avoir, 1 ouverture).

## Dossiers ouverts aujourd'hui

- **10/11/2026 — Qualité : demi-veau sous la mère Label Rouge** (`ord_020507`, `inv_012027`)
  Franck appelle à réception : gras de couverture insuffisant (commande CMD-2026-005945, 291,07 kg). Franck : « Je te fais confiance. »

## Comment leur parler

- Parler conformation, gras et éleveur.
- Tutoyer s'il tutoie, beaucoup se connaissent depuis l'apprentissage.
- Annoncer la cotation du lundi.

## Prix & groupe

Groupes : **Bouchers** (`bouchers`).
Pas de prix négocié.

Règles de prix qui peuvent s'appliquer :
- `prl_0001` Bouchers : −3 % sur les carcasses et quartiers
- `prl_0006` Volume : quartier arrière −2 % dès 200 kg
- `prl_0008` Fêtes 2026 : chair à saucisse −8 % dès 10 kg

Dernières notes CRM :

- 08/06/2026, Aurélie (commerciale) : Aurélie passe le voir chaque mois avec la cotation.
- 27/08/2026, Aurélie (commerciale) : Théo veut toujours le numéro de l'éleveur pour sa vitrine.
