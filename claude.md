# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Annoy - Guide de référence Claude

> Outil d'anonymisation de données conforme à la Loi 25 du Québec

## Vue d'ensemble

**Annoy** est un outil professionnel d'anonymisation de données personnelles pour la conformité à la **Loi 25 du Québec**. Application full-stack production-ready qui détecte automatiquement les données sensibles, applique des techniques d'anonymisation professionnelles, et évalue la conformité selon les critères de la loi.

**Status**: ✅ MVP 100% complet (v0.1.0-beta)
**Branche de travail actuelle**: `v4`
**Branche historique**: `v2` (ancienne branche principale)

### Stack technique

| Composant               | Technologie  | Version     |
| ----------------------- | ------------ | ----------- |
| **Backend**             | FastAPI      | 0.109+      |
| **Frontend**            | Next.js      | 16.1        |
| **Language (Backend)**  | Python       | 3.11+       |
| **Language (Frontend)** | TypeScript   | 5           |
| **UI Framework**        | React        | 19          |
| **Database**            | PostgreSQL   | 15          |
| **ORM**                 | SQLAlchemy   | 2.0         |
| **Validation**          | Pydantic     | 2.6         |
| **Styling**             | Tailwind CSS | v4          |
| **PDF Generation**      | ReportLab    | 4.0         |
| **AI/ML**               | Ollama       | gemma3:4b   |
| **Containerization**    | Docker       | Latest      |
| **Reverse Proxy**       | Nginx        | Alpine      |

---

## Architecture

```
                    ┌─────────────────┐
                    │   Browser       │
                    └────────┬────────┘
                             │ HTTP/HTTPS
                    ┌────────▼────────┐
                    │  Nginx :80/443  │
                    │  (Reverse Proxy)│
                    └────┬────────┬───┘
                         │        │
              ┌──────────▼──┐  ┌─▼──────────┐
              │  Next.js    │  │  FastAPI   │
              │  Frontend   │  │  Backend   │
              │  :3000      │  │  :8000     │
              └─────────────┘  └─────┬──────┘
                                     │
                             ┌───────▼────────┐
                             │  PostgreSQL 15 │
                             │      :5432     │
                             └────────────────┘
```

**Workflow principal**:

```
Upload CSV → Detection → Anonymization → Risk Assessment → Export (CSV + PDF)
```

---

## Structure du projet

```
annoy/
├── backend/                    # FastAPI backend application
│   ├── app/
│   │   ├── main.py            # Point d'entrée FastAPI ⭐
│   │   ├── api/v1/            # Routes API versionnées
│   │   │   ├── router.py      # Agrégateur de routes
│   │   │   └── endpoints/
│   │   │       ├── datasets.py        # CRUD datasets
│   │   │       └── anonymization.py   # Anonymisation
│   │   ├── core/
│   │   │   ├── config.py      # Configuration Pydantic Settings
│   │   │   └── database.py    # SQLAlchemy engine & sessions
│   │   ├── models/
│   │   │   ├── database.py    # 5 modèles SQLAlchemy ORM
│   │   │   └── schemas.py     # Pydantic v2 validation schemas
│   │   └── services/          # Logique métier ⭐
│   │       ├── data_ingestion.py      # Upload & parsing CSV
│   │       ├── detector.py            # Détection données sensibles
│   │       ├── anonymizer.py          # Techniques d'anonymisation (Masking, Generalization, Suppression, DP)
│   │       ├── risk_evaluator.py      # Évaluation Loi 25 (incluant risk DP)
│   │       └── report_generator.py    # Génération PDF
│   ├── alembic/               # Migrations base de données
│   ├── tests/                 # Tests E2E
│   │   ├── test_e2e_workflow.py
│   │   └── fixtures/
│   ├── uploads/               # Fichiers temporaires
│   ├── pyproject.toml         # Dependencies Poetry ⭐
│   └── Dockerfile.prod        # Container production
│
├── src/                       # Next.js frontend application
│   ├── app/
│   │   ├── page.tsx           # Page upload (home) ⭐
│   │   ├── detection/[id]/page.tsx      # Résultats détection
│   │   ├── anonymization/[id]/page.tsx  # Config anonymisation
│   │   └── results/[id]/page.tsx        # Résultats & conformité
│   └── lib/
│       ├── api.ts             # Client API type-safe ⭐
│       └── utils.ts           # Fonctions utilitaires
│
├── docs/                      # Documentation complète
│   ├── USER_GUIDE.md         # Guide utilisateur (40 pages)
│   └── TECHNICAL.md          # Doc technique
│
├── nginx/
│   └── nginx.conf            # Config reverse proxy production
│
├── docker-compose.yml         # Dev environment ⭐
├── docker-compose.prod.yml    # Production stack
├── README.md                  # Documentation principale ⭐
├── CHANGELOG.md              # Historique versions
├── .env.example              # Template variables d'environnement
└── package.json              # Frontend dependencies

⭐ = Fichiers les plus importants
```

