"""
SQLAlchemy ORM models for database tables.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, Enum, Float, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


def utc_now():
    """Return current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class Dataset(Base):
    """
    Stores metadata about uploaded CSV datasets.
    """

    __tablename__ = "datasets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=False)  # Size in bytes
    file_path = Column(String(512), nullable=False)  # Path to stored file
    row_count = Column(Integer, nullable=False)
    column_count = Column(Integer, nullable=False)
    upload_date = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Risk assessment
    risk_score = Column(Float, nullable=True)  # Overall risk score (0-100)
    is_loi25_compliant = Column(Boolean, default=False)

    # Anonymization status
    is_anonymized = Column(Boolean, default=False)
    parent_dataset_id = Column(UUID(as_uuid=True), ForeignKey("datasets.id"), nullable=True)

    # Metadata
    encoding = Column(String(50), default="utf-8")
    delimiter = Column(String(5), default=",")

    # Relationships
    columns = relationship("DatasetColumn", back_populates="dataset", cascade="all, delete-orphan")
    anonymization_jobs = relationship(
        "AnonymizationJob",
        back_populates="dataset",
        foreign_keys="AnonymizationJob.dataset_id",
        cascade="all, delete-orphan"
    )
    parent_dataset = relationship("Dataset", remote_side=[id], uselist=False)

    def __repr__(self):
        return f"<Dataset(id={self.id}, filename={self.filename})>"


class DatasetColumn(Base):
    """
    Stores information about each column in a dataset.
    """

    __tablename__ = "dataset_columns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_id = Column(UUID(as_uuid=True), ForeignKey("datasets.id"), nullable=False)

    # Column information
    name = Column(String(255), nullable=False)
    position = Column(Integer, nullable=False)  # Column index in CSV
    data_type = Column(String(50), nullable=False)  # pandas dtype

    # Sensitive data classification
    sensitivity_type = Column(
        String(50),
        nullable=True
    )  # direct_identifier, quasi_identifier, sensitive, non_sensitive

    category = Column(String(50), nullable=True)  # personal, financial, health, etc.
    confidence = Column(Float, nullable=True)  # Detection confidence (0-100)

    # Statistical metadata
    null_count = Column(Integer, default=0)
    unique_count = Column(Integer, default=0)
    sample_values = Column(JSON, nullable=True)  # List of sample values

    # Relationships
    dataset = relationship("Dataset", back_populates="columns")

    def __repr__(self):
        return f"<DatasetColumn(name={self.name}, type={self.sensitivity_type})>"


