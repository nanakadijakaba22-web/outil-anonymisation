# 🛡️ MVP - Outil d'Anonymisation Conforme Loi 25 Québec

## 📋 Vue d'ensemble

**Durée :** 2 semaines  
**Objectif :** Démonstration fonctionnelle d'un outil d'anonymisation pour données financières  
**Stack recommandé :** Python (FastAPI) + React + PostgreSQL

---

## 🎯 Périmètre MVP (Scope)

### ✅ INCLUS dans le MVP
- Import de fichiers CSV
- Détection automatique des types de données sensibles
- 4 techniques d'anonymisation (masquage, généralisation, suppression, pseudonymisation)
- Évaluation des risques (3 critères Loi 25)
- Interface web simple
- Export CSV anonymisé
- Rapport de conformité PDF basique

### ❌ EXCLU du MVP (Phase 2)
- Multi-algorithmes avancés (k-anonymité, differential privacy)
- Traitement temps réel
- Intégration cloud hybride
- Gestion multi-utilisateurs complète
- Workflow d'approbation complexe

---

## 📅 SEMAINE 1 : Backend Core

---

### ÉTAPE 1 : Setup du projet (Jour 1 - 4h)

#### Instructions pour Claude Code :
```
Crée un projet Python avec la structure suivante :
- Backend FastAPI avec poetry pour la gestion des dépendances
- Structure modulaire avec les dossiers : api/, core/, models/, services/, utils/
- Configuration Docker pour développement local
- PostgreSQL comme base de données
- Fichier .env.example avec les variables nécessaires
```

#### Structure attendue :
```
anonymisation-tool/
├── backend/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── upload.py
│   │   │   ├── anonymize.py
│   │   │   └── reports.py
│   │   └── dependencies.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   └── database.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── dataset.py
│   │   └── anonymization.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── detector.py
│   │   ├── anonymizer.py
│   │   ├── risk_evaluator.py
│   │   └── report_generator.py
│   ├── utils/
│   │   └── __init__.py
│   ├── main.py
│   ├── pyproject.toml
│   └── Dockerfile
├── frontend/
├── docker-compose.yml
├── .env.example
└── README.md
```

#### ✅ Critères de validation :
```bash
# Test 1 : Le serveur démarre
cd backend && uvicorn main:app --reload
# Résultat attendu : Server running on http://127.0.0.1:8000

# Test 2 : Health check fonctionne
curl http://localhost:8000/health
# Résultat attendu : {"status": "healthy"}

# Test 3 : Docker compose fonctionne
docker-compose up -d
docker-compose ps
# Résultat attendu : Tous les services "Up"
```

---

### ÉTAPE 2 : Service d'import de données (Jour 1-2 - 6h)

#### Instructions pour Claude Code :
```
Crée un service d'upload et parsing de fichiers CSV avec :
1. Endpoint POST /api/v1/upload pour recevoir un fichier CSV
2. Validation du format (taille max 1GB, encodage UTF-8)
3. Stockage temporaire du fichier
4. Parsing avec pandas et détection automatique des types de colonnes
5. Sauvegarde des métadonnées en base de données
6. Retour d'un dataset_id pour les opérations suivantes
```

#### Fichier clé : `services/data_ingestion.py`
```python
# Fonctionnalités requises :
# - parse_csv(file) -> DataFrame
# - detect_column_types(df) -> dict avec types détectés
# - save_dataset_metadata(df, filename) -> dataset_id
# - get_dataset_preview(dataset_id, n_rows=10) -> dict
```

#### ✅ Critères de validation :
```bash
# Test 1 : Upload d'un CSV simple
curl -X POST -F "file=@test_data.csv" http://localhost:8000/api/v1/upload
# Résultat attendu : {"dataset_id": "uuid-xxx", "columns": [...], "row_count": N}

# Test 2 : Rejet d'un fichier invalide
curl -X POST -F "file=@image.png" http://localhost:8000/api/v1/upload
# Résultat attendu : {"error": "Format non supporté"}

# Test 3 : Preview des données
curl http://localhost:8000/api/v1/datasets/{dataset_id}/preview
# Résultat attendu : {"columns": [...], "sample": [...]}
```