---

## Backend (FastAPI)

### Points d'entrée

**Fichier principal**: `backend/app/main.py`

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.router import api_router

app = FastAPI(title="Annoy - Data Anonymization Tool")
app.include_router(api_router, prefix="/api/v1")
```

### Modèles de données (SQLAlchemy)

5 tables principales dans `backend/app/models/database.py`:

1. **Dataset**: Métadonnées des fichiers CSV
   - `id` (UUID), `filename`, `file_size`, `row_count`, `column_count`
   - `is_anonymized`, `parent_dataset_id`, `risk_score`, `is_loi25_compliant`

2. **DatasetColumn**: Classification des colonnes
   - `name`, `position`, `data_type`
   - `sensitivity_type` (direct_identifier, quasi_identifier, sensitive, non_sensitive)
   - `category` (personal, financial, health, other)
   - `confidence` (0-100), `sample_values` (JSONB)

3. **AnonymizationJob**: Opérations d'anonymisation
   - `dataset_id`, `anonymized_dataset_id`, `status`, `created_at`

4. **TransformationLog**: Audit trail des transformations
   - `column_name`, `technique`, `params` (JSONB), `values_affected`
   - `sample_transformations` (JSONB avec before/after)

5. **RiskAssessment**: Évaluation conformité Loi 25
   - `individualization_score`, `correlation_score`, `inference_score`
   - `overall_score`, `is_loi25_compliant`, `recommendations`

### Services principaux

#### 1. DataIngestionService (`data_ingestion.py`)

- Upload et parsing de fichiers CSV
- Validation (taille max 1GB, format CSV)
- Extraction métadonnées avec Pandas
- Détection encodage automatique

#### 2. SensitiveDataDetector (`detector.py`)

- **Détection multi-couches**:
  - Analyse du nom de colonne (heuristiques)
  - Pattern matching regex (NAS, email, téléphone, code postal)
  - Statistiques (unicité, null count)
- **Classification 4 types**:
  - Direct identifier (NAS, email, nom)
  - Quasi-identifier (âge, code postal, date naissance)
  - Sensitive (revenu, solde, données médicales)
  - Non-sensitive (autres)
- **Score de confiance**: 0-100%

**Patterns regex clés**:

```python
PATTERNS = {
    "NAS": r"^\d{3}[-\s]?\d{3}[-\s]?\d{3}$",
    "EMAIL": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
    "TELEPHONE_CA": r"^(\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}$",
    "CODE_POSTAL_CA": r"^[A-Z]\d[A-Z]\s?\d[A-Z]\d$",
}
```

#### 3. Anonymizer (`anonymizer.py`)

**4 techniques d'anonymisation**:

a. **Masking** (Masquage)

- Usage: Emails, téléphones, cartes de crédit
- Exemple: `jean@test.com` → `je**@te**.com`
- Paramètre: `visible_chars` (défaut: 2)

b. **Generalization** (Généralisation)

- Usage: Âges, revenus, codes postaux
- Exemple: `75000` → `"75000-100000"`
- Paramètre: `bins` (nombre de tranches, défaut: 5)

c. **Suppression**

- Usage: NAS, données ultra-sensibles
- Résultat: Colonne complètement retirée
- Aucun paramètre

d. **Differential Privacy** (Confidentialité différentielle)

- Usage: Données numériques (revenu, montants, etc.)
- Exemple: `75000` → `75124` (ε=0.1)
- Algorithme: Mécanisme de Laplace
- Garantie: Protection mathématique contre l'inférence

**Performance**: ~17.6 µs par ligne (88ms pour 5000 lignes!)

#### 4. RiskEvaluator (`risk_evaluator.py`)

**Évaluation selon 3 critères de la Loi 25**:

1. **Individualisation** (40% du score)
   - Question: Peut-on isoler un individu?
   - Mesure: Taux d'unicité des quasi-identifiants
   - Seuil élevé: > 15%

2. **Corrélation** (35% du score)
   - Question: Données liables à d'autres sources?
   - Mesure: % de colonnes liables (ville, code postal, etc.)
   - Seuil élevé: > 20%

3. **Inférence** (25% du score)
   - Question: Peut-on déduire des informations?
   - Mesure: Corrélations fortes entre colonnes (Pearson |r| > 0.7)
   - Seuil élevé: > 25%

**Score global**:

```
Overall = (Individualisation × 0.40) + (Corrélation × 0.35) + (Inférence × 0.25)
```

**Seuil de conformité Loi 25**: Score < 20% = ✅ CONFORME

#### 5. PDFReportGenerator (`report_generator.py`)

- Génération de rapports PDF avec ReportLab
- 3 pages minimum:
  - Page titre avec statut conformité
  - Tableau des risques avec code couleur
  - Détails et recommandations
- Performance: ~68ms pour 3 pages

### API Endpoints

**Base URL**: `/api/v1`

**Datasets**:

- `POST /datasets/upload` - Upload CSV
- `GET /datasets/{id}` - Métadonnées dataset
- `GET /datasets/{id}/preview?n_rows=10` - Aperçu données
- `DELETE /datasets/{id}` - Supprimer dataset

**Detection**:

- `POST /datasets/{id}/detect` - Détecter données sensibles

**Anonymization**:

- `POST /datasets/{id}/anonymize` - Appliquer anonymisation
  - Body: `[{"column_name": "salaire", "technique": "differential_privacy", "params": {...}}]`
- `GET /datasets/{id}/download` - Télécharger CSV anonymisé

**Risk Assessment**:

- `GET /datasets/{id}/risk-assessment` - Évaluer conformité Loi 25

**Reports**:

- `GET /datasets/{id}/report` - Générer rapport PDF

**Health**:

- `GET /health` - Health check

**Documentation interactive**: `http://localhost:8000/docs` (FastAPI auto-generated)