class AnonymizationJob(Base):
    """
    Tracks anonymization operations performed on datasets.
    """

    __tablename__ = "anonymization_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_id = Column(UUID(as_uuid=True), ForeignKey("datasets.id"), nullable=False)

    # Job information
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(
        String(20),
        default="pending"
    )  # pending, processing, completed, failed

    # Configuration
    config = Column(JSON, nullable=False)  # Anonymization configuration per column

    # Results
    output_dataset_id = Column(UUID(as_uuid=True), ForeignKey("datasets.id"), nullable=True)
    error_message = Column(Text, nullable=True)

    # Metrics
    processing_time_seconds = Column(Float, nullable=True)
    rows_processed = Column(Integer, default=0)

    # Relationships
    dataset = relationship("Dataset", back_populates="anonymization_jobs", foreign_keys=[dataset_id])
    transformation_logs = relationship("TransformationLog", back_populates="job", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<AnonymizationJob(id={self.id}, status={self.status})>"


class TransformationLog(Base):
    """
    Audit trail of transformations applied to data.
    """

    __tablename__ = "transformation_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("anonymization_jobs.id"), nullable=False)

    # Transformation details
    column_name = Column(String(255), nullable=False)
    technique = Column(
        String(50),
        nullable=False
    )  # masking, generalization, suppression, pseudonymization

    params = Column(JSON, nullable=True)  # Technique-specific parameters

    # Statistics
    values_affected = Column(Integer, nullable=False)
    timestamp = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Sample transformations (for reporting)
    sample_transformations = Column(JSON, nullable=True)  # [{original: x, anonymized: y}, ...]

    # Relationships
    job = relationship("AnonymizationJob", back_populates="transformation_logs")

    def __repr__(self):
        return f"<TransformationLog(column={self.column_name}, technique={self.technique})>"


class VerificationLog(Base):
    """
    Stores post-anonymization verification results.

    Critical safety check to ensure anonymization was effective.
    """

    __tablename__ = "verification_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("anonymization_jobs.id"), nullable=False)
    dataset_id = Column(UUID(as_uuid=True), ForeignKey("datasets.id"), nullable=False)

    # Verification timestamp
    verified_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Pass/fail status
    passed = Column(Boolean, nullable=False)
    failure_reason = Column(Text, nullable=True)

    # Detected issues
    direct_ids_found = Column(JSON, nullable=True)  # List of column names
    k_value = Column(Integer, nullable=True)
    k_violations_percentage = Column(Float, nullable=True)
    overall_risk_score = Column(Float, nullable=False)

    # Recommendations
    recommendations = Column(JSON, nullable=True)  # List of fix recommendations

    # Relationships
    dataset = relationship("Dataset")

    def __repr__(self):
        status = "PASSED" if self.passed else "FAILED"
        return f"<VerificationLog(dataset_id={self.dataset_id}, status={status})>"


class RiskAssessment(Base):
    """
    Stores risk assessment results for datasets.
    """

    __tablename__ = "risk_assessments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_id = Column(UUID(as_uuid=True), ForeignKey("datasets.id"), nullable=False)

    # Assessment timestamp
    assessed_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Law 25 risk criteria
    individualization_score = Column(Float, nullable=False)  # 0-100
    individualization_level = Column(String(20), nullable=False)  # faible, moyen, élevé

    correlation_score = Column(Float, nullable=False)  # 0-100
    correlation_level = Column(String(20), nullable=False)

    inference_score = Column(Float, nullable=False)  # 0-100
    inference_level = Column(String(20), nullable=False)

    # k-anonymity metrics (Sweeney, 2002)
    k_anonymity_value = Column(Integer, nullable=True)  # Minimum group size (k)
    k_anonymity_violations = Column(Float, nullable=True)  # % of records in groups < 5

    # Overall assessment
    overall_score = Column(Float, nullable=False)
    overall_level = Column(String(20), nullable=False)
    is_loi25_compliant = Column(Boolean, nullable=False)

    # Details
    details = Column(JSON, nullable=True)  # Detailed analysis per criterion
    recommendations = Column(JSON, nullable=True)  # List of recommendations

    # Visualization data (Phase 3: Enhanced data visualization)
    visualization_data = Column(JSON, nullable=True)  # Compact summary for charts/graphs

    # Relationships
    dataset = relationship("Dataset")

    def __repr__(self):
        return f"<RiskAssessment(dataset_id={self.dataset_id}, overall={self.overall_level})>"


class SuppressedColumn(Base):
    """
    Stores audit trail for suppressed (deleted) columns.

    Critical for compliance: When columns are completely removed,
    we must maintain a record of what was deleted, when, and why.
    """

    __tablename__ = "suppressed_columns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("anonymization_jobs.id"), nullable=False)
    dataset_id = Column(UUID(as_uuid=True), ForeignKey("datasets.id"), nullable=False)

    # Column information
    column_name = Column(String(255), nullable=False)
    column_position = Column(Integer, nullable=False)  # Original position in dataset
    data_type = Column(String(50), nullable=False)  # Original data type

    # Sensitivity information (why was it suppressed?)
    sensitivity_type = Column(String(50), nullable=True)  # direct_identifier, etc.
    sensitivity_category = Column(String(50), nullable=True)  # personal, financial, etc.

    # Statistics (before suppression)
    row_count = Column(Integer, nullable=False)  # How many values were deleted
    unique_count = Column(Integer, nullable=True)  # How many unique values
    null_count = Column(Integer, nullable=True)  # How many null values

    # Sample values (for audit, encrypted/hashed in production)
    sample_values = Column(JSON, nullable=True)  # First 3-5 values (sanitized)

    # Metadata
    suppressed_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    reason = Column(Text, nullable=True)  # Justification for suppression

    # Relationships
    job = relationship("AnonymizationJob")
    dataset = relationship("Dataset")

    def __repr__(self):
        return f"<SuppressedColumn(column={self.column_name}, job_id={self.job_id})>"


class User(Base):
    """
    Stores user accounts for authentication and authorization.

    Compliant with Quebec Law 25 for personal information protection.
    """

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)

    # Account status
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    last_login = Column(DateTime(timezone=True), nullable=True)

    # Profile information (optional)
    full_name = Column(String(255), nullable=True)

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, is_active={self.is_active})>"
