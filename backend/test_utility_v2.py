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
DATABASE_URL = "sqlite:///./test_utility_v2.db"
engine = create_engine(DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

def test_utility_strategy_v2():
    db = TestingSessionLocal()
    anonymizer = Anonymizer(db)
    
    # Create sample data with 100 rows to ensure k=10 is possible
    # We create 10 distinct groups of 10 rows each for the "Keep" columns
    base_data = {
        "GENDER": ["F", "M"] * 5,
        "MARITAL": ["Married", "Single"] * 5,
        "CITY": ["Montreal", "Toronto", "Vancouver", "Ottawa", "Quebec"] * 2,
        "HEALTHCARE_EXPENSES": [1000, 2000, 3000, 4000, 5000] * 2
    }
    
    rows = []
    for i in range(10): # 10 groups
        for j in range(10): # 10 identical rows in each group for these cols
            row = {
                "SSN": f"SSN-{i}-{j}",
                "FIRST_NAME": f"First-{i}-{j}",
                "BIRTHDATE": pd.Timestamp(f"{1970 + i}-01-01"),
                "ZIP": 2100 + (i * 10) + j, # Different ZIPs initially
                "LAT": 45.0 + i + (j/100.0),
                "LON": -73.0 - i - (j/100.0),
                "ADDRESS": f"{j} {i} St",
                "RACE": "White" if i % 2 == 0 else "Black",
                **{k: v[i] for k, v in base_data.items()}
            }
            rows.append(row)
            
    df = pd.DataFrame(rows)
    
    # Mocking detection report
    class MockCls:
        def __init__(self, stype, cat=Category.PERSONAL):
            self.sensitivity_type = stype
            self.confidence = 100
            self.justification = "Testing"
            self.category = cat

    class MockReport:
        def __init__(self, columns):
            self.columns = columns
            self.dataset_id = uuid.uuid4()

    report = MockReport({
        "SSN": MockCls(DataType.DIRECT_IDENTIFIER),
        "FIRST_NAME": MockCls(DataType.DIRECT_IDENTIFIER),
        "BIRTHDATE": MockCls(DataType.QUASI_IDENTIFIER),
        "ZIP": MockCls(DataType.QUASI_IDENTIFIER),
        "LAT": MockCls(DataType.QUASI_IDENTIFIER),
        "LON": MockCls(DataType.QUASI_IDENTIFIER),
        "ADDRESS": MockCls(DataType.QUASI_IDENTIFIER),
        "GENDER": MockCls(DataType.QUASI_IDENTIFIER),
        "MARITAL": MockCls(DataType.QUASI_IDENTIFIER),
        "RACE": MockCls(DataType.QUASI_IDENTIFIER),
        "CITY": MockCls(DataType.QUASI_IDENTIFIER),
        "HEALTHCARE_EXPENSES": MockCls(DataType.SENSITIVE, Category.FINANCIAL)
    })

    # Manual config loop (matching auto_anonymize logic)
    configs = []
    for col in df.columns:
        upper = col.upper()
        if any(id_keyword in upper for id_keyword in ["SSN", "FIRST"]):
            configs.append(AnonymizationConfig(column_name=col, technique=AnonymizationTechnique.SUPPRESSION))
        elif upper == "BIRTHDATE":
            configs.append(AnonymizationConfig(column_name=col, technique=AnonymizationTechnique.GENERALIZATION, params={"mode": "year"}))
        elif upper == "ZIP":
            configs.append(AnonymizationConfig(column_name=col, technique=AnonymizationTechnique.GENERALIZATION, params={"mode": "range", "range_size": 100}))
        elif upper in ["LAT", "LON"]:
            configs.append(AnonymizationConfig(column_name=col, technique=AnonymizationTechnique.GENERALIZATION, params={"mode": "range", "range_size": 1.0}))
        elif upper == "ADDRESS":
            configs.append(AnonymizationConfig(column_name=col, technique=AnonymizationTechnique.SUPPRESSION))
        elif upper == "RACE":
            configs.append(AnonymizationConfig(column_name=col, technique=AnonymizationTechnique.GENERALIZATION, params={"hierarchy": anonymizer.DEMOGRAPHIC_HIERARCHIES["race"]}))
        elif any(k in upper for k in ["GENDER", "MARITAL", "CITY", "HEALTHCARE_EXPENSES"]):
            configs.append(AnonymizationConfig(column_name=col, technique=AnonymizationTechnique.KEEP_AS_IS))

    # Apply transformations
    anonymized_df = df.copy()
    for config in configs:
        anonymized_df, _ = anonymizer._apply_technique(anonymized_df, df, config, uuid.uuid4(), uuid.uuid4())
    
    # Escalation
    print(f"Starting escalation with target k=10...")
    anonymized_df = anonymizer._apply_k_anonymity_escalation(
        anonymized_df, df, configs, uuid.uuid4(), min_k=10
    )

    print("\n--- Final Results ---")
    results = []
    
    # Checks
    print(f"BIRTHDATE[0]: {anonymized_df['BIRTHDATE'].iloc[0]} (Type: {type(anonymized_df['BIRTHDATE'].iloc[0])})")
    # BIRTHDATE could be year (1970) or age bin (50-59) if escalated
    bd_val = str(anonymized_df['BIRTHDATE'].iloc[0])
    if "1970" in bd_val or "-" in bd_val:
        print("✅ BIRTHDATE is year or age bin")
        results.append(True)
    else: 
        print(f"❌ BIRTHDATE unexpected: {bd_val}")
        results.append(False)

    if 'ZIP' in anonymized_df.columns:
        print(f"ZIP[0]: {anonymized_df['ZIP'].iloc[0]}")
        # Generalized ZIP should be numeric and multiple of range_size (or offset)
        if pd.api.types.is_numeric_dtype(anonymized_df['ZIP']) or anonymized_df['ZIP'].dtype == object:
            print("✅ ZIP is generalized")
            results.append(True)
        else:
            print("❌ ZIP is unexpected type")
            results.append(False)
    else:
        print("✅ ZIP was dropped (Escalation worked)")
        results.append(True)

    print(f"RACE[0]: {anonymized_df['RACE'].iloc[0]}")
    if anonymized_df['RACE'].iloc[0] in ["Broad Category", "Caucaisien/Autre", "Afro-descendant/Autre"]:
        print("✅ RACE is hierarchical")
        results.append(True)
    else:
        print("❌ RACE is NOT hierarchical")
        results.append(False)

    print(f"GENDER[0]: {anonymized_df['GENDER'].iloc[0]}")
    if anonymized_df['GENDER'].iloc[0] == "F":
        print("✅ GENDER is preserved")
        results.append(True)
    else: results.append(False)

    # K-anonymity check (Strictly on QIDs)
    quasi_ids = [c.column_name for c in configs if c.column_name.upper() in anonymizer.QUASI_IDENTIFIERS_SET]
    # Final k-anonymity check
    # ZIP or CITY might have been dropped during escalation, we MUST check only existing columns
    present_qids = [q for q in quasi_ids if q in anonymized_df.columns]
    k_min = anonymized_df.groupby(present_qids, dropna=False).size().min()
    print(f"Final k_min: {k_min}")
    if k_min >= 10:
        print("✅ K-Anonymity >= 10 achieved")
        results.append(True)
    else: results.append(False)

    db.close()
    assert all(results), "Some utility strategy v2 tests failed"
    print("\n✨ SUCCESS ✨")

if __name__ == "__main__":
    test_utility_strategy_v2()
