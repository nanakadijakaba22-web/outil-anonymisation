"""
Anonymization service implementing 5 techniques for Quebec Law 25 compliance.

Techniques:
1. Masking - Partial character replacement (emails, phones)
2. Generalization - Replace with broader categories (ages, incomes)
3. Suppression - Complete column removal (NAS, SSN)
4. Differential Privacy - Mathematical noise addition for formal guarantees (OPTIONAL)
"""
import hashlib
import logging
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

    

        elif technique == AnonymizationTechnique.DIFFERENTIAL_PRIVACY:
            # DP only for numeric columns
            if column not in df.columns:
                raise ValueError(f"Colonne introuvable: {column}")

            # If column is text -> DP not allowed (would crash)
            if not pd.api.types.is_numeric_dtype(df[column]):
                raise ValueError(
                    f"Confidentialité différentielle impossible sur colonne non numérique: {column}"
                )

            # IMPORTANT: _add_differential_privacy returns (df, metadata)
            df, dp_metadata = self._add_differential_privacy(df, column, params)
            params["dp_metadata"] = dp_metadata  # optional


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

        AUTOMATIC TYPE DETECTION:
          - Text (string/object) → Prefix mode (garde les N premiers caractères)
          - Numeric (int/float) → Tranches mode (divise en intervalles)
          - Dates (datetime) → Range d'années mode (extrait l'année)

        Params:
          - bins: Nombre de tranches pour les numériques (défaut: 5)
          - prefix_length: Longueur du préfixe pour le texte (défaut: 3)
          - range_size: Taille des tranches pour les numériques (optionnel, alternative à bins)
        """

        # === DÉTECTION AUTOMATIQUE DU TYPE ===

        # 1. Vérifier si c'est une date (datetime)
        if pd.api.types.is_datetime64_any_dtype(df[column]):
            logger.info(f"Colonne '{column}': Type DATE détecté → Mode range d'années")
            df[column] = pd.to_datetime(df[column], errors="coerce").dt.year
            return df

        # 2. Essayer de détecter les dates sous forme de texte
        if df[column].dtype == "object" or pd.api.types.is_string_dtype(df[column]):
            # Échantillon pour test de conversion date
            sample = df[column].dropna().head(20)
            try:
                # Tenter conversion en date
                date_conversion = pd.to_datetime(sample, errors="coerce")
                # Si au moins 70% des valeurs sont des dates valides
                if date_conversion.notna().sum() / len(sample) >= 0.7:
                    logger.info(f"Colonne '{column}': Dates textuelles détectées → Mode range d'années")
                    df[column] = pd.to_datetime(df[column], errors="coerce").dt.year
                    return df
            except (ValueError, TypeError):
                pass  # Pas une date, continuer

        # 3. Vérifier si c'est numérique
        if pd.api.types.is_numeric_dtype(df[column]):
            logger.info(f"Colonne '{column}': Type NUMÉRIQUE détecté → Mode tranches")

            # Option A: Utiliser bins (nombre de tranches)
            if "bins" in params or "range_size" not in params:
                bins = int(params.get("bins", 5))

                # Créer les tranches avec labels descriptifs
                binned = pd.cut(df[column], bins=bins, include_lowest=True, duplicates="drop")
                df[column] = binned.astype(str)
                return df

            # Option B: Utiliser range_size (largeur fixe)
            else:
                range_size = int(params.get("range_size", 10))
                df[column] = df[column].apply(
                    lambda x: self._generalize_to_range(x, range_size) if pd.notna(x) else x
                )
                return df

        # 4. Par défaut: Texte → Mode préfixe
        logger.info(f"Colonne '{column}': Type TEXTE détecté → Mode préfixe")
        prefix_length = int(params.get("prefix_length", 3))
        df[column] = df[column].apply(
            lambda x: self._generalize_text_prefix(x, prefix_length) if pd.notna(x) else x
        )

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

    def _generalize_text_prefix(self, value: Any, prefix_length: int) -> str:
        """
        Generalize text by keeping prefix and replacing rest with asterisks.
        
        Examples:
            "G1X 3J4" -> "G1X ***" (prefix_length=3)
            "Montreal" -> "Mon ***" (prefix_length=3)
        """
        if pd.isna(value):
            return value
        
        text_str = str(value).strip()
        
        # Keep prefix and replace rest with asterisks
        if len(text_str) > prefix_length:
            prefix = text_str[:prefix_length]
            return f"{prefix} ***"
        else:
            # If too short, just return as is
            return text_str

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

    

    def _add_differential_privacy(
        self,
        df: pd.DataFrame,
        column: str,
        params: Dict[str, Any]
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
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

        return df, metadata

    async def auto_anonymize(self, dataset_id: UUID) -> AnonymizationResponse:
        """
        Applique automatiquement les techniques d'anonymisation selon la sensibilité détectée.

        Cette méthode exécute d'abord une détection des données sensibles, puis applique
        automatiquement les techniques d'anonymisation appropriées selon les règles suivantes:

        RÈGLES D'ANONYMISATION 100% AUTOMATIQUES (l'utilisateur ne choisit rien):

        1. IDENTIFIANTS DIRECTS → SUPPRESSION (suppression complète de la colonne)
           - NAS, SSN, email, téléphone, nom, prénom, carte de crédit, etc.
           - TOUS les identifiants directs sont supprimés, sans exception

        2. DONNÉES SENSIBLES → Selon le type de données:
           - Colonnes NUMÉRIQUES: DIFFERENTIAL_PRIVACY (epsilon=0.1, mechanism=laplace)
           - Colonnes NON-NUMÉRIQUES: GENERALIZATION (prefix_length=3)

        3. QUASI-IDENTIFIANTS → GENERALIZATION selon le type:
           - Colonnes DATE/DATETIME: mode "year" (extrait l'année uniquement)
           - Colonnes NUMÉRIQUES: mode "bins" (divise en 5 tranches)
           - Colonnes TEXTE: mode "prefix" (garde les 3 premiers caractères)

        Args:
            dataset_id: UUID of the dataset to auto-anonymize

        Returns:
            AnonymizationResponse with job details, new dataset ID, and applied techniques
        """
        from app.services.ai_enhanced_detector import AIEnhancedDetector

        # 1. Charger le dataset en utilisant le service d'ingestion
        df = self.ingestion_service.load_dataframe(dataset_id)

        # 2. Exécuter la détection (avec IA si disponible)
        detector = AIEnhancedDetector(self.db)
        detection_report = await detector.analyze_dataset(dataset_id)

        # 3. Construire la configuration automatique
        configs: List[AnonymizationConfig] = []
        applied_techniques: Dict[str, Any] = {}

        for column_name, classification in detection_report.columns.items():
            config = None

            # =========================================================================
            # RÈGLE 1: IDENTIFIANTS DIRECTS → SUPPRESSION (toujours, sans exception)
            # =========================================================================
            if classification.sensitivity_type.value == "direct_identifier":
                # TOUS les identifiants directs sont SUPPRIMÉS (colonne retirée)
                # Cela inclut: NAS, SSN, email, téléphone, nom, prénom, carte de crédit, etc.
                config = AnonymizationConfig(
                    column_name=column_name,
                    technique=AnonymizationTechnique.SUPPRESSION,
                    params={}
                )
                logger.info(
                    f"Identifiant direct '{column_name}' → SUPPRESSION "
                    f"(justification: {classification.justification})"
                )

            # =========================================================================
            # RÈGLE 2: DONNÉES SENSIBLES → DP (numérique) ou GENERALIZATION (texte)
            # =========================================================================
            elif classification.sensitivity_type.value == "sensitive":
                if column_name in df.columns and pd.api.types.is_numeric_dtype(df[column_name]):
                    # Données sensibles NUMÉRIQUES: Confidentialité différentielle
                    # epsilon=0.1 = protection FORTE (très bruité mais très privé)
                    config = AnonymizationConfig(
                        column_name=column_name,
                        technique=AnonymizationTechnique.DIFFERENTIAL_PRIVACY,
                        params={"epsilon": 0.1, "mechanism": "laplace"}
                    )
                    logger.info(
                        f"Donnée sensible numérique '{column_name}' → DIFFERENTIAL_PRIVACY "
                        f"(epsilon=0.1, mechanism=laplace)"
                    )
                else:
                    # Données sensibles NON-NUMÉRIQUES: Généralisation par préfixe
                    config = AnonymizationConfig(
                        column_name=column_name,
                        technique=AnonymizationTechnique.GENERALIZATION,
                        params={"prefix_length": 3}
                    )
                    logger.info(
                        f"Donnée sensible texte '{column_name}' → GENERALIZATION "
                        f"(prefix_length=3)"
                    )

            # =========================================================================
            # RÈGLE 3: QUASI-IDENTIFIANTS → GENERALIZATION selon le type de données
            # =========================================================================
            elif classification.sensitivity_type.value == "quasi_identifier":
                if column_name in df.columns:
                    col_data = df[column_name]

                    # 3a. Colonnes DATE/DATETIME → Généralisation par année
                    if pd.api.types.is_datetime64_any_dtype(col_data):
                        config = AnonymizationConfig(
                            column_name=column_name,
                            technique=AnonymizationTechnique.GENERALIZATION,
                            params={"mode": "year"}
                        )
                        logger.info(
                            f"Quasi-identifiant date '{column_name}' → GENERALIZATION (mode=year)"
                        )

                    # 3b. Détecter les dates sous forme de texte
                    elif col_data.dtype == "object" or pd.api.types.is_string_dtype(col_data):
                        sample = col_data.dropna().head(10)
                        is_date_string = False
                        if len(sample) > 0:
                            try:
                                date_conversion = pd.to_datetime(sample, errors="coerce")
                                if date_conversion.notna().sum() / len(sample) >= 0.7:
                                    is_date_string = True
                            except (ValueError, TypeError):
                                pass

                        if is_date_string:
                            config = AnonymizationConfig(
                                column_name=column_name,
                                technique=AnonymizationTechnique.GENERALIZATION,
                                params={"mode": "year"}
                            )
                            logger.info(
                                f"Quasi-identifiant date (texte) '{column_name}' → GENERALIZATION (mode=year)"
                            )
                        else:
                            # 3c. Colonnes TEXTE → Généralisation par préfixe
                            config = AnonymizationConfig(
                                column_name=column_name,
                                technique=AnonymizationTechnique.GENERALIZATION,
                                params={"prefix_length": 3}
                            )
                            logger.info(
                                f"Quasi-identifiant texte '{column_name}' → GENERALIZATION (prefix_length=3)"
                            )

                    # 3d. Colonnes NUMÉRIQUES → Généralisation par tranches (bins)
                    elif pd.api.types.is_numeric_dtype(col_data):
                        config = AnonymizationConfig(
                            column_name=column_name,
                            technique=AnonymizationTechnique.GENERALIZATION,
                            params={"bins": 5}
                        )
                        logger.info(
                            f"Quasi-identifiant numérique '{column_name}' → GENERALIZATION (bins=5)"
                        )

                    # 3e. Fallback: tout autre type → Généralisation par préfixe
                    else:
                        config = AnonymizationConfig(
                            column_name=column_name,
                            technique=AnonymizationTechnique.GENERALIZATION,
                            params={"prefix_length": 3}
                        )
                        logger.info(
                            f"Quasi-identifiant (autre) '{column_name}' → GENERALIZATION (prefix_length=3)"
                        )

            # Ajouter la configuration si définie
            if config:
                configs.append(config)
                applied_techniques[column_name] = {
                    "technique": config.technique.value,
                    "params": config.params,
                    "reason": classification.sensitivity_type.value,
                    "confidence": classification.confidence
                }

        # 4. Appliquer l'anonymisation en utilisant la méthode existante
        if configs:
            result = await self.anonymize_dataset(dataset_id, configs)
            # Add applied techniques info to the result as extra metadata
            logger.info(
                f"Auto-anonymization completed for dataset {dataset_id}. "
                f"Applied {len(configs)} transformations: {list(applied_techniques.keys())}"
            )
            return result
        else:
            # No sensitive columns found, return a response indicating no changes
            logger.info(f"No sensitive columns detected in dataset {dataset_id}, no anonymization applied")
            raise ValueError("Aucune colonne sensible détectée nécessitant une anonymisation")

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
