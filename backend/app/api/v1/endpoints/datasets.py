"""
API endpoints for dataset management.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.schemas import DatasetResponse, DatasetPreview, DetectionReport, RiskAssessmentResponse
from app.services.data_ingestion import DataIngestionService
from app.services.detector import SensitiveDataDetector
from app.services.risk_evaluator import RiskEvaluator
from app.services.report_generator import PDFReportGenerator
from app.services.visualization import DataVisualizationService

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


@router.get("/{dataset_id}/statistics")
def get_dataset_statistics(
    dataset_id: UUID,
    db: Session = Depends(get_db)
) -> dict:
    """
    Get comprehensive statistical analysis and visualization data for a dataset.

    - **dataset_id**: UUID of the dataset to analyze

    Returns detailed statistics including:

    **Overview:**
    - Total rows, columns
    - Numeric vs categorical breakdown
    - Memory usage
    - Duplicate rows count

    **Numeric Statistics:**
    - Mean, median, std, min, max
    - Quartiles (Q1, Q2, Q3)
    - Skewness, kurtosis
    - Range, IQR

    **Categorical Statistics:**
    - Unique values count
    - Mode and frequency
    - Top 10 most common values
    - Entropy (diversity measure)

    **Missing Data Analysis:**
    - Total missing values
    - Missing percentage per column

    **Distributions:**
    - Histogram data for numeric columns (bins + counts)
    - Frequency data for categorical columns (top 20 values)

    **Correlation Analysis:**
    - Correlation matrix for numeric columns
    - Strong correlations (|r| > 0.7)

    **Outlier Detection:**
    - Outlier count and percentage per column (IQR method)
    - Upper and lower bounds

    **Use Cases:**
    - Data exploration and understanding
    - Frontend visualization (charts, graphs)
    - Quality assessment
    - Before/after anonymization comparison
    """
    viz_service = DataVisualizationService(db)
    return viz_service.generate_statistics(dataset_id)


@router.get("/{dataset_id}/compare/{anonymized_id}")
def compare_datasets(
    dataset_id: UUID,
    anonymized_id: UUID,
    db: Session = Depends(get_db)
) -> dict:
    """
    Compare original and anonymized datasets.

    - **dataset_id**: UUID of the original dataset
    - **anonymized_id**: UUID of the anonymized dataset

    Returns comparison metrics:
    - Column changes (removed, added, retained)
    - Statistical changes (mean, std, range)
    - Row count changes

    **Use Case:** Understand impact of anonymization on data utility
    """
    viz_service = DataVisualizationService(db)
    return viz_service.compare_datasets(dataset_id, anonymized_id)


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


@router.get("/{dataset_id}/report")
async def generate_compliance_report(
    dataset_id: UUID,
    db: Session = Depends(get_db)
) -> StreamingResponse:
    """
    Generate a comprehensive PDF compliance report for Quebec Law 25.

    - **dataset_id**: UUID of the dataset (original or anonymized)

    **IMPORTANT**: Run detection and risk assessment first to populate the report with:
    - Detection results (`POST /{dataset_id}/detect`)
    - Risk assessment (`GET /{dataset_id}/risk-assessment`)

    Returns a professional PDF report including:
    - Executive summary with compliance status
    - Risk assessment details (individualization, correlation, inference)
    - Sensitive data detection results
    - Anonymization transformations (if applicable)
    - Data visualization (histograms, correlations, outliers)
    - Actionable recommendations

    The report is suitable for compliance audits and stakeholder communication.
    """
    # Get dataset
    service = DataIngestionService(db)
    dataset = service.get_dataset(dataset_id)

    # Get risk assessment (required)
    evaluator = RiskEvaluator(db)
    risk_assessment = await evaluator.evaluate_dataset(dataset_id)

    # Try to get detection report (optional, might not exist for anonymized datasets)
    detection_report = None
    try:
        detector = SensitiveDataDetector(db)
        detection_report = await detector.analyze_dataset(dataset_id)
    except Exception:
        # Detection not available or failed - continue without it
        pass

    # Get anonymization details if this is an anonymized dataset
    anonymization_response = None
    if dataset.is_anonymized and dataset.anonymization_jobs:
        # Get the latest anonymization job
        latest_job = max(dataset.anonymization_jobs, key=lambda j: j.created_at)
        from app.models.schemas import AnonymizationResponse, TransformationResult, SampleTransformation

        # Build anonymization response from job data
        transformations = []
        for log in latest_job.transformation_logs:
            transformations.append(
                TransformationResult(
                    column_name=log.column_name,
                    technique=log.technique,
                    params=log.params or {},
                    values_affected=log.values_affected,
                    sample_transformations=[
                        SampleTransformation(
                            original=sample.get("original", ""),
                            anonymized=sample.get("anonymized", "")
                        )
                        for sample in (log.sample_transformations or [])[:5]
                    ]
                )
            )

        anonymization_response = AnonymizationResponse(
            job_id=latest_job.id,
            anonymized_dataset_id=dataset.id,
            transformations=transformations
        )

    # Get visualization data (optional)
    visualization_data = None
    try:
        viz_service = DataVisualizationService(db)
        visualization_data = viz_service.generate_statistics(dataset_id)
    except Exception:
        # Visualization not available or failed - continue without it
        pass

    # Generate PDF
    generator = PDFReportGenerator()
    pdf_buffer = generator.generate_compliance_report(
        dataset=DatasetResponse.model_validate(dataset),
        detection_report=detection_report,
        risk_assessment=risk_assessment,
        anonymization_response=anonymization_response,
        visualization_data=visualization_data
    )

    # Return PDF as streaming response
    filename = f"rapport_loi25_{dataset.filename.replace('.csv', '')}.pdf"
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )
