"""
SQLAlchemy ORM models for database tables.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.json_utils import json_dumps


def utc_now():
    """Return current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class RobustJSON(JSON):
    """JSON type that handles JSON serialization with shared encoder."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.json_dumps = json_dumps


class Dataset(Base):
    """Stores metadata about uploaded CSV datasets."""

    __tablename__ = "datasets"
    __table_args__ = {"extend_existing": True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=False)
    file_path = Column(String(512), nullable=False)
    row_count = Column(Integer, nullable=False)
    column_count = Column(Integer, nullable=False)
    upload_date = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    risk_score = Column(Float, nullable=True)
    is_loi25_compliant = Column(Boolean, default=False)

    is_anonymized = Column(Boolean, default=False)
    parent_dataset_id = Column(UUID(as_uuid=True), ForeignKey("datasets.id"), nullable=True)

    encoding = Column(String(50), default="utf-8")
    delimiter = Column(String(5), default=",")

    columns = relationship("DatasetColumn", back_populates="dataset", cascade="all, delete-orphan")
    anonymization_jobs = relationship(
        "AnonymizationJob",
        back_populates="dataset",
        foreign_keys="AnonymizationJob.dataset_id",
        cascade="all, delete-orphan",
    )
    parent_dataset = relationship("Dataset", remote_side=[id], uselist=False)

    def __repr__(self):
        return f"<Dataset(id={self.id}, filename={self.filename})>"


class DatasetColumn(Base):
    """Stores information about each column in a dataset."""

    __tablename__ = "dataset_columns"
    __table_args__ = {"extend_existing": True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_id = Column(UUID(as_uuid=True), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)

    name = Column(String(255), nullable=False)
    position = Column(Integer, nullable=False)
    data_type = Column(String(50), nullable=False)

    sensitivity_type = Column(String(50), nullable=True)
    category = Column(String(50), nullable=True)
    confidence = Column(Float, nullable=True)

    null_count = Column(Integer, default=0)
    unique_count = Column(Integer, default=0)
    sample_values = Column(RobustJSON, nullable=True)

    dataset = relationship("Dataset", back_populates="columns")

    def __repr__(self):
        return f"<DatasetColumn(name={self.name}, type={self.sensitivity_type})>"


class AnonymizationJob(Base):
    """Tracks anonymization operations performed on datasets."""

    __tablename__ = "anonymization_jobs"
    __table_args__ = {"extend_existing": True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_id = Column(UUID(as_uuid=True), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(20), default="pending")

    config = Column(RobustJSON, nullable=False)

    output_dataset_id = Column(UUID(as_uuid=True), ForeignKey("datasets.id"), nullable=True)
    error_message = Column(Text, nullable=True)

    processing_time_seconds = Column(Float, nullable=True)
    rows_processed = Column(Integer, default=0)

    dataset = relationship("Dataset", back_populates="anonymization_jobs", foreign_keys=[dataset_id])
    transformation_logs = relationship("TransformationLog", back_populates="job", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<AnonymizationJob(id={self.id}, status={self.status})>"


class TransformationLog(Base):
    """Audit trail of transformations applied to data."""

    __tablename__ = "transformation_logs"
    __table_args__ = {"extend_existing": True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("anonymization_jobs.id", ondelete="CASCADE"), nullable=False)

    column_name = Column(String(255), nullable=False)
    technique = Column(String(50), nullable=False)

    params = Column(RobustJSON, nullable=True)

    values_affected = Column(Integer, nullable=False)
    timestamp = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    sample_transformations = Column(RobustJSON, nullable=True)

    job = relationship("AnonymizationJob", back_populates="transformation_logs")

    def __repr__(self):
        return f"<TransformationLog(column={self.column_name}, technique={self.technique})>"


class VerificationLog(Base):
    """Stores post-anonymization verification results."""

    __tablename__ = "verification_logs"
    __table_args__ = {"extend_existing": True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("anonymization_jobs.id", ondelete="CASCADE"), nullable=False)
    dataset_id = Column(UUID(as_uuid=True), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)

    verified_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    passed = Column(Boolean, nullable=False)
    failure_reason = Column(Text, nullable=True)

    direct_ids_found = Column(RobustJSON, nullable=True)
    k_value = Column(Integer, nullable=True)
    k_violations_percentage = Column(Float, nullable=True)
    overall_risk_score = Column(Float, nullable=False)

    recommendations = Column(RobustJSON, nullable=True)

    dataset = relationship("Dataset")

    def __repr__(self):
        status = "PASSED" if self.passed else "FAILED"
        return f"<VerificationLog(dataset_id={self.dataset_id}, status={status})>"


class RiskAssessment(Base):
    """Stores risk assessment results for datasets."""

    __tablename__ = "risk_assessments"
    __table_args__ = {"extend_existing": True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_id = Column(UUID(as_uuid=True), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)

    assessed_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    individualization_score = Column(Float, nullable=False)
    individualization_level = Column(String(20), nullable=False)

    correlation_score = Column(Float, nullable=False)
    correlation_level = Column(String(20), nullable=False)

    inference_score = Column(Float, nullable=False)
    inference_level = Column(String(20), nullable=False)

    k_anonymity_value = Column(Integer, nullable=True)
    k_anonymity_violations = Column(Float, nullable=True)

    overall_score = Column(Float, nullable=False)
    overall_level = Column(String(20), nullable=False)
    is_loi25_compliant = Column(Boolean, nullable=False)

    details = Column(RobustJSON, nullable=True)
    recommendations = Column(RobustJSON, nullable=True)
    visualization_data = Column(RobustJSON, nullable=True)

    dataset = relationship("Dataset")

    def __repr__(self):
        return f"<RiskAssessment(dataset_id={self.dataset_id}, overall={self.overall_level})>"


class SuppressedColumn(Base):
    """Stores audit trail for suppressed columns."""

    __tablename__ = "suppressed_columns"
    __table_args__ = {"extend_existing": True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("anonymization_jobs.id", ondelete="CASCADE"), nullable=False)
    dataset_id = Column(UUID(as_uuid=True), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)

    column_name = Column(String(255), nullable=False)
    column_position = Column(Integer, nullable=False)
    data_type = Column(String(50), nullable=False)

    sensitivity_type = Column(String(50), nullable=True)
    sensitivity_category = Column(String(50), nullable=True)

    row_count = Column(Integer, nullable=False)
    unique_count = Column(Integer, nullable=True)
    null_count = Column(Integer, nullable=True)

    sample_values = Column(RobustJSON, nullable=True)

    suppressed_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    reason = Column(Text, nullable=True)

    job = relationship("AnonymizationJob")
    dataset = relationship("Dataset")

    def __repr__(self):
        return f"<SuppressedColumn(column={self.column_name}, job_id={self.job_id})>"


class User(Base):
    """Stores user accounts for authentication and authorization."""

    __tablename__ = "users"
    __table_args__ = {"extend_existing": True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)

    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    last_login = Column(DateTime(timezone=True), nullable=True)

    full_name = Column(String(255), nullable=True)

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, is_active={self.is_active})>"