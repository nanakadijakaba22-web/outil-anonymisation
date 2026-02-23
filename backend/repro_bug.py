
import pandas as pd
import sys
import os
from unittest.mock import MagicMock

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.services.anonymizer import Anonymizer

def test_repro():
    print("="*60)
    print("TESTING REPRODUCTION: Empty Params for Numeric")
    print("="*60)

    mock_db = MagicMock()
    try:
        anonymizer = Anonymizer(mock_db)
    except Exception as e:
        print(f"Failed to instantiate Anonymizer: {e}")
        return

    data = {
        "Age": [25, 34, 42, 56],
    }
    df = pd.DataFrame(data)
    
    print("\n--- Test: Numeric (Age) - Empty Params ---")
    # START OF BUG REPRODUCTION
    # Passing empty params to force default path
    params_age = {} 
    df_age = anonymizer._generalize_column(df.copy(), "Age", params_age)
    print(f"Resulting values: {df_age['Age'].tolist()}")
    
    # Check if it looks like a range (x-y) or a bin interval ((x, y])
    first_val = str(df_age["Age"].iloc[0])
    print(f"First value: {first_val}")

    if "(" in first_val and "]" in first_val:
        print("DETECTED: Uses pd.cut bin intervals (e.g. (24.969, 31.2]) -> This might be confusing/wrong for user.")
    elif "-" in first_val:
        print("DETECTED: Uses range format (e.g. 20-30).")
    else:
        print("DETECTED: Something else.")

if __name__ == "__main__":
    test_repro()
