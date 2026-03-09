import sys
import os
import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from uuid import uuid4
from datetime import datetime
import asyncio
from unittest.mock import patch, MagicMock

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock settings
from app.core.config import settings

from app.services.anonymizer import Anonymizer
from app.models.database import Dataset, DatasetColumn, Base
from app.models.schemas import DataType, Category, AnonymizationTechnique

async def test_auto_anonymize_consistency():
    # Setup in-memory DB
    engine = create_engine("sqlite:///:memory:")
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    anonymizer = Anonymizer(db)
    
    # Create the actual CSV file first to get size
    ds_id = uuid4()
    file_path = f"/tmp/{ds_id}_test_consistency.csv"
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    df = pd.DataFrame({
        "SSN": ["123-456-789", "987-654-321", "555-444-333", "222-111-000", "000-000-000"],
        "CITY": ["Montreal", "Quebec", "Laval", "Longueuil", "Sherbrooke"],
        "HEALTHCARE_EXPENSES": [1000.0, 2000.0, 3000.0, 4000.0, 5000.0],
        "OTHER_INFO": ["A", "B", "C", "D", "E"]
    })
    df.to_csv(file_path, index=False)
    file_size = os.path.getsize(file_path)
    
    # Create a mock dataset record
    dataset = Dataset(
        id=ds_id,
        filename="test_consistency.csv",
        file_path=file_path,
        row_count=5,
        column_count=4,
        file_size=file_size,
        upload_date=datetime.now(),
        encoding="utf-8",
        delimiter=","
    )
    db.add(dataset)
    
    # Pre-classify columns in DB
    cols = [
        DatasetColumn(dataset_id=ds_id, name="SSN", sensitivity_type="direct_identifier", category="personal", position=0, data_type="string", null_count=0, unique_count=5),
        DatasetColumn(dataset_id=ds_id, name="CITY", sensitivity_type="quasi_identifier", category="other", position=1, data_type="string", null_count=0, unique_count=5),
        DatasetColumn(dataset_id=ds_id, name="HEALTHCARE_EXPENSES", sensitivity_type="sensitive", category="health", position=2, data_type="float", null_count=0, unique_count=5),
        DatasetColumn(dataset_id=ds_id, name="OTHER_INFO", sensitivity_type="non_sensitive", category="other", position=3, data_type="string", null_count=0, unique_count=5)
    ]
    for col in cols:
        db.add(col)
    db.commit()
    
    print("Starting auto_anonymize...")
    # Disable AI via settings patch
    with patch.object(settings, "ENABLE_AI_DETECTION", False):
        try:
            response = await anonymizer.auto_anonymize(ds_id)
            print("Auto-anonymization completed successfully.")
            
            # Load the anonymized dataset
            anon_ds_id = response.anonymized_dataset_id
            anon_ds = db.query(Dataset).filter(Dataset.id == anon_ds_id).first()
            anon_df = pd.read_csv(anon_ds.file_path)
            
            print(f"Anonymized columns: {anon_df.columns.tolist()}")
            
            # 1. Check SSN is suppressed (removed)
            assert "SSN" not in anon_df.columns, "SSN should be removed (suppressed)"
            
            # 2. Check CITY is generalized (prefix 3 + "...")
            assert "CITY" in anon_df.columns
            for v in anon_df["CITY"]:
                s = str(v)
                # "Montreal" -> "Mon..." (6 chars)
                # "Quebec" -> "Que..." (6 chars)
                if len(s.strip()) > 6:
                     assert False, f"CITY value '{s}' is too long (expected <= 6 with dots)"
                if "..." not in s and len(s) > 3:
                     assert False, f"CITY value '{s}' should contain dots if generalized"
            
            # 3. Check HEALTHCARE_EXPENSES is noisy (DP)
            assert "HEALTHCARE_EXPENSES" in anon_df.columns
            diff = (anon_df["HEALTHCARE_EXPENSES"] - df["HEALTHCARE_EXPENSES"]).abs().sum()
            print(f"Healthcare expenses absolute diff sum: {diff}")
            assert diff > 0, "HEALTHCARE_EXPENSES should have noise from DP"
            
            # 4. Check status in Response
            print(f"Transformations reported: {[t.technique for t in response.transformations]}")
            any_dp = any(t.technique == AnonymizationTechnique.DIFFERENTIAL_PRIVACY for t in response.transformations)
            assert any_dp, "Differential Privacy should be reported in transformations"

            print("Consistency test PASSED!")
            
        except Exception as e:
            print(f"Test FAILED with error: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

if __name__ == "__main__":
    asyncio.run(test_auto_anonymize_consistency())
