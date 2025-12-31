# Annoy - Outil d'Anonymisation de Données Conforme à la Loi 25

**Outil d'anonymisation de données personnelles pour la conformité à la Loi 25 du Québec**

[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688.svg)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-16.1-black)](https://nextjs.org)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org)
[![License](https://img.shields.io/badge/License-Proprietary-red.svg)]()

---

## 📋 Table des matières

- [Présentation](#présentation)
- [Fonctionnalités](#fonctionnalités)
- [Installation rapide](#installation-rapide)
- [Documentation API](#documentation-api)
- [Workflow complet](#workflow-complet)
- [Architecture](#architecture)
- [Statut du projet](#statut-du-projet)

---

## 🎯 Présentation

**Annoy** est un outil professionnel d'anonymisation de données conçu pour aider les organisations québécoises à se conformer à la **Loi 25** (modernisation des dispositions législatives en matière de protection des renseignements personnels).

L'outil analyse automatiquement les fichiers CSV, détecte les données sensibles, et applique des techniques d'anonymisation adaptées tout en évaluant le niveau de conformité selon trois critères de risque définis par la loi.

---

## ✨ Fonctionnalités Principales

### 1. 🔍 Détection Automatique de Données Sensibles

- Pattern matching intelligent (regex + heuristiques)
- Classification en 4 catégories selon la Loi 25
- Scores de confiance (0-100%)
- Justifications détaillées

**Types de données détectés:**
- ✅ **Identifiants directs**: NAS, email, téléphone, noms
- ✅ **Quasi-identifiants**: date de naissance, code postal, âge, genre
- ✅ **Données sensibles**: informations financières, médicales
- ✅ **Données non-sensibles**: informations générales

### 2. 🛡️ Anonymisation Multi-Technique

**4 techniques d'anonymisation:**

| Technique | Exemple | Usage |
|-----------|---------|-------|
| **Masquage** | `jean@test.com` → `je**@te**.com` | Emails, téléphones |
| **Généralisation** | `75000` → `"75000-100000"` | Revenus, âges |
| **Suppression** | Colonne NAS → Supprimée | Données très sensibles |
| **Pseudonymisation** | `Tremblay` → `PERSON_66D67C` | Noms (cohérence garantie) |

**Performance:** ~0.022s pour 10 lignes

### 3. 📊 Évaluation des Risques Loi 25

**3 critères d'évaluation:**

1. **Individualisation (40%)**: Peut-on isoler un individu?
2. **Corrélation (35%)**: Données liables à d'autres sources?
3. **Inférence (25%)**: Peut-on déduire des informations?

**Seuil de conformité:** Score global < 20%

**Exemple de résultat:**
```
Dataset: NON-CONFORME (Score: 69.9%)

├─ Individualisation: 100% (ÉLEVÉ)
│  └─ 10/10 combinaisons uniques
│
├─ Corrélation: 61.5% (ÉLEVÉ)
│  └─ 8/13 colonnes liables
│
└─ Inférence: 33.3% (ÉLEVÉ)
   └─ Corrélation revenu ↔ solde

Recommandations:
⚠️ Anonymisation requise
```

---

## 🚀 Installation Rapide

### Prérequis
- Docker & Docker Compose

### Démarrage

```bash
# 1. Cloner le projet
git clone <repository-url>
cd annoy

# 2. Démarrer les services
docker-compose up -d

# 3. Appliquer les migrations
docker-compose exec backend poetry run alembic upgrade head

# 4. Vérifier
curl http://localhost:8000/health

# 5. Accéder à la documentation
open http://localhost:8000/docs
```

**Services démarrés:**
- 🔹 Backend API: http://localhost:8000
- 🔹 Frontend: http://localhost:3000 (à venir)
- 🔹 PostgreSQL: localhost:5432

---

## 📖 Documentation API

### Swagger UI
**http://localhost:8000/docs**

### Endpoints Disponibles

```bash
# Datasets
POST   /api/v1/datasets/upload           # Upload CSV (max 100MB)
GET    /api/v1/datasets/{id}             # Métadonnées
GET    /api/v1/datasets/{id}/preview     # Aperçu
DELETE /api/v1/datasets/{id}             # Suppression

# Détection
POST   /api/v1/datasets/{id}/detect      # Analyse sensibilité

# Anonymisation
POST   /api/v1/datasets/{id}/anonymize   # Appliquer techniques
GET    /api/v1/datasets/{id}/download    # Télécharger CSV

# Évaluation
GET    /api/v1/datasets/{id}/risk-assessment  # Conformité Loi 25
```

---

## 🔄 Workflow Complet

### Exemple d'utilisation

```bash
# 1. Upload d'un fichier
curl -X POST http://localhost:8000/api/v1/datasets/upload \
  -F "file=@data.csv"
# → Retourne dataset_id

# 2. Détection des données sensibles
curl -X POST "http://localhost:8000/api/v1/datasets/{dataset_id}/detect"
# → Classification de toutes les colonnes

# 3. Évaluation des risques AVANT anonymisation
curl "http://localhost:8000/api/v1/datasets/{dataset_id}/risk-assessment"
# → Score: 69.9% - NON-CONFORME

# 4. Anonymisation
curl -X POST "http://localhost:8000/api/v1/datasets/{dataset_id}/anonymize" \
  -H "Content-Type: application/json" \
  -d '[
    {"column_name": "email", "technique": "masking", "params": {"visible_chars": 2}},
    {"column_name": "nas", "technique": "suppression", "params": {}},
    {"column_name": "nom", "technique": "pseudonymization", "params": {"prefix": "PERSON_"}}
  ]'
# → Retourne anonymized_dataset_id

# 5. Évaluation APRÈS anonymisation
curl "http://localhost:8000/api/v1/datasets/{anonymized_id}/risk-assessment"
# → Score: 54.6% - Amélioré mais toujours NON-CONFORME

# 6. Télécharger le résultat
curl "http://localhost:8000/api/v1/datasets/{anonymized_id}/download" \
  -o data_anonymized.csv
```

### Fichier de test fourni

`backend/tests/fixtures/test_data.csv` - 10 lignes avec:
- 5 identifiants directs
- 3 quasi-identifiants
- 2 données sensibles

**Configuration d'anonymisation de test:**
`backend/tests/fixtures/anonymization_config.json`

---

## 🏗️ Architecture

### Stack Technique

**Backend:**
- FastAPI 0.109+ (Python 3.11+)
- PostgreSQL 15
- SQLAlchemy 2.0 + Alembic
- Pandas 2.2
- Pydantic v2

**Frontend:**
- Next.js 16.1
- React 19.2
- TypeScript 5
- Tailwind CSS v4

**Infrastructure:**
- Docker & Docker Compose
- Poetry (gestion dépendances)

### Base de Données

**5 tables:**
1. `datasets` - Métadonnées des CSV
2. `dataset_columns` - Info colonnes
3. `anonymization_jobs` - Historique
4. `transformation_logs` - Audit trail
5. `risk_assessments` - Évaluations Loi 25

---

## 📊 Statut du Projet

**Progression globale: 62.5% (15/24 tâches)**

### ✅ Complété (Backend)

- [x] **Phase 1:** Infrastructure (Docker, DB, API)
- [x] **Phase 2:** Détection de données sensibles
- [x] **Phase 3:** 4 techniques d'anonymisation
- [x] **Phase 4:** Évaluation des risques Loi 25

### 🚧 En cours

- [ ] **Phase 5:** Frontend Next.js (0%)
- [ ] **Phase 6:** Rapports PDF (0%)
- [ ] **Phase 7:** Tests & Déploiement (0%)

---

## 🔒 Conformité Loi 25

Implémente les articles clés de la Loi 25:
- ✅ **Article 3.3**: Évaluation des facteurs de risque
- ✅ **Article 3.5**: Anonymisation et désidentification
- ✅ **Article 3.6**: Mesures de protection appropriées
- ✅ **Article 63.1**: Documentation des mesures

**Critères d'évaluation conformes aux meilleures pratiques**

---

## 🛠️ Développement

### Backend local (sans Docker)

```bash
cd backend
poetry install
poetry run uvicorn app.main:app --reload
```

### Frontend local

```bash
npm install
npm run dev
# http://localhost:3000
```

### Commandes utiles

```bash
# Logs
docker-compose logs -f backend

# Shell backend
docker-compose exec backend bash

# Migrations
docker-compose exec backend poetry run alembic revision --autogenerate -m "description"
docker-compose exec backend poetry run alembic upgrade head

# Tests (à venir)
docker-compose exec backend poetry run pytest
```

---

## 📝 Configuration

Voir `.env.example` pour les variables d'environnement.

**Principales variables:**
```bash
POSTGRES_SERVER=db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=annoy_db
MAX_UPLOAD_SIZE=104857600  # 100MB
```

---

## 🗺️ Roadmap

**Prochaines étapes:**
- Frontend Next.js complet
- Génération rapports PDF
- Tests automatisés

**Futur:**
- Support Excel/XLSX
- K-anonymity avancé
- Differential privacy
- Multi-tenancy

---

## 📄 License

Proprietary - Tous droits réservés

---

**Version:** 0.1.0-beta
**Dernière mise à jour:** 2025-12-31