#### Fichier de test à créer : `test_data.csv`
```csv
id,nom,prenom,email,telephone,date_naissance,nas,revenu_annuel,solde_compte
1,Tremblay,Jean,jean.tremblay@email.com,514-555-1234,1985-03-15,123-456-789,75000,15420.50
2,Gagnon,Marie,m.gagnon@company.ca,418-555-5678,1990-07-22,987-654-321,62000,8750.25
3,Roy,Pierre,pierre.roy@gmail.com,450-555-9012,1978-11-08,456-789-123,95000,42100.00
```

---

### ÉTAPE 3 : Détecteur de données sensibles (Jour 2-3 - 8h)

#### Instructions pour Claude Code :
```
Crée un service de détection automatique des identifiants avec :
1. Détection des identifiants DIRECTS : NAS, email, téléphone, nom, prénom, adresse
2. Détection des quasi-identifiants : date naissance, code postal, genre, âge
3. Classification automatique par catégorie (Loi 25) :
   - Renseignement personnel
   - Finance
   - Santé
   - Assurance
4. Score de confiance pour chaque détection (0-100%)
5. Utilisation de regex + heuristiques sur les noms de colonnes
```

#### Fichier clé : `services/detector.py`
```python
class SensitiveDataDetector:
    """
    Catégories de données selon Loi 25 :
    - DIRECT_IDENTIFIER : Identifie directement une personne
    - QUASI_IDENTIFIER : Peut identifier par combinaison
    - SENSITIVE : Données sensibles (santé, finance)
    - NON_SENSITIVE : Données non sensibles
    """
    
    def analyze_dataset(self, df: DataFrame) -> DetectionReport:
        """Analyse complète d'un dataset"""
        pass
    
    def detect_column_type(self, column_name: str, sample_values: list) -> ColumnClassification:
        """Détecte le type d'une colonne spécifique"""
        pass
    
    def get_risk_score(self, column_classification: dict) -> float:
        """Calcule un score de risque global (0-1)"""
        pass
```

#### Patterns de détection à implémenter :
```python
PATTERNS = {
    # Identifiants directs
    "NAS": r"^\d{3}[-\s]?\d{3}[-\s]?\d{3}$",
    "EMAIL": r"^[\w\.-]+@[\w\.-]+\.\w+$",
    "TELEPHONE_CA": r"^\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}$",
    
    # Noms de colonnes suspects
    "DIRECT_NAMES": ["nom", "name", "prenom", "firstname", "lastname", 
                     "email", "courriel", "telephone", "phone", "nas", 
                     "sin", "ssn", "adresse", "address"],
    "QUASI_NAMES": ["date_naissance", "birthdate", "dob", "age", 
                    "code_postal", "postal_code", "zip", "genre", "gender"],
    "FINANCIAL_NAMES": ["revenu", "income", "salary", "salaire", "solde", 
                        "balance", "credit", "dette", "debt"]
}
```

#### ✅ Critères de validation :
```bash
# Test 1 : Détection sur le dataset test
curl http://localhost:8000/api/v1/datasets/{dataset_id}/detect
# Résultat attendu :
{
  "columns": {
    "nom": {"type": "DIRECT_IDENTIFIER", "category": "personal", "confidence": 95},
    "email": {"type": "DIRECT_IDENTIFIER", "category": "personal", "confidence": 98},
    "nas": {"type": "DIRECT_IDENTIFIER", "category": "personal", "confidence": 99},
    "date_naissance": {"type": "QUASI_IDENTIFIER", "category": "personal", "confidence": 90},
    "revenu_annuel": {"type": "SENSITIVE", "category": "financial", "confidence": 85}
  },
  "overall_risk_score": 0.87
}

# Test 2 : Détection correcte du NAS
# Le pattern 123-456-789 doit être reconnu comme NAS

# Test 3 : Emails détectés avec haute confiance (>95%)
```

