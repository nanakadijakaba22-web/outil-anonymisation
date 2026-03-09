import sys
import os
import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from uuid import uuid4

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.anonymizer import Anonymizer
from app.models.schemas import AnonymizationConfig, AnonymizationTechnique

def test_dp_actual_change():
    engine = create_engine("sqlite:///:memory:")
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    anonymizer = Anonymizer(db)
    
    # Test data with numeric sensitive values
    df = pd.DataFrame({
        "HEALTHCARE_EXPENSES": [1000.0, 5000.0, 10000.0, 20000.0, 50000.0],
        "HEALTHCARE_COVERAGE": [900.0, 4500.0, 8000.0, 15000.0, 40000.0]
    })
    
    # Apply Differential Privacy
    config_expenses = AnonymizationConfig(
        column_name="HEALTHCARE_EXPENSES",
        technique=AnonymizationTechnique.DIFFERENTIAL_PRIVACY,
        params={"epsilon": 1.0, "mechanism": "laplace"}
    )
    
    # We call _apply_technique directly for unit test
    df_noisy, transformation = anonymizer._apply_technique(
        df=df.copy(),
        original_df=df.copy(),
        config=config_expenses,
        job_id=uuid4(),
        dataset_id=uuid4()
    )
    
    print(f"Original: {df['HEALTHCARE_EXPENSES'].tolist()}")
    print(f"Noisy:    {df_noisy['HEALTHCARE_EXPENSES'].tolist()}")
    
    # Check if values actually changed
    percent_diff = (df_noisy['HEALTHCARE_EXPENSES'] - df['HEALTHCARE_EXPENSES']).abs().mean()
    print(f"Mean absolute difference: {percent_diff}")
    
    assert not df['HEALTHCARE_EXPENSES'].equals(df_noisy['HEALTHCARE_EXPENSES']), "Values should have changed with DP!"
    assert percent_diff > 0, "Mean difference should be greater than 0"

    print("DP Consistency test passed!")

if __name__ == "__main__":
    test_dp_actual_change()
