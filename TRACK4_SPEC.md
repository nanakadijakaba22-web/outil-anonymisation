# Track 4: Accessibility and UX Improvements

## Priority: IMPORTANT (Issues #6 and #7)

## Issues to Fix

### Issue #6: Replace Spinner with Skeleton Loader
**File**: `src/components/DataPreviewTable.tsx`, lines 11-39

**Current Code**:
```typescript
if (isLoading) {
  return (
    <div className="flex items-center justify-center p-12">
      <div className="text-center">
        <svg className="animate-spin h-10 w-10 text-blue-600 mx-auto mb-4" ...>
          {/* Spinner SVG */}
        </svg>
        <p className="text-gray-600">Chargement de la prévisualisation...</p>
      </div>
    </div>
  );
}
```

**Problem**:
Spinner doesn't respect the shape of the content that will load. Skeleton loaders provide better UX by:
- Showing the structure of the upcoming content
- Reducing perceived loading time
- Providing visual continuity
- Modern best practice for loading states

**Solution Required**:
Replace spinner with a skeleton loader that mimics the table structure.

**Recommended Implementation**:

```typescript
if (isLoading) {
  // Skeleton loader that matches the table structure
  return (
    <div className="space-y-4 animate-pulse">
      {/* Summary Stats Skeleton */}
      <div className="bg-gray-100 border border-gray-200 rounded-lg p-4">
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          <div>
            <div className="h-4 bg-gray-300 rounded w-20 mb-2"></div>
            <div className="h-8 bg-gray-300 rounded w-12"></div>
          </div>
          <div>
            <div className="h-4 bg-gray-300 rounded w-24 mb-2"></div>
            <div className="h-8 bg-gray-300 rounded w-16"></div>
          </div>
          <div className="col-span-2 md:col-span-1">
            <div className="h-4 bg-gray-300 rounded w-28 mb-2"></div>
            <div className="h-8 bg-gray-300 rounded w-12"></div>
          </div>
        </div>
      </div>

      {/* Table Skeleton */}
      <div className="border border-gray-200 rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                {[1, 2, 3, 4, 5].map((i) => (
                  <th key={`skeleton-header-${i}`} className="px-6 py-3">
                    <div className="h-4 bg-gray-300 rounded w-24"></div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {[1, 2, 3, 4, 5].map((rowIdx) => (
                <tr key={`skeleton-row-${rowIdx}`}>
                  {[1, 2, 3, 4, 5].map((colIdx) => (
                    <td key={`skeleton-cell-${rowIdx}-${colIdx}`} className="px-6 py-4">
                      <div className="h-4 bg-gray-200 rounded w-32"></div>
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Preview Notice Skeleton */}
      <div className="h-4 bg-gray-200 rounded w-64 mx-auto"></div>
    </div>
  );
}
```

### Issue #7: Missing Accessibility Features
**File**: `src/components/DataPreviewTable.tsx`, lines 62-97

**Current Code**:
```typescript
<div className="border border-gray-200 rounded-lg overflow-hidden">
  <div className="overflow-x-auto">
    <table className="min-w-full divide-y divide-gray-200">
      <thead className="bg-gray-50">
        {/* ... */}
      </thead>
      <tbody className="bg-white divide-y divide-gray-200">
        {/* ... */}
      </tbody>
    </table>
  </div>
</div>
```

**Problems**:
- Missing `role` attributes for semantic HTML
- No `caption` element to describe the table
- No `aria-label` for screen readers
- No `scope` attributes on header cells (already present, good!)
- Loading state not announced to screen readers

**Solution Required**:
Add proper ARIA attributes and semantic HTML for accessibility.

**Recommended Implementation**:

