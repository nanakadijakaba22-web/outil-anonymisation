import pytest
from app.services.detector import SensitiveDataDetector
from app.models.schemas import DataType, Category
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

def test_law25_categorization_rules():
    # Setup a mock DB session
    engine = create_engine("sqlite:///:memory:")
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    detector = SensitiveDataDetector(db)
    
    # Test cases: (column_name, expected_type, expected_category)
    test_cases = [
        # Identifiants directs -> Personnel
        ("ssn", DataType.DIRECT_IDENTIFIER, Category.PERSONAL),
        ("passport", DataType.DIRECT_IDENTIFIER, Category.PERSONAL),
        ("drivers", DataType.DIRECT_IDENTIFIER, Category.PERSONAL),
        ("first_name", DataType.DIRECT_IDENTIFIER, Category.PERSONAL),
        ("last_name", DataType.DIRECT_IDENTIFIER, Category.PERSONAL),
        ("maiden_name", DataType.DIRECT_IDENTIFIER, Category.PERSONAL),
        
        # Quasi-identifiants -> Personnel
        ("birthdate", DataType.QUASI_IDENTIFIER, Category.PERSONAL),
        ("gender", DataType.SENSITIVE, Category.ORIENTATION_SEXUELLE),
        ("address", DataType.QUASI_IDENTIFIER, Category.PERSONAL),
        ("city", DataType.QUASI_IDENTIFIER, Category.PERSONAL),
        ("state", DataType.QUASI_IDENTIFIER, Category.PERSONAL),
        ("zip", DataType.QUASI_IDENTIFIER, Category.PERSONAL),
        ("latitude", DataType.QUASI_IDENTIFIER, Category.PERSONAL),
        ("longitude", DataType.QUASI_IDENTIFIER, Category.PERSONAL),
        
        # Données sensibles -> Origine ethnique ou raciale
        ("race", DataType.SENSITIVE, Category.ETHNIC_OR_RACIAL_ORIGIN),
        ("ethnicity", DataType.SENSITIVE, Category.ETHNIC_OR_RACIAL_ORIGIN),
        
        # Données de santé -> Santé
        ("healthcare_expenses", DataType.SENSITIVE, Category.SANTE),
        ("healthcare_coverage", DataType.SENSITIVE, Category.SANTE),
        
        # Données non sensibles -> Autre
        ("prefix", DataType.NON_SENSITIVE, Category.OTHER),
        ("suffix", DataType.NON_SENSITIVE, Category.OTHER),
        ("marital_status", DataType.NON_SENSITIVE, Category.OTHER),
        ("county", DataType.NON_SENSITIVE, Category.OTHER),
        ("birthplace", DataType.NON_SENSITIVE, Category.OTHER),
    ]
    
    for col_name, exp_type, exp_cat in test_cases:
        classification = detector.detect_column_type(col_name, [], 0, "string")
        res_type = classification.sensitivity_type
        res_cat = classification.category
        
        print(f"Testing {col_name}: Expected({exp_type}, {exp_cat}) -> Got({res_type}, {res_cat})")
        assert res_type == exp_type, f"Failed type for {col_name}: {res_type} != {exp_type}"
        assert res_cat == exp_cat, f"Failed category for {col_name}: {res_cat} != {exp_cat}"

    # Test "Finance" bias reduction
    # "amount" should not be SENSITIVE by keyword now (unless context added, but here empty values)
    classification = detector.detect_column_type("transaction_amount", [], 0, "float")
    res_type = classification.sensitivity_type
    res_cat = classification.category
    
    print(f"Testing transaction_amount: Got({res_type}, {res_cat})")
    # It might be classified as non_sensitive or quasi depending on other factors, 
    # but it should NOT be SENSITIVE/FINANCE just by name "amount"
    assert not (res_type == DataType.SENSITIVE and res_cat == Category.FINANCE), "Bias for 'amount' still exists"

if __name__ == '__main__':
    try:
        test_law25_categorization_rules()
        print("\nALL CATEGORIZATION TESTS PASSED!")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"\nTEST FAILED: {e}")
        exit(1)
