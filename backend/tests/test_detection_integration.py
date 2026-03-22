import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from uuid import UUID

from app.main import app

client = TestClient(app)

def test_upload_preview_detect_flow():
    """
    Test the full flow: Upload a tricky CSV -> Preview -> Detect
    Ensures that empty values, nulls, and weird columns don't crash the detection with 500 errors.
    """
    # 1. Create a tricky CSV content
    csv_content = """id,nom,prenom,age,salaire,email,ville_residence,colonne_vide
1,Dupont,Jean,45,55000,jean.d@example.com,Paris,
2,Martin,Marie,,62000,marie.m@test.com,,
3,,,,,none@none.com,,
4,Bernard,Luc,30,48000.50,luc.b@domain.net,Lyon,
"""
    
    # Write to a temp file
    import tempfile
    import os
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv", mode="w") as tmp:
        tmp.write(csv_content)
        tmp_path = tmp.name

    try:
        # 2. Upload
        with open(tmp_path, "rb") as f:
            response = client.post(
                "/api/v1/datasets/upload",
                files={"file": ("tricky_dataset.csv", f, "text/csv")}
            )
        
        assert response.status_code == 201, f"Upload failed: {response.text}"
        dataset = response.json()
        dataset_id = dataset["id"]
        
        # 3. Preview
        response = client.get(f"/api/v1/datasets/{dataset_id}/preview")
        assert response.status_code == 200, f"Preview failed: {response.text}"
        
        # 4. Detect - This is the crucial part that used to throw 500
        response = client.post(f"/api/v1/datasets/{dataset_id}/detect")
        
        # If it throws 500, the test fails here. We expect 200 OK.
        assert response.status_code == 200, f"Detection failed with 500: {response.text}"
        
        report = response.json()
        assert "overall_risk_score" in report
        assert "columns" in report
        
        # Check that 'colonne_vide' is handled (probably NON_SENSITIVE or OTHER)
        assert "colonne_vide" in report["columns"]
        col_classification = report["columns"]["colonne_vide"]
        assert col_classification["sensitivity_type"] in ["non_sensitive", "sensitive", "direct_identifier", "quasi_identifier"]

    finally:
        os.remove(tmp_path)
