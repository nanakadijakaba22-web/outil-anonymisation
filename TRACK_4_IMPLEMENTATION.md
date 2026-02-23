# TRACK 4: Accessibilité & Skeleton Loader - Plan d'implémentation

## Objectif
Améliorer l'accessibilité et l'expérience utilisateur du composant DataPreviewTable en remplaçant le spinner par un skeleton loader et en ajoutant les attributs ARIA appropriés.

## Fichier à modifier
- `/Users/mabiri/development/canada/annoy/src/components/DataPreviewTable.tsx`

## Modifications à effectuer

### 1. Skeleton Loader (lignes 11-39)

**Remplacer le spinner actuel par un skeleton loader complet qui respecte la structure visuelle de la table finale.**

Code actuel (à remplacer):
```typescript
if (isLoading) {
  return (
    <div className="flex items-center justify-center p-12">
      <div className="text-center">
        <svg className="animate-spin h-10 w-10 text-blue-600 mx-auto mb-4" ... >
          ...
        </svg>
        <p className="text-gray-600">Chargement de la prévisualisation...</p>
      </div>
    </div>
  );
}
```

Nouveau code:
```typescript
if (isLoading) {
  return (
    <div className="space-y-4 animate-pulse">
      {/* Stats skeleton */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          {[1, 2, 3].map(i => (
            <div key={`stat-${i}`}>
              <div className="h-4 bg-gray-300 rounded w-24 mb-2"></div>
              <div className="h-6 bg-gray-400 rounded w-16"></div>
            </div>
          ))}
        </div>
      </div>

      {/* Table skeleton */}
      <div className="border border-gray-200 rounded-lg overflow-hidden">
        <div className="bg-gray-50 p-4">
          <div className="flex gap-4">
            {[1, 2, 3, 4].map(i => (
              <div key={`header-${i}`} className="h-4 bg-gray-300 rounded flex-1"></div>
            ))}
          </div>
        </div>

        <div className="divide-y divide-gray-200">
          {[1, 2, 3, 4, 5].map(i => (
            <div key={`row-${i}`} className="p-4 flex gap-4">
              {[1, 2, 3, 4].map(j => (
                <div key={`cell-${i}-${j}`} className="h-4 bg-gray-200 rounded flex-1"></div>
              ))}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
```

**Justification**: Le skeleton loader donne une meilleure indication visuelle de ce qui se charge en mimant la structure finale de la table.

---

### 2. Attributs ARIA pour l'accessibilité (lignes 62-96)

**Ajouter les attributs ARIA nécessaires à la table pour améliorer l'accessibilité.**

Code actuel (ligne 64):
```typescript
<table className="min-w-full divide-y divide-gray-200">
```

Nouveau code:
```typescript
<table
  className="min-w-full divide-y divide-gray-200"
  role="table"
  aria-label="Aperçu des données du fichier téléchargé"
>
  <caption className="sr-only">
    Affichage des {preview.sample_rows.length} premières lignes sur {preview.total_rows} au total
  </caption>
```

**Note**: Ajouter aussi `className="sr-only"` nécessite une classe Tailwind. Vérifier si elle existe ou utiliser:
```css
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border-width: 0;
}
```

**Justification**: Les lecteurs d'écran ont besoin d'attributs ARIA pour comprendre la structure de la table.

---

### 3. Gestion des textes longs (lignes 82-90)

**Modifier les cellules pour gérer les textes longs avec truncate au lieu de whitespace-nowrap.**

Code actuel (lignes 82-90):
```typescript
<td
  key={colIndex}
  className="px-6 py-4 whitespace-nowrap text-sm text-gray-900"
>
  {row[column] !== null && row[column] !== undefined
    ? String(row[column])
    : <span className="text-gray-400 italic">null</span>
  }
</td>
```

Nouveau code:
```typescript
<td
  key={colIndex}
  className="px-6 py-4 text-sm text-gray-900 max-w-xs truncate"
>
  {row[column] !== null && row[column] !== undefined
    ? String(row[column])
    : <span className="text-gray-400 italic">null</span>
  }
</td>
```

**Changements**:
- Retirer `whitespace-nowrap`
- Ajouter `max-w-xs truncate`

**Justification**: `max-w-xs` limite la largeur maximale à 20rem (320px) et `truncate` ajoute l'ellipsis (...) pour les textes trop longs.

---

## Validation

Après implémentation, vérifier:

1. **Skeleton Loader**:
   - Le skeleton loader apparaît pendant le chargement
   - Il ressemble visuellement à la table finale (3 stats + table avec headers + 5 lignes)
   - L'animation `animate-pulse` fonctionne correctement

2. **Accessibilité**:
   - L'attribut `role="table"` est présent
   - L'attribut `aria-label` décrit correctement la table
   - La `<caption>` est présente et cachée visuellement (`sr-only`)
   - Les `scope="col"` sont toujours présents sur les `<th>`

3. **Textes longs**:
   - Les cellules avec textes longs affichent `...` à la fin
   - La largeur maximale est respectée (`max-w-xs`)
   - Les cellules null affichent toujours correctement le texte grisé

## Fichiers à ne PAS modifier

- Ne pas modifier `/Users/mabiri/development/canada/annoy/src/lib/api.ts`
- Ne pas modifier les autres composants
- Ne pas modifier la logique de chargement des données

## Notes importantes

- Utiliser exactement les classes Tailwind spécifiées
- Respecter la structure existante du composant
- Ne pas changer les props ou l'interface du composant
- Maintenir la compatibilité avec le reste de l'application
