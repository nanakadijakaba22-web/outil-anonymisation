# Guide d'installation Ollama pour Annoy

## Introduction

Ce guide vous accompagne dans l'installation et la configuration d'Ollama pour activer la détection IA améliorée dans Annoy.

**Pourquoi Ollama?**
- 🔒 **100% Local**: Vos données sensibles ne quittent jamais votre infrastructure
- 💰 **Gratuit**: Aucun coût d'API, aucun quota
- 🚀 **Performant**: Inférence optimisée sur votre matériel
- ✅ **Conforme Loi 25**: Pas d'envoi de données au cloud

---

## Table des matières

1. [Prérequis système](#prérequis-système)
2. [Installation Ollama](#installation-ollama)
3. [Installation du modèle](#installation-du-modèle)
4. [Configuration Annoy](#configuration-annoy)
5. [Vérification](#vérification)
6. [Troubleshooting](#troubleshooting)
7. [Migration depuis Groq](#migration-depuis-groq)

---

## Prérequis système

### Système d'exploitation

- ✅ **macOS** (10.15+)
- ✅ **Linux** (Ubuntu 20.04+, Debian, Fedora, CentOS)
- ✅ **Windows** (10/11 avec WSL2 recommandé)

### Matériel

**Minimum**:
- CPU: Intel i5 / AMD Ryzen 5 ou équivalent
- RAM: **4 GB** (pour gemma3:4b)
- Disque: 5 GB libres

**Recommandé**:
- CPU: Apple Silicon (M1/M2/M3) / Intel i7 / AMD Ryzen 7
- RAM: **8 GB**
- Disque: 10 GB libres
- GPU: NVIDIA/AMD (optionnel, pour accélération)

---

## Installation Ollama

### macOS

**Méthode 1: Installation automatique (recommandée)**

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

**Méthode 2: Homebrew**

```bash
brew install ollama
```

**Vérification**:
```bash
ollama --version
# Output: ollama version is 0.x.x
```

### Linux

**Ubuntu/Debian**:

```bash
# Installation automatique
curl -fsSL https://ollama.com/install.sh | sh

# Démarrer le service
sudo systemctl start ollama
sudo systemctl enable ollama  # Démarrage auto au boot

# Vérifier le service
sudo systemctl status ollama
```

**Fedora/CentOS/RHEL**:

```bash
# Installation
curl -fsSL https://ollama.com/install.sh | sh

# Démarrer le service
sudo systemctl start ollama
sudo systemctl enable ollama
```

**Arch Linux**:

```bash
# Via AUR
yay -S ollama

# Ou pacman (si disponible)
sudo pacman -S ollama
```

### Windows

**Option 1: Installation native (Preview)**

1. Télécharger l'installeur: [ollama.com/download/windows](https://ollama.com/download/windows)
2. Exécuter `OllamaSetup.exe`
3. Suivre l'assistant d'installation

**Option 2: WSL2 (Production-ready)**

```bash
# Dans WSL2 Ubuntu
curl -fsSL https://ollama.com/install.sh | sh

# Démarrer Ollama
ollama serve
```

### Docker (toutes plateformes)

```bash
# Option 1: Image officielle
docker run -d -v ollama:/root/.ollama -p 11434:11434 --name ollama ollama/ollama

# Option 2: Avec GPU NVIDIA
docker run -d --gpus=all -v ollama:/root/.ollama -p 11434:11434 --name ollama ollama/ollama
```

---

## Installation du modèle

### Gemma 3 4B (Recommandé)

```bash
# Télécharger le modèle
ollama pull gemma3:4b
```

**Progression**:
```
pulling manifest
pulling xxxxxxxx... 100% ▕████████████████▏ 3.3 GB
pulling xxxxxxxx... 100% ▕████████████████▏  11 KB
pulling xxxxxxxx... 100% ▕████████████████▏  12 KB
verifying sha256 digest
writing manifest
success
```

**Temps de téléchargement**: 3-10 minutes (selon connexion Internet)

**Vérifier l'installation**:
```bash
ollama list
```

**Output attendu**:
```
NAME              ID              SIZE    MODIFIED
gemma3:4b         xxxxxxxx        3.3 GB  5 minutes ago
```

### Alternatives

**Llama 3.2 3B** (pour RAM limitée):
```bash
ollama pull llama3.2:3b
```
- Taille: 2 GB
- RAM: 4 GB minimum
- Bon compromis taille/performance

**Llama 3.1 8B** (pour plus de precision):
```bash
ollama pull llama3.1:8b
```
- Taille: 4.7 GB
- RAM: 8 GB minimum
- Meilleure precision, plus lent

---

## Configuration Annoy

### 1. Variables d'environnement

**Fichier `.env`** (à la racine du projet):

```bash
# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=gemma3:4b

# AI Detection Settings
ENABLE_AI_DETECTION=true
AI_CONFIDENCE_THRESHOLD=70.0
```

**Configuration Docker** (si backend dans container):

```bash
# Pour macOS/Windows Docker Desktop
OLLAMA_BASE_URL=http://host.docker.internal:11434

# Pour Linux Docker
OLLAMA_BASE_URL=http://172.17.0.1:11434
```

**Note**: `host.docker.internal` permet au container Docker d'accéder à Ollama sur la machine hôte.

### 2. Démarrer les services

**Option A: Tout avec Docker**

```bash
# Démarrer Ollama (sur la machine hôte)
ollama serve  # Ou déjà démarré en service

# Démarrer Annoy
docker-compose up -d
```

**Option B: Backend local**

```bash
cd backend

# Vérifier que ollama-python est installé
poetry install

# Démarrer
poetry run uvicorn app.main:app --reload
```

---

## Vérification

### 1. Tester Ollama directement

```bash
# Vérifier le service
curl http://localhost:11434/api/tags

# Tester génération simple
curl -X POST http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemma3:4b",
    "prompt": "Classify this column: email_address",
    "stream": false
  }'
```

**Output attendu**: JSON avec réponse du modèle

### 2. Tester l'intégration Annoy

**Via API**:

```bash
# 1. Upload un dataset
curl -X POST http://localhost:8000/api/v1/datasets/upload \
  -F "file=@test_data.csv"

# → Retourne dataset_id

# 2. Lancer détection (avec IA)
curl -X POST "http://localhost:8000/api/v1/datasets/{dataset_id}/detect"
```

**Vérifier les logs backend**:
```bash
docker-compose logs backend | grep -i ollama
```

**Output attendu**:
```
INFO - Ollama AI detection initialized successfully (model: gemma3:4b)
INFO - AI improved classification for 3 columns
```

### 3. Vérifier l'endpoint health

```bash
curl http://localhost:8000/api/v1/health
```

**Output attendu**:
```json
{
  "status": "healthy",
  "ai_detection_enabled": true,
  "ollama_model": "gemma3:4b",
  "ollama_available": true
}
```

---

## Troubleshooting

### Problème 1: Ollama n'est pas accessible

**Symptômes**:
```
ERROR - Failed to connect to Ollama at http://localhost:11434
```

**Solutions**:

1. **Vérifier que Ollama tourne**:
```bash
# Voir les processus
ps aux | grep ollama

# Tester connexion
curl http://localhost:11434/api/tags
```

2. **Redémarrer Ollama**:
```bash
# Linux (service)
sudo systemctl restart ollama

# macOS/Windows (manuel)
ollama serve
```

3. **Vérifier le port**:
```bash
# Port 11434 doit être libre
lsof -i :11434
```

### Problème 2: Modèle non trouvé

**Symptômes**:
```
ERROR - Model gemma3:4b not found
```

**Solutions**:

```bash
# Lister les modèles installés
ollama list

# Télécharger le modèle manquant
ollama pull gemma3:4b
```

### Problème 3: Docker ne peut pas accéder à Ollama

**macOS/Windows**:
```bash
# Dans .env
OLLAMA_BASE_URL=http://host.docker.internal:11434
```

**Linux**:
```bash
# Option 1: IP de l'hôte
OLLAMA_BASE_URL=http://172.17.0.1:11434

# Option 2: Network host (moins sécurisé)
docker run --network host ...
```

**Vérifier depuis le container**:
```bash
docker-compose exec backend bash
curl http://host.docker.internal:11434/api/tags
```

### Problème 4: Performance lente

**Causes possibles**:
- RAM insuffisante
- CPU surchargé
- Modèle trop gros

**Solutions**:

1. **Utiliser un modèle plus léger**:
```bash
ollama pull llama3.2:3b
# Mettre à jour .env: OLLAMA_MODEL=llama3.2:3b
# Note: gemma3:4b est déjà un modèle léger et performant
```

2. **Augmenter RAM allouée (Docker)**:
```bash
# Docker Desktop > Settings > Resources
# Augmenter RAM à 8-12 GB
```

3. **Fermer applications gourmandes**:
```bash
# macOS
Activity Monitor > Quit apps

# Linux
htop (Shift+Q pour quitter apps)
```

### Problème 5: Erreur "Out of Memory"

**Symptômes**:
```
ERROR - Ollama: failed to allocate memory
```

**Solutions**:

1. **Vérifier RAM disponible**:
```bash
# macOS/Linux
free -h

# Output devrait montrer > 8GB disponible
```

2. **Redémarrer Ollama**:
```bash
sudo systemctl restart ollama
```

3. **Utiliser un modèle plus léger**:
```bash
ollama pull llama3.2:3b  # 2GB au lieu de 4.7GB
```

---

## Migration depuis Groq

Si vous migrez depuis une configuration Groq existante:

### 1. Sauvegarder ancienne configuration

```bash
# Sauvegarder .env
cp .env .env.groq.backup
```

### 2. Remplacer variables d'environnement

**Avant (Groq)**:
```bash
GROQ_API_KEY=gsk_xxxxx
GROQ_MODEL=llama-3.3-70b-versatile
ENABLE_AI_DETECTION=true
```

**Après (Ollama)**:
```bash
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=gemma3:4b
ENABLE_AI_DETECTION=true
```

### 3. Supprimer dépendances Groq

```bash
cd backend

# Retirer groq de pyproject.toml (si présent)
# poetry remove groq

# Ajouter ollama (déjà fait normalement)
poetry add ollama
```

### 4. Redémarrer services

```bash
# Arrêter tout
docker-compose down

# Démarrer Ollama
ollama serve

# Redémarrer Annoy
docker-compose up -d
```

### 5. Vérifier la migration

```bash
# Tester détection
curl -X POST "http://localhost:8000/api/v1/datasets/{dataset_id}/detect"

# Vérifier logs
docker-compose logs backend | grep -E "(Ollama|ollama)"
```

**Output attendu**:
```
INFO - Ollama AI detection initialized successfully
INFO - Using model: gemma3:4b
```

---

## Performance et optimisations

### GPU Acceleration (NVIDIA)

**Linux avec GPU NVIDIA**:

1. **Installer NVIDIA Container Toolkit**:
```bash
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
```

2. **Redémarrer Docker**:
```bash
sudo systemctl restart docker
```

3. **Lancer Ollama avec GPU**:
```bash
docker run -d --gpus=all \
  -v ollama:/root/.ollama \
  -p 11434:11434 \
  --name ollama \
  ollama/ollama
```

**Vérification**:
```bash
# Dans les logs, vous devriez voir "GPU detected"
docker logs ollama
```

### Cache et optimisations

**Augmenter cache Ollama**:

```bash
# Créer/éditer ~/.ollama/config.json
{
  "cache_size": "8GB",
  "num_gpu": 1
}
```

---

## Support et ressources

### Documentation officielle
- [Ollama GitHub](https://github.com/ollama/ollama)
- [Ollama Models Library](https://ollama.com/library)
- [Ollama Python Library](https://github.com/ollama/ollama-python)

### Communauté
- [Ollama Discord](https://discord.gg/ollama)
- [GitHub Issues](https://github.com/ollama/ollama/issues)

### Annoy-specific
- [AI_ENHANCED_DETECTION.md](./AI_ENHANCED_DETECTION.md) - Guide complet détection IA
- [CLAUDE.md](../CLAUDE.md) - Architecture et développement
- [README.md](../README.md) - Documentation principale

---

## Conclusion

Une fois Ollama configuré, vous bénéficiez de:
- ✅ Détection IA 100% locale et privée
- ✅ Aucun coût d'API
- ✅ Performance optimale sur votre matériel
- ✅ Conformité totale à la Loi 25

**Prochaines étapes**:
1. Tester la détection sur un dataset réel
2. Ajuster `AI_CONFIDENCE_THRESHOLD` selon vos besoins
3. Explorer d'autres modèles Ollama si besoin

---

**Version**: 1.0.0
**Dernière mise à jour**: 2026-01-25
**Auteur**: Annoy Team
