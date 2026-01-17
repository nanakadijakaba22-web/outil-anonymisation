"""
Pydantic models for request/response validation and serialization.
"""
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


# Enums
class DataType(str, Enum):
    """Types of data sensitivity."""

    DIRECT_IDENTIFIER = "direct_identifier"
    QUASI_IDENTIFIER = "quasi_identifier"
    SENSITIVE = "sensitive"
    NON_SENSITIVE = "non_sensitive"


class Category(str, Enum):
    """Data categories per Law 25."""

    PERSONAL = "personal"
    FINANCIAL = "financial"
    HEALTH = "health"
    INSURANCE = "insurance"
    OTHER = "other"


class RiskLevel(str, Enum):
    """Risk levels for Law 25 assessment."""

    LOW = "faible"
    MEDIUM = "moyen"
    HIGH = "élevé"


class AnonymizationTechnique(str, Enum):
    """Available anonymization techniques."""

    MASKING = "masking"
    GENERALIZATION = "generalization"
    SUPPRESSION = "suppression"
    
    DIFFERENTIAL_PRIVACY = "differential_privacy"


class JobStatus(str, Enum):
    """Anonymization job statuses."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# Column Schemas
class ColumnInfo(BaseModel):
    """Information about a dataset column."""

    name: str
    position: int
    data_type: str
    sensitivity_type: Optional[DataType] = None
    category: Optional[Category] = None
    confidence: Optional[float] = None
    null_count: int = 0
    unique_count: int = 0
    sample_values: Optional[list[Any]] = None

    model_config = ConfigDict(from_attributes=True)


class ColumnClassification(BaseModel):
    """Classification result for a column."""

    column_name: str
    sensitivity_type: DataType
    category: Category
    confidence: float = Field(ge=0, le=100, description="Confidence score 0-100")
    justification: str


class ColumnSensitivityUpdate(BaseModel):
    """Schema for updating column sensitivity classification."""

    sensitivity_type: DataType
    category: Optional[Category] = None
    justification: Optional[str] = Field(
        None,
        description="Optional reason for manual override"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "sensitivity_type": "direct_identifier",
                "category": "personal",
                "justification": "Contains unique client identifiers"
            }
        }
    )


class BulkSensitivityUpdate(BaseModel):
    """Schema for bulk updating multiple columns' sensitivity."""

    updates: dict[str, ColumnSensitivityUpdate] = Field(
        ...,
        description="Map of column_name to sensitivity updates"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "updates": {
                    "client_id": {
                        "sensitivity_type": "direct_identifier",
                        "category": "personal"
                    },
                    "age": {
                        "sensitivity_type": "quasi_identifier",
                        "category": "personal"
                    }
                }
            }
        }
    )


# Dataset Schemas
class DatasetCreate(BaseModel):
    """Schema for dataset creation (internal use)."""

    filename: str
    file_size: int
    file_path: str
    row_count: int
    column_count: int
    encoding: str = "utf-8"
    delimiter: str = ","


class DatasetResponse(BaseModel):
    """Dataset information response."""

    id: UUID
    filename: str
    file_size: int
    row_count: int
    column_count: int
    upload_date: datetime
    is_anonymized: bool
    risk_score: Optional[float] = None
    is_loi25_compliant: bool = False
    columns: list[ColumnInfo] = []

    model_config = ConfigDict(from_attributes=True)


class DatasetPreview(BaseModel):
    """Dataset preview with sample rows."""

    dataset_id: UUID
    columns: list[str]
    sample_rows: list[dict[str, Any]]
    total_rows: int


# Detection Schemas
class DetectionReport(BaseModel):
    """Report of sensitive data detection."""

    dataset_id: UUID
    columns: dict[str, ColumnClassification]
    overall_risk_score: float = Field(ge=0, le=100)
    summary: dict[str, int]  # Count by sensitivity type


# Anonymization Schemas
class AnonymizationConfig(BaseModel):
    """Configuration for anonymizing a single column."""

    column_name: str
    technique: AnonymizationTechnique
    params: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "column_name": "email",
                "technique": "masking",
                "params": {"visible_chars": 2}
            }
        }
    )


class AnonymizationRequest(BaseModel):
    """Request to anonymize a dataset."""

    dataset_id: UUID
    config: list[AnonymizationConfig]


class TransformationDetail(BaseModel):
    """Details of a single transformation."""

    column_name: str
    technique: AnonymizationTechnique
    params: dict[str, Any]
    values_affected: int
    sample_transformations: Optional[list[dict[str, Any]]] = None


class AnonymizationResponse(BaseModel):
    """Response after anonymization."""

    job_id: UUID
    anonymized_dataset_id: UUID
    transformations: list[TransformationDetail]
    processing_time_seconds: float
    status: JobStatus


# Risk Assessment Schemas
class RiskScore(BaseModel):
    """Risk score for a single criterion."""

    score: float = Field(ge=0, le=100)
    level: RiskLevel
    justification: str
    affected_columns: list[str] = []


class RiskAssessmentResponse(BaseModel):
    """Complete risk assessment response."""

    dataset_id: UUID
    assessed_at: datetime

    # Three Law 25 criteria
    individualization: RiskScore
    correlation: RiskScore
    inference: RiskScore

    # Overall assessment
    overall_score: float = Field(ge=0, le=100)
    overall_level: RiskLevel
    is_loi25_compliant: bool

    recommendations: list[str]
    details: Optional[dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


# Report Schemas
class ReportRequest(BaseModel):
    """Request for generating a compliance report."""

    dataset_id: UUID
    include_charts: bool = True
    language: str = "fr"  # French by default for Quebec Law 25


# Health Check
class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    service: str
    version: str
