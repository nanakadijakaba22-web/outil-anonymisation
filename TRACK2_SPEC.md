# Track 2: Error Handling and Timeout Implementation

## Priority: CRITICAL (Issues #2 and #3)

## Issues to Fix

### Issue #2: Inconsistent Error Handling
**File**: `src/app/page.tsx`, lines 82-95
**Current Code**:
```typescript
// Load preview
setLoadingPreview(true);
try {
  const previewData = await api.getDatasetPreview(dataset.id, 10);
  setPreview(previewData);
  setShowPreview(true);
} catch (previewErr) {
  console.error('Error loading preview:', previewErr);
  setError('Fichier uploadé avec succès, mais erreur lors de la prévisualisation');
  // Still allow continuing to detection
  setShowPreview(true);  // ❌ BUG: Shows preview even on error!
} finally {
  setLoadingPreview(false);
}
```

**Problems**:
1. Error message not specific enough (doesn't tell user what went wrong)
2. `setShowPreview(true)` is called even when preview fails - UX inconsistency
3. No retry mechanism for transient failures
4. User can't see what the actual error was

**Solution Required**:

1. Improve error messages to be more specific
2. Don't show preview UI when preview fails
3. Add a retry button for failed preview loads
4. Show actual error details to help debugging

**Recommended Implementation**:

Add new state for preview error:
```typescript
const [previewError, setPreviewError] = useState<string | null>(null);
```

Update error handling:
```typescript
try {
  const previewData = await api.getDatasetPreview(dataset.id, 10);
  setPreview(previewData);
  setPreviewError(null);
  setShowPreview(true);
} catch (previewErr) {
  console.error('Error loading preview:', previewErr);
  const errorMessage = previewErr instanceof Error
    ? previewErr.message
    : 'Erreur inconnue lors de la prévisualisation';
  setPreviewError(`Impossible de charger la prévisualisation: ${errorMessage}`);
  setShowPreview(false); // Don't show preview UI on error
}
```

Add retry function:
```typescript
const handleRetryPreview = async () => {
  if (!uploadedDataset) return;

  setLoadingPreview(true);
  setPreviewError(null);

  try {
    const previewData = await api.getDatasetPreview(uploadedDataset.id, 10);
    setPreview(previewData);
    setShowPreview(true);
  } catch (err) {
    const errorMessage = err instanceof Error ? err.message : 'Erreur inconnue';
    setPreviewError(`Impossible de charger la prévisualisation: ${errorMessage}`);
  } finally {
    setLoadingPreview(false);
  }
};
```

Update UI to show error with retry button:
```typescript
{previewError && (
  <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
    <p className="text-sm text-yellow-800 mb-2">{previewError}</p>
    <button
      onClick={handleRetryPreview}
      className="text-sm text-yellow-700 hover:text-yellow-900 font-medium"
    >
      Réessayer la prévisualisation
    </button>
  </div>
)}
```

### Issue #3: Missing API Timeout
**File**: `src/app/page.tsx`, lines 82-95
**Current Code**: No timeout mechanism

**Problem**: API calls can hang indefinitely if server doesn't respond. This creates poor UX.

**Solution Required**:
Implement AbortController with 30-second timeout for API calls.

**Recommended Implementation**:

Create a helper function with timeout:
```typescript
const fetchWithTimeout = async <T,>(
  fetchFn: () => Promise<T>,
  timeoutMs: number = 30000
): Promise<T> => {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const result = await fetchFn();
    clearTimeout(timeoutId);
    return result;
  } catch (error) {
    clearTimeout(timeoutId);
    if (error instanceof Error && error.name === 'AbortError') {
      throw new Error('La requête a expiré (timeout après 30 secondes)');
    }
    throw error;
  }
};
```

Update API client to support AbortController:
```typescript
// In api.ts, update getDatasetPreview to accept signal
async getDatasetPreview(
  datasetId: string,
  nRows: number = 10,
  signal?: AbortSignal
): Promise<DatasetPreview> {
  const response = await fetch(
    `${this.baseUrl}/datasets/${datasetId}/preview?n_rows=${nRows}`,
    { signal }
  );
  const data = await this.handleResponse<DatasetPreview>(response);

  // ... validation code ...

  return data;
}
```

Use in page.tsx:
```typescript
try {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 30000);

  const previewData = await api.getDatasetPreview(dataset.id, 10, controller.signal);
  clearTimeout(timeoutId);

  setPreview(previewData);
  setPreviewError(null);
  setShowPreview(true);
} catch (previewErr) {
  if (previewErr instanceof Error && previewErr.name === 'AbortError') {
    setPreviewError('La prévisualisation a pris trop de temps (timeout)');
  } else {
    const errorMessage = previewErr instanceof Error
      ? previewErr.message
      : 'Erreur inconnue';
    setPreviewError(`Impossible de charger la prévisualisation: ${errorMessage}`);
  }
  setShowPreview(false);
}
```

## Files to Modify

1. `/Users/mabiri/development/canada/annoy/src/app/page.tsx`
   - Add previewError state
   - Improve error handling in handleUpload
   - Add handleRetryPreview function
   - Implement timeout with AbortController
   - Update UI to show errors and retry button

2. `/Users/mabiri/development/canada/annoy/src/lib/api.ts`
   - Update getDatasetPreview to accept AbortSignal parameter
   - Update uploadDataset to accept AbortSignal (optional enhancement)

## Testing Requirements

1. Test normal upload flow works
2. Test error handling when API returns error
3. Test retry button works after error
4. Test timeout mechanism (can simulate by adding delay in backend)
5. Verify error messages are clear and actionable
6. Test that preview UI doesn't show when error occurs

## Success Criteria

- Clear, specific error messages shown to users
- Preview UI only shows when preview loads successfully
- Retry button allows recovery from transient failures
- 30-second timeout prevents indefinite hangs
- All timeout errors handled gracefully
- Existing functionality preserved
