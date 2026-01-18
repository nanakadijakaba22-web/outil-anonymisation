# Track 3: Fix React Keys Anti-Pattern

## Priority: CRITICAL (Issue #4)

## Issue to Fix

### Issue #4: Using Index as Key
**File**: `src/components/DataPreviewTable.tsx`, lines 67, 79, 81

**Current Code**:
```typescript
// Line 67 - Column headers
{preview.columns.map((column, index) => (
  <th key={index} ...>  // ❌ Bad: using index as key
    {column}
  </th>
))}

// Line 79 - Table rows
{preview.sample_rows.map((row, rowIndex) => (
  <tr key={rowIndex} ...>  // ❌ Bad: using index as key
    {preview.columns.map((column, colIndex) => (
      <td key={colIndex} ...>  // ❌ Bad: using index as key
        {row[column]}
      </td>
    ))}
  </tr>
))}
```

**Problem**:
Using array indices as keys is an anti-pattern in React because:
1. Keys should be stable across re-renders
2. Index keys can cause bugs when list items are reordered, filtered, or updated
3. React may incorrectly reuse components leading to stale data
4. Performance issues with reconciliation algorithm

**Solution Required**:
Use stable, unique keys based on the actual data.

**Recommended Implementation**:

```typescript
{/* Column headers - use column name as key */}
<thead className="bg-gray-50">
  <tr>
    {preview.columns.map((column) => (
      <th
        key={column}  // ✅ Good: column name is unique and stable
        scope="col"
        className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider whitespace-nowrap"
      >
        {column}
      </th>
    ))}
  </tr>
</thead>

{/* Table rows - use composite key */}
<tbody className="bg-white divide-y divide-gray-200">
  {preview.sample_rows.map((row, rowIndex) => (
    <tr key={`row-${rowIndex}`} className="hover:bg-gray-50">
      {preview.columns.map((column) => (
        <td
          key={`${rowIndex}-${column}`}  // ✅ Good: composite key unique per cell
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
```

**Rationale for Key Choices**:

1. **Column headers**: `key={column}`
   - Column names are unique within a dataset
   - Column names don't change during the component's lifecycle
   - Stable and predictable

2. **Table rows**: `key={`row-${rowIndex}`}`
   - Since we don't have unique row IDs from the API, using `row-${rowIndex}` is acceptable
   - The preview is read-only and rows aren't reordered
   - Adding "row-" prefix makes it clear what the key represents

3. **Table cells**: `key={`${rowIndex}-${column}`}`
   - Composite key ensures uniqueness per cell
   - Combines row position with column name
   - Each cell gets a predictable, stable key

## Files to Modify

1. `/Users/mabiri/development/canada/annoy/src/components/DataPreviewTable.tsx`
   - Update line 67: Change `key={index}` to `key={column}`
   - Update line 79: Change `key={rowIndex}` to `key={`row-${rowIndex}`}`
   - Update line 81: Change `key={colIndex}` to `key={`${rowIndex}-${column}`}`

## Testing Requirements

1. Verify table renders correctly after changes
2. Test with different datasets to ensure keys remain unique
3. Verify no console warnings about duplicate keys
4. Test that hover states work correctly on rows
5. Verify no React reconciliation bugs (elements not updating correctly)

## Success Criteria

- No array indices used as React keys
- All keys are stable and predictable
- Column headers use column name as key
- Table cells use composite keys combining row and column
- No React warnings in console
- Table functionality unchanged
- Performance is maintained or improved
