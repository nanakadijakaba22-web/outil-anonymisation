import os
import pandas as pd
import numpy as np
import uuid
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Mocking app context
sys.path.append(os.getcwd())

from app.services.anonymizer import Anonymizer
from app.models.schemas import AnonymizationConfig, AnonymizationTechnique, DataType, Category
from app.core.database import Base

# Setup test database
DATABASE_URL = "sqlite:///./test_cleanup.db"
engine = create_engine(DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

def test_dataset_cleanup():
    db = TestingSessionLocal()
    anonymizer = Anonymizer(db)
    
    # Create sample data
    # BIRTHDATE: to be YEAR only
    # DEATHDATE: sparse (90% null)
    # BIRTHPLACE: to be empty after generalization
    # SSN: direct id (to be removed)
    data = {
        "SSN": [f"SSN-{i}" for i in range(20)],
        "BIRTHDATE": pd.to_datetime(["1970-01-01"] * 20),
        "DEATHDATE": [None] * 18 + ["2020-01-01", "2021-01-01"], # 90% null
        "BIRTHPLACE": ["Montreal"] * 20, # Will be generalized to None
        "GENDER": ["F", "M"] * 10,
        "HEALTHCARE_EXPENSES": [1000] * 20,
        "LAT": [45.5 + i/1000 for i in range(20)] # Unique lats to force escalation
    }
    
    df = pd.DataFrame(data)
    
    # Matching auto_anonymize logic
    configs = []
    # SSN -> Suppression
    configs.append(AnonymizationConfig(column_name="SSN", technique=AnonymizationTechnique.SUPPRESSION))
    # BIRTHDATE -> Generalization YEAR
    configs.append(AnonymizationConfig(column_name="BIRTHDATE", technique=AnonymizationTechnique.GENERALIZATION, params={"mode": "year"}))
    # DEATHDATE -> Generalization YEAR
    configs.append(AnonymizationConfig(column_name="DEATHDATE", technique=AnonymizationTechnique.GENERALIZATION, params={"mode": "year"}))
    # BIRTHPLACE -> Generalization empty hierarchy
    configs.append(AnonymizationConfig(column_name="BIRTHPLACE", technique=AnonymizationTechnique.GENERALIZATION, params={"hierarchy": {}}))
    # GENDER -> Keep as is
    configs.append(AnonymizationConfig(column_name="GENDER", technique=AnonymizationTechnique.KEEP_AS_IS))
    # Expenses -> Keep as is
    configs.append(AnonymizationConfig(column_name="HEALTHCARE_EXPENSES", technique=AnonymizationTechnique.KEEP_AS_IS))
    # LAT -> Generalization range
    configs.append(AnonymizationConfig(column_name="LAT", technique=AnonymizationTechnique.GENERALIZATION, params={"range_size": 1.0}))

    # Apply transformations
    anonymized_df = df.copy()
    transformations = []
    for config in configs:
        anonymized_df, transformation = anonymizer._apply_technique(anonymized_df, df, config, uuid.uuid4(), uuid.uuid4())
        transformations.append(transformation)
    
    # Escalation (should trigger cleanup at the end and report drops)
    print("Starting escalation/cleanup...")
    anonymized_df = anonymizer._apply_k_anonymity_escalation(
        anonymized_df, df, configs, uuid.uuid4(), transformations, min_k=10
    )

    print("\n--- Reported Transformations ---")
    trans_cols = [t.column_name for t in transformations]
    print(trans_cols)
    
    results = []
    
    # 1. SSN must be removed
    if "SSN" not in anonymized_df.columns:
        print("✅ SSN removed from header")
        results.append(True)
    else: 
        print("❌ SSN still present")
        results.append(False)
        
    # 2. BIRTHDATE must be YEAR only (string or int, not a range)
    bd_val = str(anonymized_df['BIRTHDATE'].iloc[0])
    if bd_val == "1970" or bd_val == "1970.0":
        print("✅ BIRTHDATE is YEAR only")
        results.append(True)
    else:
        print(f"❌ BIRTHDATE unexpected: {bd_val}")
        results.append(False)
        
    # 3. DEATHDATE must be preserved (threshold 95% > 90% null)
    if "DEATHDATE" in anonymized_df.columns:
        print("✅ DEATHDATE preserved (threshold 95%)")
        results.append(True)
    else:
        print("❌ DEATHDATE removed incorrectly")
        results.append(False)
        
    # 4. BIRTHPLACE must be removed (empty)
    if "BIRTHPLACE" not in anonymized_df.columns:
        print("✅ BIRTHPLACE removed (empty)")
        results.append(True)
    else:
        print("❌ BIRTHPLACE still present")
        results.append(False)
        
    # 6. Check if dropped columns are in transformations
    # BIRTHPLACE should be reported as suppressed (empty after anonymization)
    # SSN should be reported as suppressed (explicit config)
    # DEATHDATE should NOT be removed now (threshold is 95%, it was 90% null in test)
    # Wait, let's check DEATHDATE logic
    
    suppressed_cols = [t.column_name for t in transformations if t.technique == AnonymizationTechnique.SUPPRESSION]
    print(f"Suppressed columns in report: {suppressed_cols}")
    
    if "BIRTHPLACE" in suppressed_cols:
        print("✅ BIRTHPLACE (empty) correctly reported as suppressed")
        results.append(True)
    else:
        print("❌ BIRTHPLACE (empty) NOT reported as suppressed")
        results.append(False)

    if "LAT" in suppressed_cols:
        print("✅ LAT (escalated) correctly reported as suppressed")
        results.append(True)
    else:
        print("❌ LAT (escalated) NOT reported as suppressed")
        results.append(False)

    db.close()
    if all(results):
        print("\n✨ CLEANUP SUCCESS ✨")
        sys.exit(0)
    else:
        print("\n❌ CLEANUP FAILURE ❌")
        sys.exit(1)

if __name__ == "__main__":
    test_dataset_cleanup()
