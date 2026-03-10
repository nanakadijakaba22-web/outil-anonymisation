# Classification des données selon la Loi 25 (Québec)

L'outil d'anonymisation intègre une logique de détection automatique conforme à la **Loi 25 du Québec**. Cette classification permet d'identifier les renseignements personnels nécessitant un niveau de protection élevé.

## Catégories de Données Sensibles

Conformément à l'Article 110 et aux orientations gouvernementales, les renseignements suivants sont classés comme **Sensibles** par nature, indépendamment de leur capacité à identifier directement une personne :

1.  **Renseignements financiers** : Salaires, scores de crédit, soldes bancaires, dettes.
2.  **Renseignements génétiques ou biométriques** : Empreintes digitales, ADN, reconnaissance faciale.
3.  **Renseignements concernant la santé** : Diagnostics, antécédents médicaux, traitements, dossiers médicaux.
4.  **Vie sexuelle ou orientation sexuelle** : Orientation, vie privée.
5.  **Convictions religieuses ou philosophiques** : Religions, croyances, appartenance à des ordres religieux.
6.  **Opinions politiques** : Affiliations à des partis, intentions de vote.
7.  **Origine ethnique ou raciale** : Race, ethnie, origine ancestrale.

## Priorité de Classification

Le moteur de détection applique la hiérarchie de priorité suivante pour garantir la sécurité des données :

1.  **Identifiant Direct** (Priorité Maximale) : NAS, Courriel, Nom complet, No de téléphone.
2.  **Renseignement Sensible (Loi 25)** : Les 7 catégories citées ci-dessus.
3.  **Quasi-identifiant** : Code postal, Date de naissance, Genre.
4.  **Non-sensible** : Informations générales de l'entreprise ou produits.

## Justifications

Chaque classification est accompagnée d'une justification explicite citant la Loi 25 lorsque applicable, permettant aux utilisateurs de comprendre la base légale de la suggestion d'anonymisation.