---

## Frontend (Next.js)

### App Router (Next.js 13+)

**4 pages principales**:

1. **`/`** (Home - Upload)
   - Fichier: `src/app/page.tsx`
   - Drag & drop CSV upload
   - Validation: CSV only, max 1GB
   - Redirection automatique vers `/detection/[id]`

2. **`/detection/[id]`** (Résultats détection)
   - Fichier: `src/app/detection/[id]/page.tsx`
   - Cartes de résumé (4 types de sensibilité)
   - Liste des colonnes avec badges colorés
   - Score de risque global
   - Navigation vers `/anonymization/[id]`

3. **`/anonymization/[id]`** (Configuration)
   - Fichier: `src/app/anonymization/[id]/page.tsx`
   - Sélecteur de technique par colonne
   - Configuration des paramètres
   - Bouton "Lancer l'anonymisation"
   - Redirection vers `/results/[anonymized_id]`

4. **`/results/[id]`** (Résultats & conformité)
   - Fichier: `src/app/results/[id]/page.tsx`
   - Banner conformité (CONFORME/NON-CONFORME)
   - 3 jauges de risque circulaires
   - Recommandations
   - Boutons: Télécharger CSV + Rapport PDF

### Client API (`src/lib/api.ts`)

Client TypeScript type-safe:

