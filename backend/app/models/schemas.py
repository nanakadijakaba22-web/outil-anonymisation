"""
Pydantic models for request/response validation and serialization.
"""
from datetime import datetime
from enum import Enum
from typing import Any, Optional, List, Dict, Union
from uuid import UUID

import numpy as np
from pydantic import BaseModel, Field, ConfigDict, model_validator


def convert_numpy(obj: Any) -> Any:
    """Helper to convert NumPy types to standard Python types recursively."""
    if obj is None:
        return None
    
    # Handle Pydantic models (nested)
    if hasattr(obj, "model_dump"):
        return convert_numpy(obj.model_dump())
        
    if isinstance(obj, dict):
        return {k: convert_numpy(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple, set)):
        return [convert_numpy(v) for v in obj]
    elif isinstance(obj, (np.int64, np.int32, np.int16, np.int8, np.integer)):
        return int(obj)
    elif isinstance(obj, (np.float64, np.float32, np.float16, np.floating)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return convert_numpy(obj.tolist())
    elif isinstance(obj, np.bool_):
        return bool(obj)
    return obj


class BaseSchema(BaseModel):
    """Base schema that handles NumPy type serialization automatically."""
    
    @model_validator(mode="after")
    def handle_numpy_types(self) -> "BaseSchema":
        """Convert all NumPy types in the model to standard Python types."""
        # Convert NumPy types in all fields, including nested ones
        for field_name in self.model_fields:
            try:
                value = getattr(self, field_name)
                if value is not None:
                    new_value = convert_numpy(value)
                    # For Pydantic models, we might need to update the field if it changed
                    if new_value is not value:
                        setattr(self, field_name, new_value)
            except Exception as e:
                # Fallback: just log and continue
                print(f"Warning: Failed to convert field {field_name}: {e}")
        return self


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
class ColumnInfo(BaseSchema):
    """Information about a dataset column."""

    name: str
    position: int
    data_type: str
    sensitivity_type: Optional[DataType] = None
    category: Optional[Category] = None
    confidence: Optional[float] = None
    null_count: int = 0
    unique_count: int = 0
    sample_values: Optional[List[Any]] = None

    model_config = ConfigDict(from_attributes=True)


class ColumnClassification(BaseSchema):
    """Classification result for a column."""

    column_name: str
    sensitivity_type: DataType
    category: Category
    confidence: float = Field(ge=0, le=100, description="Confidence score 0-100")
    justification: str
    suggested_config: Optional["AnonymizationConfig"] = None


class AnonymizationConfig(BaseSchema):
    """Configuration for anonymizing a single column."""

    column_name: str
    technique: AnonymizationTechnique
    params: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "column_name": "email",
                "technique": "masking",
                "params": {"visible_chars": 2}
            }
        }
    )


class ColumnSensitivityUpdate(BaseSchema):
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


class BulkSensitivityUpdate(BaseSchema):
    """Schema for bulk updating multiple columns' sensitivity."""

    updates: Dict[str, ColumnSensitivityUpdate] = Field(
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
class DatasetCreate(BaseSchema):
    """Schema for dataset creation (internal use)."""

    filename: str
    file_size: int
    file_path: str
    row_count: int
    column_count: int
    encoding: str = "utf-8"
    delimiter: str = ","


class DatasetResponse(BaseSchema):
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
    columns: List[ColumnInfo] = []

    model_config = ConfigDict(from_attributes=True)


class DatasetPreview(BaseSchema):
    """Dataset preview with sample rows."""

    dataset_id: UUID
    columns: List[str]
    sample_rows: List[Dict[str, Any]]
    total_rows: int


# Detection Schemas
class DetectionReport(BaseSchema):
    """Report of sensitive data detection."""

    dataset_id: UUID
    columns: Dict[str, ColumnClassification]
    overall_risk_score: float = Field(ge=0, le=100)
    summary: Dict[str, int]  # Count by sensitivity type


# Anonymization Schemas
class AnonymizationRequest(BaseSchema):
    """Request to anonymize a dataset."""

    dataset_id: UUID
    config: List[AnonymizationConfig]


class TransformationDetail(BaseSchema):
    """Details of a single transformation."""

    column_name: str
    technique: AnonymizationTechnique
    params: Dict[str, Any]
    values_affected: int
    sample_transformations: Optional[List[Dict[str, Any]]] = None


class AnonymizationResponse(BaseSchema):
    """Response after anonymization."""

    job_id: UUID
    anonymized_dataset_id: UUID
    transformations: List[TransformationDetail]
    processing_time_seconds: float
    status: JobStatus


# Risk Assessment Schemas
class RiskScore(BaseSchema):
    """Risk score for a single criterion."""

    score: float = Field(ge=0, le=100)
    level: RiskLevel
    justification: str
    affected_columns: List[str] = []


class RiskAssessmentResponse(BaseSchema):
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

    recommendations: List[str]
    details: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


# Report Schemas
class ReportRequest(BaseSchema):
    """Request for generating a compliance report."""

    dataset_id: UUID
    include_charts: bool = True
    language: str = "fr"  # French by default for Quebec Law 25


# Health Check
class HealthResponse(BaseSchema):
    """Health check response."""

    status: str
    service: str
    version: str


# Authentication Schemas
class UserBase(BaseSchema):
    """Base user schema with common fields."""

    email: str = Field(..., description="User email address", max_length=255)
    full_name: Optional[str] = Field(None, description="User full name", max_length=255)


class UserCreate(UserBase):
    """Schema for user registration."""

    password: str = Field(..., min_length=8, description="User password (min 8 characters)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "user@example.com",
                "full_name": "Jean Tremblay",
                "password": "SecurePassword123!"
            }
        }
    )


class UserLogin(BaseSchema):
    """Schema for user login."""

    email: str = Field(..., description="User email address")
    password: str = Field(..., description="User password")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "user@example.com",
                "password": "SecurePassword123!"
            }
        }
    )


class UserResponse(UserBase):
    """Schema for user response (excludes password)."""

    id: UUID
    is_active: bool
    is_superuser: bool
    created_at: datetime
    last_login: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class Token(BaseSchema):
    """JWT token response."""

    access_token: str
    token_type: str = "bearer"


class TokenData(BaseSchema):
    """Data stored in JWT token."""

    email: Optional[str] = None
    user_id: Optional[UUID] = None
