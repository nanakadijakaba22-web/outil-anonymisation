import pytest
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import uuid
import asyncio
from app.models.database import Base, Dataset, DatasetColumn
from app.services.detector import SensitiveDataDetector
from app.models.schemas import DataType, Category

# Setup in-memory database
engine = create_engine("sqlite:///:memory:")
SessionLocal = sessionmaker(bind=engine)
Base.metadata.create_all(bind=engine)

@pytest.mark.asyncio
async def test_improved_detection():
    db = SessionLocal()
    
    # Create fake dataset
    dataset_id = uuid.uuid4()
    dataset = Dataset(
        id=dataset_id,
        filename="test.csv",
        file_size=1024,
        row_count=100,
        column_count=4,
        file_path="/tmp/test.csv"
    )
    db.add(dataset)
    
    cols = [
        DatasetColumn(dataset_id=dataset_id, name="age", data_type="int64", unique_count=50),
        DatasetColumn(dataset_id=dataset_id, name="ville", data_type="object", unique_count=20),
        DatasetColumn(dataset_id=dataset_id, name="type_compte", data_type="object", unique_count=5),
        DatasetColumn(dataset_id=dataset_id, name="nom", data_type="object", unique_count=100)
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
                "ville": ["Montreal", "Quebec", "Laval", "Sherbrooke"] * 25,
                "type_compte": ["Epargne", "Courant"] * 50,
                "nom": [f"User{i}" for i in range(100)]
            })
            
    detector = SensitiveDataDetector(db)
    detector.ingestion_service = MockIngestion()
    
    report = await detector.analyze_dataset(dataset_id)
    
    # Verify age detection
    age_col = report.columns["age"]
    assert age_col.sensitivity_type == DataType.QUASI_IDENTIFIER
    assert age_col.confidence >= 60
    assert "Format âge détecté" in age_col.justification or "Nom de colonne suggère" in age_col.justification

    # Verify ville detection
    ville_col = report.columns["ville"]
    assert ville_col.sensitivity_type == DataType.QUASI_IDENTIFIER
    assert ville_col.confidence >= 60

    # Verify type_compte detection
    type_compte_col = report.columns["type_compte"]
    assert type_compte_col.sensitivity_type == DataType.QUASI_IDENTIFIER
    assert type_compte_col.confidence >= 60

    print("\n✅ Verification passed!")

if __name__ == "__main__":
    asyncio.run(test_improved_detection())
