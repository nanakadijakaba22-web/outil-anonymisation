# Track 1: Type Casting and Data Validation Fixes

## Priority: CRITICAL (Issues #1 and #5)

## Issues to Fix

### Issue #1: Dangerous Type Casting
**File**: `src/app/page.tsx`, line 338
**Current Code**:
```typescript
<DataPreviewTable preview={{} as DatasetPreview} isLoading={true} />
```

**Problem**: Unsafe type casting with empty object violates type safety and can cause runtime errors.

**Solution Required**:
Create a proper empty preview constant OR make the preview prop optional in DataPreviewTable.

**Recommended Approach**:
1. Create a constant `EMPTY_PREVIEW` with valid structure:
```typescript
const EMPTY_PREVIEW: DatasetPreview = {
  dataset_id: '',
  columns: [],
  sample_rows: [],
  total_rows: 0
};
```

2. Use it instead of type casting:
```typescript
<DataPreviewTable preview={EMPTY_PREVIEW} isLoading={true} />
```

### Issue #5: Missing API Response Validation
**File**: `src/lib/api.ts`, lines 153-158
**Current Code**:
```typescript
async getDatasetPreview(datasetId: string, nRows: number = 10): Promise<DatasetPreview> {
  const response = await fetch(
    `${this.baseUrl}/datasets/${datasetId}/preview?n_rows=${nRows}`
  );
  return this.handleResponse<DatasetPreview>(response);
}
```

**Problem**: No validation that the response actually matches DatasetPreview interface. Malformed API responses will cause runtime errors.

**Solution Required**:
Add validation in `getDatasetPreview()` to verify response structure.

**Recommended Implementation**:
```typescript
async getDatasetPreview(datasetId: string, nRows: number = 10): Promise<DatasetPreview> {
  const response = await fetch(
    `${this.baseUrl}/datasets/${datasetId}/preview?n_rows=${nRows}`
  );
  const data = await this.handleResponse<DatasetPreview>(response);

  // Validate response structure
  if (!Array.isArray(data.columns) || !Array.isArray(data.sample_rows)) {
    throw new Error('Invalid preview data structure: missing columns or sample_rows arrays');
  }

  if (typeof data.total_rows !== 'number') {
    throw new Error('Invalid preview data: total_rows must be a number');
  }

  return data;
}
```

## Files to Modify

1. `/Users/mabiri/development/canada/annoy/src/app/page.tsx`
   - Add EMPTY_PREVIEW constant
   - Replace line 338 with safe version

2. `/Users/mabiri/development/canada/annoy/src/lib/api.ts`
   - Add validation to getDatasetPreview() method

## Testing Requirements

After making changes:
1. Verify the upload page loads without errors
2. Test loading state when preview is loading
3. Test error handling when API returns invalid data
4. Verify TypeScript compilation passes with no errors

## Success Criteria

- No more unsafe type casting with `{} as Type`
- API responses validated before use
- TypeScript compilation succeeds
- All existing functionality preserved
- No runtime errors when loading preview
