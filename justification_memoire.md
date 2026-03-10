# Justification Méthodologique et Technique de l'Outil d'Anonymisation (Annoy)

Ce document présente une analyse exhaustive et rigoureuse des fondements scientifiques, techniques et juridiques de l'outil Annoy. Il détaille chaque étape du pipeline de données, les algorithmes utilisés, les paramètres de décision et les sources académiques/réglementaires appuyant ces choix.

---

## Chapitre 1 : Phase d'Ingestion et Pré-traitement des Données

L'ingestion des données constitue le socle de la fiabilité de l'outil. Annoy ne se contente pas de lire un fichier ; il analyse sa structure pour prévenir les biais d'analyse.

### 1.1 Détection Automatique de la Structure (Encoding & Sniffing)
L'outil implémente un mécanisme de détection multi-niveaux pour garantir l'intégrité des caractères :
- **Algorithme d'Encodage** : Essai itératif sur les formats `UTF-8`, `Latin-1` et `CP1252`.
- **Sniffing de Délimiteur** : Utilisation de `csv.Sniffer` sur les 4096 premiers octets pour identifier le dialecte (` , `, ` ; `, ` | `, ` \t `).
- **Fondement Scientifique** : Cette approche repose sur le principe de **"Multi-Hypothesis Parsing"** (Mühlbauer & Boncz, 2017), nécessaire pour transformer des données CSV hétérogènes en structures tabulaires fiables. L'identification précise du dialecte et de l'encodage est une étape critique de **Qualité des Données** (Rahm & Do, 2000), car un mauvais typage d'encodage peut altérer des caractères pivots (ex: accents), rendant les regex de détection inopérantes et créant des risques de ré-identification par "bruit structurel" (Gimenez-García & Alambiaga, 2024).

### 1.2 Élagage des Données Creuses (Sparsity Cleanup)
Annoy applique un seuil de **vacuité de 95%** (Sparsity Threshold). 
- **Logique** : Toute colonne ayant plus de 95% de valeurs nulles est automatiquement supprimée.
- **Fondement Scientifique** : Les données creuses agissent comme des "signatures uniques" (outliers). Selon de Montjoye (2013), la rareté de l'information facilite la ré-identification par croisement avec des bases externes.

---

## Chapitre 2 : Identification et Classification (Conformité Loi 25)

La classification repose sur une hiérarchie de preuves (heuristiques, regex, statistiques, IA).

### 2.1 Heuristiques et Pattern Matching
L'outil utilise une bibliothèque de **Regex spécialisées** pour le contexte québécois et canadien :
- **NAS (Social Insurance Number)** : Regex couplée à l'**algorithme de Luhn** (checksum modulo 10).
  - *Justification Scientifique* : Ce mécanisme de contrôle de validité par somme de contrôle est le standard technique utilisé par **Emploi et Développement social Canada** pour garantir l'intégrité des dossiers et prévenir les erreurs de saisie.
- **RAMQ** : Format `[A-Z]{4} \d{4} \d{4}`.
- **Codes Postaux (CA)** : Format `LNL NLN`.
  - *Base Réglementaire* : Ces formats suivent les normes strictes de la **RAMQ** et de **Postes Canada**, permettant une identification granulaire sans extraction de contenu textuel libre.

### 2.2 Analyse Heuristique des Noms de Colonnes
Annoy utilise un dictionnaire de mots-clés normalisés (minuscules, sans accents) en français et anglais pour classer les colonnes en quatre catégories :
#### Catégories de Données Sensibles (Loi 25)
L'outil identifie précisément les 7 catégories de renseignements personnels sensibles définies par la Loi 25 du Québec :

1. **Financier** (`financial`) : Informations bancaires, revenus, transactions.
2. **Génétique ou biométrique** (`genetic_or_biometric`) : Empreintes, ADN, scans rétiniens.
3. **Santé** (`health`) : Diagnostics, dossiers médicaux, traitements.
4. **Vie sexuelle ou orientation sexuelle** (`sexual_life_or_orientation`) : Préférences et identité.
5. **Convictions religieuses ou philosophiques** (`religious_or_philosophical_beliefs`) : Appartenance religieuse, écoles de pensée.
6. **Opinions politiques** (`political_opinions`) : Appartenance à des partis, votes, engagements.
7. **Origine ethnique ou raciale** (`ethnic_or_racial_origin`) : Ascendance, groupes culturels.