```typescript
import { api } from "@/lib/api";

// Upload
const dataset = await api.uploadDataset(file);

// Detection
const report = await api.detectSensitiveData(datasetId);

// Anonymization
const config = [
  {
    column_name: "salaire",
    technique: "differential_privacy",
    params: { epsilon: 0.1 },
  },
];
const response = await api.anonymizeDataset(datasetId, config);

// Risk assessment
const assessment = await api.assessRisk(datasetId);

// Downloads
const csvBlob = await api.downloadDataset(datasetId);
const pdfBlob = await api.downloadComplianceReport(datasetId);
```

### Styling

- **Tailwind CSS v4** (via PostCSS)
- **Design system**:
  - Couleurs: blue-600 (primary), green-600 (success), red-600 (danger)
  - Badges de sensibilité: Rouge (direct), Orange (quasi), Bleu (sensible), Vert (non-sensible)
  - Gradient background: `from-blue-50 to-indigo-100`

---

## Base de données

**PostgreSQL 15**

### Schéma principal

```sql
datasets
├── id (UUID PK)
├── filename, file_size, row_count, column_count
├── is_anonymized, parent_dataset_id (FK)
└── risk_score, is_loi25_compliant

dataset_columns
├── id (UUID PK)
├── dataset_id (FK)
├── name, position, data_type
├── sensitivity_type, category, confidence
└── sample_values (JSONB)

anonymization_jobs
├── id (UUID PK)
├── dataset_id (FK)
└── anonymized_dataset_id (FK), status

transformation_logs
├── id (UUID PK)
├── job_id (FK)
├── column_name, technique, params (JSONB)
└── sample_transformations (JSONB)

risk_assessments
├── id (UUID PK)
├── dataset_id (FK)
├── individualization_score, correlation_score, inference_score
├── overall_score, is_loi25_compliant
└── details (JSONB), recommendations (ARRAY)
```

### Migrations

**Alembic** pour versioning du schéma:

```bash
# Créer migration
alembic revision -m "description"

# Appliquer migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

---

## Patterns et conventions

### Naming

| Contexte                | Convention | Exemple                 |
| ----------------------- | ---------- | ----------------------- |
| **Backend files**       | snake_case | `data_ingestion.py`     |
| **Backend functions**   | snake_case | `analyze_dataset()`     |
| **Backend classes**     | PascalCase | `SensitiveDataDetector` |
| **DB tables**           | snake_case | `dataset_columns`       |
| **DB columns**          | snake_case | `sensitivity_type`      |
| **Frontend files**      | PascalCase | `page.tsx`              |
| **Frontend components** | PascalCase | `UploadPage`            |
| **Frontend functions**  | camelCase  | `handleUpload()`        |
| **Frontend types**      | PascalCase | `DatasetResponse`       |

### API Patterns

- **RESTful design**: Resources avec verbes HTTP standards
- **Versioning**: `/api/v1` dans l'URL
- **IDs**: UUID v4 (pas d'auto-increment)
- **Responses**: JSON avec structure cohérente
- **Errors**: `{"detail": "message"}` avec status codes appropriés
- **Pagination**: Query params `?offset=0&limit=100` (si applicable)

### Code Style

**Backend (Python)**:

- Formatter: **Black** (line length: 100)
- Linter: **Ruff**
- Type hints: Encouraged mais pas obligatoire
- Docstrings: Google style
- Async/await: Utilisé pour I/O operations

**Frontend (TypeScript)**:

- Linter: **ESLint** (config Next.js)
- Formatter: Built-in
- Types: Strict mode (`tsconfig.json`)
- Components: Functional components avec hooks
- Server components par défaut (Next.js 13+)

---

## Commandes importantes

### Développement

```bash
# Démarrer l'environnement complet
docker-compose up -d

