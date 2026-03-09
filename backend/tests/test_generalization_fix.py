import sys
import os
import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.anonymizer import Anonymizer
from app.models.schemas import AnonymizationConfig, AnonymizationTechnique

def test_prefix_generalization():
    engine = create_engine("sqlite:///:memory:")
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    anonymizer = Anonymizer(db)
    
    df = pd.DataFrame({"city": ["Montreal", "Quebec", "Laval"]})
    params = {"mode": "prefix", "prefix_length": 3}
    
    result_df = anonymizer._generalize_column(df.copy(), "city", params)
    
    print("Original: Montreal, Quebec, Laval")
    print(f"Generalized: {result_df['city'].tolist()}")
    
    assert result_df["city"].iloc[0] == "Mon..."
    assert result_df["city"].iloc[1] == "Que..."
    print("Prefix generalization test passed!")

def test_masking():
    engine = create_engine("sqlite:///:memory:")
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    anonymizer = Anonymizer(db)
    
    # Text masking
    s = "John Doe"
    masked = anonymizer._mask_string(s, 2, "*")
    print(f"Original: {s}, Masked: {masked}")
    assert masked == "Jo******"
    print("Masking test passed!")

if __name__ == "__main__":
    test_prefix_generalization()
    test_masking()