| Catégorie | Poids | Impact (NIST) | Justification Technique | Source |
| :--- | :--- | :--- | :--- | :--- |
| **Identifiants Directs** | **40** | Critique | Identification immédiate (probabilité 1.0). | Sweeney (2002) |
| **Quasi-identifiants** | **25** | Élevé | Requièrent une liaison externe (*Linkability*). | Cavoukian (2009) |
| **Données Sensibles** | **20** | Modéré | Risque de préjudice sans identification directe (Loi 25). | G29 (2014) |
| **Données Non-Sensibles** | **0** | Négligeable | Aucun impact sur la vie privée. | Standard |

- **Fondement Théorique** : Cette classification s'appuie sur les travaux de **Sweeney (2002)**. Les identifiants directs permettent une ré-identification immédiate, tandis que les quasi-identifiants (ex: code postal, date de naissance) peuvent être combinés pour désanonymiser un individu.

### 2.3 Approche Hybride : Intelligence Artificielle (Ollama)
Pour les colonnes dont la confiance heuristique est **inférieure à 80%**, l'outil sollicite un modèle de langage (LLM) local via Ollama. 
- **Modèle de Référence** : Cette architecture s'inspire du framework **RECAP** (*Regex and Context-Aware Prompting*), qui combine la précision déterministe des expressions régulières pour les formats fixes et la puissance sémantique des LLM pour les données semi-structurées ou ambiguës.
- **Politique de Sécurité (Conservative Classification)** : En cas de divergence entre les méthodes, l'outil retient la classification la plus protectrice. Ce principe de **"Privacy as the Default"** (Cavoukian, 2009) garantit qu'aucune donnée potentiellement sensible ne soit traitée comme publique par défaut.

---

## Chapitre 3 : Évaluation Mathématique des Risques (Critères G29)

Conformément à l'**Avis 05/2014 (WP 216)** du Groupe de Travail Article 29, l'outil évalue le risque selon trois critères.

### 3.1 Individualisation (Singling-out)
Mesurée par le **k-anonymat** (Sweeney, 2002).
- **Méthode** : Calcul de la taille du plus petit groupe d'équivalence sur les quasi-identifiants ($QI$).
- **Score d'Individualisation** : Corrélation directe avec le pourcentage d'enregistrements violant le seuil de $k=5$.
- **Seuils Techniques** :
- **Identifié comme Risque Élevé** si plus de **15%** des combinaisons sont uniques ou quasi-uniques.
- **Standard Industriel** : $k \ge 5$ (Acceptable), recommandé $k \ge 10$ pour les données sensibles.

### 3.2 Corrélation (Linkability)
Mesurée par le **Ratio d'Unicité** des colonnes susceptibles d'être des clés de jointure.
- **Seuil d'Alerte** : Un score supérieur à **20%** de colonnes liables déclenche un niveau de risque "Élevé".

### 3.3 Inférence (Inference)
Mesurée par la **Matrice de Corrélation de Pearson** pour les données numériques.
- **Algorithme** : Identification des paires de variables ayant une corrélation $|r| > 0.7$.
- **Seuil d'Alerte** : Si plus de **25%** des paires possibles présentent une corrélation forte, le risque d'inférence est jugé critique.

### 3.4 Formule du Score Global

Le score global de risque est calculé à l’aide d’un modèle de somme pondérée (Weighted Sum Model – WSM), une méthode classique d’analyse multicritère permettant de combiner plusieurs dimensions du risque en un indicateur unique (Triantaphyllou, 2000). Cette approche est cohérente avec les cadres d’évaluation des risques recommandés dans les standards du NIST SP 800-30.

La formule générale du modèle est la suivante :

$$Score = \sum_{i=1}^{n} w_i \times S_i$$

où :
- $S_i$ représente le score du critère de risque $i$
- $w_i$ représente le poids attribué à ce critère
- $n$ représente le nombre total de critères évalués.

