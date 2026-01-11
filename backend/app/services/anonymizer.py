"""
Anonymization service implementing 5 techniques for Quebec Law 25 compliance.

Techniques:
1. Masking - Partial character replacement (emails, phones)
2. Generalization - Replace with broader categories (ages, incomes)
3. Suppression - Complete column removal (NAS, SSN)
4. Pseudonymization - Consistent fake ID generation (names)
5. Differential Privacy - Mathematical noise addition for formal guarantees (OPTIONAL)
"""
import hmac
import hashlib
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple
from uuid import UUID

import pandas as pd
from sqlalchemy.orm import Session

from app.models.database import (
    Dataset,
    AnonymizationJob,
    TransformationLog,
    SuppressedColumn,
)
from app.models.schemas import (
    AnonymizationConfig,
    AnonymizationTechnique,
    AnonymizationResponse,
    TransformationDetail,
    JobStatus,
    DatasetCreate,
)
from app.services.data_ingestion import DataIngestionService
from app.services.differential_privacy import DifferentialPrivacyEngine, DPMechanism

logger = logging.getLogger(__name__)


class Anonymizer:
    """
    Anonymization engine implementing Law 25 compliant techniques.
    """

    def __init__(self, db: Session):
        self.db = db
        self.ingestion_service = DataIngestionService(db)
        # Cache for pseudonymization to ensure consistency
        self._pseudonym_cache: Dict[str, str] = {}

    async def anonymize_dataset(
        self,
        dataset_id: UUID,
        config: List[AnonymizationConfig]
    ) -> AnonymizationResponse:
        """
        Anonymize a dataset using specified techniques.

        Args:
            dataset_id: UUID of the dataset to anonymize
            config: List of anonymization configurations per column

        Returns:
            AnonymizationResponse with job details and new dataset ID
        """
        start_time = datetime.now(timezone.utc)

        # Load dataset
        dataset = self.ingestion_service.get_dataset(dataset_id)
        df = self.ingestion_service.load_dataframe(dataset_id)
        original_df = df.copy()

        # Create job record
        job = AnonymizationJob(
            dataset_id=dataset_id,
            status=JobStatus.PROCESSING.value,
            config=[c.model_dump() for c in config],
        )
        self.db.add(job)
        self.db.flush()

        transformations: List[TransformationDetail] = []

        try:
            # Apply each anonymization configuration
            for conf in config:
                if conf.column_name not in df.columns:
                    continue

                # Apply technique
                df, transformation = self._apply_technique(
                    df=df,
                    original_df=original_df,
                    config=conf,
                    job_id=job.id,
                    dataset_id=dataset_id,
                )

                transformations.append(transformation)

                # Log transformation
                log = TransformationLog(
                    job_id=job.id,
                    column_name=conf.column_name,
                    technique=conf.technique.value,
                    params=conf.params,
                    values_affected=transformation.values_affected,
                    sample_transformations=transformation.sample_transformations,
                )
                self.db.add(log)

            # Save anonymized dataset
            anonymized_dataset = await self._save_anonymized_dataset(
                df=df,
                original_dataset=dataset,
                parent_id=dataset_id,
            )

            # Update job
            end_time = datetime.now(timezone.utc)
            processing_time = (end_time - start_time).total_seconds()

            job.status = JobStatus.COMPLETED.value
            job.completed_at = end_time
            job.processing_time_seconds = processing_time
            job.rows_processed = len(df)
            job.output_dataset_id = anonymized_dataset.id

            # CRITICAL: Post-anonymization verification
            # Re-run detection to ensure no direct identifiers remain
            from app.services.verification import PostAnonymizationVerifier
            verifier = PostAnonymizationVerifier(self.db)
            verification = await verifier.verify_anonymization(
                anonymized_dataset.id,
                job.id
            )

            # If verification failed, update dataset status
            if not verification.passed:
                anonymized_dataset.is_loi25_compliant = False
                anonymized_dataset.risk_score = max(verification.overall_risk_score, 25.0)

                # Add warning to job
                job.error_message = (
                    f"AVERTISSEMENT: Vérification post-anonymisation a échoué. "
                    f"{verification.failure_reason} "
                    f"Recommandations: {'; '.join(verification.recommendations[:2])}"
                )

                logger.warning(
                    f"Post-anonymization verification FAILED for job {job.id}. "
                    f"Reason: {verification.failure_reason}"
                )
            else:
                logger.info(
                    f"Post-anonymization verification PASSED for job {job.id}. "
                    f"k-anonymity: {verification.k_anonymity_value}, "
                    f"Risk: {verification.overall_risk_score:.1f}%"
                )

            self.db.commit()

            return AnonymizationResponse(
                job_id=job.id,
                anonymized_dataset_id=anonymized_dataset.id,
                transformations=transformations,
                processing_time_seconds=processing_time,
                status=JobStatus.COMPLETED,
            )

        except Exception as e:
            job.status = JobStatus.FAILED.value
            job.error_message = str(e)
            self.db.commit()
            raise

    def _apply_technique(
        self,
        df: pd.DataFrame,
        original_df: pd.DataFrame,
        config: AnonymizationConfig,
        job_id: UUID,
        dataset_id: UUID,
    ) -> Tuple[pd.DataFrame, TransformationDetail]:
        """Apply a specific anonymization technique to a column."""

        column = config.column_name
        technique = config.technique
        params = config.params

        # Get sample transformations (before/after)
        sample_before = original_df[column].head(5).tolist()

        if technique == AnonymizationTechnique.MASKING:
            df = self._mask_column(df, column, params)

        elif technique == AnonymizationTechnique.GENERALIZATION:
            df = self._generalize_column(df, column, params)

        elif technique == AnonymizationTechnique.SUPPRESSION:
            df = self._suppress_column(df, column, job_id, dataset_id)

        elif technique == AnonymizationTechnique.PSEUDONYMIZATION:
            df = self._pseudonymize_column(df, column, params)

        elif technique == AnonymizationTechnique.DIFFERENTIAL_PRIVACY:
            df = self._add_differential_privacy(df, column, params)

        # Get sample after transformations
        if column in df.columns:
            sample_after = df[column].head(5).tolist()
        else:
            sample_after = [None] * 5  # Column was suppressed

        sample_transformations = [
            {"original": str(before), "anonymized": str(after)}
            for before, after in zip(sample_before, sample_after)
        ]

        transformation = TransformationDetail(
            column_name=column,
            technique=technique,
            params=params,
            values_affected=len(original_df),
            sample_transformations=sample_transformations,
        )

        return df, transformation

    def _mask_column(
        self,
        df: pd.DataFrame,
        column: str,
        params: Dict[str, Any]
    ) -> pd.DataFrame:
        """
        Masking: Partial character replacement with type awareness.

        Params:
            visible_start: Chars to keep at start (default: 2)
            visible_end: Chars to keep at end (default: 2)
            mask_char: Character to use (default: '*')
        """
        v_start = params.get("visible_start", params.get("visible_chars", 2))
        v_end = params.get("visible_end", 2)
        mask_char = params.get("mask_char", "*")

        def mask_value(val):
            if pd.isna(val):
                return val

            val_str = str(val)

            # 1. Email masking: [token]@domain.tld or keep first/last of local
            if "@" in val_str:
                local, domain = val_str.split("@", 1)
                # Keep first letter of local, mask rest
                masked_local = local[0] + (mask_char * 5) if len(local) > 1 else mask_char * 5
                return f"{masked_local}@{domain}"

            # 2. Phone masking: keep area code only
            phone_digits = re.sub(r"\D", "", val_str)
            if len(phone_digits) >= 10:
                return f"{phone_digits[:3]}-{mask_char*3}-{mask_char*4}"

            # 3. General string masking: Keep start AND end
            if len(val_str) <= (v_start + v_end):
                return mask_char * len(val_str)
            
            return val_str[:v_start] + mask_char * 5 + val_str[-v_end:]

        df[column] = df[column].apply(mask_value)
        return df

    def _generalize_column(
        self,
        df: pd.DataFrame,
        column: str,
        params: Dict[str, Any]
    ) -> pd.DataFrame:
        """
        Generalization: Replace with broader categories.

        Params:
            method: 'range' | 'year_only' | 'prefix' | 'custom'
            range_size: For numeric ranges (default: 10)
            custom_mapping: Dict for custom mappings
        """
        method = params.get("method", "range")

        if method == "range":
            # Numeric ranges (e.g., ages, incomes)
            range_size = params.get("range_size", 10)
            df[column] = df[column].apply(
                lambda x: self._generalize_to_range(x, range_size) if pd.notna(x) else x
            )

        elif method == "year_only":
            # Dates -> Keep year only
            df[column] = pd.to_datetime(df[column], errors='coerce').dt.year

        elif method == "prefix":
            # Keep only prefix (e.g., postal code H3B 1A1 -> H3B)
            prefix_length = params.get("prefix_length", 3)
            df[column] = df[column].apply(
                lambda x: str(x)[:prefix_length] if pd.notna(x) else x
            )

        elif method == "custom":
            # Custom mapping provided by user
            mapping = params.get("custom_mapping", {})
            df[column] = df[column].map(lambda x: mapping.get(str(x), x))

        return df

    def _generalize_to_range(self, value: Any, range_size: int) -> str:
        """Convert numeric value to range string."""
        try:
            num = float(value)
            lower = int(num // range_size) * range_size
            upper = lower + range_size
            return f"{lower}-{upper}"
        except (ValueError, TypeError):
            return str(value)

    def _suppress_column(
        self,
        df: pd.DataFrame,
        column: str,
        job_id: UUID,
        dataset_id: UUID
    ) -> pd.DataFrame:
        """
        Suppression: Complete column removal with audit trail.

        CRITICAL: We must log suppressed columns for compliance and auditability.
        """
        if column not in df.columns:
            return df

        # Capture metadata BEFORE suppression
        col_data = df[column]
        col_position = df.columns.get_loc(column)
        col_dtype = str(col_data.dtype)

        # Statistics
        row_count = len(col_data)
        unique_count = int(col_data.nunique())
        null_count = int(col_data.isnull().sum())

        # Sample values (sanitized - only first 3 for audit)
        sample_values = col_data.head(3).astype(str).tolist()

        # Create audit trail record
        suppressed_record = SuppressedColumn(
            job_id=job_id,
            dataset_id=dataset_id,
            column_name=column,
            column_position=col_position,
            data_type=col_dtype,
            row_count=row_count,
            unique_count=unique_count,
            null_count=null_count,
            sample_values=sample_values,
            reason=f"Suppression technique applied to column '{column}'",
        )

        self.db.add(suppressed_record)
        self.db.flush()  # Persist immediately

        logger.info(
            f"Column '{column}' suppressed from dataset {dataset_id}. "
            f"Audit record created: {suppressed_record.id}"
        )

        # Now perform the actual suppression
        df = df.drop(columns=[column])
        return df

    def _pseudonymize_column(
        self,
        df: pd.DataFrame,
        column: str,
        params: Dict[str, Any]
    ) -> pd.DataFrame:
        """
        Pseudonymization: Consistent replacement with HMAC-SHA256.
        IMPORTANT: This is NOT anonymization, but pseudonymization (reversible if key is leaked).

        Params:
            prefix: Prefix for pseudonyms (default: "ID_")
            seed: Salt/Seed (optional, additional to secret key)
        """
        prefix = params.get("prefix", "ID_")
        seed = str(params.get("seed", "law25_default_seed"))
        
        # Get server secret key for HMAC
        secret_key = os.getenv("ANONYMIZER_SECRET_KEY", "loi25_quebec_super_secret_key_2024").encode('utf-8')

        def pseudonymize_value(val):
            if pd.isna(val):
                return val

            val_str = str(val)

            # Check cache to avoid re-computing HMAC for same values in same job
            if val_str in self._pseudonym_cache:
                return self._pseudonym_cache[val_str]

            # HMAC-SHA256 for deterministic, secure pseudonymization
            # We combine value + seed for extra entropy
            message = f"{val_str}_{seed}".encode('utf-8')
            signature = hmac.new(secret_key, message, hashlib.sha256).hexdigest()
            
            # Truncate to 12 characters for usability while maintaining high collision resistance
            hash_part = signature[:12].upper()
            pseudonym = f"{prefix}{hash_part}"

            self._pseudonym_cache[val_str] = pseudonym
            return pseudonym

        df[column] = df[column].apply(pseudonymize_value)
        return df

    def _add_differential_privacy(
        self,
        df: pd.DataFrame,
        column: str,
        params: Dict[str, Any]
    ) -> pd.DataFrame:
        """
        Differential Privacy: Add calibrated noise for formal privacy guarantees.

        IMPORTANT: This is OPTIONAL and reduces data utility. Use only when:
        - Formal mathematical privacy guarantees are required
        - Statistical analysis will be performed
        - Individual-level precision is not critical

        Params:
            epsilon: Privacy budget (default: 1.0)
                    - Strong: < 0.1 (very noisy)
                    - Moderate: 1.0 (US Census standard)
                    - Weak: > 10 (minimal noise)
            delta: Failure probability for Gaussian (default: 1e-5)
            mechanism: "laplace" (pure DP) or "gaussian" (approximate DP)
            sensitivity: Manual sensitivity override (auto-calculated if None)
            clip_to_range: Keep values in original [min, max] (default: True)
        """
        epsilon = params.get("epsilon", 1.0)
        delta = params.get("delta", 1e-5)
        mechanism_str = params.get("mechanism", "laplace")
        sensitivity = params.get("sensitivity", None)
        clip_to_range = params.get("clip_to_range", True)

        # Convert mechanism string to enum
        mechanism = DPMechanism.LAPLACE if mechanism_str == "laplace" else DPMechanism.GAUSSIAN

        # Create DP engine
        dp_engine = DifferentialPrivacyEngine(epsilon=epsilon, delta=delta)

        # Apply noise to column
        df, metadata = dp_engine.apply_to_column(
            df=df,
            column_name=column,
            mechanism=mechanism,
            sensitivity=sensitivity,
            clip_to_range=clip_to_range
        )

        logger.info(
            f"Applied differential privacy to '{column}': "
            f"mechanism={metadata['mechanism']}, ε={metadata['epsilon']}, "
            f"noise_magnitude={metadata['noise_magnitude']:.2f}"
        )

        return df

    async def _save_anonymized_dataset(
        self,
        df: pd.DataFrame,
        original_dataset: Dataset,
        parent_id: UUID,
    ) -> Dataset:
        """Save anonymized dataframe as a new dataset."""

        # Generate new filename
        new_filename = f"anonymized_{original_dataset.filename}"
        file_path = self.ingestion_service.upload_dir / f"{parent_id}_{new_filename}"

        # Save CSV
        df.to_csv(file_path, index=False)

        # Create dataset record
        dataset_create = DatasetCreate(
            filename=new_filename,
            file_size=file_path.stat().st_size,
            file_path=str(file_path),
            row_count=len(df),
            column_count=len(df.columns),
        )

        dataset = Dataset(**dataset_create.model_dump())
        dataset.is_anonymized = True
        dataset.parent_dataset_id = parent_id

        self.db.add(dataset)
        self.db.flush()

        # Create column records
        for idx, col_name in enumerate(df.columns):
            from app.models.database import DatasetColumn
            col_data = df[col_name]

            column = DatasetColumn(
                dataset_id=dataset.id,
                name=str(col_name),
                position=idx,
                data_type=str(col_data.dtype),
                null_count=int(col_data.isnull().sum()),
                unique_count=int(col_data.nunique()),
            )
            self.db.add(column)

        self.db.flush()
        return dataset