```typescript
return (
  <div className="space-y-4">
    {/* Summary Stats - Add aria-label */}
    <div
      className="bg-blue-50 border border-blue-200 rounded-lg p-4"
      role="region"
      aria-label="Statistiques du jeu de données"
    >
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        <div>
          <p className="text-sm text-gray-600" id="columns-label">Colonnes</p>
          <p className="text-2xl font-bold text-gray-900" aria-labelledby="columns-label">
            {preview.columns.length}
          </p>
        </div>
        <div>
          <p className="text-sm text-gray-600" id="total-rows-label">Lignes totales</p>
          <p className="text-2xl font-bold text-gray-900" aria-labelledby="total-rows-label">
            {preview.total_rows.toLocaleString()}
          </p>
        </div>
        <div className="col-span-2 md:col-span-1">
          <p className="text-sm text-gray-600" id="shown-rows-label">Lignes affichées</p>
          <p className="text-2xl font-bold text-gray-900" aria-labelledby="shown-rows-label">
            {preview.sample_rows.length}
          </p>
        </div>
      </div>
    </div>

    {/* Table with accessibility attributes */}
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      <div className="overflow-x-auto">
        <table
          className="min-w-full divide-y divide-gray-200"
          role="table"
          aria-label="Prévisualisation des données du fichier CSV"
        >
          <caption className="sr-only">
            Prévisualisation des {preview.sample_rows.length} premières lignes du jeu de données contenant {preview.columns.length} colonnes
          </caption>
          <thead className="bg-gray-50">
            <tr role="row">
              {preview.columns.map((column) => (
                <th
                  key={column}
                  scope="col"
                  role="columnheader"
                  className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider whitespace-nowrap"
                >
                  {column}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {preview.sample_rows.map((row, rowIndex) => (
              <tr key={`row-${rowIndex}`} role="row" className="hover:bg-gray-50">
                {preview.columns.map((column) => (
                  <td
                    key={`${rowIndex}-${column}`}
                    role="cell"
                    className="px-6 py-4 whitespace-nowrap text-sm text-gray-900"
                  >
                    {row[column] !== null && row[column] !== undefined
                      ? String(row[column])
                      : <span className="text-gray-400 italic">null</span>
                    }
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>

    {/* Preview Notice with aria-live for dynamic updates */}
    {preview.sample_rows.length < preview.total_rows && (
      <p
        className="text-sm text-gray-500 text-center"
        role="status"
        aria-live="polite"
      >
        Affichage des {preview.sample_rows.length} premières lignes sur {preview.total_rows.toLocaleString()} au total
      </p>
    )}
  </div>
);
```

**Also update loading state for accessibility**:
```typescript
if (isLoading) {
  return (
    <div
      className="space-y-4 animate-pulse"
      role="status"
      aria-live="polite"
      aria-label="Chargement de la prévisualisation des données"
    >
      {/* Skeleton content */}
    </div>
  );
}
```

## Files to Modify

1. `/Users/mabiri/development/canada/annoy/src/components/DataPreviewTable.tsx`
   - Replace spinner with skeleton loader (lines 11-39)
   - Add ARIA attributes to table and surrounding elements
   - Add caption element to table
   - Add role attributes for semantic structure
   - Add aria-live regions for dynamic content

## Testing Requirements

1. **Visual Testing**:
   - Verify skeleton loader displays correctly
   - Check that skeleton matches final table structure
   - Test responsive behavior on mobile and desktop

2. **Accessibility Testing**:
   - Use screen reader (VoiceOver on Mac, NVDA on Windows) to verify announcements
   - Check that table structure is properly announced
   - Verify loading states are announced to screen readers
   - Run accessibility audit (Lighthouse or axe DevTools)
   - Ensure keyboard navigation works correctly

3. **Functional Testing**:
   - Verify data still displays correctly after loading
   - Test that all existing functionality works
   - Check that animations are smooth

## Success Criteria

- Skeleton loader replaces spinner
- Skeleton structure matches actual table layout
- All ARIA attributes properly applied
- Screen readers can navigate and understand the table
- Lighthouse accessibility score improves
- No accessibility warnings in console
- Existing functionality preserved
- Better perceived performance with skeleton loader