Dans le cadre de cet outil d’anonymisation, trois dimensions principales du risque de réidentification sont considérées :
- le risque d’individualisation ($S_{indiv}$)
- le risque de corrélation ($S_{corr}$)
- le risque d’inférence ($S_{inf}$)

La formule opérationnelle utilisée par l’outil est donc :

$$Score = (S_{indiv} \times 0.40) + (S_{corr} \times 0.35) + (S_{inf} \times 0.25)$$

Le score final est exprimé en pourcentage sur une échelle allant de 0 % à 100 %.

La somme des pondérations est égale à 100 %, ce qui garantit que chaque dimension du risque contribue proportionnellement à l’évaluation globale, tout en accordant une importance plus élevée au risque d’identification directe.

### 3.5 Seuil de conformité

Un jeu de données est considéré comme conforme aux exigences d’anonymisation de la Loi 25 lorsque :

$$Score < 20\%$$

Ce seuil correspond à un niveau de risque résiduel faible, cohérent avec les approches de classification du risque proposées dans les cadres de gestion des risques (NIST SP 800-30) et avec les recommandations méthodologiques en matière de dé-identification des données.

### 3.6 Axiome d’honnêteté et risque résiduel

Conformément aux travaux de Machanavajjhala et al. (2007), qui démontrent que l’anonymisation parfaite est théoriquement impossible, l’outil introduit un **plancher de risque résiduel de 0.1%**.

Ce mécanisme vise à éviter qu’un jeu de données soit artificiellement considéré comme présentant un risque nul, ce qui serait irréaliste dans un contexte où des attaques par connaissances auxiliaires peuvent toujours exister.

Ainsi, même après application des mécanismes d’anonymisation, un risque minimal est maintenu afin de refléter la réalité des attaques potentielles sur les données anonymisées.

Le jeu de données est finalement jugé « Conforme Loi 25 » lorsque le score global de risque demeure inférieur au seuil de 20%.

## Chapitre 4 : Mécanismes d’Anonymisation

### 4.1 Stratégies de Généralisation

La généralisation consiste à réduire la précision des données afin de diminuer l’unicité des enregistrements et limiter les risques de réidentification. Cette approche constitue un mécanisme fondamental des techniques de k-anonymat et des méthodes de dé-identification des données.

**Intervalle numérique.**
Les valeurs numériques sont transformées en intervalles, puis représentées par le point milieu de la tranche correspondante. Cette transformation permet de préserver une information statistique tout en réduisant la granularité des données. Cette approche est couramment utilisée dans les techniques de généralisation associées au k-anonymat (Sweeney, 2002). Référence : Latanya Sweeney.

**Dates.**
Les dates sont tronquées à l’année uniquement, en supprimant le mois et le jour. Les dates complètes étant des quasi-identifiants puissants, cette réduction de granularité temporelle permet de limiter les risques de réidentification. Cette pratique est cohérente avec les recommandations du National Institute of Standards and Technology dans le document NISTIR 8053 – De-Identification of Personal Information.

**Textes.**
Les attributs textuels sont traités soit par généralisation par préfixe (conservation des N premières lettres), soit par suppression lorsque la valeur reste trop spécifique ou trop courte. Cette approche correspond aux techniques de masquage partiel des chaînes de caractères utilisées dans les méthodes de dé-identification (El Emam, 2013). Référence : Khaled El Emam.

### 4.2 Escalade Automatique (Anonymisation Itérative)

Afin de garantir un niveau suffisant de protection, l’outil applique un processus d’anonymisation itérative. Après chaque transformation, la condition de k-anonymat (k = 10) est vérifiée. Si cette condition n’est pas satisfaite, un mécanisme d’escalade hiérarchique est déclenché.

Le concept de k-anonymat a été introduit par Latanya Sweeney (Sweeney, 2002) et vise à garantir que chaque individu soit indistinguable d’au moins k−1 autres individus dans le jeu de données. Dans la littérature sur l’anonymisation, des valeurs de k comprises entre 5 et 10 sont généralement recommandées afin d’atteindre un compromis entre protection de la vie privée et utilité analytique des données. Les travaux de Khaled El Emam (El Emam, 2013) indiquent notamment que k ≥ 5 constitue un minimum acceptable dans les processus de dé-identification. Dans ce contexte, le choix de k = 10 représente une approche plus conservatrice visant à renforcer la protection contre l’individualisation.

