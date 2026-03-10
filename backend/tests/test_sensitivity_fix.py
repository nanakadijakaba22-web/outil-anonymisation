import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.detector import SensitiveDataDetector
from app.models.schemas import DataType, Category

def test_ethnic_origin_classification():
    # Mock DB session
    engine = create_engine("sqlite:///:memory:")
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    detector = SensitiveDataDetector(db)
    
    # Test column name 'origine'
    classification = detector.detect_column_type(
        column_name="origine",
        sample_values=["Québécois", "Canadien"],
        unique_ratio=0.1,
        data_type="object"
    )
    
    print(f"Column: {classification.column_name}")
    print(f"Type: {classification.sensitivity_type}")
    print(f"Category: {classification.category}")
    print(f"Justification: {classification.justification}")
    
    assert classification.sensitivity_type == DataType.SENSITIVE
    assert classification.category == Category.ETHNIC_OR_RACIAL_ORIGIN
    print("Test passed!")

if __name__ == "__main__":
    test_ethnic_origin_classification()
