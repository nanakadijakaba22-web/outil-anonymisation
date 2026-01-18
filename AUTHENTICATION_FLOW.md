# Flow d'Authentification - Annoy

## Diagramme de flux complet

```
                    ┌─────────────────────────────────┐
                    │  Utilisateur visite l'app       │
                    └────────────┬────────────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────────────┐
                    │  AuthProvider chargé            │
                    │  (useEffect au mount)           │
                    └────────────┬────────────────────┘
                                 │
                    ┌────────────┴────────────┐
                    │                         │
                    ▼                         ▼
        ┌───────────────────┐    ┌───────────────────┐
        │ Token trouvé      │    │ Pas de token      │
        │ dans localStorage │    │ localStorage vide │
        └────────┬──────────┘    └────────┬──────────┘
                 │                         │
                 ▼                         ▼
        ┌───────────────────┐    ┌───────────────────┐
        │ Appel GET /auth/me│    │ isAuthenticated   │
        │ avec Bearer token │    │ = false           │
        └────────┬──────────┘    └────────┬──────────┘
                 │                         │
    ┌────────────┴────────────┐           │
    │                         │           │
    ▼                         ▼           ▼
┌─────────┐            ┌──────────┐  ┌──────────────┐
│ Token   │            │ Token    │  │ Redirection  │
│ valide  │            │ invalide │  │ vers /login  │
└────┬────┘            └─────┬────┘  └──────────────┘
     │                       │
     │                       ▼
     │              ┌──────────────┐
     │              │ Nettoyer     │
     │              │ localStorage │
     │              └─────┬────────┘
     │                    │
     │                    ▼
     │              ┌──────────────┐
     │              │ Redirection  │
     │              │ vers /login  │
     │              └──────────────┘
     │
     ▼
┌──────────────────┐
│ setUser(data)    │
│ isAuthenticated  │
│ = true           │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ ProtectedRoute   │
│ affiche children │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Header visible   │
│ + Page content   │
└──────────────────┘
```

## Flow de connexion

```
┌──────────────┐
│ User sur     │
│ /login       │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Saisie email │
│ et password  │
└──────┬───────┘
       │
       ▼
┌──────────────────┐
│ Submit form      │
│ login(email, pwd)│
└──────┬───────────┘
       │
       ▼
┌──────────────────────┐
│ POST /auth/login     │
│ (OAuth2 password)    │
│ username=email       │
│ password=password    │
└──────┬───────────────┘
       │
   ┌───┴────┐
   │        │
   ▼        ▼
┌──────┐  ┌──────┐
│ 200  │  │ 401  │
│ OK   │  │ Error│
└──┬───┘  └───┬──┘
   │          │
   │          ▼
   │      ┌──────────┐
   │      │ Afficher │
   │      │ erreur   │
   │      └──────────┘
   │
   ▼
┌──────────────────┐
│ Recevoir         │
│ access_token     │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ localStorage.    │
│ setItem('auth_   │
│ token', token)   │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ GET /auth/me     │
│ Bearer token     │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ setUser(data)    │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ router.push('/')  │
│ Redirection accueil│
└──────────────────┘
```

## Flow d'inscription

```
┌──────────────┐
│ User sur     │
│ /register    │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Saisie form: │
│ - email      │
│ - password   │
│ - confirm    │
│ - full_name  │
└──────┬───────┘
       │
       ▼
┌──────────────────┐
│ Validation côté  │
│ client:          │
│ - pwd = confirm  │
│ - pwd >= 8 chars │
└──────┬───────────┘
       │
   ┌───┴────┐
   │        │
   ▼        ▼
┌──────┐  ┌──────┐
│ OK   │  │ Error│
└──┬───┘  └───┬──┘
   │          │
   │          ▼
   │      ┌──────────┐
   │      │ Afficher │
   │      │ erreur   │
   │      └──────────┘
   │
   ▼
┌──────────────────┐
│ POST /auth/      │
│ register         │
│ {email, pwd,     │
│  full_name}      │
└──────┬───────────┘
       │
   ┌───┴────┐
   │        │
   ▼        ▼
┌──────┐  ┌──────┐
│ 200  │  │ Error│
│ OK   │  │ 4xx  │
└──┬───┘  └───┬──┘
   │          │
   │          ▼
   │      ┌──────────┐
   │      │ Afficher │
   │      │ erreur   │
   │      └──────────┘
   │
   ▼
┌──────────────────┐
│ Auto-login       │
│ login(email, pwd)│
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ router.push('/')  │
│ Redirection accueil│
└──────────────────┘
```

## Flow de déconnexion

```
┌──────────────┐
│ User clique  │
│ "Se décon-   │
│ necter"      │
└──────┬───────┘
       │
       ▼
┌──────────────────┐
│ logout()         │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ localStorage.    │
│ removeItem(      │
│ 'auth_token')    │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ setToken(null)   │
│ setUser(null)    │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ router.push(     │
│ '/login')        │
└──────────────────┘
```