Cette approche repose sur le principe des hiérarchies de généralisation, largement utilisées dans les algorithmes d’anonymisation (Samarati, 2001). Référence : Pierangela Samarati.

**Localisation.**
Les informations géographiques sont généralisées progressivement selon la hiérarchie :
Ville → Comté → Province → Suppression.

**Code postal.**
Le code postal est progressivement réduit :
3 premiers caractères → 2 premiers caractères → Suppression.
Cette approche s’inspire des pratiques de diffusion statistique utilisées par le US Census Bureau afin de réduire la précision géographique.

**Coordonnées GPS.**
Les coordonnées géographiques sont généralisées par réduction progressive de la précision :
Arrondi à 1 décimale → Arrondi à 0 décimale → Suppression.
La réduction de précision spatiale permet de limiter les attaques de réidentification basées sur la localisation (Narayanan & Shmatikov, 2008). Référence : Arvind Narayanan.

### 4.3 Confidentialité Différentielle (Differential Privacy)

Pour certaines variables numériques sensibles, l’outil implémente un mécanisme de confidentialité différentielle basé sur le mécanisme de Laplace, introduit par Cynthia Dwork (Dwork, 2006).

**Paramètre ε (epsilon).**
Le paramètre de confidentialité ε = 1.0 est utilisé par défaut, représentant un compromis entre protection de la vie privée et utilité analytique des données. Des valeurs similaires sont utilisées dans certains systèmes statistiques, notamment dans les mécanismes de confidentialité différentielle du US Census Bureau.

**Modèle mathématique.**
Le mécanisme ajoute un bruit aléatoire calibré selon la distribution de Laplace :

$$Laplace(0, \frac{\Delta f}{\epsilon})$$

où $\Delta f$ représente la sensibilité de la requête (variation maximale possible lorsque les données d’un individu sont modifiées) et $\epsilon$ contrôle le niveau de protection de la confidentialité.

---

## Chapitre 5 : Audit, Vérification et Respect du Droit