---

### ÉTAPE 4 : Moteur d'anonymisation (Jour 3-4 - 10h)

#### Instructions pour Claude Code :
```
Crée un moteur d'anonymisation avec 4 techniques configurables :

1. MASQUAGE (Masking)
   - Remplace par des caractères (ex: jean@email.com → j***@e****.com)
   - Configurable : nb de caractères visibles

2. GÉNÉRALISATION (Generalization)  
   - Remplace par une catégorie plus large
   - Ex: âge 34 → "30-40", code postal H3B 1A1 → "H3B"
   
3. SUPPRESSION (Suppression)
   - Supprime complètement la colonne
   
4. PSEUDONYMISATION
   - Remplace par un identifiant unique cohérent
   - Même valeur = même pseudo (pour garder les relations)
   
Chaque technique doit :
- Être réversible ou non selon configuration
- Logger les transformations appliquées
- Préserver les types de données quand possible
```

#### Fichier clé : `services/anonymizer.py`
```python
from enum import Enum
from typing import Callable

class AnonymizationTechnique(Enum):
    MASKING = "masking"
    GENERALIZATION = "generalization"
    SUPPRESSION = "suppression"
    PSEUDONYMIZATION = "pseudonymization"

class Anonymizer:
    def __init__(self):
        self.transformations_log = []
    
    def anonymize_dataset(
        self, 
        df: DataFrame, 
        config: dict  # {column_name: {technique: ..., params: {...}}}
    ) -> tuple[DataFrame, TransformationLog]:
        """Applique les anonymisations configurées"""
        pass
    
    def mask_value(self, value: str, visible_chars: int = 2) -> str:
        """Ex: 'jean.tremblay@email.com' → 'je**.**********@em***.com'"""
        pass
    
    def generalize_value(self, value, rules: dict) -> Any:
        """Ex: age 34 → '30-40', postal 'H3B 1A1' → 'H3B'"""
        pass
    
    def pseudonymize_column(self, values: list, seed: int = None) -> list:
        """Remplace par des pseudos cohérents (même input = même output)"""
        pass
```

#### Règles de généralisation à implémenter :
```python
GENERALIZATION_RULES = {
    "age": lambda x: f"{(x // 10) * 10}-{(x // 10) * 10 + 9}",
    "postal_code": lambda x: x[:3] if len(x) >= 3 else x,
    "date": lambda x: x.strftime("%Y") if hasattr(x, 'strftime') else str(x)[:4],
    "income": lambda x: categorize_income(x),  # <50k, 50-100k, >100k
}
```

#### ✅ Critères de validation :
```bash
# Test 1 : Anonymisation avec masquage
curl -X POST http://localhost:8000/api/v1/datasets/{dataset_id}/anonymize \
  -H "Content-Type: application/json" \
  -d '{
    "config": {
      "email": {"technique": "masking", "params": {"visible_chars": 2}},
      "nom": {"technique": "pseudonymization"},
      "nas": {"technique": "suppression"},
      "date_naissance": {"technique": "generalization", "params": {"level": "year"}}
    }
  }'
# Résultat attendu : {"anonymized_dataset_id": "uuid-yyy", "transformations": [...]}

# Test 2 : Vérification du masquage email
# "jean.tremblay@email.com" → "je************@em***.com"

# Test 3 : Vérification pseudonymisation cohérente
# Si "Tremblay" apparaît 2 fois, il doit avoir le même pseudo

# Test 4 : Export du dataset anonymisé
curl http://localhost:8000/api/v1/datasets/{anonymized_id}/download
# Résultat : Fichier CSV avec données anonymisées
```

---

### ÉTAPE 5 : Évaluateur de risques Loi 25 (Jour 4-5 - 8h)

