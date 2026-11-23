# Prix et crédit

## Prix de vente

- Carcasses et quartiers : prix indexé sur la cotation hebdomadaire (cadran de Limoges) publiée le lundi, plus la plus-value Label Rouge.
- Pièces PAD, abats, élaborés et charcuterie : tarif mensuel, envoyé le 1er.
- Facturation au poids réel pesé à l'expédition ; le BL indique le poids et le numéro de lot.
- Franco 200 € HT ; en dessous, 15 € de livraison (sauf marchés publics).
- Seuls Jean-Louis et les commerciaux peuvent accorder une remise ; Coralie applique le tarif.

Ordre de résolution : prix négocié client > règle de prix (client, puis groupe) > prix liste.

## Groupes de clients

- **Bouchers** (`bouchers`) : Boucheries artisanales : carcasses, quartiers, veaux et agneaux entiers.
- **Restaurants** (`restaurants`) : Restaurants traditionnels et gastronomiques : pièces PAD, maturé, abats.
- **GMS** (`gms`) : Rayons boucherie de supermarchés : contrat indexé sur la cotation.
- **Collectivités** (`collectivites`) : Cuisines centrales, EHPAD : clause locale, surgelé, J-3.
- **Marché public** (`marche-public`) : Prix au bordereau, mandat administratif.
- **Traiteurs** (`traiteurs`) : Charcutiers-traiteurs et banquets.
- **Brasseries** (`brasseries`) : Brasseries et routiers : plat du jour.
- **Auberges** (`auberges`) : Hôtels et auberges touristiques, saisonniers.
- **Grands comptes** (`grands-comptes`) : Les plus gros chiffres d'affaires des 12 derniers mois, suivis par la direction.
- **À surveiller** (`a-surveiller`) : Retards de paiement, litiges ou compte bloqué : vérifier l'encours avant toute commande.
- **Clients perdus** (`perdus`) : Plus de commande depuis plusieurs mois (partis à la concurrence ou fermés) : à reconquérir.

## Règles de prix

- `prl_0001` Bouchers : −3 % sur les carcasses et quartiers, du 01/01/2025
- `prl_0002` GMS : coût + 24 % sur les carcasses, du 01/01/2026 — Contrat cotation + marge fixe.
- `prl_0003` Restaurants : −4 % sur le bœuf PAD, du 01/03/2025
- `prl_0004` Collectivités : −5 % sur les surgelés, du 01/01/2025
- `prl_0005` Traiteurs : −4 % sur le porc, du 01/01/2025
- `prl_0006` Volume : quartier arrière −2 % dès 200 kg, du 01/01/2024
- `prl_0007` Pâques 2026 : agneau entier −5 % dès 3 carcasses (inactive), du 20/03/2026 au 05/04/2026
- `prl_0008` Fêtes 2026 : chair à saucisse −8 % dès 10 kg, du 01/12/2026 au 31/12/2026 — Farces de Noël.

## Crédit et relances

- Plafond d'encours par client (TTC) ; au-delà, validation par Josette.
- Relance à J+5 par mail, J+15 par téléphone, J+30 courrier ; blocage à J+60 ou au deuxième prélèvement rejeté.
- Déblocage : règlement d'au moins 50 % de l'échu et échéancier validé par Jean-Louis.
- Saisonniers : paiement de la saison accepté jusqu'au 31 octobre, au-delà blocage.
- Marchés publics : pas de relance avant J+30 (mandat administratif).

## Clients à surveiller (au 24/11)

- Cuisine centrale de Saint-Junien (cli_0004) : mandat administratif : paiement lent mais sûr, 1 facture échue pour 21 823,64 € TTC.
- Boucherie Lacour de Tulle (cli_0005) : mauvais payeur, compte à risque, 13 facture échues pour 104 548,27 € TTC — **bloqué**.
- Le Relais du Lac de Vassivière (cli_0006) : mauvais payeur, compte à risque, 3 facture échues pour 49 496,43 € TTC — **bloqué**.
- Brasserie Le Saint-Martial (cli_0008) : paie en retard (3 à 6 semaines), mais finit par payer.
- Intermarché Indépendant d'Ussel (cli_0012) : paie à l'heure mais déduit ce qu'il conteste, 2 facture échues pour 2 785,48 € TTC.
- Le Petit Roger (cli_0016) : paie en retard (3 à 6 semaines), mais finit par payer, 3 facture échues pour 2 666,38 € TTC.
- Les Saveurs de Panazol (cli_0021) : paie en retard (3 à 6 semaines), mais finit par payer, 1 facture échue pour 1 264,25 € TTC.
- Les Saveurs d'Uzerche (cli_0030) : paie en retard (3 à 6 semaines), mais finit par payer, 3 facture échues pour 4 200,40 € TTC.
- Boucherie Serge et Fils (cli_0032) : paie en retard (3 à 6 semaines), mais finit par payer, 6 facture échues pour 20 360,17 € TTC.
- Maison Hubert (cli_0036) : paie en retard (3 à 6 semaines), mais finit par payer, 5 facture échues pour 10 409,01 € TTC.
- Rey Traiteur (cli_0039) : paie à l'heure mais déduit ce qu'il conteste, 1 facture échue pour 183,25 € TTC.
- Super Proxi Les Casseaux (cli_0044) : paie à l'heure mais déduit ce qu'il conteste, 1 facture échue pour 2 018,40 € TTC.
- EHPAD Les Bleuets (cli_0045) : mandat administratif : paiement lent mais sûr, 1 facture échue pour 12 677,32 € TTC.
- Boucherie-Charcuterie Leroux (cli_0046) : mauvais payeur, compte à risque, 14 facture échues pour 118 341,22 € TTC — **bloqué**.
- Maison Desbordes (cli_0049) : paie à l'heure mais déduit ce qu'il conteste.