### 5.1 Vérification Post-Anonymisation
Une fois le traitement terminé, l'outil effectue un **second scan (Post-Audit)** :
- Validation qu'aucun identifiant direct n'est présent (Suppression forcée à l'export).
- Re-calcul du score de risque sur le fichier de sortie.

### 5.2 Traçabilité (Audit Trail)
Chaque opération génère des métadonnées stockées dans la base :
- `TransformationLog` : Trace chaque modification par ligne/colonne.
- `SuppressedColumn` : Registre des données jugées trop risquées et supprimées.
- `VerificationLog` : Preuve de conformité signée temporellement.

### 5.3 Rapport d’anonymisation et Preuve de Conformité

Le rapport généré après le processus d’anonymisation constitue un élément essentiel du mécanisme de conformité aux exigences de la Loi 25 du Québec sur la protection des renseignements personnels. En effet, la réglementation exige que l’organisation soit en mesure de démontrer que les données ont été traitées de manière à réduire le risque de réidentification à un niveau très faible avant toute utilisation secondaire.

Dans cette optique, le rapport d’anonymisation produit par l’outil documente de manière structurée l’ensemble de l’analyse effectuée sur le dataset. Il présente d’abord un sommaire exécutif indiquant le niveau global de risque et la décision de conformité, puis une évaluation détaillée des trois critères de risque reconnus dans la littérature scientifique et par les autorités européennes, à savoir l’individualisation, la corrélation (ou liaison) et l’inférence, tels que définis dans l’Opinion 05/2014 du Groupe de travail Article 29 sur les techniques d’anonymisation.

Le rapport inclut également la détection des identifiants directs, quasi-identifiants et données sensibles, afin de documenter les catégories d’informations présentes dans le dataset et les transformations appliquées. Des analyses statistiques complémentaires sont aussi produites, notamment la distribution des variables, la détection de valeurs aberrantes et l’analyse de corrélation, afin de vérifier que l’anonymisation réduit efficacement les risques tout en conservant une utilité analytique minimale des données.

L’objectif de ce rapport est donc double : assurer la traçabilité du processus d’anonymisation et fournir une preuve documentaire que le risque résiduel de réidentification est faible, ce qui correspond aux principes reconnus dans les travaux scientifiques sur l’anonymisation des données (Sweeney, 2002 ; Machanavajjhala et al., 2007 ; El Emam, 2013) ainsi qu’aux recommandations du Groupe de travail Article 29 (2014) relatives à l’évaluation du risque dans les processus d’anonymisation.

---

## Chapitre 6 : Validation Expérimentale (Cas d'utilisation "Parents")

Les variables présentées dans les visualisations du rapport d’anonymisation ont été sélectionnées en raison de leur importance pour l’évaluation du risque de réidentification et pour la préservation de l’utilité analytique du jeu de données.

Certaines colonnes, telles que BIRTHDATE, RACE, ETHNICITY et GENDER, sont identifiées comme quasi-identifiants, c’est-à-dire des attributs qui, lorsqu’ils sont combinés avec d’autres informations externes, peuvent permettre d’isoler ou de réidentifier un individu. La littérature scientifique montre que des attributs démographiques comme la date de naissance, le genre ou la localisation peuvent fortement contribuer à la réidentification des individus dans un dataset (Sweeney, 2002).

Par ailleurs, certaines variables numériques telles que HEALTHCARE_EXPENSES ou HEALTHCARE_COVERAGE sont également analysées afin de vérifier que les transformations appliquées lors du processus d’anonymisation (généralisation, suppression ou ajout de bruit) ne détruisent pas la structure statistique des données. Cette analyse permet d’évaluer le compromis entre protection de la vie privée et utilité des données (privacy-utility trade-off), principe largement reconnu dans la littérature sur l’anonymisation des données (El Emam, 2013 ; Article 29 Working Party, 2014).

Les graphiques de distribution permettent également de détecter d’éventuelles valeurs aberrantes (outliers) et de vérifier l’absence de corrélations fortes pouvant favoriser des attaques par inférence, conformément aux recommandations du Groupe de travail Article 29 dans l’Opinion 05/2014 sur les techniques d’anonymisation.

---

## Bibliographie Sélective (APA)

- **Groupe de travail Article 29 (G29)**. (2014). *Avis 05/2014 sur les techniques d'anonymisation*, adopté le 10 avril 2014, WP 216.
- **Cavoukian, A. (2009)**. *Privacy by Design: The 7 Foundational Principles*. Information and Privacy Commissioner of Ontario, Canada.
- **de Montjoye, Y.-A., et al. (2013)**. *Unique in the Crowd: The privacy bounds of human mobility*. Scientific Reports.
- **Dwork, C. (2006)**. *Differential Privacy*. ICALP.
- **El Emam, K. (2013)**. *Guide to the De-identification of Personal Health Information*.
- **Machanavajjhala, A., Kifer, D., Gehrke, J., & Venkitasubramaniam, M. (2007)**. *l-diversity: Privacy beyond k-anonymity*. ACM TKDD.
- **Narayanan, A., & Shmatikov, V. (2008)**. *Robust De-anonymization of Large Sparse Datasets*. IEEE Security & Privacy.
- **NIST SP 800-30 (2012)**. *Guide for Conducting Risk Assessments*.
- **NIST SP 800-188 (2023)**. *De-Identifying Government Datasets*.
- **Samarati, P. (2001)**. *Protecting respondents’ privacy in microdata release through aggregation and generalization*. IEEE TKDE.
- **Sweeney, L. (2002)**. *k-anonymity: A model for protecting privacy*.
- **Triantaphyllou, E. (2000)**. *Multi-criteria Decision Making Methods: A Comparative Study*.
- **Gimenez-García, J. M., & Alambiaga, C. G. (2024)**. *Detecting CSV File Dialects by Table Uniformity Measurement and Data Type Inference*.
- **Mühlbauer, M. D. J. H., & Boncz, P. A. (2017)**. *Multi-Hypothesis CSV Parsing*. 
- **Rahm, E., & Do, H. H. (2000)**. *Data cleaning: Problems and current approaches*. IEEE Data Engineering Bulletin.
- **Gouvernement du Québec (2024)**. *Règlement sur l'anonymisation des renseignements personnels*.
- **Article 29 Working Party (2014)**. *Opinion 05/2014 on Anonymisation Techniques*.
