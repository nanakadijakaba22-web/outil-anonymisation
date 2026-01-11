import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import uuid
import asyncio
import sys
import os

# Mock the app environment
sys.path.append(os.getcwd())

from app.models.database import Base, Dataset, DatasetColumn
from app.services.detector import SensitiveDataDetector
from app.models.schemas import DataType, Category

# Setup in-memory database
engine = create_engine("sqlite:///:memory:")
SessionLocal = sessionmaker(bind=engine)
Base.metadata.create_all(bind=engine)

async def test_improved_detection():
    db = SessionLocal()
    
    # Create fake dataset
    dataset_id = uuid.uuid4()
    dataset = Dataset(
        id=dataset_id,
        filename="test.csv",
        file_size=1024,
        row_count=100,
        column_count=5,
        file_path="/tmp/test.csv"
    )
    db.add(dataset)
    
    cols = [
        DatasetColumn(dataset_id=dataset_id, name="age", data_type="int64", unique_count=50),
        DatasetColumn(dataset_id=dataset_id, name="Âge", data_type="int64", unique_count=50),
        DatasetColumn(dataset_id=dataset_id, name="Ville de résidence", data_type="object", unique_count=20),
        DatasetColumn(dataset_id=dataset_id, name="Type de compte", data_type="object", unique_count=5),
        DatasetColumn(dataset_id=dataset_id, name="Nom complet", data_type="object", unique_count=100)
    ]
    for col in cols:
        db.add(col)
    db.commit()
    
    # Mock DataIngestionService.load_dataframe
    class MockIngestion:
        def get_dataset(self, id): return dataset
        def load_dataframe(self, id):
            return pd.DataFrame({
                "age": [20, 30, 40, 50] * 25,
                "Âge": [20, 30, 40, 50] * 25,
                "Ville de résidence": ["Montreal", "Quebec", "Laval", "Sherbrooke"] * 25,
                "Type de compte": ["Epargne", "Courant"] * 50,
                "Nom complet": [f"User{i}" for i in range(100)]
            })
            
    detector = SensitiveDataDetector(db)
    detector.ingestion_service = MockIngestion()
    
    report = await detector.analyze_dataset(dataset_id)
    
    results = {}
    for col_name, classification in report.columns.items():
        results[col_name] = classification
        print(f"Column: {col_name} -> {classification.sensitivity_type} ({classification.confidence}%)")

    # Assertions
    assert results["age"].sensitivity_type == DataType.QUASI_IDENTIFIER
    assert results["Âge"].sensitivity_type == DataType.QUASI_IDENTIFIER
    assert results["Ville de résidence"].sensitivity_type == DataType.QUASI_IDENTIFIER
    assert results["Type de compte"].sensitivity_type == DataType.QUASI_IDENTIFIER
    assert results["Nom complet"].sensitivity_type == DataType.DIRECT_IDENTIFIER

    print("\n✅ Verification passed!")

if __name__ == "__main__":
    asyncio.run(test_improved_detection())
