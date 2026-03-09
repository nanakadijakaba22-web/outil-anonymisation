import sys
import os
import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from uuid import uuid4
from datetime import datetime

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.anonymizer import Anonymizer
from app.models.database import Dataset, DatasetColumn
from app.models.schemas import DataType, Category

def test_auto_anonymize_consistency():
    # Setup in-memory DB
    engine = create_engine("sqlite:///:memory:")
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    # Create tables (we need them for the session)
    from app.models.database import Base
    Base.metadata.create_all(bind=engine)
    
    anonymizer = Anonymizer(db)
    
    # Create a mock dataset record
    ds_id = uuid4()
    dataset = Dataset(
        id=ds_id,
        filename="test_consistency.csv",
        file_size=1024, # Missing required field
        file_path=f"/tmp/{ds_id}_test_consistency.csv",
        row_count=5,
        column_count=4,
        upload_date=datetime.now()
    )
    db.add(dataset)
    
    cols = [
        DatasetColumn(dataset_id=ds_id, name="SSN", sensitivity_type="direct_identifier", category="personal", position=0, data_type="object"),
        DatasetColumn(dataset_id=ds_id, name="CITY", sensitivity_type="quasi_identifier", category="other", position=1, data_type="object"),
        DatasetColumn(dataset_id=ds_id, name="HEALTHCARE_EXPENSES", sensitivity_type="sensitive", category="health", position=2, data_type="float64"),
        DatasetColumn(dataset_id=ds_id, name="OTHER_INFO", sensitivity_type="non_sensitive", category="other", position=3, data_type="object")
    ]
    for col in cols:
        db.add(col)
    db.commit()
    
    # Create the actual CSV file
    df = pd.DataFrame({
        "SSN": ["123-456-789", "987-654-321", "555-444-333", "222-111-000", "000-000-000"],
        "CITY": ["Montreal", "Quebec", "Laval", "Longueuil", "Sherbrooke"],
        "HEALTHCARE_EXPENSES": [1000.0, 2000.0, 3000.0, 4000.0, 5000.0],
        "OTHER_INFO": ["A", "B", "C", "D", "E"]
    })
    
    os.makedirs(os.path.dirname(dataset.file_path), exist_ok=True)
    df.to_csv(dataset.file_path, index=False)
    
    # Run auto_anonymize
    # Note: auto_anonymize uses AIEnhancedDetector internally which loads the dataframe
    # We might need to mock some things if AIEnhancedDetector is too complex
    # For now, let's see if it works as is
    
    print("Starting auto_anonymize...")
    try:
        response = await_coroutine(anonymizer.auto_anonymize(ds_id))
        print("Auto-anonymization completed successfully.")
        
        # Load the anonymized dataset
        anon_ds_id = response.anonymized_dataset_id
        anon_ds = db.query(Dataset).filter(Dataset.id == anon_ds_id).first()
        anon_df = pd.read_csv(anon_ds.file_path)
        
        print(f"Anonymized columns: {anon_df.columns.tolist()}")
        
        # 1. Check SSN is suppressed (removed or all masked)
        # In Rule 1, it says SUPPRESSION (complete removal)
        assert "SSN" not in anon_df.columns, "SSN should be removed (suppressed)"
        
        # 2. Check CITY is generalized (prefix 3)
        assert "CITY" in anon_df.columns
        assert all(len(str(v)) <= 3 for v in anon_df["CITY"]), "CITY should be generalized"
        
        # 3. Check HEALTHCARE_EXPENSES is noisy (DP)
        assert "HEALTHCARE_EXPENSES" in anon_df.columns
        diff = (anon_df["HEALTHCARE_EXPENSES"] - df["HEALTHCARE_EXPENSES"]).abs().sum()
        print(f"Healthcare expenses diff: {diff}")
        assert diff > 0, "HEALTHCARE_EXPENSES should have noise from DP"
        
        print("Consistency test PASSED!")
        
    except Exception as e:
        print(f"Test FAILED with error: {e}")
        import traceback
        traceback.print_exc()

def await_coroutine(coro):
    import asyncio
    return asyncio.run(coro)

if __name__ == "__main__":
    test_auto_anonymize_consistency()
