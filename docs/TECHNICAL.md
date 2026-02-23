# Documentation Technique - Annoy

## Architecture et implémentation détaillée

---

## Table des matières

1. [Architecture globale](#architecture-globale)
2. [Backend (FastAPI)](#backend-fastapi)
3. [Frontend (Next.js)](#frontend-nextjs)
4. [Base de données](#base-de-données)
5. [Algorithmes d'anonymisation](#algorithmes-danonymisation)
6. [API Reference](#api-reference)
7. [Performance et optimisation](#performance-et-optimisation)
8. [Sécurité](#sécurité)

---

## Architecture globale

### Stack technologique

```
┌─────────────────────────────────────────────────────────┐
│                    CLIENT (Browser)                      │
└────────────────────┬────────────────────────────────────┘
                     │ HTTP/HTTPS
┌────────────────────▼────────────────────────────────────┐
│                  NGINX (Reverse Proxy)                   │
│  - Rate limiting                                         │
│  - SSL/TLS termination                                   │
│  - Static file serving                                   │
│  - Load balancing                                        │
└────────────┬───────────────────────────┬────────────────┘
             │                           │
┌────────────▼────────────┐   ┌─────────▼──────────────┐
│   Next.js Frontend      │   │   FastAPI Backend      │
│   - React 19            │   │   - Python 3.11        │
│   - TypeScript 5        │   │   - Async/await        │
│   - Tailwind CSS v4     │   │   - Pydantic v2        │
│   - Client-side routing │   │   - SQLAlchemy 2.0     │
└─────────────────────────┘   └────────┬───────────────┘
                                       │
                          ┌────────────▼───────────────┐
                          │    PostgreSQL 15           │
                          │    - JSONB columns         │
                          │    - Indexes optimisés     │
                          │    - Full-text search      │
                          └────────────────────────────┘
```

### Flux de données

```
Upload CSV → Ingestion → Detection → Anonymization → Risk Assessment → Export
    ↓           ↓           ↓             ↓                ↓              ↓
  Store    Parse &     Pattern      Transform        Evaluate      Generate
  File     Analyze     Matching     Data             3 Criteria    PDF/CSV
```

---

## Backend (FastAPI)

### Structure des dossiers

```
backend/
├── app/
│   ├── main.py                 # Application FastAPI
│   ├── core/
│   │   ├── config.py          # Configuration (Pydantic Settings)
│   │   └── database.py        # SQLAlchemy engine & sessions
│   ├── models/
│   │   ├── database.py        # SQLAlchemy ORM models
│   │   └── schemas.py         # Pydantic schemas (validation)
│   ├── api/
│   │   └── v1/
│   │       ├── router.py      # API router principal
│   │       └── endpoints/
│   │           ├── datasets.py      # CRUD datasets
│   │           └── anonymization.py # Anonymisation
│   └── services/
│       ├── data_ingestion.py      # Upload & parsing CSV
│       ├── detector.py            # Détection données sensibles
│       ├── anonymizer.py          # 4 techniques d'anonymisation
│       ├── risk_evaluator.py      # Évaluation Loi 25
│       └── report_generator.py    # Génération PDF
├── tests/
│   ├── fixtures/
│   │   └── test_data.csv
│   └── test_e2e_workflow.py
├── alembic/                   # Migrations de base de données
├── uploads/                   # Fichiers uploadés
├── pyproject.toml            # Dependencies (Poetry)
└── Dockerfile                # Container production
```

### Modèles de données (SQLAlchemy)

#### Dataset
```python
class Dataset(Base):
    __tablename__ = "datasets"

    id: UUID                          # Identifiant unique
    filename: str                     # Nom du fichier original
    file_path: str                    # Chemin stockage
    file_size: int                    # Taille en bytes
    row_count: int                    # Nombre de lignes
    column_count: int                 # Nombre de colonnes
    upload_date: datetime             # Date d'upload
    is_anonymized: bool = False       # Anonymisé?
    parent_dataset_id: UUID (nullable)# Dataset parent si anonymisé
    risk_score: float (nullable)      # Score de risque (0-100)
    is_loi25_compliant: bool = False  # Conforme Loi 25?

    # Relations
    columns: List[DatasetColumn]
    anonymization_jobs: List[AnonymizationJob]
    risk_assessments: List[RiskAssessment]
```

#### DatasetColumn
```python
class DatasetColumn(Base):
    __tablename__ = "dataset_columns"

    id: UUID
    dataset_id: UUID (FK)
    name: str                         # Nom de la colonne
    position: int                     # Position dans le CSV
    data_type: str                    # Type pandas (int64, object, etc.)
    sensitivity_type: str (nullable)  # direct_identifier, quasi, etc.
    category: str (nullable)          # personal, financial, medical
    confidence: float (nullable)      # Score de confiance (0-100)
    null_count: int                   # Nombre de NULL
    unique_count: int                 # Nombre de valeurs uniques
    sample_values: JSONB              # Échantillon de valeurs
```

#### AnonymizationJob
```python
class AnonymizationJob(Base):
    __tablename__ = "anonymization_jobs"

    id: UUID
    dataset_id: UUID (FK)            # Dataset source
    anonymized_dataset_id: UUID (FK)  # Dataset résultat
    created_at: datetime
    status: str                       # pending, completed, failed

    # Relations
    transformation_logs: List[TransformationLog]
```

#### TransformationLog
```python
class TransformationLog(Base):
    __tablename__ = "transformation_logs"

    id: UUID
    job_id: UUID (FK)
    column_name: str                  # Colonne transformée
    technique: str                    # masking, generalization, etc.
    params: JSONB                     # Paramètres utilisés
    values_affected: int              # Nombre de valeurs modifiées
    sample_transformations: JSONB     # Exemples avant/après
```

#### RiskAssessment
```python
class RiskAssessment(Base):
    __tablename__ = "risk_assessments"

    id: UUID
    dataset_id: UUID (FK)
    assessed_at: datetime
    individualization_score: float    # 0-100
    correlation_score: float          # 0-100
    inference_score: float            # 0-100
    overall_score: float              # Moyenne pondérée
    is_loi25_compliant: bool         # < 20% = conforme
    details: JSONB                    # Détails critères
```

### Services principaux

#### 1. SensitiveDataDetector

**Responsabilité**: Détecter les données sensibles dans un dataset

**Algorithme**:
```python
def analyze_dataset(dataset_id: UUID) -> DetectionReport:
    # 1. Charger le dataset
    dataset = load_dataset(dataset_id)
    df = pd.read_csv(dataset.file_path)

    # 2. Pour chaque colonne
    for column in df.columns:
        # 2.1 Analyser le nom de la colonne
        name_hints = analyze_column_name(column)

        # 2.2 Analyser les valeurs avec patterns regex
        pattern_matches = match_patterns(df[column])

        # 2.3 Analyser les statistiques
        stats = calculate_stats(df[column])

        # 2.4 Combiner les résultats
        classification = classify_column(
            name_hints,
            pattern_matches,
            stats
        )

        # 2.5 Calculer score de confiance
        confidence = calculate_confidence(classification)

    # 3. Calculer score de risque global
    overall_risk = calculate_overall_risk(classifications)

    return DetectionReport(...)
```

**Patterns regex utilisés**:
```python
PATTERNS = {
    "NAS": r"^\d{3}[-\s]?\d{3}[-\s]?\d{3}$",
    "EMAIL": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
    "TELEPHONE_CA": r"^(\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}$",
    "CODE_POSTAL_CA": r"^[A-Z]\d[A-Z]\s?\d[A-Z]\d$",
    "DATE": r"^\d{4}-\d{2}-\d{2}$",
    "CARTE_CREDIT": r"^\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}$",
}
```

**Classification**:
```python
def classify_column(name_hints, patterns, stats):
    # Identifiants directs (si pattern match fort)
    if patterns["NAS"] or patterns["EMAIL"]:
        return "direct_identifier"

    # Quasi-identifiants (combinaison)
    if patterns["DATE"] and "naissance" in name_hints:
        return "quasi_identifier"

    # Sensibles (montants d'argent)
    if stats["is_numeric"] and ("revenu" in name_hints or "solde" in name_hints):
        return "sensitive"

    # Par défaut
    return "non_sensitive"
```

#### 2. Anonymizer

**4 techniques implémentées**:

##### A. Masquage
```python
def _mask_value(value: str, visible_chars: int = 2) -> str:
    """
    Masque une partie de la valeur en gardant quelques caractères visibles.

    Exemples:
    - Email: jean@test.com → je**@te**.com
    - Téléphone: 514-555-1234 → 514-***-****
    """
    if "@" in value:  # Email
        local, domain = value.split("@")
        masked_local = local[:visible_chars] + "*" * (len(local) - visible_chars)
        domain_parts = domain.split(".")
        masked_domain = domain_parts[0][:visible_chars] + "*" * (len(domain_parts[0]) - visible_chars)
        return f"{masked_local}@{masked_domain}.{'.'.join(domain_parts[1:])}"
    else:  # Numéro (téléphone, carte)
        parts = value.split("-")
        return parts[0] + "-" + "-".join("*" * len(p) for p in parts[1:])
```

##### B. Généralisation
```python
def _generalize_value(value: Any, bins: int = 5) -> str:
    """
    Généralise une valeur numérique en créant des tranches.

    Algorithme:
    1. Collecter toutes les valeurs de la colonne
    2. Calculer min/max
    3. Créer N tranches égales
    4. Attribuer chaque valeur à sa tranche

    Exemple:
    - Valeur: 75000
    - Min: 30000, Max: 200000
    - 5 tranches: [30k-64k, 64k-98k, 98k-132k, 132k-166k, 166k-200k]
    - Résultat: "64000-98000"
    """
    min_val, max_val = column_values.min(), column_values.max()
    bin_size = (max_val - min_val) / bins

    bin_index = int((value - min_val) / bin_size)
    bin_start = min_val + (bin_index * bin_size)
    bin_end = bin_start + bin_size

    return f"{int(bin_start)}-{int(bin_end)}"
```

##### C. Suppression
```python
def _suppress_column(df: pd.DataFrame, column_name: str) -> pd.DataFrame:
    """
    Supprime complètement une colonne du dataset.

    Utilisé pour:
    - NAS (trop sensible)
    - Données médicales critiques
    - Informations légalement protégées
    """
    return df.drop(columns=[column_name])
```

##### D. confidentialité différentielle
```python
def _pseudonymize_value(value: str, prefix: str = "ANON_", seed: int = 42) -> str:
    """
    Remplace une valeur par un valeur anonymisée basé sur hash.

    Caractéristiques:
    - Déterministe: même valeur → même valeur anonymisée
    - Irréversible: impossible de retrouver l'original sans clé
    - Cohérent: permet le suivi longitudinal

    Algorithme:
    1. Concaténer valeur + seed
    2. Calculer SHA-256 hash
    3. Prendre les 6 premiers caractères hex
    4. Ajouter le préfixe

    Exemple:
    - Valeur: "Tremblay"
    - Seed: 42
    - Hash: sha256("Tremblay_42") = "66d67c..."
    - Résultat: "PERSON_66D67C"
    """
    hash_input = f"{value}_{seed}".encode('utf-8')
    hash_hex = hashlib.sha256(hash_input).hexdigest()[:6].upper()
    return f"{prefix}{hash_hex}"
```

#### 3. RiskEvaluator

**3 critères de la Loi 25**:

##### A. Individualisation (40% du score)
```python
def evaluate_individualization(df: pd.DataFrame, quasi_columns: List[str]) -> CriterionResult:
    """
    Mesure si on peut isoler un individu.

    Méthode:
    1. Combiner tous les quasi-identifiants
    2. Compter les combinaisons uniques
    3. Score = (combinaisons uniques / total) * 100

    Interprétation:
    - 100%: Chaque ligne est unique → RISQUE ÉLEVÉ
    - 50%: 1 personne sur 2 est unique → RISQUE MOYEN
    - 5%: Très peu d'unicité → RISQUE FAIBLE

    Seuil:
    - > 15%: ÉLEVÉ
    - 5-15%: MOYEN
    - < 5%: FAIBLE
    """
    if not quasi_columns:
        return CriterionResult(score=0, level="faible")

    # Combiner quasi-identifiants
    combined = df[quasi_columns].astype(str).agg("_".join, axis=1)

    # Calculer unicité
    unique_combinations = combined.nunique()
    total_rows = len(df)
    uniqueness_rate = (unique_combinations / total_rows) * 100

    return CriterionResult(
        score=uniqueness_rate,
        level="élevé" if uniqueness_rate > 15 else "moyen" if uniqueness_rate > 5 else "faible"
    )
```

##### B. Corrélation (35% du score)
```python
def evaluate_correlation(df: pd.DataFrame, all_columns: List[Column]) -> CriterionResult:
    """
    Évalue si les données peuvent être liées à des sources externes.

    Colonnes considérées "liables":
    - Code postal (annuaires, cartes)
    - Ville (bases géographiques)
    - Profession (registres professionnels)
    - Dates (événements publics)

    Score = (colonnes liables / total) * 100

    Seuil:
    - > 20%: ÉLEVÉ
    - 10-20%: MOYEN
    - < 10%: FAIBLE
    """
    linkable_keywords = ["postal", "ville", "profession", "date", "lieu"]
    linkable_count = 0

    for column in all_columns:
        if any(kw in column.name.lower() for kw in linkable_keywords):
            linkable_count += 1

    linkable_rate = (linkable_count / len(all_columns)) * 100

    return CriterionResult(
        score=linkable_rate,
        level="élevé" if linkable_rate > 20 else "moyen" if linkable_rate > 10 else "faible"
    )
```

##### C. Inférence (25% du score)
```python
def evaluate_inference(df: pd.DataFrame, numeric_columns: List[str]) -> CriterionResult:
    """
    Vérifie si on peut déduire des informations via corrélations.

    Méthode:
    1. Calculer matrice de corrélation (Pearson)
    2. Compter corrélations fortes (|r| > 0.7)
    3. Score basé sur nombre de corrélations

    Exemple:
    - Si revenu fortement corrélé à âge (r=0.85)
      → On peut déduire le revenu approximatif si on connaît l'âge

    Seuil:
    - > 25%: ÉLEVÉ
    - 10-25%: MOYEN
    - < 10%: FAIBLE
    """
    if len(numeric_columns) < 2:
        return CriterionResult(score=0, level="faible")

    # Matrice de corrélation
    corr_matrix = df[numeric_columns].corr()

    # Compter corrélations fortes (hors diagonale)
    strong_correlations = 0
    total_pairs = 0

    for i in range(len(corr_matrix)):
        for j in range(i + 1, len(corr_matrix)):
            total_pairs += 1
            if abs(corr_matrix.iloc[i, j]) > 0.7:
                strong_correlations += 1

    if total_pairs == 0:
        return CriterionResult(score=0, level="faible")

    inference_rate = (strong_correlations / total_pairs) * 100

    return CriterionResult(
        score=inference_rate,
        level="élevé" if inference_rate > 25 else "moyen" if inference_rate > 10 else "faible"
    )
```

##### Score global
```python
def calculate_overall_score(individualization, correlation, inference) -> float:
    """
    Calcul du score global pondéré.

    Formule:
    Score = (Individualisation × 0.40) + (Corrélation × 0.35) + (Inférence × 0.25)

    Conformité Loi 25:
    - Score < 20%: CONFORME ✅
    - Score ≥ 20%: NON-CONFORME ❌
    """
    return (
        individualization.score * 0.40 +
        correlation.score * 0.35 +
        inference.score * 0.25
    )
```

#### 4. PDFReportGenerator

**Génération de rapports professionnels avec ReportLab**

```python
def generate_compliance_report(
    dataset: DatasetResponse,
    detection_report: Optional[DetectionReport],
    risk_assessment: RiskAssessmentResponse,
    anonymization_response: Optional[AnonymizationResponse]
) -> BytesIO:
    """
    Génère un rapport PDF de 3 pages minimum.

    Structure:
    - Page 1: Page de titre avec statut conformité
    - Page 2: Évaluation des risques (tableau coloré)
    - Page 3: Détails et recommandations

    Utilise:
    - Styles personnalisés (titres, sous-titres, corps)
    - Tableaux avec code couleur (vert/jaune/rouge)
    - Mise en page professionnelle
    """
```

---

## Frontend (Next.js)

### Structure des dossiers

```
src/
├── app/
│   ├── page.tsx                    # Page d'accueil (upload)
│   ├── detection/
│   │   └── [id]/
│   │       └── page.tsx            # Résultats de détection
│   ├── anonymization/
│   │   └── [id]/
│   │       └── page.tsx            # Configuration anonymisation
│   └── results/
│       └── [id]/
│           └── page.tsx            # Résultats finaux
└── lib/
    ├── api.ts                      # Client API type-safe
    └── utils.ts                    # Fonctions utilitaires
```

### Client API (TypeScript)

```typescript
class AnnoyAPIClient {
  private baseUrl: string;

  constructor() {
    this.baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  }

  // Upload dataset
  async uploadDataset(file: File): Promise<Dataset> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${this.baseUrl}/api/v1/datasets/upload`, {
      method: 'POST',
      body: formData,
    });

    return this.handleResponse<Dataset>(response);
  }

  // Detect sensitive data
  async detectSensitiveData(datasetId: string): Promise<DetectionReport> {
    const response = await fetch(
      `${this.baseUrl}/api/v1/datasets/${datasetId}/detect`,
      { method: 'POST' }
    );

    return this.handleResponse<DetectionReport>(response);
  }

  // Anonymize dataset
  async anonymizeDataset(
    datasetId: string,
    config: AnonymizationConfig[]
  ): Promise<AnonymizationResponse> {
    const response = await fetch(
      `${this.baseUrl}/api/v1/datasets/${datasetId}/anonymize`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      }
    );

    return this.handleResponse<AnonymizationResponse>(response);
  }

  // Assess risk
  async assessRisk(datasetId: string): Promise<RiskAssessment> {
    const response = await fetch(
      `${this.baseUrl}/api/v1/datasets/${datasetId}/risk-assessment`
    );

    return this.handleResponse<RiskAssessment>(response);
  }

  // Download CSV
  async downloadDataset(datasetId: string): Promise<Blob> {
    const response = await fetch(
      `${this.baseUrl}/api/v1/datasets/${datasetId}/download`
    );

    if (!response.ok) throw new Error('Download failed');
    return response.blob();
  }

  // Download PDF report
  async downloadComplianceReport(datasetId: string): Promise<Blob> {
    const response = await fetch(
      `${this.baseUrl}/api/v1/datasets/${datasetId}/report`
    );

    if (!response.ok) throw new Error('Report generation failed');
    return response.blob();
  }

  private async handleResponse<T>(response: Response): Promise<T> {
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Request failed');
    }
    return response.json();
  }
}

export const api = new AnnoyAPIClient();
```

---

## Base de données

### Schéma PostgreSQL

```sql
-- Datasets table
CREATE TABLE datasets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size INTEGER NOT NULL,
    row_count INTEGER NOT NULL,
    column_count INTEGER NOT NULL,
    upload_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_anonymized BOOLEAN DEFAULT FALSE,
    parent_dataset_id UUID REFERENCES datasets(id) ON DELETE SET NULL,
    risk_score FLOAT,
    is_loi25_compliant BOOLEAN DEFAULT FALSE
);

-- Index for performance
CREATE INDEX idx_datasets_upload_date ON datasets(upload_date DESC);
CREATE INDEX idx_datasets_parent ON datasets(parent_dataset_id);

-- Dataset columns
CREATE TABLE dataset_columns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dataset_id UUID NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    position INTEGER NOT NULL,
    data_type VARCHAR(50) NOT NULL,
    sensitivity_type VARCHAR(50),
    category VARCHAR(50),
    confidence FLOAT,
    null_count INTEGER NOT NULL,
    unique_count INTEGER NOT NULL,
    sample_values JSONB
);

CREATE INDEX idx_columns_dataset ON dataset_columns(dataset_id);
CREATE INDEX idx_columns_sensitivity ON dataset_columns(sensitivity_type);

-- Anonymization jobs
CREATE TABLE anonymization_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dataset_id UUID NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
    anonymized_dataset_id UUID REFERENCES datasets(id) ON DELETE SET NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) NOT NULL DEFAULT 'pending'
);

