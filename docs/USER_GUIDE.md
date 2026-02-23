# Guide Utilisateur - Annoy

## Guide complet d'utilisation de l'outil d'anonymisation Loi 25

---

## Table des matières

1. [Introduction](#introduction)
2. [Démarrage rapide](#démarrage-rapide)
3. [Interface utilisateur](#interface-utilisateur)
4. [Workflow complet](#workflow-complet)
5. [Comprendre les résultats](#comprendre-les-résultats)
6. [Meilleures pratiques](#meilleures-pratiques)
7. [FAQ](#faq)

---

## Introduction

**Annoy** est un outil d'anonymisation de données conçu pour aider les organisations québécoises à se conformer à la **Loi 25** sur la protection des renseignements personnels.

### À qui s'adresse cet outil?

- **Responsables de la protection des données** (DPO)
- **Analystes de données**
- **Développeurs** traitant des données personnelles
- **Organisations** soumises à la Loi 25

### Que fait Annoy?

1. **Détecte** automatiquement les données sensibles dans vos fichiers CSV
2. **Anonymise** les données selon 4 techniques professionnelles
3. **Évalue** le niveau de risque selon 3 critères de la Loi 25
4. **Génère** un rapport PDF de conformité

---

## Démarrage rapide

### Installation (5 minutes)

```bash
# 1. Cloner le projet
git clone <repository-url>
cd annoy

# 2. Démarrer l'application
docker-compose up -d

# 3. Accéder à l'interface
# Frontend: http://localhost:3000
# API: http://localhost:8000
# Documentation API: http://localhost:8000/docs
```

### Premier test (2 minutes)

1. Ouvrir http://localhost:3000
2. Glisser-déposer un fichier CSV
3. Suivre le workflow guidé
4. Télécharger le CSV anonymisé et le rapport PDF

---

## Interface utilisateur

### Page 1: Upload de fichier

**Objectif**: Téléverser votre fichier de données

**Étapes**:
1. Glissez-déposez votre fichier CSV (ou cliquez pour sélectionner)
2. Vérifiez les informations affichées (nom, taille)
3. Cliquez sur "Téléverser et analyser"

**Contraintes**:
- Format: CSV uniquement
- Taille maximale: 1 GB
- Encodage: UTF-8 recommandé

**Temps estimé**: < 5 secondes

---

### Page 2: Résultats de détection

**Objectif**: Visualiser les données sensibles détectées

**Ce que vous voyez**:

#### Cartes de résumé (en haut)
- 🔴 **Identifiants directs**: Données qui identifient directement une personne (NAS, email, nom)
- 🟠 **Quasi-identifiants**: Combinaison pouvant identifier (âge + code postal)
- 🔵 **Sensibles**: Informations financières, médicales
- 🟢 **Non-sensibles**: Données générales

#### Barre de risque global
- **< 20%**: Risque faible (possiblement conforme)
- **20-50%**: Risque moyen (anonymisation recommandée)
- **> 50%**: Risque élevé (anonymisation requise)

#### Liste des colonnes
Chaque colonne affiche:
- **Badge coloré**: Type de sensibilité
- **Score de confiance**: Fiabilité de la détection (0-100%)
- **Justification**: Pourquoi cette classification

**Actions disponibles**:
- "Nouveau fichier": Recommencer avec un autre fichier
- "Configurer l'anonymisation": Passer à l'étape suivante

**Temps estimé**: 1-2 minutes pour révision

---

### Page 3: Configuration de l'anonymisation

**Objectif**: Choisir comment anonymiser chaque colonne sensible

**Techniques disponibles**:

#### 1. 🎭 Masquage
**Quand l'utiliser**: Emails, téléphones, numéros de carte
**Exemple**: `jean@test.com` → `je**@te**.com`
**Paramètre**: Caractères visibles (0-10)

**Avantages**:
- ✅ Conserve le format
- ✅ Permet la validation (email reste reconnaissable)
- ✅ Rapide

**Inconvénients**:
- ⚠️ Ne garantit pas l'anonymat complet
- ⚠️ Peut être réversible avec des dictionnaires

---

#### 2. 📊 Généralisation
**Quand l'utiliser**: Âges, revenus, codes postaux, dates
**Exemple**: `75000` → `"75000-100000"`
**Paramètre**: Nombre de tranches (bins)

**Avantages**:
- ✅ Préserve l'utilité des données (analyses statistiques)
- ✅ Réduit fortement le risque
- ✅ Facile à comprendre

**Inconvénients**:
- ⚠️ Perte de précision
- ⚠️ Moins adapté pour des valeurs très dispersées

---

#### 3. 🗑️ Suppression
**Quand l'utiliser**: NAS, données ultra-sensibles
**Exemple**: Colonne NAS complètement retirée
**Paramètre**: Aucun

**Avantages**:
- ✅ Anonymat garanti
- ✅ Simple et efficace
- ✅ Conforme Loi 25

**Inconvénients**:
- ⚠️ Perte totale de l'information
- ⚠️ Peut limiter certaines analyses

---

#### 4. 🔑 confidentialité différentielle
**Quand l'utiliser**: Noms, prénoms, identifiants
**Exemple**: `Tremblay` → `PERSON_66D67C`
**Paramètre**: Préfixe personnalisé

**Avantages**:
- ✅ Cohérence garantie (même valeur = même valeur anonymisée)
- ✅ Permet le suivi longitudinal
- ✅ Réversible si besoin (avec clé secrète)

**Inconvénients**:
- ⚠️ Nécessite une gestion sécurisée de la clé
- ⚠️ Hash visible peut révéler des patterns

---

### Recommandations pré-sélectionnées

L'outil recommande automatiquement:

| Type de donnée | Technique recommandée | Raison |
|----------------|----------------------|---------|
| NAS, numéro sécurité | Suppression | Trop sensible |
| Nom, prénom | confidentialité différentielle | Cohérence nécessaire |
| Email, téléphone | Masquage | Format à préserver |
| Âge, revenu | Généralisation | Utilité statistique |
| Code postal | Généralisation | Localisation approximative |

**Vous pouvez modifier ces recommandations selon vos besoins!**

**Actions disponibles**:
- "Retour à la détection": Revoir les colonnes détectées
- "Lancer l'anonymisation": Appliquer la configuration

**Temps estimé**: 2-5 minutes pour configuration

---

### Page 4: Résultats et conformité

**Objectif**: Vérifier la conformité et télécharger les résultats

**Banner de conformité**:
- 🟢 **CONFORME**: Score < 20%, dataset utilisable en sécurité
- 🔴 **NON-CONFORME**: Score > 20%, anonymisation insuffisante

**Jauges de risque** (3 critères):

#### 1. Individualisation (40% du score)
**Question**: Peut-on isoler un individu dans le dataset?
- Mesure l'unicité des combinaisons de quasi-identifiants
- Exemple: Si âge + code postal + genre = unique → RISQUE ÉLEVÉ

#### 2. Corrélation (35% du score)
**Question**: Peut-on lier ces données à d'autres sources?
- Évalue le nombre de colonnes liables à des bases externes
- Exemple: Code postal + nom de ville → facilement corrélable

#### 3. Inférence (25% du score)
**Question**: Peut-on déduire des informations sensibles?
- Analyse les corrélations fortes entre colonnes
- Exemple: Si revenu fortement corrélé à âge → possibilité de déduction

**Recommandations**:
- Liste numérotée d'actions concrètes
- Suggestions d'améliorations si non-conforme

**Informations dataset**:
- Statistiques (lignes, colonnes)
- Score de risque final
- Statut de conformité

**Actions disponibles**:
- "Nouveau fichier": Recommencer
- "Télécharger le CSV": Export des données anonymisées
- "Rapport PDF Loi 25": Rapport de conformité complet

**Temps estimé**: 2-3 minutes pour révision

---

## Workflow complet

### Exemple pratique: Données bancaires

#### Étape 1: Préparation
```csv
id,nom,prenom,email,age,revenu,solde
1,Tremblay,Jean,jean@test.com,45,75000,15420.50
```

#### Étape 2: Upload et détection
- Upload: 1 seconde
- Détection identifie:
  - Directs: nom, prenom, email
  - Quasi: age
  - Sensibles: revenu, solde
- Score initial: 65% (NON-CONFORME)

#### Étape 3: Configuration
Configuration recommandée:
- nom → confidentialité différentielle (PERSON_*)
- prenom → confidentialité différentielle (PERSON_*)
- email → Masquage (2 chars)
- age → Généralisation (5 tranches)
- revenu → Généralisation (5 tranches)
- solde → Généralisation (5 tranches)

#### Étape 4: Anonymisation
Temps: 0.02 secondes
Résultat:
```csv
id,nom,prenom,email,age,revenu,solde
1,PERSON_66D67C,PERSON_71BC60,je**@te**.com,40-50,75000-80000,15000-16000
```

#### Étape 5: Validation
- Score final: 0.0% (CONFORME ✅)
- Individualisation: 0.0%
- Corrélation: 0.0%
- Inférence: 0.0%

#### Étape 6: Export
- CSV anonymisé téléchargé
- Rapport PDF généré (3 pages)

**Temps total: < 5 minutes**

---

## Comprendre les résultats

### Scores de confiance

| Score | Interprétation | Action |
|-------|----------------|--------|
| 90-100% | Très haute confiance | Confiance totale |
| 70-89% | Haute confiance | Généralement fiable |
| 50-69% | Confiance moyenne | Vérifier manuellement |
| < 50% | Faible confiance | Révision requise |

### Niveaux de risque

| Niveau | Score | Signification |
|--------|-------|---------------|
| FAIBLE | 0-20% | Conforme Loi 25 |
| MOYEN | 20-50% | Anonymisation recommandée |
| ÉLEVÉ | 50-100% | Anonymisation requise |

### Interprétation du rapport PDF

Le rapport PDF contient:

**Page 1: Page de titre**
- Statut de conformité (CONFORME/NON-CONFORME)
- Métadonnées du dataset
- Date d'analyse

**Page 2: Évaluation des risques**
- Tableau avec les 3 critères
- Scores et justifications
- Colonnes affectées

**Page 3: Détails et recommandations**
- Colonnes sensibles détectées
- Transformations appliquées (si anonymisé)
- Recommandations d'action

---

## Meilleures pratiques

### Avant l'anonymisation

1. **Sauvegardez vos données originales**
   - L'anonymisation est irréversible
   - Gardez une copie sécurisée des données sources

2. **Comprenez vos besoins**
   - Quelles analyses devez-vous faire?
   - Quelles colonnes sont essentielles?
   - Quel niveau de précision nécessaire?

3. **Nettoyez vos données**
   - Supprimez les colonnes inutiles avant upload
   - Vérifiez la cohérence des formats
   - Assurez-vous de l'encodage UTF-8

### Pendant l'anonymisation

1. **Révisez les détections**
   - Vérifiez que toutes les colonnes sensibles sont détectées
   - Ajustez manuellement si nécessaire

2. **Testez plusieurs configurations**
   - Commencez conservateur (plus d'anonymisation)
   - Ajustez progressivement si trop de perte de données

3. **Validez sur un échantillon**
   - Testez d'abord sur 100-1000 lignes
   - Vérifiez que le résultat répond à vos besoins

### Après l'anonymisation

1. **Vérifiez le score de conformité**
   - Visez < 20% pour être conforme
   - Documentez les décisions prises

2. **Conservez le rapport PDF**
   - Preuve de conformité pour audits
   - Documentation des mesures prises

3. **Testez l'utilité des données**
   - Vérifiez que vos analyses fonctionnent encore
   - Assurez-vous de la cohérence des résultats

---

## FAQ

### Questions générales

**Q: Mes données sont-elles sécurisées?**
R: Oui. Les données sont traitées localement sur votre serveur. Rien n'est envoyé à l'extérieur.

**Q: Puis-je anonymiser plusieurs fichiers à la fois?**
R: Non, un fichier à la fois. Cela garantit un meilleur contrôle de chaque anonymisation.

**Q: L'anonymisation est-elle réversible?**
R: Non, sauf pour la confidentialité différentielle si vous gardez la clé secrète. Les autres techniques sont irréversibles.

**Q: Quel format de fichier est supporté?**
R: Uniquement CSV pour le moment. Excel/XLSX sera ajouté dans une future version.

### Questions techniques

**Q: Quelle est la taille maximale de fichier?**
R: 1 GB par défaut (configurable dans .env avec MAX_UPLOAD_SIZE).

**Q: Combien de temps prend l'anonymisation?**
R: ~17 microsecondes par ligne. 5000 lignes = ~88ms.

**Q: Les performances se dégradent avec de gros fichiers?**
R: Non, linéaire. 50,000 lignes ≈ 880ms, 500,000 lignes ≈ 8.8s.

**Q: Puis-je modifier la configuration après anonymisation?**
R: Non. Vous devez recommencer avec le dataset original.

### Questions sur la Loi 25

**Q: Qu'est-ce que la Loi 25?**
R: La loi modernisant les dispositions législatives en matière de protection des renseignements personnels au Québec.

**Q: Un score de 0% garantit-il la conformité légale?**
R: C'est un excellent indicateur, mais consultez un expert juridique pour validation finale.

**Q: Dois-je anonymiser toutes les données?**
R: Non, seulement les données personnelles sensibles selon l'article 3.3 de la Loi 25.

**Q: Le rapport PDF est-il valide pour un audit?**
R: Oui, il documente les mesures prises conformément à l'article 63.1.

### Dépannage

**Q: L'upload échoue**
R: Vérifiez:
- Taille < 1 GB
- Format CSV (pas Excel)
- Encodage UTF-8
- Pas de caractères spéciaux dans le nom

**Q: Détection incorrecte**
R: C'est possible. L'outil fait de son mieux mais n'est pas parfait. Vérifiez manuellement les résultats.

**Q: Le PDF ne se télécharge pas**
R: Vérifiez que le dataset a été évalué (page résultats). Rafraîchissez la page si nécessaire.

**Q: L'application est lente**
R: Vérifiez les ressources Docker (CPU, RAM). Augmentez si nécessaire.

---

## Support et ressources

### Documentation
- Guide utilisateur: Ce document
- Documentation API: http://localhost:8000/docs
- Guide technique: `docs/TECHNICAL.md`

### Support
- Issues GitHub: <repository-url>/issues
- Email: support@annoy.local

### Ressources externes
- [Loi 25 - Texte complet](https://www.legisquebec.gouv.qc.ca/)
- [Commission d'accès à l'information du Québec](https://www.cai.gouv.qc.ca/)
- [Guide de la Loi 25 pour les entreprises](https://www.educaloi.qc.ca/)

---

**Version**: 1.0.0
**Dernière mise à jour**: 2025-12-31
**Auteur**: Équipe Annoy