## ProtectedRoute - Flow détaillé

```
┌──────────────────────────┐
│ Component render         │
│ <ProtectedRoute>         │
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│ useAuth() hook           │
│ - isAuthenticated        │
│ - isLoading              │
└──────────┬───────────────┘
           │
     ┌─────┴──────┐
     │            │
     ▼            ▼
┌─────────┐  ┌─────────┐
│isLoading│  │ Loaded  │
│= true   │  │         │
└────┬────┘  └────┬────┘
     │            │
     ▼            │
┌─────────────┐   │
│ Afficher    │   │
│ spinner de  │   │
│ chargement  │   │
└─────────────┘   │
                  │
          ┌───────┴────────┐
          │                │
          ▼                ▼
    ┌──────────┐     ┌──────────┐
    │isAuthen- │     │isAuthen- │
    │ticated   │     │ticated   │
    │= false   │     │= true    │
    └────┬─────┘     └────┬─────┘
         │                │
         ▼                ▼
    ┌──────────┐     ┌──────────┐
    │useEffect:│     │ Render   │
    │router.   │     │ children │
    │push('/   │     │          │
    │login')   │     └──────────┘
    └──────────┘
```

## Header - Structure des composants

```
┌─────────────────────────────────────────────────────────┐
│ Header Component                                        │
│ ┌─────────────────────────────────────────────────────┐│
│ │ useAuth() → user                                    ││
│ │                                                     ││
│ │ ┌─────────────────┐  ┌──────────┐  ┌────────────┐ ││
│ │ │ Avatar + Email  │  │  Profil  │  │Se décon-   │ ││
│ │ │                 │  │  button  │  │necter btn  │ ││
│ │ │ 👤 Jean         │  │          │  │            │ ││
│ │ │    jean@mail.ca │  │          │  │            │ ││
│ │ └─────────────────┘  └────┬─────┘  └─────┬──────┘ ││
│ │                           │              │        ││
│ │                           ▼              ▼        ││
│ │                    router.push    handleLogout   ││
│ │                    ('/profile')   + redirect     ││
│ └─────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
```

## Gestion des erreurs

```
                    ┌──────────────┐
                    │ API Request  │
                    │ with token   │
                    └──────┬───────┘
                           │
                  ┌────────┴─────────┐
                  │                  │
                  ▼                  ▼
        ┌─────────────┐    ┌─────────────┐
        │ Response    │    │ Response    │
        │ 200 OK      │    │ 401/403     │
        └──────┬──────┘    └──────┬──────┘
               │                  │
               │                  ▼
               │         ┌─────────────────┐
               │         │ Token invalide  │
               │         │ ou expiré       │
               │         └──────┬──────────┘
               │                │
               │                ▼
               │         ┌─────────────────┐
               │         │ localStorage.   │
               │         │ removeItem(     │
               │         │ 'auth_token')   │
               │         └──────┬──────────┘
               │                │
               │                ▼
               │         ┌─────────────────┐
               │         │ setToken(null)  │
               │         │ setUser(null)   │
               │         └──────┬──────────┘
               │                │
               │                ▼
               │         ┌─────────────────┐
               │         │ Redirection     │
               │         │ vers /login     │
               │         └─────────────────┘
               │
               ▼
        ┌──────────────┐
        │ Process data │
        │ normally     │
        └──────────────┘
```

## État de l'application

### Avant authentification

```
AuthContext:
├─ user: null
├─ token: null
├─ isLoading: true → false
└─ isAuthenticated: false

localStorage:
└─ (vide)

Router:
└─ /login ou /register (accessible)
```

### Après authentification réussie

```
AuthContext:
├─ user: {
│   ├─ id: "uuid"
│   ├─ email: "user@example.com"
│   ├─ full_name: "Jean Tremblay"
│   ├─ is_active: true
│   ├─ is_superuser: false
│   ├─ created_at: "2026-01-18T..."
│   └─ last_login: "2026-01-18T..."
│  }
├─ token: "eyJhbGci..."
├─ isLoading: false
└─ isAuthenticated: true

localStorage:
└─ auth_token: "eyJhbGci..."

Router:
├─ / (accessible)
├─ /detection/[id] (accessible)
├─ /anonymization/[id] (accessible)
├─ /results/[id] (accessible)
└─ /profile (accessible)
```

### Après déconnexion

```
AuthContext:
├─ user: null
├─ token: null
├─ isLoading: false
└─ isAuthenticated: false

localStorage:
└─ (vide - token supprimé)

Router:
└─ Redirection automatique vers /login
```

---

**Documentation créée le**: 2026-01-18
**Version**: 1.0.0
