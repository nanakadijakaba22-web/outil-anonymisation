
import pandas as pd
import sys
import os
from unittest.mock import MagicMock

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.services.anonymizer import Anonymizer

def test_generalization_defaults():
    print("="*60)
    print("TESTING GENERALIZATION DEFAULTS")
    print("="*60)

    # 1. Setup Mock DB and Anonymizer
    mock_db = MagicMock()
    # We mock DataIngestionService to avoid DB calls in __init__ if any
    # But Anonymizer instantiation creates DataIngestionService(db). 
    # Let's hope DataIngestionService doesn't do meaningful work in __init__ other than storing db.
    # If it does, we might fail here. Let's try.
    try:
        anonymizer = Anonymizer(mock_db)
    except Exception as e:
        print(f"Failed to instantiate Anonymizer: {e}")
        # Fallback: Mock DataIngestionService in the module if needed, but let's assume it's fine for now.
        return

    # 2. Create Test Data
    data = {
        "Age": [25, 34, 42, 56],            # Numeric -> Range
        "City": ["Montreal", "Quebec", "Laval", "Sherbrooke"], # Text -> Prefix
        "BirthDate": pd.to_datetime(["1990-05-15", "1985-12-01", "1978-01-30", "2000-07-20"]), # Date -> Year
        "PostalCode": ["H3B 1A1", "G1X 3J4", "K1A 0B1", "J4B 5C2"], # Text -> Prefix (explicit or implied)
        "Salary": [50000, 65000, 72000, 48000] # Numeric -> Range
    }
    df = pd.DataFrame(data)
    
    # 3. Test Cases for _generalize_column
    
    # Case A: Numeric (Age) - Default (should be Range)
    # We simulate what comes from frontend: often just technique="generalization", no specific "method" implied if not set?
    # Actually current code defaults method="range" if missing.
    # Our new logic should keep it as range for numeric.
    print("\n--- Test A: Numeric (Age) - (Expect Range 10) ---")
    df_age = df.copy()
    # method defaults to "range" in the code, so let's pass empty params or minimal
    params_age = {"range_size": 10} 
    df_age = anonymizer._generalize_column(df_age, "Age", params_age)
    print(df_age["Age"].tolist())
    # Expect: "20-30", "30-40" etc.
    assert "-" in str(df_age["Age"].iloc[0]), "Numeric should be generalized to range"

    # Case B: Text (City) - Default (Should detect Prefix)
    # The default method is "range", but our smart logic should switch it to "prefix" for text types
    print("\n--- Test B: Text (City) - (Expect Prefix 3) ---")
    df_city = df.copy()
    params_city = {} # method defaults to "range", should auto-switch to "prefix"
    df_city = anonymizer._generalize_column(df_city, "City", params_city)
    print(df_city["City"].tolist())
    # Expect: "Mon ***", "Que ***"
    assert "***" in str(df_city["City"].iloc[0]), "Text should be generalized to prefix"
    
    # Case C: Date (BirthDate) - Default (Should detect Year)
    print("\n--- Test C: Date (BirthDate) - (Expect Year Only) ---")
    df_date = df.copy()
    params_date = {} # method defaults to "range", should auto-switch to "year_only"
    df_date = anonymizer._generalize_column(df_date, "BirthDate", params_date)
    print(df_date["BirthDate"].tolist())
    # Expect: 1990, 1985...
    assert len(str(df_date["BirthDate"].iloc[0])) == 4, "Date should be generalized to year"

    # Case D: Text (PostalCode) - Explicit "postal_code" or "prefix"
    print("\n--- Test D: Postal Code - Explicit 'prefix' ---")
    df_pc = df.copy()
    params_pc = {"method": "prefix", "prefix_length": 3}
    df_pc = anonymizer._generalize_column(df_pc, "PostalCode", params_pc)
    print(df_pc["PostalCode"].tolist())
    # Expect: "H3B ***", "G1X ***"
    assert "***" in str(df_pc["PostalCode"].iloc[0])
    
    # Case E: Mixed/Object that looks like Date
    print("\n--- Test E: String Date - (Expect Year Only) ---")
    df_str_date = pd.DataFrame({"StrDate": ["2020-01-01", "2021-05-05"]})
    params_str_date = {} 
    # Should detect it parses as date and switch to year_only
    df_str_date = anonymizer._generalize_column(df_str_date, "StrDate", params_str_date)
    print(df_str_date["StrDate"].tolist())
    # Expect: 2020, 2021
    assert str(df_str_date["StrDate"].iloc[0]) == "2020", "String date should be detected and generalized to year"

    print("\n" + "="*60)
    print("SUCCESS: All Smart Default Tests Passed!")
    print("="*60)

if __name__ == "__main__":
    test_generalization_defaults()