CREATE INDEX idx_jobs_dataset ON anonymization_jobs(dataset_id);
CREATE INDEX idx_jobs_created ON anonymization_jobs(created_at DESC);

-- Transformation logs
CREATE TABLE transformation_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL REFERENCES anonymization_jobs(id) ON DELETE CASCADE,
    column_name VARCHAR(255) NOT NULL,
    technique VARCHAR(50) NOT NULL,
    params JSONB,
    values_affected INTEGER NOT NULL,
    sample_transformations JSONB
);

CREATE INDEX idx_logs_job ON transformation_logs(job_id);

-- Risk assessments
CREATE TABLE risk_assessments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dataset_id UUID NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
    assessed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    individualization_score FLOAT NOT NULL,
    correlation_score FLOAT NOT NULL,
    inference_score FLOAT NOT NULL,
    overall_score FLOAT NOT NULL,
    is_loi25_compliant BOOLEAN NOT NULL,
    details JSONB
);

CREATE INDEX idx_risk_dataset ON risk_assessments(dataset_id);
CREATE INDEX idx_risk_compliant ON risk_assessments(is_loi25_compliant);
```

---

## API Reference

### Endpoints

#### POST /api/v1/datasets/upload
Upload un fichier CSV.

**Request**: `multipart/form-data`
- `file`: CSV file (max 1GB)

**Response**: `201 Created`
```json
{
  "id": "uuid",
  "filename": "data.csv",
  "row_count": 5000,
  "column_count": 15,
  "columns": [...]
}
```

#### POST /api/v1/datasets/{id}/detect
Détecte les données sensibles.

**Response**: `200 OK`
```json
{
  "dataset_id": "uuid",
  "columns": {
    "nom": {
      "sensitivity_type": "direct_identifier",
      "confidence": 80.0,
      "justification": "..."
    }
  },
  "summary": {
    "direct_identifier": 4,
    "quasi_identifier": 2
  },
  "overall_risk_score": 16.7
}
```

#### POST /api/v1/datasets/{id}/anonymize
Anonymise un dataset.

**Request**: `application/json`
```json
[
  {
    "column_name": "nom",
    "technique": "confidentialité différentielle",
    "params": {"prefix": "PERSON_"}
  }
]
```

**Response**: `200 OK`
```json
{
  "job_id": "uuid",
  "anonymized_dataset_id": "uuid",
  "transformations": [...]
}
```

#### GET /api/v1/datasets/{id}/risk-assessment
Évalue les risques.

**Response**: `200 OK`
```json
{
  "overall_score": 0.0,
  "is_loi25_compliant": true,
  "individualization": {...},
  "correlation": {...},
  "inference": {...},
  "recommendations": [...]
}
```

#### GET /api/v1/datasets/{id}/download
Télécharge le CSV.

**Response**: `200 OK`
- Content-Type: `text/csv`
- Content-Disposition: `attachment; filename="data.csv"`

#### GET /api/v1/datasets/{id}/report
Génère le rapport PDF.

**Response**: `200 OK`
- Content-Type: `application/pdf`
- Content-Disposition: `attachment; filename="rapport_loi25_*.pdf"`

---

## Performance et optimisation

### Benchmarks

Test avec 5000 lignes × 15 colonnes (779 KB):

| Opération | Temps | Débit |
|-----------|-------|-------|
| Upload | < 1s | ~800 KB/s |
| Détection | < 1s | ~5000 lignes/s |
| Anonymisation | 88ms | ~56,800 lignes/s |
| Évaluation | < 1s | ~5000 lignes/s |
| PDF | 68ms | ~73 pages/s |
| **Total** | **< 3s** | **~1,667 lignes/s** |

### Optimisations appliquées

1. **Pandas vectorisation**:
   - Utilisation de `apply()` avec `axis=1`
   - Broadcasting pour opérations numériques
   - Évite les boucles Python pures

2. **Base de données**:
   - Index sur colonnes fréquemment requêtées
   - JSONB pour données flexibles
   - Connexion pooling (SQLAlchemy)

3. **FastAPI**:
   - Async/await pour I/O
   - 4 workers en production
   - Streaming pour gros fichiers

4. **Caching**:
   - Résultats de détection mis en cache
   - Statistiques pré-calculées

---

## Sécurité

### Mesures implémentées

1. **Validation des entrées**:
   - Pydantic v2 pour validation stricte
   - Taille maximale de fichier (1 GB)
   - Type MIME vérifié

2. **Injection SQL**:
   - SQLAlchemy ORM (pas de raw SQL)
   - Paramètres bindés automatiquement

3. **Rate limiting** (Nginx):
   - 10 req/s général
   - 5 req/min pour uploads

4. **Headers de sécurité**:
   - X-Frame-Options: SAMEORIGIN
   - X-Content-Type-Options: nosniff
   - X-XSS-Protection: 1; mode=block

5. **CORS**:
   - Whitelist d'origines configurée
   - Credentials non autorisés par défaut

6. **Containers**:
   - Utilisateurs non-root
   - Pas de privilèges élevés
   - Network isolation

---

**Version**: 1.0.0
**Dernière mise à jour**: 2025-12-31
