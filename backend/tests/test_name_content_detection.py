import pytest
from app.services.detector import SensitiveDataDetector
from app.models.schemas import DataType, Category
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

def test_name_vs_number_detection():
    # Setup a mock DB session
    engine = create_engine("sqlite:///:memory:")
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    detector = SensitiveDataDetector(db)
    
    # CASE 1: "first" with actual names
    samples_names = ["Jean", "Marie", "Pierre", "Sophie", "Thomas"]
    classification = detector.detect_column_type("first", samples_names, 1.0, "string")
    print(f"CASE 1 (first/names): Got {classification.sensitivity_type}")
    assert classification.sensitivity_type == DataType.DIRECT_IDENTIFIER
    assert classification.category == Category.PERSONAL

    # CASE 2: "first" with numbers (e.g. order index)
    samples_numbers = ["1", "2", "3", "4", "5"]
    classification = detector.detect_column_type("first", samples_numbers, 1.0, "integer")
    print(f"CASE 2 (first/numbers): Got {classification.sensitivity_type}")
    # Should NOT be DIRECT_IDENTIFIER because content doesn't match name pattern
    assert classification.sensitivity_type != DataType.DIRECT_IDENTIFIER

    # CASE 3: "last" with actual names
    samples_last = ["Dupont", "Durand", "Lefebvre", "Petit", "Moreau"]
    classification = detector.detect_column_type("last", samples_last, 1.0, "string")
    print(f"CASE 3 (last/names): Got {classification.sensitivity_type}")
    assert classification.sensitivity_type == DataType.DIRECT_IDENTIFIER

    # CASE 4: "last" with dates
    samples_dates = ["2023-01-01", "2023-02-01", "2023-03-01"]
    classification = detector.detect_column_type("last", samples_dates, 0.3, "date")
    print(f"CASE 4 (last/dates): Got {classification.sensitivity_type}")
    assert classification.sensitivity_type != DataType.DIRECT_IDENTIFIER

if __name__ == '__main__':
    try:
        test_name_vs_number_detection()
        print("\nNAME CONTENT DETECTION TESTS PASSED!")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"\nTEST FAILED: {e}")
        exit(1)
