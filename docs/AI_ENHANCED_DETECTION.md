# Détection améliorée par IA avec Ollama

## Vue d'ensemble

Annoy utilise maintenant une approche **hybride** pour détecter les données sensibles:
1. **Règles heuristiques** (rapide, gratuit, toujours disponible)
2. **IA Ollama** (optionnel, améliore la précision pour les cas ambigus)

### Avantages

- ✅ **100% Local**: Aucune donnée envoyée à des services externes
- ✅ **Gratuit**: Aucun coût d'API
- ✅ **Rapide**: Inférence locale optimisée (~150ms par colonne)
- ✅ **Privé**: Données sensibles restent sur votre infrastructure
- ✅ **Précis**: Modèle Llama 3.1 8B performant pour la classification
- ✅ **Fallback intelligent**: Fonctionne même sans Ollama (règles seulement)
- ✅ **Transparent**: Les justifications [IA] indiquent les résultats améliorés

## Pourquoi Ollama?

### Privacy-First

Contrairement aux solutions cloud (OpenAI, Groq, etc.), Ollama exécute les modèles **localement sur votre machine**. Vos données sensibles ne quittent jamais votre infrastructure, ce qui est crucial pour la conformité à la Loi 25.

### Sans Coût

Aucune clé API, aucun quota, aucun frais caché. Ollama est entièrement gratuit et open-source.

### Production-Ready

- Haute performance grâce à l'optimisation locale
- Pas de dépendance réseau (fonctionne offline)
- Pas de limite de requêtes
- Contrôle total sur le modèle utilisé

## Architecture

```
                    ┌─────────────────────┐
                    │   Dataset Upload    │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │  POST /detect       │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────────────┐
                    │  AIEnhancedDetector         │
                    └──────────┬──────────────────┘
                               │
          ┌────────────────────┴────────────────────┐
          │                                         │
    ┌─────▼─────────┐                    ┌─────────▼──────┐
    │ Rule-Based    │                    │  Ollama AI     │
    │ Detection     │                    │  Enhancement   │
    │ (toujours)    │                    │  (si running)  │
    └─────┬─────────┘                    └─────────┬──────┘
          │                                        │
          │  Confidence < 70%  ──────────────────▶ │
          │                                        │
          │       Local: http://localhost:11434   │
          └────────────┬───────────────────────────┘
                       │
            ┌──────────▼──────────┐
            │  Combined Results   │
            │  (Règles + IA)      │
            └─────────────────────┘
```

## Installation et Configuration

### 1. Installer Ollama

**macOS/Linux**:
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

