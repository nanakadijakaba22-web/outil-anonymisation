# Configuration de l'Authentification - Annoy

## Vue d'ensemble

Toutes les pages de l'application Annoy nécessitent désormais l'authentification, à l'exception des pages publiques (login et register).

## Architecture

### Composants créés

1. **ProtectedRoute** (`src/components/ProtectedRoute.tsx`)
   - Vérifie l'état d'authentification avec `useAuth()`
   - Affiche un spinner de chargement pendant `isLoading`
   - Redirige vers `/login` si l'utilisateur n'est pas authentifié
   - Affiche les enfants si l'utilisateur est authentifié

2. **Header** (`src/components/Header.tsx`)
   - Affiche l'email de l'utilisateur avec avatar (première lettre)
   - Bouton "Profil" vers `/profile`
   - Bouton "Se déconnecter" qui effectue le logout et redirige vers `/login`
   - Design cohérent avec le gradient blue-indigo de l'application

### Pages protégées

Toutes les pages suivantes sont wrappées avec `<ProtectedRoute>` et incluent `<Header>`:

1. **Page d'accueil** (`src/app/page.tsx`)
   - Upload de fichiers CSV

2. **Page de détection** (`src/app/detection/[id]/page.tsx`)
   - Résultats de la détection de données sensibles

3. **Page d'anonymisation** (`src/app/anonymization/[id]/page.tsx`)
   - Configuration des techniques d'anonymisation

4. **Page de résultats** (`src/app/results/[id]/page.tsx`)
   - Évaluation des risques et conformité Loi 25

5. **Page de profil** (`src/app/profile/page.tsx`)
   - Informations utilisateur et gestion du compte

### Pages publiques

Ces pages ne nécessitent pas d'authentification:

1. **Login** (`src/app/login/page.tsx`)
2. **Register** (`src/app/register/page.tsx`)

## Workflow d'authentification

```
┌─────────────────┐
│  Utilisateur    │
│  non connecté   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  /login ou      │
│  /register      │
└────────┬────────┘
         │
         ▼ (authentification réussie)
┌─────────────────┐
│  Token stocké   │
│  dans           │
│  localStorage   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Accès aux      │
│  pages          │
│  protégées      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Header visible │
│  sur toutes les │
│  pages          │
└─────────────────┘
```

## Contexte d'authentification

Le contexte d'authentification (`src/lib/auth-context.tsx`) fournit:

- `user`: Objet utilisateur (id, email, full_name, etc.)
- `token`: Token JWT d'authentification
- `isLoading`: État de chargement
- `isAuthenticated`: Boolean indiquant si l'utilisateur est connecté
- `login(email, password)`: Fonction de connexion
- `register(email, password, fullName)`: Fonction d'inscription
- `logout()`: Fonction de déconnexion

## Sécurité

### Protection des routes

- **ProtectedRoute** vérifie l'authentification avant chaque render
- Redirection automatique vers `/login` si non authentifié
- Token vérifié à chaque chargement de page

### Gestion du token

- Token stocké dans `localStorage` sous la clé `auth_token`
- Token envoyé dans le header `Authorization: Bearer <token>`
- Token vérifié par le backend à chaque requête API

### Gestion des sessions

- Vérification du token au chargement de l'application
- Récupération automatique des informations utilisateur
- Nettoyage du token en cas d'erreur d'authentification

## Design

### Header

```
┌──────────────────────────────────────────────────────────┐
│  👤 Jean Tremblay         [Profil] [Se déconnecter]     │
│     jean@example.com                                     │
└──────────────────────────────────────────────────────────┘
```

### Spinner de chargement

Affiche un spinner centré avec le message "Vérification de l'authentification..." pendant le chargement initial.

## Tests

### Vérifier la protection

1. Essayer d'accéder à `/` sans être connecté → Redirection vers `/login`
2. Se connecter → Accès à toutes les pages protégées
3. Cliquer sur "Se déconnecter" → Retour à `/login`
4. Essayer d'accéder à une page protégée après déconnexion → Redirection vers `/login`

### Vérifier le Header

1. Se connecter
2. Vérifier que le Header s'affiche sur toutes les pages
3. Cliquer sur "Profil" → Navigation vers `/profile`
4. Cliquer sur "Se déconnecter" → Déconnexion et redirection

## Configuration

### Variables d'environnement

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Backend

Le backend doit fournir les endpoints suivants:

- `POST /api/v1/auth/login` - Connexion (OAuth2 password flow)
- `POST /api/v1/auth/register` - Inscription
- `GET /api/v1/auth/me` - Récupération des informations utilisateur

## Maintenance

### Ajouter une nouvelle page protégée

1. Créer la page dans `src/app/`
2. Importer les composants:
   ```tsx
   import ProtectedRoute from '@/components/ProtectedRoute';
   import Header from '@/components/Header';
   ```
3. Wrapper le contenu:
   ```tsx
   export default function MaNouvellePage() {
     return (
       <ProtectedRoute>
         <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
           <Header />
           {/* Votre contenu ici */}
         </div>
       </ProtectedRoute>
     );
   }
   ```

### Modifier le Header

Pour ajouter des boutons ou modifier le design, éditer `src/components/Header.tsx`.

## Statut

✅ **Toutes les pages sont protégées**

- ✅ Page d'accueil (upload)
- ✅ Page de détection
- ✅ Page d'anonymisation
- ✅ Page de résultats
- ✅ Page de profil

✅ **Pages publiques fonctionnelles**

- ✅ Login
- ✅ Register

✅ **Composants créés**

- ✅ ProtectedRoute
- ✅ Header

✅ **Tests de compilation**

- ✅ Next.js build réussi
- ✅ TypeScript compilation réussie
- ✅ Aucune erreur de syntaxe

## Prochaines étapes

- [ ] Ajouter un système de refresh token
- [ ] Implémenter la gestion des rôles (admin, user)
- [ ] Ajouter une page "Mot de passe oublié"
- [ ] Implémenter la persistance du token avec expiration
- [ ] Ajouter des tests unitaires pour les composants d'authentification

---

**Version**: 1.0.0
**Date**: 2026-01-18
**Status**: ✅ Production-ready