#### Instructions pour Claude Code :
```
Crée un évaluateur de risques basé sur les 3 critères de la Loi 25 québécoise :

1. RISQUE D'INDIVIDUALISATION
   - Peut-on isoler un individu dans le dataset?
   - Vérifier l'unicité des combinaisons de quasi-identifiants
   
2. RISQUE DE CORRÉLATION  
   - Peut-on lier les données à d'autres sources?
   - Analyser les champs qui pourraient servir de clés de jointure
   
3. RISQUE D'INFÉRENCE
   - Peut-on déduire des informations sur un individu?
   - Vérifier les corrélations statistiques fortes

Chaque risque doit retourner :
- Score (0-100)
- Niveau (FAIBLE / MOYEN / ÉLEVÉ)
- Justification textuelle
- Recommandations
```

#### Fichier clé : `services/risk_evaluator.py`
```python
class RiskLevel(Enum):
    LOW = "faible"
    MEDIUM = "moyen"
    HIGH = "élevé"

@dataclass
class RiskAssessment:
    individualization_score: float  # 0-100
    correlation_score: float        # 0-100
    inference_score: float          # 0-100
    overall_level: RiskLevel
    details: dict
    recommendations: list[str]
    is_loi25_compliant: bool

class RiskEvaluator:
    def evaluate_dataset(self, df: DataFrame, detection_report: dict) -> RiskAssessment:
        """Évaluation complète selon critères Loi 25"""
        pass
    
    def check_individualization(self, df: DataFrame, quasi_identifiers: list) -> float:
        """
        Calcule le risque d'individualisation.
        Méthode : % de combinaisons uniques de quasi-identifiants
        Score élevé si >5% des lignes sont uniques
        """
        pass
    
    def check_correlation(self, df: DataFrame, columns: list) -> float:
        """
        Calcule le risque de corrélation externe.
        Analyse les colonnes pouvant servir de clés de jointure
        """
        pass
    
    def check_inference(self, df: DataFrame) -> float:
        """
        Calcule le risque d'inférence.
        Détecte les corrélations fortes entre colonnes
        """
        pass
```

#### Seuils de conformité Loi 25 :
```python
COMPLIANCE_THRESHOLDS = {
    "individualization": 15,  # Max 15% de lignes uniques
    "correlation": 20,        # Max 20 score de corrélation
    "inference": 25,          # Max 25 score d'inférence
    "overall": 20             # Score global max pour conformité
}
```

#### ✅ Critères de validation :
```bash
# Test 1 : Évaluation avant anonymisation (doit être non-conforme)
curl http://localhost:8000/api/v1/datasets/{dataset_id}/risk-assessment
# Résultat attendu :
{
  "individualization": {"score": 85, "level": "élevé"},
  "correlation": {"score": 70, "level": "élevé"},
  "inference": {"score": 45, "level": "moyen"},
  "overall_level": "élevé",
  "is_loi25_compliant": false,
  "recommendations": [
    "Supprimer ou masquer la colonne 'nas'",
    "Généraliser la colonne 'date_naissance'",
    ...
  ]
}

# Test 2 : Évaluation après anonymisation (doit être conforme)
curl http://localhost:8000/api/v1/datasets/{anonymized_id}/risk-assessment
# Résultat attendu : is_loi25_compliant: true
```

---

## 📅 SEMAINE 2 : Frontend + Rapports

---

### ÉTAPE 6 : Frontend - Interface d'upload (Jour 6 - 6h)

#### Instructions pour Claude Code :
```
Crée une application React avec :
1. Page d'accueil avec drag & drop pour upload CSV
2. Affichage de la progression d'upload
3. Preview des données (tableau des 10 premières lignes)
4. Navigation vers l'étape suivante

Stack :
- React 18+ avec Vite
- TailwindCSS pour le styling
- React Query pour les appels API
- React Router pour la navigation
```

