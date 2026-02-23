#!/usr/bin/env python3
"""
Test script for verifying the /datasets/{id}/preview endpoint.

This script tests that:
1. The endpoint exists and returns 200 OK
2. The response format matches DatasetPreview schema
3. The data is suitable for frontend consumption
"""

import sys
import requests
from pathlib import Path

# Configuration
BASE_URL = "http://localhost:8000/api/v1"
TEST_CSV_PATH = Path(__file__).parent / "tests" / "fixtures" / "test_data.csv"

def test_preview_endpoint():
    """Test the complete workflow: upload -> preview."""

    print("=" * 70)
    print("Testing Dataset Preview Endpoint")
    print("=" * 70)

    # Step 1: Upload a test CSV
    print("\n[1] Uploading test CSV file...")

    if not TEST_CSV_PATH.exists():
        print(f"❌ Test file not found: {TEST_CSV_PATH}")
        print("   Please ensure test_data.csv exists in backend/tests/fixtures/")
        return False

    with open(TEST_CSV_PATH, 'rb') as f:
        files = {'file': ('test_data.csv', f, 'text/csv')}
        response = requests.post(f"{BASE_URL}/datasets/upload", files=files)

    if response.status_code != 201:
        print(f"❌ Upload failed: {response.status_code}")
        print(f"   Response: {response.text}")
        return False

    dataset = response.json()
    dataset_id = dataset['id']
    print(f"✅ Upload successful. Dataset ID: {dataset_id}")
    print(f"   Filename: {dataset['filename']}")
    print(f"   Rows: {dataset['row_count']}, Columns: {dataset['column_count']}")

    # Step 2: Get preview
    print("\n[2] Requesting dataset preview (10 rows)...")

    response = requests.get(f"{BASE_URL}/datasets/{dataset_id}/preview?n_rows=10")

    if response.status_code != 200:
        print(f"❌ Preview failed: {response.status_code}")
        print(f"   Response: {response.text}")
        return False

    preview = response.json()
    print(f"✅ Preview retrieved successfully")

    # Step 3: Validate response format
    print("\n[3] Validating response format...")

    required_fields = ['dataset_id', 'columns', 'sample_rows', 'total_rows']
    missing_fields = [field for field in required_fields if field not in preview]

    if missing_fields:
        print(f"❌ Missing required fields: {missing_fields}")
        return False

    print(f"✅ All required fields present: {required_fields}")

    # Step 4: Validate data structure
    print("\n[4] Validating data structure...")

    # Check dataset_id matches
    if preview['dataset_id'] != dataset_id:
        print(f"❌ Dataset ID mismatch: {preview['dataset_id']} != {dataset_id}")
        return False

    print(f"✅ Dataset ID matches: {dataset_id}")

    # Check columns is a list of strings
    if not isinstance(preview['columns'], list):
        print(f"❌ 'columns' should be a list, got {type(preview['columns'])}")
        return False

    if not all(isinstance(col, str) for col in preview['columns']):
        print(f"❌ All columns should be strings")
        return False

    print(f"✅ Columns is valid list of strings ({len(preview['columns'])} columns)")
    print(f"   Columns: {preview['columns'][:5]}{'...' if len(preview['columns']) > 5 else ''}")

    # Check sample_rows is a list of dicts
    if not isinstance(preview['sample_rows'], list):
        print(f"❌ 'sample_rows' should be a list, got {type(preview['sample_rows'])}")
        return False

    if len(preview['sample_rows']) == 0:
        print(f"❌ 'sample_rows' is empty")
        return False

    print(f"✅ Sample rows is valid list ({len(preview['sample_rows'])} rows)")

    # Check each row is a dict with column keys
    first_row = preview['sample_rows'][0]
    if not isinstance(first_row, dict):
        print(f"❌ Each row should be a dict, got {type(first_row)}")
        return False

    # Verify all columns are present in rows
    row_keys = set(first_row.keys())
    expected_keys = set(preview['columns'])

    if row_keys != expected_keys:
        missing = expected_keys - row_keys
        extra = row_keys - expected_keys
        if missing:
            print(f"❌ Missing columns in row: {missing}")
        if extra:
            print(f"❌ Extra columns in row: {extra}")
        return False

    print(f"✅ Row structure matches columns")

    # Check total_rows matches upload metadata
    if preview['total_rows'] != dataset['row_count']:
        print(f"❌ Total rows mismatch: {preview['total_rows']} != {dataset['row_count']}")
        return False

    print(f"✅ Total rows matches: {preview['total_rows']}")

    # Step 5: Display sample data
    print("\n[5] Sample data preview:")
    print("-" * 70)

    # Display first 3 rows
    for i, row in enumerate(preview['sample_rows'][:3], 1):
        print(f"\nRow {i}:")
        for col in preview['columns'][:5]:  # Show first 5 columns
            value = row[col]
            # Truncate long values
            if isinstance(value, str) and len(value) > 30:
                value = value[:27] + "..."
            print(f"  {col}: {value}")

        if len(preview['columns']) > 5:
            print(f"  ... and {len(preview['columns']) - 5} more columns")

    if len(preview['sample_rows']) > 3:
        print(f"\n... and {len(preview['sample_rows']) - 3} more rows")

    # Step 6: Test with different n_rows
    print("\n[6] Testing with n_rows=5...")

    response = requests.get(f"{BASE_URL}/datasets/{dataset_id}/preview?n_rows=5")

    if response.status_code != 200:
        print(f"❌ Preview with n_rows=5 failed: {response.status_code}")
        return False

    preview_5 = response.json()

    if len(preview_5['sample_rows']) != 5:
        print(f"❌ Expected 5 rows, got {len(preview_5['sample_rows'])}")
        return False

    print(f"✅ Preview with n_rows=5 returned {len(preview_5['sample_rows'])} rows")

    # Step 7: Test max limit
    print("\n[7] Testing max limit (n_rows=100)...")

    response = requests.get(f"{BASE_URL}/datasets/{dataset_id}/preview?n_rows=100")

    if response.status_code != 200:
        print(f"❌ Preview with n_rows=100 failed: {response.status_code}")
        return False

    print(f"✅ Max limit (100 rows) works correctly")

    # Step 8: Test exceeding max limit
    print("\n[8] Testing exceeding max limit (n_rows=101)...")

    response = requests.get(f"{BASE_URL}/datasets/{dataset_id}/preview?n_rows=101")

    if response.status_code != 400:
        print(f"❌ Expected 400 Bad Request, got {response.status_code}")
        return False

    print(f"✅ Correctly rejects n_rows > 100 with 400 Bad Request")

    # Cleanup: Delete dataset
    print("\n[9] Cleaning up test dataset...")

    response = requests.delete(f"{BASE_URL}/datasets/{dataset_id}")

    if response.status_code != 204:
        print(f"⚠️  Warning: Failed to delete dataset (status {response.status_code})")
    else:
        print(f"✅ Test dataset deleted successfully")

    # Final summary
    print("\n" + "=" * 70)
    print("✅ ALL TESTS PASSED!")
    print("=" * 70)
    print("\nEndpoint Summary:")
    print(f"  URL: GET /datasets/{{id}}/preview?n_rows=N")
    print(f"  Default n_rows: 10")
    print(f"  Max n_rows: 100")
    print(f"  Response format: DatasetPreview")
    print(f"    - dataset_id: UUID")
    print(f"    - columns: list[str]")
    print(f"    - sample_rows: list[dict[str, Any]]")
    print(f"    - total_rows: int")
    print("\n✅ Ready for frontend integration!")
    print("=" * 70)

    return True


if __name__ == "__main__":
    try:
        success = test_preview_endpoint()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
