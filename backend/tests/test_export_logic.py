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

def test_export_values():
    engine = create_engine("sqlite:///:memory:")
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    anonymizer = Anonymizer(db)
    
    # Test data with Race and Gender
    df = pd.DataFrame({
        "race": ["white", "black", "asian", "unknown"],
        "gender": ["male", "female", "homme", "unknown"],
        "city": ["Montreal", "Quebec", "Laval", "Vancouver"]
    })
    
    # 1. Test Race Hierarchy (should not be "Broad Category")
    params_race = {"hierarchy": anonymizer.DEMOGRAPHIC_HIERARCHIES["race"]}
    df_race = anonymizer._generalize_column(df.copy(), "race", params_race)
    print(f"Race values: {df_race['race'].tolist()}")
    assert "Broad Category" not in df_race["race"].tolist()
    assert "Caucaisien/Autre" in df_race["race"].tolist()
    
    # 2. Test Gender Hierarchy (should be M/F or original, not Person)
    params_gender = {"hierarchy": anonymizer.DEMOGRAPHIC_HIERARCHIES["gender"]}
    df_gender = anonymizer._generalize_column(df.copy(), "gender", params_gender)
    print(f"Gender values: {df_gender['gender'].tolist()}")
    assert "M" in df_gender["gender"].tolist()
    assert "F" in df_gender["gender"].tolist()
    # Check that unknown remains unknown (not Person or None)
    assert "unknown" in df_gender["gender"].tolist()
    
    # 3. Test City Generalization (should not be None)
    params_city = {"mode": "prefix", "prefix_length": 3}
    df_city = anonymizer._generalize_column(df.copy(), "city", params_city)
    print(f"City values: {df_city['city'].tolist()}")
    assert all(isinstance(x, str) and x.endswith(" ***") for x in df_city["city"].tolist())

    print("Export values test passed!")

if __name__ == "__main__":
    test_export_values()