#### Structure frontend :
```
frontend/
├── src/
│   ├── components/
│   │   ├── FileUpload.jsx
│   │   ├── DataPreview.jsx
│   │   ├── ProgressBar.jsx
│   │   └── Layout.jsx
│   ├── pages/
│   │   ├── Home.jsx
│   │   ├── Detection.jsx
│   │   ├── Anonymization.jsx
│   │   └── Report.jsx
│   ├── services/
│   │   └── api.js
│   ├── App.jsx
│   └── main.jsx
├── package.json
└── vite.config.js
```

#### ✅ Critères de validation :
```
# Test 1 : L'application React démarre
npm run dev
# Accéder à http://localhost:5173 → Page d'accueil visible

# Test 2 : Drag & drop fonctionnel
# Glisser un CSV → Affiche progression → Affiche preview

# Test 3 : Navigation vers détection
# Après upload → Bouton "Analyser" → Redirige vers /detection
```

---

### ÉTAPE 7 : Frontend - Interface de détection (Jour 6-7 - 4h)

#### Instructions pour Claude Code :
```
Crée la page de détection des données sensibles :
1. Affiche chaque colonne avec son type détecté
2. Code couleur : Rouge (direct), Orange (quasi), Vert (non-sensible)
3. Badge de confiance (%)
4. Possibilité de corriger manuellement le type
5. Bouton pour passer à l'anonymisation
```

#### Composants à créer :
```jsx
// ColumnCard.jsx - Affiche une colonne avec sa classification
// DetectionDashboard.jsx - Vue d'ensemble de toutes les colonnes
// RiskIndicator.jsx - Jauge visuelle du risque global
```

#### ✅ Critères de validation :
```
# Test 1 : Affichage des colonnes
# Toutes les colonnes du CSV sont listées

# Test 2 : Classification correcte
# 'nas' doit être en rouge (DIRECT_IDENTIFIER)
# 'date_naissance' doit être en orange (QUASI_IDENTIFIER)

# Test 3 : Modification manuelle
# Cliquer sur un type → Menu déroulant → Changer le type
```

---

### ÉTAPE 8 : Frontend - Interface d'anonymisation (Jour 7-8 - 6h)

#### Instructions pour Claude Code :
```
Crée l'interface de configuration de l'anonymisation :
1. Pour chaque colonne sensible, choix de la technique :
   - Dropdown : Masquage / Généralisation / Suppression / Pseudonymisation
2. Paramètres spécifiques par technique (ex: nb caractères visibles)
3. Preview en temps réel de l'anonymisation sur un échantillon
4. Bouton "Anonymiser" avec confirmation
5. Barre de progression pendant le traitement
```

#### Composants clés :
```jsx
// AnonymizationConfig.jsx - Configuration par colonne
// TechniqueSelector.jsx - Sélection de la technique
// PreviewPanel.jsx - Aperçu avant/après sur 5 lignes
// ProcessingModal.jsx - Modal de progression
```

#### ✅ Critères de validation :
```
# Test 1 : Sélection technique pour chaque colonne
# Dropdown fonctionnel pour chaque colonne sensible

# Test 2 : Preview temps réel
# Changer une technique → Preview se met à jour

# Test 3 : Lancement anonymisation
# Clic sur "Anonymiser" → Modal de progression → Redirection vers résultats
```

---

### ÉTAPE 9 : Générateur de rapport PDF (Jour 8-9 - 8h)

#### Instructions pour Claude Code :
```
Crée un service de génération de rapports PDF de conformité :

Le rapport doit inclure :
1. Page de titre avec logo, date, nom du dataset
2. Résumé exécutif (1 page)
3. Détail des colonnes détectées et leur classification
4. Techniques d'anonymisation appliquées
5. Évaluation des risques (3 critères Loi 25)
6. Conclusion de conformité (CONFORME / NON CONFORME)
7. Recommandations

Utiliser ReportLab ou WeasyPrint pour la génération PDF.
```