# Vérifier les services
curl http://localhost:8000/health  # Backend
curl http://localhost:3000          # Frontend

# Logs
docker-compose logs -f backend
docker-compose logs -f db
```

### Backend (sans Docker)

```bash
cd backend

# Installation dependencies
poetry install

# Démarrer serveur dev (avec hot reload)
poetry run uvicorn app.main:app --reload --port 8000

# Appliquer migrations
poetry run alembic upgrade head

# Format code
poetry run black app/

# Lint
poetry run ruff check app/
```

### Frontend (sans Docker)

```bash
# Installation dependencies
npm install
# ou
pnpm install

# Démarrer dev server
npm run dev  # Port 3000

# Build production
npm run build

# Démarrer prod
npm start

# Lint
npm run lint
```

### Tests

```bash
# Tests E2E backend (workflow complet)
docker-compose exec backend poetry run pytest tests/test_e2e_workflow.py -v -s

# Avec coverage
docker-compose exec backend poetry run pytest --cov=app tests/

# Test spécifique d'une classe
docker-compose exec backend poetry run pytest tests/test_e2e_workflow.py::TestE2EWorkflow::test_complete_workflow -v

# Tester un service spécifique sans Docker
cd backend
poetry run pytest tests/test_generalization.py -v

# Tester avec output détaillé
poetry run pytest tests/test_generalization_fix.py -v -s

# Exécuter tous les tests
docker-compose exec backend poetry run pytest tests/ -v
```

### Database

```bash
# Accéder au shell PostgreSQL
docker-compose exec db psql -U postgres -d annoy_db

# Backup
docker-compose exec db pg_dump -U postgres annoy_db > backup.sql

# Restore
docker-compose exec -T db psql -U postgres annoy_db < backup.sql
```

---

## Configuration

### Variables d'environnement

**Fichiers**:

- `.env.example` - Template développement
- `.env.production.example` - Template production
- `.env.local` - Local overrides (gitignored)

**Variables clés**:

```bash
# Backend / PostgreSQL
POSTGRES_SERVER=db              # ou localhost
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=annoy_db
POSTGRES_PORT=5432

# API
API_V1_STR=/api/v1
PROJECT_NAME=Annoy - Data Anonymization Tool
BACKEND_CORS_ORIGINS=http://localhost:3000

# Upload
MAX_UPLOAD_SIZE=1073741824      # 1 GB
UPLOAD_DIR=./uploads

# Anonymization
# (Pseudonym_seed removed - using differential privacy instead)

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Configuration FastAPI

**Fichier**: `backend/app/core/config.py`

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    # ...

    class Config:
        env_file = ".env"
        case_sensitive = True
```

---

## Tests

### Tests E2E

**Emplacement**: `backend/tests/test_e2e_workflow.py`

**Framework**: pytest + pytest-asyncio + httpx

**Ce qui est testé**:

1. Upload CSV (5000 lignes)
2. Détection données sensibles
3. Évaluation risque (avant)
4. Configuration anonymisation
5. Application anonymisation
6. Évaluation risque (après)
7. Téléchargement CSV
8. Génération PDF

**Exemple d'exécution**:

```bash
poetry run pytest tests/test_e2e_workflow.py -v -s

