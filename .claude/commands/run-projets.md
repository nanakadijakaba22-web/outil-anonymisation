# Run Project Command

Lance le projet Annoy (outil d'anonymisation conforme à la Loi 25 du Québec).

## Instructions

Quand l'utilisateur exécute cette commande, démarre tous les services du projet Annoy :

1. **Vérifier l'environnement** :
   - Vérifier que le fichier `.env` existe
   - Si absent, le créer depuis `.env.example`

2. **Démarrer les services Docker** :
   - Lancer `docker-compose up -d` pour démarrer PostgreSQL et FastAPI backend
   - Attendre que les services soient healthy

3. **Démarrer le frontend** :
   - Vérifier si `node_modules` existe, sinon exécuter `npm install`
   - Lancer `npm run dev` en arrière-plan pour Next.js

4. **Vérifier la santé des services** :
   - Backend: `curl http://localhost:8000/health`
   - Frontend: `curl http://localhost:3000`

5. **Afficher les URLs d'accès** :
   - Frontend: http://localhost:3000
   - API Docs: http://localhost:8000/docs
   - Backend Health: http://localhost:8000/health

## Résumé du projet

**Annoy** est un outil d'anonymisation de données pour la conformité à la Loi 25 du Québec.

**Stack** :
- Backend: FastAPI (Python 3.11+)
- Frontend: Next.js 16.1 (React 19, TypeScript)
- Database: PostgreSQL 15
- Containerization: Docker

**Architecture** :
```
Browser → Nginx → Next.js (3000) + FastAPI (8000) → PostgreSQL (5432)
```

**Workflow** :
Upload CSV → Detection → Anonymization → Risk Assessment → Export (CSV + PDF)

## Commandes utiles

```bash
# Arrêter les services
docker-compose down

# Voir les logs
docker-compose logs -f backend
docker-compose logs -f db

# Rebuild après changements
docker-compose up -d --build backend

# Accéder à la DB
docker-compose exec db psql -U postgres -d annoy_db

# Tests
docker-compose exec backend poetry run pytest tests/ -v
```

## Ne PAS relire

Cette commande évite de relire tout le code source. Utiliser directement les informations ci-dessus pour :
- Démarrer les services
- Vérifier leur état
- Fournir les URLs d'accès

Le fichier `CLAUDE.md` contient la documentation complète si des détails techniques sont nécessaires.