#### Fichier clé : `services/report_generator.py`
```python
class ReportGenerator:
    def generate_compliance_report(
        self,
        dataset_info: dict,
        detection_report: dict,
        anonymization_log: dict,
        risk_assessment: dict
    ) -> bytes:
        """Génère le PDF complet de conformité"""
        pass
    
    def _create_executive_summary(self) -> None:
        """Résumé exécutif d'une page"""
        pass
    
    def _create_risk_section(self) -> None:
        """Section détaillée des risques avec graphiques"""
        pass
    
    def _create_compliance_conclusion(self) -> None:
        """Conclusion avec statut de conformité"""
        pass
```

#### ✅ Critères de validation :
```bash
# Test 1 : Génération du rapport
curl http://localhost:8000/api/v1/datasets/{anonymized_id}/report \
  --output rapport.pdf
# Résultat : Fichier PDF téléchargé

# Test 2 : Le PDF s'ouvre correctement
# Vérifier que le PDF contient toutes les sections

# Test 3 : Contenu conforme
# Le statut de conformité doit correspondre à l'évaluation des risques
```

---

### ÉTAPE 10 : Frontend - Page de résultats (Jour 9-10 - 6h)

#### Instructions pour Claude Code :
```
Crée la page finale de résultats :
1. Dashboard avec les 3 jauges de risque (individualisation, corrélation, inférence)
2. Badge de conformité Loi 25 (vert si conforme, rouge sinon)
3. Tableau comparatif avant/après (échantillon de données)
4. Boutons d'action :
   - Télécharger CSV anonymisé
   - Télécharger rapport PDF
   - Recommencer avec un nouveau fichier
5. Timeline des transformations appliquées
```

#### ✅ Critères de validation :
```
# Test 1 : Affichage des résultats
# Les 3 scores de risque sont affichés avec jauges

# Test 2 : Téléchargement CSV
# Clic sur "Télécharger CSV" → Fichier téléchargé

# Test 3 : Téléchargement PDF
# Clic sur "Télécharger rapport" → PDF téléchargé

# Test 4 : Recommencer
# Clic sur "Nouveau fichier" → Retour à l'accueil
```

---

### ÉTAPE 11 : Intégration et tests E2E (Jour 10 - 4h)

#### Instructions pour Claude Code :
```
Crée les tests end-to-end du parcours complet :
1. Upload d'un fichier test
2. Vérification de la détection
3. Configuration de l'anonymisation
4. Exécution et vérification des résultats
5. Génération du rapport

Utiliser Playwright ou Cypress pour les tests E2E.
```

#### Fichier de test E2E :
```javascript
// tests/e2e/full-workflow.spec.js
describe('Parcours complet d\'anonymisation', () => {
  it('devrait anonymiser un CSV et générer un rapport conforme', () => {
    // 1. Upload
    cy.visit('/');
    cy.get('[data-testid="file-upload"]').attachFile('test_data.csv');
    cy.get('[data-testid="preview-table"]').should('be.visible');
    
    // 2. Détection
    cy.get('[data-testid="analyze-btn"]').click();
    cy.get('[data-testid="column-nas"]').should('have.class', 'direct-identifier');
    
    // 3. Anonymisation
    cy.get('[data-testid="continue-btn"]').click();
    cy.get('[data-testid="technique-nas"]').select('suppression');
    cy.get('[data-testid="technique-email"]').select('masking');
    cy.get('[data-testid="anonymize-btn"]').click();
    
    // 4. Résultats
    cy.get('[data-testid="compliance-badge"]').should('contain', 'CONFORME');
    cy.get('[data-testid="download-csv"]').click();
    cy.get('[data-testid="download-pdf"]').click();
  });
});
```

#### ✅ Critères de validation :
```bash
# Test 1 : Tests E2E passent
npm run test:e2e
# Résultat : Tous les tests verts

# Test 2 : Parcours manuel complet
# Effectuer le parcours manuellement sans erreur
```