# Output attendu:
# ✅ Complete E2E workflow successful!
# ✓ Original dataset: Risk 69.9% (NON-COMPLIANT)
# ✓ Anonymized dataset: Risk 0.0% (COMPLIANT)
# ✓ Risk reduction: 69.9%
```

### Fixtures

**Fichier de test**: `backend/tests/fixtures/test_data.csv`

- 10 lignes × 13 colonnes
- Données bancaires fictives
- Contient tous les types de sensibilité

---

## Déploiement

### Développement

```bash
# Démarrer services
docker-compose up -d

# Vérifier
curl http://localhost:8000/health
curl http://localhost:3000
```

### Production

```bash
# Copier et configurer env
cp .env.production.example .env.production
# Éditer .env.production avec valeurs réelles

# Démarrer stack production
docker-compose -f docker-compose.prod.yml up -d

# Services:
# - db: PostgreSQL :5432
# - backend: FastAPI :8000
# - frontend: Next.js :3000
# - nginx: Reverse proxy :80/443

# Vérifier health
curl http://localhost/health
```

### Architecture production

```yaml
# docker-compose.prod.yml
services:
  db: # PostgreSQL 15 avec volumes persistants
  backend: # FastAPI avec 4 workers uvicorn
  frontend: # Next.js standalone build
  nginx: # Reverse proxy avec SSL/rate limiting
```

**Nginx features**:

- Rate limiting: 10 req/s (général), 5 req/min (uploads)
- Gzip compression
- Security headers (X-Frame-Options, CSP, etc.)
- SSL/TLS ready (certificat à ajouter)
- Health checks sans rate limit

---

## Points d'attention spécifiques

### Détection automatique des types pour généralisation

Le système inclut une fonctionnalité avancée de **détection automatique des types de données** pour optimiser la généralisation:

- **Types numériques**: Détection automatique (int, float) pour généralisation en bins
- **Types catégoriels**: Détection de colonnes à faible cardinalité
- **Types temporels**: Détection de dates pour généralisation temporelle
- **Heuristiques intelligentes**: Analyse du contenu pour recommander le nombre de bins optimal

**Fichiers clés**:

- `backend/app/services/anonymizer.py` - Logique de généralisation avec auto-détection
- `backend/test_generalization.py` - Tests de généralisation de base
- `backend/test_generalization_fix.py` - Tests avancés avec auto-détection

### Loi 25 du Québec

**Articles implémentés**:

- **Article 3.3**: Évaluation des facteurs de risque
- **Article 3.5**: Anonymisation et désidentification
- **Article 3.6**: Mesures de protection appropriées
- **Article 63.1**: Documentation des mesures

**3 critères de risque** (formule officielle):

```
Overall Score = (Individualisation × 40%) + (Corrélation × 35%) + (Inférence × 25%)

Conformité: Score < 20% = CONFORME ✅
```

### Performance

**Benchmarks** (dataset de 5000 lignes × 15 colonnes):

- Upload: < 1s
- Détection: < 1s
- **Anonymisation: 88ms** (17.6 µs/ligne)
- Évaluation: < 1s
- PDF: 68ms
- **Total workflow: < 3s**

### Sécurité

**Mesures implémentées**:

- ✅ Rate limiting (Nginx)
- ✅ CORS whitelist
- ✅ Input validation (Pydantic v2)
- ✅ SQL injection protection (SQLAlchemy ORM)
- ✅ File type validation
- ✅ Size limits (1 GB)
- ✅ Containers non-root
- ✅ Security headers

**Production checklist**:

- [ ] Changer `POSTGRES_PASSWORD`
- [ ] Configurer `BACKEND_CORS_ORIGINS` avec domaine réel
- [ ] Ajouter certificat SSL dans `nginx/ssl/`
- [ ] Configurer backups automatiques
- [ ] Mettre en place monitoring (optionnel: Sentry)

---

## Workflow de développement

### Créer une nouvelle feature

```bash
# 1. Créer branche depuis v4
git checkout v4
git pull
git checkout -b feature/ma-nouvelle-feature

# 2. Développer
# ... éditer les fichiers ...

