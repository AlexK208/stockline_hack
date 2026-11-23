# Cuisine centrale de Saint-Junien (C0004, `cli_0004`)

> Fiche persona pour jouer ce client au téléphone. L'historique complet est dans `seed/clientEvents.json` (filtrer sur `clientId: "cli_0004"`).

| | |
|---|---|
| Type | Restauration collective (Restauration collective (cuisines centrales, EHPAD, lycées)) — Rue Louis-Codet, 87200 Saint-Junien |
| Zone | Haute-Vienne sud et ouest (Saint-Junien, Saint-Yrieix, Aixe) — livré wed |
| Statut | **active** — client régulier |
| Commercial | Sylvie Desbordes |
| Client depuis | 09/01/2023 (3 ans) |
| Paiement | 30 jours — mandat administratif : paiement lent mais sûr |
| Encours | 28 879,57 € TTC (plafond 35 000 €) — **1 facture échue : 21 823,64 €** |
| Tempérament | procédurier, fidèle — qualité ★★☆, prix ★☆☆, risque de départ faible |

## Qui ils sont

Cuisine centrale municipale : 2 100 repas par jour pour les écoles et l'EHPAD de Saint-Junien. Marché public viande remporté en 2023 avec une clause « bœuf limousin une fois par semaine ».

## Les personnes

- **Marc Teillet** — Responsable de production · 05 55 02 41 60 · cuisine.centrale@saint-junien.fr
  - Comment il/elle parle : Cuisinier de collectivité, calme, attaché au local.
  - Tics : « Mon bœuf limousin du jeudi, c'est sacré. » · « Je vous envoie le bon de commande. »
- **Nadia Brousse** — Diététicienne
  - Comment il/elle parle : Rigoureuse, vérifie chaque fiche technique.
  - Tics : « Tu me mets la même chose que mardi. » · « Comme d'habitude. »

## Ce qu'ils achètent et comment

Commande une fois par semaine, en général 3 jours avant entre 9h et 11h, surtout par e-mail et téléphone. Produits habituels : paleron de bœuf PAD, épaule de veau désossée, steak haché surgelé 15 % 100 g (carton 5 kg), sauté de bœuf surgelé (dés 30 g), longe de porc désossée, viande hachée fraîche 15 % MG, épaule d'agneau.

Sur les 90 derniers jours (9 commandes livrées) :

| Produit | Volume 90 j | Lignes | Dernier prix |
|---|---|---|---|
| Steak haché surgelé 15 % 100 g (carton 5 kg) (`prd_0055`) | 1 075,43 kg | 9 | 8,00 € |
| Épaule de veau désossée (`prd_0023`) | 474,89 kg | 7 | 15,77 € |
| Sauté de bœuf surgelé (dés 30 g) (`prd_0056`) | 545,72 kg | 5 | 11,31 € |
| Paleron de bœuf PAD (`prd_0017`) | 479,61 kg | 7 | 10,85 € |
| Viande hachée fraîche 15 % MG (`prd_0044`) | 351,11 kg | 6 | 11,20 € |
| Longe de porc désossée (`prd_0033`) | 395,71 kg | 4 | 6,88 € |
| Épaule d'agneau (`prd_0028`) | 180,28 kg | 4 | 14,10 € |
| Chair à saucisse (`prd_0047`) | 15,31 kg | 1 | 8,50 € |

Fiche CRM : _Commande à J-3 avant 11h par mail. Bœuf limousin pour le jeudi, surgelé pour le reste. Fermée pendant les vacances scolaires._

## Ce qui les agace

- Une facture sans numéro d'engagement
- Une substitution non validée par la diététicienne

## Historique marquant

- **13/03/2024** · qualité · Qualité : épaule de veau désossée
- **14/03/2024** · avoir · Avoir qualité : épaule de veau désossée
- **27/11/2024** · livraison · Chaîne du froid
- **28/05/2025** · livraison · Livraison en retard
- **10/11/2025** · paiement · Relance : FAC-2025-002953 échue
- **07/01/2026** · prix · Tarifs 2026
- **14/01/2026** · paiement · Relance : FAC-2025-003635 échue
- **04/02/2026** · réclamation · Rupture : épaule de veau désossée non livré
- **12/07/2026** · paiement · Relance : FAC-2026-001701 échue
- **11/09/2026** · paiement · Relance : FAC-2026-002437 échue
- **14/10/2026** · réclamation · Rupture : épaule de veau désossée non livré
- **12/11/2026** · paiement · Relance : FAC-2026-003084 échue

Historique complet : 28 événements (7 appel, 6 paiement, 4 visite, 2 qualité, 2 livraison, 2 compliment, 2 réclamation, 1 ouverture, 1 avoir, 1 prix).

## Dossiers ouverts aujourd'hui

- **12/11/2026 — Relance : FAC-2026-003084 échue** (`inv_011477`)
  Facture FAC-2026-003084 (21 823,64 € TTC) échue depuis le 31/10/2026 : relance du service facturation, mandat en cours selon la trésorerie.

## Comment leur parler

- Formel, tout par écrit.
- Toute modification passe par Nadia Brousse.

## Prix & groupe

Groupes : **Collectivités** (`collectivites`), **Marché public** (`marche-public`), **À surveiller** (`a-surveiller`).
Prix négociés (`clientPrices`, toujours prioritaires) : paleron de bœuf PAD 11,00 € (liste 11,60) ; steak haché surgelé 15 % 100 g (carton 5 kg) 8,00 € (liste 8,40).

Règles de prix qui peuvent s'appliquer :
- `prl_0004` Collectivités : −5 % sur les surgelés
- `prl_0006` Volume : quartier arrière −2 % dès 200 kg
- `prl_0008` Fêtes 2026 : chair à saucisse −8 % dès 10 kg

Dernières notes CRM :

- 20/10/2025, Sylvie (commerciale) : Marché public : prix au bordereau, révision au 1er janvier.
- 04/11/2025, Sylvie (commerciale) : Paiement par mandat administratif, 60 jours en pratique.