---

### ÉTAPE 12 : Déploiement démo (Jour 10 - 4h)

#### Instructions pour Claude Code :
```
Prépare le déploiement pour la démo :
1. Dockerfile optimisé pour production
2. docker-compose.prod.yml avec Nginx
3. Script de déploiement sur un VPS (ou instructions pour Railway/Render)
4. Variables d'environnement de production
5. README avec instructions de démarrage rapide
```

#### Fichiers de déploiement :
```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  frontend:
    build: ./frontend
    ports:
      - "80:80"
  
  backend:
    build: ./backend
    environment:
      - DATABASE_URL=${DATABASE_URL}
    
  db:
    image: postgres:15
    volumes:
      - postgres_data:/var/lib/postgresql/data
```

#### ✅ Critères de validation :
```bash
# Test 1 : Build production
docker-compose -f docker-compose.prod.yml build
# Résultat : Build réussi sans erreur

# Test 2 : Démarrage production
docker-compose -f docker-compose.prod.yml up -d
# Résultat : Application accessible sur http://localhost

# Test 3 : Données de démo incluses
# Un fichier CSV de test est disponible pour la démo
```

---

## 📦 Livrables finaux

| Livrable | Description | Format |
|----------|-------------|--------|
| Code source | Repo Git complet | GitHub |
| Démo fonctionnelle | Application déployée | URL |
| Documentation API | Swagger/OpenAPI | /docs |
| Guide utilisateur | README détaillé | Markdown |
| Présentation | Slides de démo | PDF/PPTX |

---

## 🧪 Jeu de données de test

### Fichier : `demo_data.csv` (à créer pour les tests)
```csv
id,nom,prenom,email,telephone,date_naissance,nas,genre,code_postal,revenu_annuel,solde_compte,type_compte,date_ouverture
1,Tremblay,Jean,jean.tremblay@email.com,514-555-1234,1985-03-15,123-456-789,M,H3B 1A1,75000,15420.50,Chèque,2018-01-15
2,Gagnon,Marie,m.gagnon@company.ca,418-555-5678,1990-07-22,987-654-321,F,G1R 2B3,62000,8750.25,Épargne,2019-06-20
3,Roy,Pierre,pierre.roy@gmail.com,450-555-9012,1978-11-08,456-789-123,M,J4H 3C4,95000,42100.00,Chèque,2015-09-10
4,Bouchard,Sophie,sophie.b@outlook.com,819-555-3456,1995-02-28,789-123-456,F,H2X 1Y5,48000,3200.75,Épargne,2021-03-05
5,Côté,Martin,mcote@business.qc.ca,438-555-7890,1982-09-03,321-654-987,M,G2K 4D6,110000,78500.00,Premium,2010-11-22
```

---

## ⏱️ Timeline récapitulative

| Jour | Étape | Durée | Livrable |
|------|-------|-------|----------|
| 1 | Setup + Import | 10h | Backend base + Upload fonctionnel |
| 2-3 | Détection | 8h | Détecteur opérationnel |
| 3-4 | Anonymisation | 10h | 4 techniques fonctionnelles |
| 4-5 | Risques | 8h | Évaluateur Loi 25 |
| 6 | Frontend Upload | 6h | UI Upload + Preview |
| 6-7 | Frontend Détection | 4h | UI Détection |
| 7-8 | Frontend Anonymisation | 6h | UI Configuration |
| 8-9 | Rapports PDF | 8h | Générateur opérationnel |
| 9-10 | Frontend Résultats | 6h | UI Résultats complète |
| 10 | Tests + Déploiement | 8h | MVP déployé |

**Total : ~74h de développement**

---

## 🚀 Commande de démarrage pour Claude Code

```
Commence par l'ÉTAPE 1 : Setup du projet.
Suis exactement les instructions et valide chaque critère de test avant de passer à l'étape suivante.
Après chaque étape, confirme que tous les tests passent.
```
