# TRACK 4: Tâches d'implémentation - Accessibilité & Skeleton Loader

## Status: En attente d'implémentation

---

## TÂCHE 1: Implémenter le Skeleton Loader

**Priorité**: HAUTE
**Fichier**: `/Users/mabiri/development/canada/annoy/src/components/DataPreviewTable.tsx`
**Lignes à modifier**: 11-39

### Instructions détaillées:

1. Localiser le bloc `if (isLoading)` (ligne 11)
2. Supprimer entièrement le code du spinner (lignes 12-38)
3. Remplacer par le nouveau skeleton loader qui inclut:
   - Un container avec `space-y-4 animate-pulse`
   - Une section stats skeleton avec 3 blocs (grille responsive)
   - Une section table skeleton avec:
     - 4 headers
     - 5 lignes de données
     - Chaque ligne avec 4 cellules

### Code exact à utiliser:

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

### Critères de validation:
- [ ] Le spinner a été complètement retiré
- [ ] Le skeleton loader s'affiche pendant le chargement
- [ ] L'animation pulse fonctionne
- [ ] La structure visuelle ressemble à la table finale
- [ ] Les keys React sont uniques et correctes

---

## TÂCHE 2: Ajouter les attributs ARIA

**Priorité**: HAUTE
**Fichier**: `/Users/mabiri/development/canada/annoy/src/components/DataPreviewTable.tsx`
**Lignes à modifier**: 64-96

### Instructions détaillées:

1. Localiser la balise `<table>` (ligne 64)
2. Ajouter les attributs `role` et `aria-label`
3. Ajouter un élément `<caption>` juste après la balise `<table>` ouvrante
4. Vérifier que les `<th>` ont déjà `scope="col"` (ligne 70)

### Code exact à utiliser:

**Avant** (ligne 64):
```typescript
<table className="min-w-full divide-y divide-gray-200">
```

**Après**:
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

### Note sur sr-only:

Tailwind CSS inclut la classe `sr-only` par défaut. Si elle n'est pas disponible, ajouter à votre fichier CSS global:

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

### Critères de validation:
- [ ] L'attribut `role="table"` est présent
- [ ] L'attribut `aria-label` décrit correctement la table
- [ ] La `<caption>` est présente et utilise `sr-only`
- [ ] La caption affiche le bon nombre de lignes
- [ ] Les attributs `scope="col"` sont toujours présents sur les `<th>`

---

## TÂCHE 3: Gérer les textes longs avec truncate

**Priorité**: MOYENNE
**Fichier**: `/Users/mabiri/development/canada/annoy/src/components/DataPreviewTable.tsx`
**Lignes à modifier**: 82-90

### Instructions détaillées:

1. Localiser les balises `<td>` dans le tbody (ligne 82)
2. Modifier la className pour remplacer `whitespace-nowrap` par `max-w-xs truncate`

### Code exact à utiliser:

**Avant** (ligne 82-84):
```typescript
<td
  key={colIndex}
  className="px-6 py-4 whitespace-nowrap text-sm text-gray-900"
>
```

**Après**:
```typescript
<td
  key={colIndex}
  className="px-6 py-4 text-sm text-gray-900 max-w-xs truncate"
>
```

### Critères de validation:
- [ ] `whitespace-nowrap` a été retiré
- [ ] `max-w-xs` a été ajouté
- [ ] `truncate` a été ajouté
- [ ] Les textes longs affichent `...` à la fin
- [ ] Les cellules null fonctionnent toujours correctement

---

## CHECKLIST GLOBALE DE VALIDATION

Une fois toutes les tâches complétées, vérifier:

### Tests visuels:
1. [ ] Démarrer l'application avec `npm run dev`
2. [ ] Uploader un fichier CSV
3. [ ] Vérifier que le skeleton loader s'affiche (et pas le spinner)
4. [ ] Vérifier que la table s'affiche correctement après chargement
5. [ ] Vérifier qu'un texte long dans une cellule affiche `...`

### Tests d'accessibilité:
6. [ ] Utiliser un lecteur d'écran (VoiceOver, NVDA, JAWS)
7. [ ] Vérifier que la table est annoncée correctement
8. [ ] Vérifier que le nombre de lignes est annoncé
9. [ ] Vérifier que les headers de colonnes sont identifiés

### Tests techniques:
10. [ ] Aucune erreur de console
11. [ ] Aucune warning React (keys, props, etc.)
12. [ ] Le build Next.js réussit: `npm run build`
13. [ ] Aucune régression sur les autres pages

---

## CONSIGNES IMPORTANTES

### À FAIRE:
✅ Modifier uniquement les 3 aspects spécifiés (skeleton, ARIA, truncate)
✅ Utiliser exactement les classes Tailwind spécifiées
✅ Conserver toute la logique existante du composant
✅ Tester visuellement et avec un lecteur d'écran

### À NE PAS FAIRE:
❌ Ne pas modifier l'interface du composant (props)
❌ Ne pas modifier `/Users/mabiri/development/canada/annoy/src/lib/api.ts`
❌ Ne pas modifier d'autres composants
❌ Ne pas changer la logique de chargement
❌ Ne pas ajouter de nouvelles dépendances

---

## ORDRE D'EXÉCUTION RECOMMANDÉ

1. **Étape 1**: Implémenter le skeleton loader (TÂCHE 1)
   - Tester que ça fonctionne
   - Commit: `feat(ui): add skeleton loader to DataPreviewTable`

2. **Étape 2**: Ajouter les attributs ARIA (TÂCHE 2)
   - Tester avec un lecteur d'écran
   - Commit: `feat(a11y): add ARIA attributes to DataPreviewTable`

3. **Étape 3**: Gérer les textes longs (TÂCHE 3)
   - Tester avec des données longues
   - Commit: `fix(ui): handle long text in table cells with truncate`

4. **Étape 4**: Validation globale
   - Exécuter tous les tests de la checklist
   - Build de production: `npm run build`

---

## RESSOURCES

- [Tailwind Skeleton Loaders](https://tailwindcss.com/docs/animation#pulse)
- [ARIA Tables](https://www.w3.org/WAI/ARIA/apg/patterns/table/)
- [Tailwind Truncate](https://tailwindcss.com/docs/text-overflow#truncate)

---

**Status actuel**: En attente d'implémentation
**Date de création**: 2026-01-18
**Estimé**: 30-45 minutes de développement
