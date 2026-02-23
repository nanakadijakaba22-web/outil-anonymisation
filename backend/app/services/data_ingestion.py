"""
Data ingestion service for CSV file processing.
"""
import os
import uuid
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.database import Dataset, DatasetColumn
from app.models.schemas import DatasetCreate, DatasetResponse, DatasetPreview


class DataIngestionService:
    """Service for handling CSV file upload and processing."""

    def __init__(self, db: Session):
        self.db = db
        self.upload_dir = Path(settings.UPLOAD_DIR)
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    async def upload_dataset(self, file: UploadFile) -> DatasetResponse:
        """
        Upload and process a CSV file.

        Args:
            file: Uploaded file from FastAPI

        Returns:
            DatasetResponse with dataset metadata

        Raises:
            HTTPException: If file is invalid or processing fails
        """
        # Validate file
        self._validate_file(file)

        # Save file temporarily
        file_path = await self._save_file(file)

        try:
            # Parse CSV with pandas
            df = self._parse_csv(file_path)

            # Extract metadata
            dataset_create = DatasetCreate(
                filename=file.filename,
                file_size=os.path.getsize(file_path),
                file_path=str(file_path),
                row_count=len(df),
                column_count=len(df.columns),
            )

            # Save to database
            dataset = self._create_dataset(dataset_create, df)

            # Return response
            return DatasetResponse.model_validate(dataset)

        except Exception as e:
            # Clean up file if processing fails
            if file_path.exists():
                file_path.unlink()
            raise HTTPException(status_code=500, detail=f"Failed to process CSV: {str(e)}")

    def _validate_file(self, file: UploadFile) -> None:
        """Validate uploaded file."""
        # Check file extension
        if not file.filename.endswith('.csv'):
            raise HTTPException(
                status_code=400,
                detail="Invalid file format. Only CSV files are accepted."
            )

        # File size will be checked during streaming upload
        # FastAPI doesn't load entire file into memory by default

    async def _save_file(self, file: UploadFile) -> Path:
        """Save uploaded file to disk."""
        # Generate unique filename
        file_id = uuid.uuid4()
        file_path = self.upload_dir / f"{file_id}_{file.filename}"

        # Stream file to disk
        total_size = 0
        with open(file_path, "wb") as f:
            while chunk := await file.read(8192):  # Read in 8KB chunks
                total_size += len(chunk)
                if total_size > settings.MAX_UPLOAD_SIZE:
                    f.close()
                    file_path.unlink()  # Delete partial file
                    raise HTTPException(
                        status_code=413,
                        detail=f"File too large. Maximum size is {settings.MAX_UPLOAD_SIZE / (1024*1024*1024):.1f}GB"
                    )
                f.write(chunk)

        return file_path

    def _parse_csv(self, file_path: Path) -> pd.DataFrame:
        """
        Parse CSV file with pandas.

        Handles:
        - Encoding detection (UTF-8, Latin-1, etc.)
        - Delimiter detection
        - Type inference
        """
        try:
            # Try UTF-8 first
            df = pd.read_csv(file_path, encoding='utf-8')
        except UnicodeDecodeError:
            # Fallback to Latin-1
            try:
                df = pd.read_csv(file_path, encoding='latin-1')
            except Exception as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to parse CSV file: {str(e)}"
                )

        if df.empty:
            raise HTTPException(status_code=400, detail="CSV file is empty")

        return df

    def _create_dataset(self, dataset_create: DatasetCreate, df: pd.DataFrame) -> Dataset:
        """Create dataset and column records in database."""
        # Create dataset record
        dataset = Dataset(**dataset_create.model_dump())
        self.db.add(dataset)
        self.db.flush()  # Get dataset ID without committing

        # Create column records
        for idx, col_name in enumerate(df.columns):
            col_data = df[col_name]

            column = DatasetColumn(
                dataset_id=dataset.id,
                name=str(col_name),
                position=idx,
                data_type=str(col_data.dtype),
                null_count=int(col_data.isnull().sum()),
                unique_count=int(col_data.nunique()),
                sample_values=self._get_sample_values(col_data),
            )
            self.db.add(column)

        self.db.commit()
        self.db.refresh(dataset)
        return dataset

    def _get_sample_values(self, series: pd.Series, n: int = 5) -> list[Any]:
        """Get sample values from a pandas Series."""
        # Get non-null unique values
        unique_values = series.dropna().unique()[:n]

        # Convert to native Python types
        return [self._convert_to_python_type(val) for val in unique_values]

    def _convert_to_python_type(self, value: Any) -> Any:
        """Convert pandas/numpy types to native Python types."""
        if pd.isna(value):
            return None
        if isinstance(value, pd.Timestamp):
            return value.isoformat()
        if isinstance(value, (int, float, str, bool)):
            return value
        # For numpy types
        if hasattr(value, 'item'):
            return value.item()
        return str(value)

    def get_dataset(self, dataset_id: uuid.UUID) -> Dataset:
        """Get dataset by ID."""
        dataset = self.db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")
        return dataset

    def get_dataset_preview(self, dataset_id: uuid.UUID, n_rows: int = 10) -> DatasetPreview:
        """
        Get preview of dataset (first N rows).

        Args:
            dataset_id: Dataset UUID
            n_rows: Number of rows to return

        Returns:
            DatasetPreview with sample rows
        """
        dataset = self.get_dataset(dataset_id)

        # Load CSV
        df = pd.read_csv(dataset.file_path, nrows=n_rows)

        # Convert to list of dicts
        sample_rows = df.to_dict('records')

        # Convert numpy/pandas types to Python types
        sample_rows = [
            {k: self._convert_to_python_type(v) for k, v in row.items()}
            for row in sample_rows
        ]

        return DatasetPreview(
            dataset_id=dataset_id,
            columns=list(df.columns),
            sample_rows=sample_rows,
            total_rows=dataset.row_count,
        )

    def delete_dataset(self, dataset_id: uuid.UUID) -> None:
        """Delete dataset and associated file."""
        dataset = self.get_dataset(dataset_id)

        # Delete file
        file_path = Path(dataset.file_path)
        if file_path.exists():
            file_path.unlink()

        # Delete from database (cascade will handle columns)
        self.db.delete(dataset)
        self.db.commit()

    def load_dataframe(self, dataset_id: uuid.UUID) -> pd.DataFrame:
        """Load full dataset as pandas DataFrame."""
        dataset = self.get_dataset(dataset_id)
        return pd.read_csv(dataset.file_path)
