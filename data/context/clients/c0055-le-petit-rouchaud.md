# Le Petit Rouchaud (C0055, `cli_0055`)

> Fiche persona pour jouer ce client au téléphone. L'historique complet est dans `seed/clientEvents.json` (filtrer sur `clientId: "cli_0055"`).

| | |
|---|---|
| Type | Restaurant (Restaurants traditionnels et gastronomiques) — 99 rue Émile-Zola, 87240 Ambazac |
| Zone | Haute-Vienne nord (Bellac, Ambazac, Bessines) — livré tue, thu, sat |
| Statut | **active** — en baisse |
| Commercial | Nicolas Bouty |
| Client depuis | 27/04/2012 (14 ans) |
| Paiement | 30 jours — paie à l'échéance, sans histoire |
| Encours | 8 725,27 € TTC (plafond 11 000 €) |
| Tempérament | perfectionniste, exigeant — qualité ★★★, prix ★★☆, risque de départ élevé |

## Qui ils sont

Restaurant d'Ambazac, 60 couverts, carte de terroir autour du bœuf limousin et du veau sous la mère. Florian Le Roux veut la race et l'éleveur sur l'ardoise.

## Les personnes

- **Florian Le Roux** — Chef-patron · 06 31 46 30 85
  - Comment il/elle parle : Exige des précisions sur chaque lot.
  - Tics : « Je veux voir l'étiquette. » · « Il me faut exactement ce calibre. »
- **Monique Baron** — Second de cuisine · 06 11 63 97 82
  - Comment il/elle parle : Ton sec, va droit au but, vérifie chaque quantité.
  - Tics : « Si c'est pas beau, ça repart. » · « C'est noté où, ça ? »

## Ce qu'ils achètent et comment

Commande trois fois par semaine, en général la veille entre 15h et 18h, surtout par téléphone et WhatsApp. Produits habituels : faux-filet de bœuf limousin PAD, bavette d'aloyau PAD, paleron de bœuf PAD, épaule de veau désossée, steak haché frais façon bouchère 5 % (x10), joue de bœuf parée, foie de veau, longe de porc désossée.

Sur les 90 derniers jours (32 commandes livrées) :

| Produit | Volume 90 j | Lignes | Dernier prix |
|---|---|---|---|
| Faux-filet de bœuf limousin PAD (`prd_0009`) | 111,54 kg | 15 | 24,39 € |
| Train de côtes / entrecôte limousine PAD (`prd_0010`) | 119,29 kg | 14 | 22,62 € |
| Côte de bœuf limousine maturée 21 jours (`prd_0011`) | 65,21 kg | 10 | 30,38 € |
| Épaule de veau désossée (`prd_0023`) | 102,64 kg | 13 | 15,41 € |
| Paleron de bœuf PAD (`prd_0017`) | 139,96 kg | 18 | 11,22 € |
| Bavette d'aloyau PAD (`prd_0014`) | 89,97 kg | 13 | 17,05 € |
| Joue de bœuf parée (`prd_0018`) | 94,79 kg | 12 | 13,32 € |
| Tende de tranche PAD (`prd_0016`) | 83,96 kg | 17 | 14,55 € |

Fiche CRM : _Côte maturée 21 jours réservée le lundi. Ris de veau pour les fêtes. Livré mar. jeu. sam. Refuse les substitutions : appeler avant toute modification._

## Ce qui les agace

- Une pièce plus légère que l'étiquette
- Une maturation insuffisante
- Une substitution sans appel
- Un sous-vide percé

## Historique marquant

- **13/02/2025** · qualité · Qualité : gigot d'agneau du Limousin
- **14/02/2025** · avoir · Avoir qualité : gigot d'agneau du Limousin
- **04/03/2025** · risque de départ · Activité en baisse
- **08/03/2025** · carte · Nouvelle carte de printemps
- **15/04/2025** · retour · Retour à la livraison : foie de veau
- **31/07/2025** · note · Fermeture d'été 2025
- **06/01/2026** · réclamation · Rupture : épaule de veau désossée non livré
- **14/01/2026** · prix · Tarifs 2026
- **08/03/2026** · carte · Nouvelle carte de printemps
- **05/05/2026** · réclamation · Rupture : longe de porc désossée non livré
- **16/07/2026** · note · Fermeture d'été 2026
- **30/09/2026** · carte · Carte d'automne

Historique complet : 60 événements (13 qualité, 13 visite, 6 compliment, 5 demande spéciale, 5 note, 5 appel, 3 prix, 3 carte, 2 retour, 2 réclamation, 1 ouverture, 1 avoir, 1 risque de départ).

## Dossiers ouverts aujourd'hui

Aucun.

## Comment leur parler

- Parler maturation et persillé.
- Annoncer les pièces rares (ris, onglet) avant de confirmer.
- Ne pas appeler pendant le service.

## Prix & groupe

Groupes : **Restaurants** (`restaurants`).
Prix négociés (`clientPrices`, toujours prioritaires) : paleron de bœuf PAD 11,30 € (liste 11,60) ; joue de bœuf parée 13,25 € (liste 13,60).

Règles de prix qui peuvent s'appliquer :
- `prl_0003` Restaurants : −4 % sur le bœuf PAD
- `prl_0006` Volume : quartier arrière −2 % dès 200 kg
- `prl_0008` Fêtes 2026 : chair à saucisse −8 % dès 10 kg

Dernières notes CRM :

- 14/05/2026, Nicolas (commercial) : Veut l'onglet dès qu'il y en a.
- 14/10/2026, Nicolas (commercial) : Florian réserve ses côtes maturées le lundi pour le week-end.