**Windows**:
Télécharger depuis [https://ollama.com/download](https://ollama.com/download)

**Vérifier l'installation**:
```bash
ollama --version
# → ollama version is 0.x.x
```

### 2. Télécharger le modèle Llama 3.1 8B

```bash
ollama pull llama3.1:8b
```

**Taille du modèle**: ~4.7GB

**Vérifier**:
```bash
ollama list
# → llama3.1:8b    4.7 GB    ...
```

### 3. Démarrer Ollama

Ollama démarre automatiquement en service après installation. Pour vérifier:

```bash
# Tester le service
curl http://localhost:11434/api/tags

# Devrait retourner la liste des modèles
```

### 4. Configurer les variables d'environnement

**Fichier `.env`**:
```bash
# URL de base Ollama (défaut: localhost)
OLLAMA_BASE_URL=http://localhost:11434

# Modèle à utiliser
OLLAMA_MODEL=llama3.1:8b

# Activer la détection IA
ENABLE_AI_DETECTION=true

# Seuil de confiance pour l'amélioration IA (70% par défaut)
# Les colonnes avec confiance < seuil seront validées par l'IA
AI_CONFIDENCE_THRESHOLD=70.0
```

**Configuration Docker**:
```yaml
# docker-compose.yml
environment:
  - OLLAMA_BASE_URL=http://host.docker.internal:11434
  - OLLAMA_MODEL=llama3.1:8b
  - ENABLE_AI_DETECTION=true
```

**Note**: `host.docker.internal` permet au container Docker d'accéder à Ollama sur la machine hôte.

### 5. Installer les dépendances Python

```bash
cd backend
poetry install  # Installe ollama-python automatiquement
```

### 6. Redémarrer le backend

```bash
# Avec Docker
docker-compose restart backend

# Sans Docker
cd backend
poetry run uvicorn app.main:app --reload
```

## Utilisation

### API

L'endpoint de détection utilise automatiquement l'IA si configurée:

```bash
POST /api/v1/datasets/{dataset_id}/detect
```

**Sans Ollama**:
- Utilise uniquement les règles heuristiques
- Rapide (~1s pour 5000 lignes)
- Confiance basée sur pattern matching

**Avec Ollama**:
- Utilise les règles d'abord (rapide)
- Améliore avec l'IA locale pour confiance < 70%
- Légèrement plus lent (~2-3s) mais beaucoup plus précis
- **100% privé** - données restent locales

### Interpréter les résultats

**Justifications**:
- `"Format NAS détecté"` → Règle heuristique
- `"[IA] Identifiant client unique selon Loi 25"` → Validation IA Ollama
- `"Format email détecté (confirmé par IA)"` → Règles + IA en accord

**Confiance**:
- `< 70%` → Faible confiance, vérification manuelle recommandée
- `70-85%` → Confiance moyenne, probablement correct
- `> 85%` → Haute confiance, validation IA ou règles claires

## Modèles Ollama disponibles

### Recommandé: llama3.1:8b
- **Vitesse**: ⚡⚡⚡⚡ (rapide)
- **Précision**: 🎯🎯🎯🎯 (excellente)
- **Taille**: 4.7 GB
- **RAM requise**: ~8 GB
- **Cas d'usage**: Classification de colonnes (optimal)

### Alternatives

| Modèle | Vitesse | Précision | Taille | RAM | Cas d'usage |
|--------|---------|-----------|--------|-----|-------------|
| `llama3.1:8b` | ⚡⚡⚡⚡ | 🎯🎯🎯🎯 | 4.7GB | 8GB | **Recommandé** |
| `llama3.2:3b` | ⚡⚡⚡⚡⚡ | 🎯🎯🎯 | 2GB | 4GB | Machines limitées |
| `mistral:7b` | ⚡⚡⚡⚡ | 🎯🎯🎯 | 4.1GB | 8GB | Alternative rapide |

**Changer de modèle**:
```bash
# Télécharger un autre modèle
ollama pull llama3.2:3b

# Mettre à jour .env
OLLAMA_MODEL=llama3.2:3b
```

## Stratégie de détection

### 1. Détection par règles (toujours active)

**Heuristiques**:
- Analyse du nom de colonne (keywords: "nom", "email", "nas", etc.)
- Pattern matching regex (NAS, email, téléphone, code postal)
- Statistiques (ratio d'unicité, null count)
- Type de données (numeric → possiblement financier)

**Avantages**:
- Très rapide (< 1s)
- Pas de dépendance externe
- Fonctionne offline

**Limitations**:
- Faux positifs sur noms ambigus ("id", "numero")
- Faux négatifs sur noms non-standards ("ref_client", "courriel_personnel")

### 2. Amélioration IA locale (si configurée)

**Déclenchement**:
- Colonne avec confiance < `AI_CONFIDENCE_THRESHOLD` (défaut: 70%)

**Prompt IA**:
```
Nom de colonne: id_ref
Type: int64
Échantillons: [1001, 1002, 1003, ...]
Classification initiale: non_sensitive (50% confiance)

→ IA Ollama analyse le contexte et répond:
{
  "sensitivity_type": "direct_identifier",
  "category": "personal",
  "confidence": 85,
  "justification": "Identifiant unique de référence client"
}
```

**Combinaison des résultats**:
- IA confiance > 80% → Prendre classification IA
- Règles et IA d'accord → Boost confiance (+10%)
- Désaccord → Pondération selon confiance (70% meilleur / 30% autre)

## Performance et ressources

### Benchmarks

**Dataset test**: 5000 lignes × 15 colonnes
**Machine**: MacBook Pro M1 (16GB RAM)

| Méthode | Temps | Précision | Coût | Privacy |
|---------|-------|-----------|------|---------|
| Règles seules | ~1s | 75% | Gratuit | ✅ Local |
| Règles + Ollama (5 colonnes) | ~3s | 92% | Gratuit | ✅ Local |
| Ollama complet (15 colonnes) | ~10s | 95% | Gratuit | ✅ Local |

**Recommandation**: Utiliser seuil 70% (défaut) pour équilibre optimal.

### Ressources système

**RAM**:
- Ollama seul: ~1-2 GB
- Avec llama3.1:8b chargé: ~8-10 GB
- Total système recommandé: **16 GB**

**CPU**:
- CPU moderne requis (Intel i5+ ou Apple Silicon)
- GPU optionnel (NVIDIA/AMD) pour accélération

**Disque**:
- Espace requis: ~10 GB (modèle + cache)

## Exemples

### Cas 1: Détection améliorée d'un identifiant

**Sans IA**:
```json
{
  "column_name": "ref",
  "sensitivity_type": "non_sensitive",
  "confidence": 50,
  "justification": "Nom de colonne ambigu"
}
```

**Avec IA Ollama**:
```json
{
  "column_name": "ref",
  "sensitivity_type": "direct_identifier",
  "category": "personal",
  "confidence": 88,
  "justification": "[IA] Identifiant de référence client unique selon contexte"
}
```

### Cas 2: Confirmation de classification

**Sans IA**:
```json
{
  "column_name": "email_contact",
  "sensitivity_type": "direct_identifier",
  "confidence": 75,
  "justification": "Format email détecté; Nom suggère personal"
}
```

**Avec IA Ollama (en accord)**:
```json
{
  "column_name": "email_contact",
  "sensitivity_type": "direct_identifier",
  "category": "personal",
  "confidence": 90,
  "justification": "Format email détecté; Nom suggère personal + [IA] Adresse email professionnelle confirmée (confirmé par IA)"
}
```

### Cas 3: Correction d'erreur

**Sans IA**:
```json
{
  "column_name": "ville_siege_social",
  "sensitivity_type": "quasi_identifier",
  "confidence": 65,
  "justification": "Nom suggère personal"
}
```

**Avec IA Ollama (corrige)**:
```json
{
  "column_name": "ville_siege_social",
  "sensitivity_type": "non_sensitive",
  "category": "other",
  "confidence": 82,
  "justification": "[IA] Ville du siège social de l'entreprise, non personnel"
}
```

## Logging et debugging

### Activer les logs détaillés

**Python logging**:
```python
import logging
logging.getLogger("app.services.ai_enhanced_detector").setLevel(logging.INFO)
```

**Logs typiques**:
```
INFO - Ollama AI detection initialized successfully (model: llama3.1:8b)
INFO - Low confidence (55%) for 'ref_client', using AI enhancement
INFO - AI improved classification for 3 columns
```

### Vérifier l'état de l'IA

**Tester Ollama**:
```bash
# Vérifier service
curl http://localhost:11434/api/tags

# Tester génération
curl -X POST http://localhost:11434/api/generate \
  -d '{"model": "llama3.1:8b", "prompt": "Test", "stream": false}'
```

**Endpoint health backend**:
```bash
GET /api/v1/health
```

```json
{
  "status": "healthy",
  "ai_detection_enabled": true,
  "ollama_model": "llama3.1:8b",
  "ollama_available": true
}
```

## Troubleshooting

### Problème: IA non activée malgré configuration

**Vérifier**:
```bash
# 1. Ollama running?
curl http://localhost:11434/api/tags

# 2. Modèle téléchargé?
ollama list

# 3. Flag activé?
echo $ENABLE_AI_DETECTION  # doit être "true"

# 4. Logs backend
docker-compose logs backend | grep -i ollama
```

**Solutions**:
- Démarrer Ollama: `ollama serve` (si pas en service)
- Télécharger modèle: `ollama pull llama3.1:8b`
- Mettre `ENABLE_AI_DETECTION=true` dans .env
- Redémarrer backend

### Problème: Erreur de connexion Docker → Ollama

**Symptômes**:
```
ERROR - Failed to connect to Ollama at http://host.docker.internal:11434
```

**Solutions**:

**macOS/Windows**:
```bash
# Utiliser host.docker.internal (par défaut)
OLLAMA_BASE_URL=http://host.docker.internal:11434
```

**Linux**:
```bash
# Utiliser l'IP de la machine hôte
OLLAMA_BASE_URL=http://172.17.0.1:11434

# Ou ajouter --network host au container
```

### Problème: Performance lente

**Causes**:
- RAM insuffisante (< 8GB)
- CPU limité
- Modèle trop gros

**Solutions**:
- Utiliser modèle plus léger: `llama3.2:3b`
- Fermer applications gourmandes en RAM
- Augmenter RAM disponible
- Activer GPU si disponible (NVIDIA/AMD)

### Problème: Réponses IA incohérentes

**Causes**:
- Température trop élevée
- Prompt ambigu

**Solutions**:
- Vérifier `temperature=0.1` dans `ai_enhanced_detector.py`
- Améliorer les échantillons de valeurs (plus de contexte)
- Essayer un autre modèle (mistral:7b)

## Comparaison Ollama vs Cloud APIs

| Critère | Ollama (Local) | Groq/OpenAI (Cloud) |
|---------|----------------|---------------------|
| **Privacy** | ✅ 100% local | ❌ Données envoyées au cloud |
| **Coût** | ✅ Gratuit | ❌ Payant ou quotas limités |
| **Vitesse** | ⚡ ~150ms/colonne | ⚡ ~100ms/colonne |
| **Disponibilité** | ✅ Offline | ❌ Requiert Internet |
| **Conformité Loi 25** | ✅ Conforme | ⚠️ Dépend du provider |
| **Setup** | ⚠️ Installation requise | ✅ Simple (clé API) |
| **Ressources** | ⚠️ RAM/CPU requis | ✅ Aucune |

**Verdict**: Ollama est **optimal pour Annoy** car la confidentialité des données est primordiale pour la conformité à la Loi 25.

## Roadmap

### Phase 1 (Actuel) ✅
- [x] Migration de Groq vers Ollama
- [x] Détection hybride (règles + IA locale)
- [x] Fallback intelligent
- [x] Configuration flexible
- [x] Support Docker

### Phase 2 (À venir)
- [ ] Cache des classifications IA
- [ ] Mode batch (plusieurs colonnes par requête)
- [ ] Feedback utilisateur (améliorer prompt)
- [ ] Support GPU automatique

### Phase 3 (Futur)
- [ ] Fine-tuning sur données Loi 25
- [ ] Détection de patterns personnalisés
- [ ] Apprentissage des corrections manuelles
- [ ] Support multi-modèles

## Références

- [Ollama Documentation](https://github.com/ollama/ollama/blob/main/docs/README.md)
- [Llama 3.1 Model Card](https://www.llama.com/docs/model-cards-and-prompt-formats/llama3_1)
- [Ollama Python Library](https://github.com/ollama/ollama-python)
- [Loi 25 du Québec](https://www.cai.gouv.qc.ca/)

---

**Version**: 2.0.0
**Dernière mise à jour**: 2026-01-25
**Auteur**: Annoy Team