# 3. Tester localement
docker-compose up -d
npm run dev  # frontend si nécessaire
poetry run pytest  # tests

# 4. Commit (format conventionnel)
git add .
git commit -m "feat: ajouter nouvelle fonctionnalité X"

# 5. Push et PR
git push origin feature/ma-nouvelle-feature
# Créer PR sur GitHub/GitLab
```

### Format des commits

**Convention**: [Conventional Commits](https://www.conventionalcommits.org/)

```
<type>: <description>

[optional body]

[optional footer]
```

**Types**:

- `feat`: Nouvelle fonctionnalité
- `fix`: Correction de bug
- `docs`: Documentation
- `chore`: Tâches de maintenance
- `test`: Tests
- `refactor`: Refactoring
- `perf`: Amélioration performance

**Exemples**:

```
feat: add Excel file support
fix: correct NAS detection regex
docs: update API documentation
chore: upgrade dependencies
```

---

## Documentation existante

### Fichiers de documentation

| Fichier                       | Contenu                                                          | Pages       |
| ----------------------------- | ---------------------------------------------------------------- | ----------- |
| **README.md**                 | Documentation principale (features, installation, API, exemples) | 500+ lignes |
| **docs/USER_GUIDE.md**        | Guide utilisateur complet (interface, techniques, FAQ)           | 40 pages    |
| **docs/TECHNICAL.md**         | Architecture détaillée, algorithmes, implémentation              | 30+ pages   |
| **CHANGELOG.md**              | Historique des versions et changements                           | -           |
| **MVP_PLAN_ANONYMISATION.md** | Plan MVP original et scope                                       | -           |

### Liens utiles

**API Documentation**:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

**Technologies**:

- [FastAPI](https://fastapi.tiangolo.com/)
- [Next.js](https://nextjs.org/docs)
- [SQLAlchemy 2.0](https://docs.sqlalchemy.org/en/20/)
- [Pydantic v2](https://docs.pydantic.dev/latest/)
- [ReportLab](https://www.reportlab.com/docs/reportlab-userguide.pdf)
- [Tailwind CSS v4](https://tailwindcss.com/docs)

**Loi 25**:

- [Texte complet de la Loi 25](https://www.legisquebec.gouv.qc.ca/)
- [Commission d'accès à l'information](https://www.cai.gouv.qc.ca/)

---

## Troubleshooting

### Problèmes fréquents

**1. Backend ne démarre pas**

```bash
# Vérifier logs
docker-compose logs backend

# Problème DB connection?
docker-compose exec backend poetry run alembic upgrade head
```

**2. Frontend ne compile pas**

```bash
# Nettoyer et réinstaller
rm -rf node_modules .next
npm install
npm run dev
```

**3. Migrations ne s'appliquent pas**

```bash
# Reset DB (dev only!)
docker-compose down -v
docker-compose up -d
docker-compose exec backend poetry run alembic upgrade head
```

**4. Tests échouent**

```bash
# S'assurer que les services tournent
docker-compose up -d
sleep 5  # Attendre que DB soit prêt

# Relancer tests
docker-compose exec backend poetry run pytest tests/ -v
```

**5. Upload échoue (file too large)**

- Vérifier `MAX_UPLOAD_SIZE` dans `.env`
- Nginx limite: `client_max_body_size` dans `nginx.conf`

---

## Raccourcis et astuces

### Accès rapides

```bash
# Shell backend container
docker-compose exec backend bash

# Shell DB
docker-compose exec db psql -U postgres -d annoy_db

# Tail logs en temps réel
docker-compose logs -f backend

# Restart un service spécifique
docker-compose restart backend

# Rebuild après changement code
docker-compose up -d --build backend
```

### Commandes utiles

```bash
# Compter lignes de code
find backend/app -name "*.py" | xargs wc -l
find src -name "*.tsx" -o -name "*.ts" | xargs wc -l

