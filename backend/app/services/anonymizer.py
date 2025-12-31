"""
Anonymization service implementing 4 techniques for Quebec Law 25 compliance.

Techniques:
1. Masking - Partial character replacement (emails, phones)
2. Generalization - Replace with broader categories (ages, incomes)
3. Suppression - Complete column removal (NAS, SSN)
4. Pseudonymization - Consistent fake ID generation (names)
"""
import hashlib
import re
from datetime import datetime
from typing import Any, Dict, List, Tuple
from uuid import UUID

import pandas as pd
from sqlalchemy.orm import Session

from app.models.database import (
    Dataset,
    AnonymizationJob,
    TransformationLog,
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
        start_time = datetime.utcnow()

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
            end_time = datetime.utcnow()
            processing_time = (end_time - start_time).total_seconds()

            job.status = JobStatus.COMPLETED.value
            job.completed_at = end_time
            job.processing_time_seconds = processing_time
            job.rows_processed = len(df)
            job.output_dataset_id = anonymized_dataset.id

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
            df = self._suppress_column(df, column)

        elif technique == AnonymizationTechnique.PSEUDONYMIZATION:
            df = self._pseudonymize_column(df, column, params)

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
        Masking: Partial character replacement.

        Params:
            visible_chars: Number of characters to keep visible at start/end (default: 2)
            mask_char: Character to use for masking (default: '*')
        """
        visible_chars = params.get("visible_chars", 2)
        mask_char = params.get("mask_char", "*")

        def mask_value(val):
            if pd.isna(val):
                return val

            val_str = str(val)

            # Email masking: keep local/domain prefixes
            if "@" in val_str:
                local, domain = val_str.split("@", 1)
                if "." in domain:
                    domain_name, tld = domain.rsplit(".", 1)
                    masked_local = self._mask_string(local, visible_chars, mask_char)
                    masked_domain = self._mask_string(domain_name, visible_chars, mask_char)
                    return f"{masked_local}@{masked_domain}.{tld}"

            # Phone masking: keep area code
            phone_match = re.match(r"^(\d{3})[-.\s]?(\d{3})[-.\s]?(\d{4})$", val_str)
            if phone_match:
                area, prefix, line = phone_match.groups()
                return f"{area}-{mask_char * 3}-{mask_char * 4}"

            # General string masking
            return self._mask_string(val_str, visible_chars, mask_char)

        df[column] = df[column].apply(mask_value)
        return df

    def _mask_string(self, s: str, visible: int, mask_char: str) -> str:
        """Helper to mask a string keeping visible characters at start."""
        if len(s) <= visible * 2:
            return mask_char * len(s)
        return s[:visible] + mask_char * (len(s) - visible)

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

    def _suppress_column(self, df: pd.DataFrame, column: str) -> pd.DataFrame:
        """
        Suppression: Complete column removal.
        """
        if column in df.columns:
            df = df.drop(columns=[column])
        return df

    def _pseudonymize_column(
        self,
        df: pd.DataFrame,
        column: str,
        params: Dict[str, Any]
    ) -> pd.DataFrame:
        """
        Pseudonymization: Consistent replacement with fake IDs.

        Params:
            prefix: Prefix for pseudonyms (default: "PERSON_")
            seed: Random seed for consistency (default: 42)
        """
        prefix = params.get("prefix", "PERSON_")
        seed = params.get("seed", 42)

        def pseudonymize_value(val):
            if pd.isna(val):
                return val

            val_str = str(val)

            # Check cache
            if val_str in self._pseudonym_cache:
                return self._pseudonym_cache[val_str]

            # Generate deterministic pseudonym using hash
            hash_input = f"{val_str}_{seed}".encode('utf-8')
            hash_hex = hashlib.sha256(hash_input).hexdigest()[:6].upper()
            pseudonym = f"{prefix}{hash_hex}"

            # Cache it
            self._pseudonym_cache[val_str] = pseudonym
            return pseudonym

        df[column] = df[column].apply(pseudonymize_value)
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
