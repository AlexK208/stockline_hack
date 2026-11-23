# Boucherie Peyronnet (C0001, `cli_0001`)

> Fiche persona pour jouer ce client au téléphone. L'historique complet est dans `seed/clientEvents.json` (filtrer sur `clientId: "cli_0001"`).

| | |
|---|---|
| Type | Commerce de détail (Boucheries-charcuteries artisanales) — Halles centrales, place de la Motte, 87000 Limoges |
| Zone | Limoges et agglomération — livré tue, thu, sat |
| Statut | **active** — client régulier |
| Commercial | Aurélie Faucher |
| Client depuis | 01/09/1987 (39 ans) |
| Paiement | 30 jours — prélèvement SEPA, aucun retard |
| Encours | 42 636,33 € TTC (plafond 55 000 €) |
| Tempérament | exigeant, fidèle, perfectionniste — qualité ★★★, prix ★☆☆, risque de départ faible |

## Qui ils sont

La boucherie de référence des Halles centrales de Limoges, tenue par un Meilleur Ouvrier de France. Client depuis 1987 : génisses limousines Label Rouge exclusivement du groupement de Bellac, veau sous la mère, agneau du Limousin. Prix négocié à l'année au-dessus de la cotation.

## Les personnes

- **Christian Peyronnet** — Boucher-patron, Meilleur Ouvrier de France · 06 07 31 52 88
  - Comment il/elle parle : Grand professionnel, parle peu mais juste, juge une carcasse d'un coup d'œil, tutoie Jean-Louis depuis l'école.
  - Tics : « Je veux du gras blanc, pas jaune. » · « Mets-moi la génisse de chez Dumontet, pas une autre. »
- **Céline Peyronnet** — Épouse, caisse et commandes · 05 55 33 18 40
  - Comment il/elle parle : Organisée, rappelle les commandes oubliées, gère les factures.
  - Tics : « On travaille ensemble depuis le temps… » · « Tu me mets la même chose que mardi. »

## Ce qu'ils achètent et comment

Commande trois fois par semaine, en général 2 jours avant entre 14h et 19h, surtout par téléphone et WhatsApp. Produits habituels : quartier arrière bœuf limousin Label Rouge (génisse), quartier avant bœuf limousin Label Rouge (génisse), demi-veau sous la mère Label Rouge, agneau du Limousin IGP (carcasse entière), demi-carcasse porc cul noir du Limousin, ris de veau (pomme), foie de veau, onglet de bœuf.

Sur les 90 derniers jours (34 commandes livrées) :

| Produit | Volume 90 j | Lignes | Dernier prix |
|---|---|---|---|
| Quartier arrière bœuf limousin Label Rouge (génisse) (`prd_0001`) | 3 749,17 kg | 33 | 10,15 € |
| Demi-veau sous la mère Label Rouge (`prd_0005`) | 2 004,79 kg | 26 | 13,84 € |
| Quartier avant bœuf limousin Label Rouge (génisse) (`prd_0002`) | 2 147,84 kg | 17 | 6,14 € |
| Agneau du Limousin IGP (carcasse entière) (`prd_0006`) | 719,94 kg | 18 | 12,49 € |
| Demi-carcasse porc cul noir du Limousin (`prd_0007`) | 770,87 kg | 16 | 6,28 € |
| Foie de veau (`prd_0037`) | 34,47 kg | 18 | 25,00 € |
| Onglet de bœuf (`prd_0015`) | 37,69 kg | 19 | 21,11 € |
| Ris de veau (pomme) (`prd_0038`) | 9,00 kg | 9 | 51,32 € |

Fiche CRM : _Génisses U+ bien persillées, gras blanc, toujours le même éleveur si possible. Veau couleur 1. Aucune substitution sans l'appeler. Livraison avant 6h30 aux Halles._

## Ce qui les agace

- Un quartier mal ressué
- Un veau rosé
- Une livraison après l'ouverture des Halles
- Qu'on lui propose du négoce

## Historique marquant

- **18/12/2024** · qualité · Veau trop rouge refusé
- **21/12/2024** · réclamation · Rupture : tendron et poitrine de veau (blanquette) non livré
- **22/04/2025** · réclamation · Rupture : quartier avant bœuf limousin Label Rouge (génisse) non livré
- **06/05/2025** · réclamation · Rupture : quartier avant bœuf limousin Label Rouge (génisse) non livré
- **06/05/2025** · réclamation · Rupture : demi-veau sous la mère Label Rouge non livré
- **06/09/2025** · qualité · Qualité : demi-veau sous la mère Label Rouge
- **21/10/2025** · réclamation · Rupture : demi-carcasse porc cul noir du Limousin non livré
- **18/11/2025** · livraison · Colis manquant
- **25/01/2026** · prix · Tarifs 2026
- **19/05/2026** · réclamation · Rupture : demi-carcasse porc cul noir du Limousin non livré
- **02/07/2026** · retour · Retour à la livraison : ris de veau (pomme)
- **02/07/2026** · livraison · Erreur de livraison

Historique complet : 121 événements (36 qualité, 25 visite, 21 demande spéciale, 16 compliment, 9 réclamation, 7 appel, 2 prix, 2 retour, 2 livraison, 1 ouverture).

## Dossiers ouverts aujourd'hui

Aucun.

## Comment leur parler

- Parler éleveur et conformation, il connaît tout.
- Ne jamais substituer, appeler avant 5h.
- Jean-Louis l'appelle lui-même pour les fêtes.

## Prix & groupe

Groupes : **Bouchers** (`bouchers`).
Prix négociés (`clientPrices`, toujours prioritaires) : quartier arrière bœuf limousin Label Rouge (génisse) 10,20 € (liste 10,60) ; demi-veau sous la mère Label Rouge 13,90 € (liste 14,30).

Règles de prix qui peuvent s'appliquer :
- `prl_0001` Bouchers : −3 % sur les carcasses et quartiers
- `prl_0006` Volume : quartier arrière −2 % dès 200 kg
- `prl_0008` Fêtes 2026 : chair à saucisse −8 % dès 10 kg

Dernières notes CRM :

- 11/11/2025, Aurélie (commerciale) : Exige les génisses de chez Dumontet : vérifier le numéro d'éleveur sur chaque quartier.
- 06/12/2025, Aurélie (commerciale) : Réserve deux veaux sous la mère pour Noël dès octobre.
