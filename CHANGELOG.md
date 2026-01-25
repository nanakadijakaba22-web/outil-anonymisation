# Changelog

Toutes les modifications notables du projet Annoy sont documentées dans ce fichier.

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/),
et ce projet adhère au [Semantic Versioning](https://semver.org/lang/fr/).

## [0.1.0-beta] - 2025-12-31

### 🎉 Version Initiale - MVP Complet

Premier release fonctionnel de l'outil d'anonymisation conforme à la Loi 25 du Québec.

### ✨ Ajouté

#### Backend (FastAPI)
- Infrastructure complète avec Docker et PostgreSQL 15
- API RESTful avec documentation OpenAPI automatique
- Upload et ingestion de fichiers CSV (max 1 GB)
- Détection automatique de données sensibles avec 4 types de classification
- 4 techniques d'anonymisation professionnelles:
  - Masquage (emails, téléphones, cartes de crédit)
  - Généralisation (âges, revenus, codes postaux)
  - Suppression (données ultra-sensibles)
  - Pseudonymisation (noms, prénoms)
- Évaluation des risques selon 3 critères de la Loi 25:
  - Individualisation (40% du score)
  - Corrélation (35% du score)
  - Inférence (25% du score)
- Génération de rapports PDF professionnels avec ReportLab
- 5 modèles SQLAlchemy (Dataset, DatasetColumn, AnonymizationJob, TransformationLog, RiskAssessment)
- Migrations de base de données avec Alembic
- Tests E2E complets du workflow

#### Frontend (Next.js)
- 4 pages interactives avec React 19 et TypeScript 5
- Page d'upload avec drag & drop
- Visualisation des résultats de détection avec badges colorés
- Configuration interactive de l'anonymisation
- Dashboard de conformité avec jauges de risque circulaires
- Client API type-safe avec gestion d'erreurs
- Téléchargement de CSV anonymisés
- Téléchargement de rapports PDF
- Design responsive avec Tailwind CSS v4

#### Documentation
- README complet avec exemples et guides
- Guide utilisateur détaillé (40 pages)
- Documentation technique complète (architecture, API, algorithmes)
- Guide de déploiement production
- Configuration Docker Compose pour développement et production

#### Déploiement
- Configuration production-ready avec:
  - Nginx reverse proxy (rate limiting, SSL, compression)
  - 4 workers uvicorn pour FastAPI
  - Utilisateurs non-root dans containers
  - Health checks automatiques
  - Volumes persistants pour PostgreSQL
- Template .env.production.example
- Scripts de backup et restauration
- Configuration SSL/HTTPS ready

### 🚀 Performance

- Upload: < 1s pour 779 KB
- Détection: < 1s pour 5000 lignes
- Anonymisation: **88ms pour 5000 lignes** (17.6 µs/ligne!)
- Évaluation: < 1s
- Génération PDF: 68ms (3 pages)
- **Workflow complet: < 3s pour 5000 clients**

### 🔒 Sécurité

- Rate limiting (10 req/s général, 5 req/min uploads)
- Headers de sécurité (X-Frame-Options, X-Content-Type-Options, CSP)
- CORS configuré avec whitelist
- Validation des entrées avec Pydantic v2
- Protection contre injection SQL (SQLAlchemy ORM)
- Containers non-root
- Taille maximale de fichier enforced

### 📊 Conformité Loi 25

- Implémentation des articles 3.3, 3.5, 3.6, 63.1
- Seuil de conformité: score < 20%
- Rapports PDF d'audit
- Documentation complète des mesures

### ✅ Tests

Test complet validé avec dataset de **5000 clients**:
- **Avant anonymisation**: Score 16.7% (presque conforme)
- **Après anonymisation**: Score 0.0% (100% conforme)
- 9 colonnes transformées
- CSV exporté + PDF généré
- Workflow en < 3 secondes

### 📝 Commits

Total de **23 commits** professionnels:
- 7 commits pour Phase 1-4 (Backend core)
- 4 commits pour Phase 5 (Frontend)
- 4 commits pour Phase 6 (PDF reports)
- 3 commits pour Phase 7 (Tests & Deployment)
- 5 commits pour documentation

### 🎯 Statistiques

- **~8,000 lignes** de code backend (Python)
- **~2,500 lignes** de code frontend (TypeScript)
- **~50+ fichiers** créés
- **500+ lignes** de documentation README
- **100% couverture** des fonctionnalités MVP

---

## [Unreleased]

### [0.2.0] - 2026-01-25

### 🔄 Changed
- **Migration de Groq vers Ollama pour détection IA**
  - Utilisation de Llama 3.1 8B en local (100% privé)
  - Aucun coût d'API, données sensibles restent locales
  - Configuration: `OLLAMA_BASE_URL` et `OLLAMA_MODEL` dans .env
  - Meilleure conformité à la Loi 25 (pas d'envoi de données au cloud)
  - Documentation complète dans `docs/AI_ENHANCED_DETECTION.md`

### 🗑️ Removed
- Dépendance Groq API et configuration associée
- Variables d'environnement `GROQ_API_KEY` et `GROQ_MODEL`

### 📝 Documentation
- Mise à jour complète de `docs/AI_ENHANCED_DETECTION.md` avec guide Ollama
- Ajout de `docs/OLLAMA_SETUP.md` pour installation détaillée
- Mise à jour de `CLAUDE.md` et `README.md` avec références Ollama
- Guide de migration Groq → Ollama dans la documentation

### À venir (v0.3.0)

#### Fonctionnalités planifiées
- Support Excel/XLSX
- K-anonymity avancé
- Differential privacy
- Multi-tenancy avec authentification
- Audit logging complet
- API webhooks pour intégrations
- Export vers formats additionnels (JSON, Parquet)
- Interface d'administration
- Gestion des datasets par organisation
- Historique des anonymisations

#### Améliorations techniques
- Cache Redis pour performances
- Elasticsearch pour recherche full-text
- Queue Celery pour traitement asynchrone
- Monitoring avec Prometheus + Grafana
- CI/CD avec GitHub Actions
- Tests de charge (k6 ou Locust)

#### Documentation
- Tutoriels vidéo
- Guide de contribution
- Architecture Decision Records (ADR)
- API client libraries (Python, JavaScript)

---

## Versioning

Ce projet utilise [Semantic Versioning](https://semver.org/):
- **MAJOR**: Changements incompatibles de l'API
- **MINOR**: Nouvelles fonctionnalités rétro-compatibles
- **PATCH**: Corrections de bugs rétro-compatibles

---

## Support

- Issues: https://github.com/<org>/annoy/issues
- Documentation: https://github.com/<org>/annoy/docs
- Email: support@annoy.local

---

**Légende**:
- ✨ Ajouté: Nouvelles fonctionnalités
- 🔧 Modifié: Changements dans les fonctionnalités existantes
- 🐛 Corrigé: Corrections de bugs
- 🔒 Sécurité: Corrections de vulnérabilités
- ⚠️ Déprécié: Fonctionnalités bientôt retirées
- 🗑️ Retiré: Fonctionnalités supprimées
- 🚀 Performance: Améliorations de performance
- 📝 Documentation: Mises à jour de documentation