# Trouver TODOs
grep -r "TODO" backend/app
grep -r "FIXME" src

# Formater tout le code backend
poetry run black backend/app
poetry run ruff check --fix backend/app

# Nettoyer containers et volumes
docker-compose down -v
docker system prune -a
```

---

## Statistiques du projet

**Code**:

- Backend: ~8,000 lignes Python
- Frontend: ~2,500 lignes TypeScript
- Tests: ~300 lignes
- Documentation: ~1,500 lignes
- **Total**: ~12,800 lignes

**Fichiers**:

- ~50+ fichiers de code
- 5 fichiers de documentation
- 24 commits professionnels

**Features**:

- ✅ 4 pages web interactives
- ✅ 5 modèles de base de données
- ✅ 5 services métier
- ✅ 4 techniques d'anonymisation
- ✅ 3 critères d'évaluation Loi 25
- ✅ Génération PDF
- ✅ Tests E2E
- ✅ Configuration production

**Performance validée**:

- ✅ 5000 clients en < 3 secondes
- ✅ 17.6 µs par ligne d'anonymisation
- ✅ 0.0% risque après anonymisation
- ✅ 100% conformité Loi 25

---

## Contact et support

**Repository**: (à compléter)
**Issues**: (à compléter)
**Documentation**: [README.md](./README.md), [docs/](./docs/)

---

**Version**: 0.1.0-beta
**Dernière mise à jour**: 2026-01-18
**Status**: ✅ Production-ready

---

## Notes importantes pour le développement

### Points critiques

1. **Branches Git**: La branche active est `v4`. Les anciennes documentations peuvent référencer `v2`.

2. **Tests de généralisation**: Des fichiers de test spécifiques existent à la racine du backend (`test_generalization.py`, `test_generalization_fix.py`) pour valider la détection automatique des types.

3. **Variables d'environnement**:
   - Toujours copier `.env.example` vers `.env` en développement
   - Les services Docker doivent pointer vers `POSTGRES_SERVER=db`
   - En local sans Docker, utiliser `POSTGRES_SERVER=localhost`

4. **Migrations Alembic**:
   - TOUJOURS exécuter `alembic upgrade head` après un `docker-compose up` initial
   - En cas de problème de migration, vérifier les logs avec `docker-compose logs backend`

5. **Hot reload**:
   - Backend: Uvicorn avec `--reload` pour développement local
   - Frontend: Next.js dev server se recharge automatiquement
   - Docker: Rebuild avec `docker-compose up -d --build` après modification de dépendances

6. **Ordre de démarrage**:

   ```bash
   # L'ordre est important!
   docker-compose up -d db          # 1. Base de données d'abord
   sleep 5                           # 2. Attendre que PostgreSQL soit prêt
   docker-compose up -d backend      # 3. Backend
   docker-compose up -d frontend     # 4. Frontend
   ```

7. **Debugging**:
   - Backend: Logs avec `docker-compose logs -f backend`
   - Frontend: Logs avec `docker-compose logs -f frontend`
   - DB: Accès direct avec `docker-compose exec db psql -U postgres -d annoy_db`

8. **Ollama Integration**: L'application utilise Ollama (gemma3:4b) pour la détection IA locale des données sensibles. Voir docs/AI_ENHANCED_DETECTION.md et docs/OLLAMA_SETUP.md pour configuration.

\*Important: I don't want you to write any code yourself. Your role is to coordinate the efforts Coding Agents Have a look at this implementation plan, and I want yo to create different tracks.h track, kick off a coding agent to implement the changes for that track. You need to use the Coder agent for this. Once the coding agent completes its work, You need to keep your context window as lean as possible. Coordinate all the different efforts between the tracks, the coder agents,

---

_Ce fichier est destiné à aider Claude à mieux comprendre et naviguer dans le projet Annoy. Il doit être mis à jour lors de changements majeurs d'architecture ou de conventions._
