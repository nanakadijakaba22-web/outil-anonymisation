"""
API endpoints for dataset management.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.schemas import DatasetResponse, DatasetPreview, DetectionReport, RiskAssessmentResponse
from app.services.data_ingestion import DataIngestionService
from app.services.detector import SensitiveDataDetector
from app.services.risk_evaluator import RiskEvaluator

router = APIRouter()


@router.post("/upload", response_model=DatasetResponse, status_code=201)
async def upload_dataset(
    file: UploadFile = File(..., description="CSV file to upload"),
    db: Session = Depends(get_db)
) -> DatasetResponse:
    """
    Upload a CSV file for anonymization.

    - **file**: CSV file (max 100MB)

    Returns dataset metadata including:
    - Dataset ID
    - Column information
    - Row/column counts
    """
    service = DataIngestionService(db)
    return await service.upload_dataset(file)


@router.get("/{dataset_id}", response_model=DatasetResponse)
def get_dataset(
    dataset_id: UUID,
    db: Session = Depends(get_db)
) -> DatasetResponse:
    """
    Get dataset metadata by ID.

    - **dataset_id**: UUID of the dataset

    Returns full dataset information including column details.
    """
    service = DataIngestionService(db)
    dataset = service.get_dataset(dataset_id)
    return DatasetResponse.model_validate(dataset)


@router.get("/{dataset_id}/preview", response_model=DatasetPreview)
def get_dataset_preview(
    dataset_id: UUID,
    n_rows: int = 10,
    db: Session = Depends(get_db)
) -> DatasetPreview:
    """
    Get preview of dataset (first N rows).

    - **dataset_id**: UUID of the dataset
    - **n_rows**: Number of rows to return (default 10, max 100)

    Returns sample data for preview purposes.
    """
    if n_rows > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 rows allowed for preview")

    service = DataIngestionService(db)
    return service.get_dataset_preview(dataset_id, n_rows)


@router.post("/{dataset_id}/detect", response_model=DetectionReport)
async def detect_sensitive_data(
    dataset_id: UUID,
    db: Session = Depends(get_db)
) -> DetectionReport:
    """
    Analyze dataset and detect sensitive data according to Quebec Law 25.

    - **dataset_id**: UUID of the dataset to analyze

    Returns detailed classification of each column:
    - **Direct identifiers**: NAS, email, phone numbers, names
    - **Quasi-identifiers**: Date of birth, postal code, gender, age
    - **Sensitive data**: Financial information, health data
    - **Non-sensitive data**: General information

    Each column includes:
    - Sensitivity type and category
    - Confidence score (0-100%)
    - Justification for classification
    - Overall dataset risk score
    """
    detector = SensitiveDataDetector(db)
    return await detector.analyze_dataset(dataset_id)


@router.get("/{dataset_id}/risk-assessment", response_model=RiskAssessmentResponse)
async def assess_risk(
    dataset_id: UUID,
    db: Session = Depends(get_db)
) -> RiskAssessmentResponse:
    """
    Evaluate dataset against Quebec Law 25 risk criteria.

    - **dataset_id**: UUID of the dataset to assess

    **IMPORTANT**: Run detection first (`POST /{dataset_id}/detect`) to classify columns
    before running risk assessment.

    Returns comprehensive risk assessment with:

    **Three Risk Criteria:**
    1. **Individualization**: Can we isolate individuals? (unique quasi-identifier combinations)
    2. **Correlation**: Can data be linked to external sources? (linkable columns)
    3. **Inference**: Can we deduce information? (strong correlations between columns)

    Each criterion includes:
    - Score (0-100%)
    - Level (faible/moyen/élevé)
    - Justification
    - Affected columns

    **Overall Assessment:**
    - Overall risk score (weighted average)
    - Law 25 compliance status (COMPLIANT/NON-COMPLIANT)
    - Actionable recommendations

    **Compliance Threshold:** Dataset is compliant if overall score < 20%
    """
    evaluator = RiskEvaluator(db)
    return await evaluator.evaluate_dataset(dataset_id)


@router.delete("/{dataset_id}", status_code=204)
def delete_dataset(
    dataset_id: UUID,
    db: Session = Depends(get_db)
) -> None:
    """
    Delete a dataset and its associated file.

    - **dataset_id**: UUID of the dataset to delete

    This will permanently delete the dataset, all column metadata,
    and the uploaded CSV file.
    """
    service = DataIngestionService(db)
    service.delete_dataset(dataset_id)
    return None
