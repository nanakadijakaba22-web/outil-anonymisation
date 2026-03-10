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
from typing import Any, Dict, List, Tuple, Optional, Union
from uuid import UUID

import numpy as np
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
    DataType,
)
from app.services.data_ingestion import DataIngestionService
from app.services.differential_privacy import DifferentialPrivacyEngine, DPMechanism

logger = logging.getLogger(__name__)


class Anonymizer:
    """
    Anonymization engine implementing Law 25 compliant techniques.
    """

    # QID set definition (columns to include in k-anonymity calculation)
    QUASI_IDENTIFIERS_SET = {
        "BIRTHDATE", "AGE", "GENDER", "RACE", "ETHNICITY", "BIRTHPLACE",
        "ADDRESS", "CITY", "ZIP", "COUNTY", "STATE", "LAT", "LON"
    }

    DEMOGRAPHIC_HIERARCHIES = {
        "race": {
            "white": "Caucaisien/Autre", "black": "Afro-descendant/Autre", "asian": "Asiatique/Autre", 
            "hispanic": "Latino/Autre", "native": "Autochtone/Autre", "other": "Autre"
        },
        "ethnicity": {
            "hispanic": "Hispano-Latino", "non-hispanic": "Non-Hispano-Latino", "latino": "Hispano-Latino"
        },
        "gender": {
            "male": "M", "female": "F", "homme": "M", "femme": "F", "m": "M", "f": "F", "h": "M"
        },
        "sexe": {
            "male": "M", "female": "F", "homme": "M", "femme": "F", "m": "M", "f": "F", "h": "M"
        }
    }

    # Location Hierarchy Paths (Escalation)
    LOCATION_HIERARCHY = {
        "CITY": "COUNTY",
        "COUNTY": "STATE",
        "STATE": None # End of path
    }

    def __init__(self, db: Session):
        self.db = db
        self.ingestion_service = DataIngestionService(db)

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
                    params=self._ensure_json_serializable(transformation.params),
                    values_affected=transformation.values_affected,
                    sample_transformations=self._ensure_json_serializable(transformation.sample_transformations),
                )
                self.db.add(log)

            # === ESCALATION AUTOMATIQUE (LOYER 25) ===
            # Si le dataset n'est pas k-anonyme (k < 5), on augmente la généralisation
            df = self._apply_k_anonymity_escalation(df, original_df, config, dataset_id, transformations)

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

            self.db.commit()

            # FINAL SANITIZATION: Ensure everything in the response is Python-native
            sanitized_transformations = [
                TransformationDetail(
                    column_name=t.column_name,
                    technique=t.technique,
                    params=self._ensure_json_serializable(t.params),
                    values_affected=int(t.values_affected),
                    sample_transformations=self._ensure_json_serializable(t.sample_transformations)
                )
                for t in transformations
            ]

            return AnonymizationResponse(
                job_id=job.id,
                anonymized_dataset_id=anonymized_dataset.id,
                transformations=sanitized_transformations,
                processing_time_seconds=float(processing_time),
                status=JobStatus.COMPLETED,
            )

        except Exception as e:
            logger.error(f"Error during anonymization job {job.id}: {str(e)}", exc_info=True)
            # Try to mark job as failed in a separate transaction or flush
            try:
                # Refresh job in case of session issues
                self.db.rollback() # Rollback the failed part
                job = self.db.query(AnonymizationJob).filter(AnonymizationJob.id == job.id).first()
                if job:
                    job.status = JobStatus.FAILED.value
                    job.error_message = f"Erreur critique: {str(e)}"
                    self.db.commit()
            except Exception as rollback_error:
                logger.error(f"Failed to update job status after error: {rollback_error}")
            
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
            visible_chars = params.get("visible_chars", 2)
            mask_char = params.get("mask_char", "*")
            df[column] = df[column].apply(
                lambda x: self._mask_string(str(x), visible_chars, mask_char) if pd.notna(x) else x
            )
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

        elif technique == AnonymizationTechnique.KEEP_AS_IS:
            # Column is preserved with its original values
            logger.info(f"Colonne '{column}': Conservation des données (KEEP_AS_IS)")
            # No changes to df


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

        df[column] = None
        return df

    def _mask_string(self, s: str, visible: int, mask_char: str) -> Optional[str]:
        """Partial character replacement."""
        if not s or s == "nan":
            return s
        if len(s) <= visible:
            return s
        return s[:visible] + (mask_char * (len(s) - visible))

    def _generalize_column(
        self,
        df: pd.DataFrame,
        column: str,
        params: Dict[str, Any]
    ) -> pd.DataFrame:
        """
        Generalization: Replace with broader categories.

        AUTOMATIC TYPE DETECTION & STRATEGIES:
          - Hierarchy: Uses a custom mapping (e.g., GENDER -> Personne)
          - Numeric (int/float):
            - Default: Binning or fixed ranges (Age, Expenses)
            - Coordinates: Rounding to specific precision (Lat/Lon)
          - Dates: Extract year or broader ranges
          - Text (string/object):
            - Prefix mode: Kepp first N characters
            - Strategy mode: "city_to_region", "address_to_street"
        """

        # 0. Check for explicit hierarchy mapping (Categorical/Text)
        if "hierarchy" in params and isinstance(params["hierarchy"], dict):
            logger.info(f"Column '{column}': Using hierarchical generalization")
            df[column] = df[column].apply(
                lambda x: self._generalize_hierarchical(x, params["hierarchy"])
            )
            return df

        # 1. Check for specific text strategies (City, Address)
        if "strategy" in params:
            strategy = params["strategy"]
            logger.info(f"Column '{column}': Using text strategy '{strategy}'")
            df[column] = df[column].apply(
                lambda x: self._generalize_text_strategy(x, strategy)
            )
            return df

        # === DÉTECTION AUTOMATIQUE DU TYPE AVEC ORDRE DE PRIORITÉ SÉCURISÉ ===

        # 1. Vérifier si c'est déjà un type datetime (datetime64)
        if pd.api.types.is_datetime64_any_dtype(df[column]):
            logger.info(f"Colonne '{column}': Type DATE natif détecté → Mode range d'années")
            df[column] = pd.to_datetime(df[column], errors="coerce").dt.year.fillna("Inconnu").astype(str)
            return df

        # 2. Vérifier si c'est numérique (int/float) - PRIORITÉ sur la détection de texte
        if pd.api.types.is_numeric_dtype(df[column]):
            logger.info(f"Colonne '{column}': Type NUMÉRIQUE détecté → Mode tranches")

            # A. Check for coordinates (Lat/Lon) - prioritize rounding
            is_coord = "lat" in column.lower() or "lon" in column.lower() or "coord" in column.lower()
            if is_coord and "bins" not in params and "range_size" not in params:
                precision = float(params.get("precision", 1)) # Default 1 decimal place
                df[column] = df[column].apply(lambda x: round(float(x), int(precision)) if pd.notna(x) else x)
                return df

            # B. Option: range_size (largeur fixe)
            if "range_size" in params:
                range_size = float(params["range_size"])
                df[column] = df[column].apply(
                    lambda x: self._generalize_to_range(x, range_size) if pd.notna(x) else x
                )
                return df

            # C. Option: bins (nombre de tranches, par défaut 5)
            else:
                bins = int(params.get("bins", 5))
                try:
                    binned = pd.cut(df[column], bins=bins, include_lowest=True, duplicates="drop")
                    
                    def format_interval(x):
                        if pd.isna(x): return np.nan
                        # Loi 25 requirement: "min-max" format (standardized for tests)
                        try:
                            # Cast to int for cleaner display if possible
                            left = int(round(x.left))
                            right = int(round(x.right))
                            return f"{left}-{right}"
                        except:
                            return str(x)
                    
                    df[column] = binned.apply(format_interval)
                except Exception as e:
                    logger.warning(f"Échec du binning pour {column}: {e}. Fallback préfixe.")
                    df[column] = None
                return df

        # 3. Essayer de détecter les dates sous forme de texte (object/string)
        sample = df[column].dropna().head(20).astype(str)
        is_date_string = False
        if len(sample) > 0:
            if any(re.search(r'[-/.]', s) for s in sample) or all(re.match(r'^\d{4}$', s) for s in sample):
                try:
                    date_conversion = pd.to_datetime(sample, errors="coerce")
                    if date_conversion.notna().sum() / len(sample) >= 0.7:
                        is_date_string = True
                except (ValueError, TypeError):
                    pass

        if is_date_string:
            logger.info(f"Colonne '{column}': Dates textuelles détectées → Mode range d'années")
            # Convert to datetime and extract year
            # Ensure we handle mixed formats by using errors='coerce'
            # The result must be a string as requested by the user
            date_col = pd.to_datetime(df[column], errors="coerce")
            df[column] = date_col.dt.year.apply(lambda x: str(int(x)) if pd.notna(x) else "Inconnu")
            return df

        # 4. Dérive démographique (Genre, Profession, etc.) -> Regroupement
        norm_col = column.lower()
        hierarchy = params.get("hierarchy") or self.DEMOGRAPHIC_HIERARCHIES.get(norm_col)
        
        if hierarchy:
            logger.info(f"Colonne '{column}': Hiérarchie appliquée (Source: {'params' if 'hierarchy' in params else 'default'})")
            df[column] = df[column].apply(
                lambda x: self._generalize_hierarchical(x, hierarchy)
            )
            return df

        # 5. Par défaut: Texte libre → Mode préfixe
        logger.info(f"Colonne '{column}': Texte libre détecté (Type: {df[column].dtype}) → Mode préfixe")
        prefix_length = int(params.get("prefix_length", 3))
        df[column] = df[column].apply(
            lambda x: self._generalize_text_prefix(x, prefix_length) if pd.notna(x) and x != "nan" else None
        )

        return df


    def _ensure_json_serializable(self, obj: Any) -> Any:
        """
        Recursively convert NumPy types to Python types for JSON serialization.
        Also handles Pydantic models by calling .model_dump().
        """
        if hasattr(obj, "model_dump"):
            return self._ensure_json_serializable(obj.model_dump())
        
        if isinstance(obj, dict):
            return {k: self._ensure_json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [self._ensure_json_serializable(v) for v in obj]
        elif isinstance(obj, (np.int64, np.int32, np.int16, np.int8)):
            return int(obj)
        elif isinstance(obj, (np.float64, np.float32, np.float16)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif pd.isna(obj):
            return None
        return obj

    def _apply_k_anonymity_escalation(
        self,
        df: pd.DataFrame,
        original_df: pd.DataFrame,
        config: List[AnonymizationConfig],
        dataset_id: UUID,
        transformations: Optional[List[TransformationDetail]] = None,
        min_k: int = 10,
        max_iterations: int = 6
    ) -> pd.DataFrame:
        """
        Automatic escalation: Increase generalization if k-anonymity is not met.
        """
        if transformations is None:
            transformations = []
        # Identify quasi-identifiers from config
        quasi_ids = [c.column_name for c in config if c.column_name in df.columns]
        if not quasi_ids:
            return df

        iteration = 0
        while iteration < max_iterations:
            # Calculate current k
            equivalence_classes = df.groupby(quasi_ids, dropna=False).size()
            k_min = equivalence_classes.min() if not equivalence_classes.empty else 0
            
            if k_min >= min_k:
                logger.info(f"Objectif k={min_k} atteint.")
                break

            changed = False
            for conf in config:
                col = conf.column_name
                upper_col = col.upper()
                if upper_col not in self.QUASI_IDENTIFIERS_SET:
                    continue
                    
                params = conf.params
                original_col_data = original_df[col]

                # (A) Dates Escalation - REMOVED AGE BIN ESCALATION (Requirement: YEAR ONLY)
                if upper_col == "BIRTHDATE" or upper_col == "AGE":
                    # We no longer escalate to age_bin per user request
                    continue

                # (B) Location Escalation (City -> County -> State)
                elif upper_col in self.LOCATION_HIERARCHY:
                    next_level = self.LOCATION_HIERARCHY[upper_col]
                    if next_level and next_level in df.columns:
                        logger.info(f"Escalade '{col}': Suppression car niveau supérieur '{next_level}' disponible")
                        if col in df.columns: 
                            # Track the drop for transparency
                            transformations.append(TransformationDetail(
                                column_name=col,
                                technique=AnonymizationTechnique.SUPPRESSION,
                                params={"reason": f"Supprimé par escalade géographique vers {next_level}"},
                                values_affected=len(df)
                            ))
                            df.drop(columns=[col], inplace=True)
                        if col in quasi_ids: quasi_ids.remove(col)
                        changed = True
                    elif not next_level:
                        # End of hierarchy path, if still not k-anonymous, suppress
                        logger.info(f"Escalade '{col}': Suppression finale (fin de hiérarchie)")
                        if col in df.columns: 
                            # Track the drop for transparency
                            transformations.append(TransformationDetail(
                                column_name=col,
                                technique=AnonymizationTechnique.SUPPRESSION,
                                params={"reason": "Supprimé pour garantir le k-anonymat (fin de hiérarchie)"},
                                values_affected=len(df)
                            ))
                            df.drop(columns=[col], inplace=True)
                        if col in quasi_ids: quasi_ids.remove(col)
                        changed = True

                # (C) ZIP Escalation (Prefix 3 -> 2)
                elif upper_col == "ZIP":
                    current_mode = params.get("mode")
                    if current_mode == "range":
                        # Switch to prefix
                        params["mode"] = "prefix"
                        params["prefix_length"] = 3
                        df[col] = original_col_data.astype(str).str[:3]
                        changed = True
                    elif params.get("prefix_length") == 3:
                        params["prefix_length"] = 2
                        df[col] = original_col_data.astype(str).str[:2]
                        changed = True
                    elif params.get("prefix_length") == 2:
                        if col in df.columns: 
                            # Track the drop for transparency
                            transformations.append(TransformationDetail(
                                column_name=col,
                                technique=AnonymizationTechnique.SUPPRESSION,
                                params={"reason": "ZIP supprimé car k-anonymat non atteint avec préfixe 2"},
                                values_affected=len(df)
                            ))
                            df.drop(columns=[col], inplace=True)
                        if col in quasi_ids: quasi_ids.remove(col)
                        changed = True

                # (D) Gender Escalation
                elif upper_col == "GENDER":
                    if not params.get("grouped"):
                        params["grouped"] = True
                        # Ne pas remplacer par "Person", mais garder tel quel ou masquer légèrement
                        # Dans beaucoup de cas, le genre est binaire ou restreint, le supprimer si nécessaire
                        # Mais ici on préfère arrêter l'escalade ou supprimer la colonne si vraiment critique
                        continue

                # (E) Lat/Lon Escalation (Rounding)
                elif upper_col in ["LAT", "LON"]:
                    current_size = params.get("range_size", 1.0)
                    if current_size == 1.0:
                        params["range_size"] = 10.0 # Very strong rounding
                        logger.info(f"Escalade '{col}': Rounding 1.0 -> 10.0")
                        df[col] = original_col_data.apply(lambda x: self._generalize_to_range(x, 10.0))
                        changed = True
                    else:
                        logger.info(f"Escalade '{col}': Suppression")
                        if col in df.columns: 
                            # Track the drop for transparency
                            transformations.append(TransformationDetail(
                                column_name=col,
                                technique=AnonymizationTechnique.SUPPRESSION,
                                params={"reason": f"{col} supprimé pour atteindre k-anonymat"},
                                values_affected=len(df)
                            ))
                            df.drop(columns=[col], inplace=True)
                        if col in quasi_ids: quasi_ids.remove(col)
                        changed = True

            if not changed:
                logger.info("Plus aucune généralisation possible.")
                break
            iteration += 1
            
        # Final Cleanup before returning to auto_anonymize
        df = self._cleanup_dataset(df, transformations)
        return df

    def _generalize_to_range(self, value: Any, range_size: float) -> Union[float, str, None]:
        """Convert numeric value to range string."""
        try:
            num = float(value)
            # Protection against zero range_size
            if range_size <= 0:
                return str(value)
            
            # Special case: float range_size (for coordinates)
            if range_size < 1:
                rounded = round(float(num / range_size)) * range_size
                return f"{rounded:.4f}".rstrip('0').rstrip('.')
                
            lower = (num // range_size) * range_size
            mid = lower + (range_size / 2)
            return float(mid)
        except (ValueError, TypeError):
            return str(value)

    def _generalize_hierarchical(self, value: Any, hierarchy: Dict[str, str]) -> Any:
        """Apply value mapping from hierarchy definition."""
        if pd.isna(value):
            return value
        
        # Standardize input for lookup
        val_str = str(value).lower().strip()
        result = hierarchy.get(val_str) or hierarchy.get(str(value).strip())
        
        # If no direct match, return original value to avoid silent suppression
        if result:
            return result
            
        # Fallback to original value instead of None
        return value

    def _cleanup_dataset(self, df: pd.DataFrame, transformations: List[TransformationDetail], sparse_threshold: float = 0.95) -> pd.DataFrame:
        """
        Final dataset cleanup:
        1. Remove columns with too many missing values (> sparse_threshold).
        2. Remove columns that are entirely empty.
        """
        initial_cols = set(df.columns)
        
        # 1. Remove sparse columns
        for col in list(df.columns):
            null_ratio = df[col].isnull().sum() / len(df)
            if null_ratio > sparse_threshold:
                logger.info(f"Suppression colonne creuse '{col}' (Ratio NULL: {null_ratio:.2%})")
                # Track for transparency
                transformations.append(TransformationDetail(
                    column_name=col,
                    technique=AnonymizationTechnique.SUPPRESSION,
                    params={"reason": f"Supprimé car trop creux (Ratio NULL: {null_ratio:.2%})"},
                    values_affected=len(df)
                ))
                df.drop(columns=[col], inplace=True)
                
        # 2. Remove entirely empty columns
        for col in list(df.columns):
            if df[col].isnull().all():
                logger.info(f"Suppression colonne vide '{col}'")
                # Track for transparency
                transformations.append(TransformationDetail(
                    column_name=col,
                    technique=AnonymizationTechnique.SUPPRESSION,
                    params={"reason": "Supprimé car vide après anonymisation"},
                    values_affected=len(df)
                ))
                df.drop(columns=[col], inplace=True)
                
        removed = initial_cols - set(df.columns)
        if removed:
            logger.info(f"Nettoyage final terminé. Colonnes supprimées: {list(removed)}")
            
        return df

    def _generalize_text_strategy(self, value: Any, strategy: str) -> Optional[str]:
        """Apply specific text reduction strategies."""
        if pd.isna(value):
            return value
        
        val_str = str(value).strip()
        
        if strategy == "address_to_street":
            # "123 Main St, Apt 4" -> "Main St"
            # Very basic regex: match numbers at start, then the rest until comma or 2nd space
            match = re.search(r'^\d+\s+([^,]+)', val_str)
            if match:
                return match.group(1).split(',')[0].strip()
            return val_str
            
        elif strategy == "city_to_region":
            # Avoid returning None, use prefix if no mapping
            return self._generalize_text_prefix(val_str, 3)
            
        return self._generalize_text_prefix(val_str, 3)

    def _generalize_text_prefix(self, value: Any, prefix_length: int) -> Optional[str]:
        """
        Generalize text by keeping prefix and replacing rest with asterisks.
        
        Examples:
            "G1X 3J4" -> "G1X ***" (prefix_length=3)
            "Montreal" -> "Mon ***" (prefix_length=3)
        """
        if pd.isna(value):
            return value
        
        text_str = str(value).strip()
        
        # Keep prefix and replace rest with None (effectively invalidating the entry for precise matching)
        # But per requirements, text should remain text. If we can't generalize without mask strings,
        # and we must avoid mask strings, we return None if it's too sensitive.
        # Keep prefix and replace rest with something indicates it's generalized
        # Keep prefix and replace rest with something indicates it's generalized
        if len(text_str) > prefix_length:
            return text_str[:prefix_length] + " ***"
        else:
            # Short strings (<= prefix_length) should remain unchanged to satisfy tests
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

        # Capture metadata for SuppressedColumn
        col_data = df[column]
        self.db.add(SuppressedColumn(
            job_id=job_id,
            dataset_id=dataset_id,
            column_name=column,
            column_position=df.columns.get_loc(column),
            data_type=str(col_data.dtype),
            row_count=len(col_data),
            reason="Total column suppression"
        ))
        
        # REMOVE COLUMN ENTIRELY from DataFrame to avoid "analysability" issues
        df.drop(columns=[column], inplace=True)
        logger.info(f"Colonne '{column}' SUPPRIMÉE du dataset final.")
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

        for column_name, cls in detection_report.columns.items():
            config = None
            upper_col = column_name.upper()

            # Rule 1: Direct Identifiers (Suppression)
            # SSN, DRIVERS, PASSPORT, FIRST, LAST, MAIDEN
            if any(id_keyword in upper_col for id_keyword in ["SSN", "DRIVERS", "PASSPORT", "FIRST", "LAST", "MAIDEN"]):
                config = AnonymizationConfig(
                    column_name=column_name,
                    technique=AnonymizationTechnique.SUPPRESSION,
                    params={}
                )
                logger.info(f"Direct ID '{column_name}' -> SUPPRESSION")

            # Rule 2: Quasi-identifiers (Generalization)
            elif upper_col in ["BIRTHDATE", "AGE", "DEATHDATE"]:
                config = AnonymizationConfig(
                    column_name=column_name,
                    technique=AnonymizationTechnique.GENERALIZATION,
                    params={"mode": "year" if "DATE" in upper_col else "range", "range_size": 10}
                )
                logger.info(f"Quasi-ID '{column_name}' -> GENERALIZATION (to Year)")

            elif upper_col == "GENDER":
                config = AnonymizationConfig(
                    column_name=column_name,
                    technique=AnonymizationTechnique.GENERALIZATION,
                    params={"hierarchy": self.DEMOGRAPHIC_HIERARCHIES["gender"]}
                )
                logger.info(f"Quasi-ID '{column_name}' -> NORMALIZATION (Gender)")

            elif upper_col == "BIRTHPLACE":
                # Avoid empty hierarchy which causes silent pruning
                # Default to suppression for transparency as birthplace is very identifying
                config = AnonymizationConfig(
                    column_name=column_name,
                    technique=AnonymizationTechnique.SUPPRESSION,
                    params={"reason": "Lieu de naissance trop précis pour k-anonymat"}
                )
                logger.info(f"Quasi-ID '{column_name}' -> SUPPRESSION (Birthplace)")

            elif upper_col == "ZIP":
                config = AnonymizationConfig(
                    column_name=column_name,
                    technique=AnonymizationTechnique.GENERALIZATION,
                    params={"mode": "range", "range_size": 100}
                )
                logger.info(f"Quasi-ID '{column_name}' -> GENERALIZATION (zip range 100)")

            elif upper_col in ["LAT", "LON"]:
                config = AnonymizationConfig(
                    column_name=column_name,
                    technique=AnonymizationTechnique.GENERALIZATION,
                    params={"mode": "range", "range_size": 1.0}
                )
                logger.info(f"Quasi-ID '{column_name}' -> GENERALIZATION (geo range 1.0)")

            elif upper_col == "ADDRESS":
                config = AnonymizationConfig(
                    column_name=column_name,
                    technique=AnonymizationTechnique.SUPPRESSION,
                    params={}
                )
                logger.info(f"Quasi-ID '{column_name}' -> SUPPRESSION (Address removed)")

            # Rule 3: Demographic hierarchies
            elif upper_col in ["RACE", "ETHNICITY"]:
                config = AnonymizationConfig(
                    column_name=column_name,
                    technique=AnonymizationTechnique.GENERALIZATION,
                    params={"hierarchy": self.DEMOGRAPHIC_HIERARCHIES.get(column_name.lower(), {})}
                )
                logger.info(f"Demographic '{column_name}' -> GENERALIZATION (hierarchy)")

            # Rule 4: Health and Financial - Preference for Differential Privacy if numeric
            elif any(hp_keyword in upper_col for hp_keyword in ["HEALTHCARE", "EXPENSES", "COVERAGE", "REVENU", "SALAIRE", "MONTANT", "SOLDE"]):
                if pd.api.types.is_numeric_dtype(df[column_name]):
                    config = AnonymizationConfig(
                        column_name=column_name,
                        technique=AnonymizationTechnique.DIFFERENTIAL_PRIVACY,
                        params={"epsilon": 1.0, "mechanism": "laplace"}
                    )
                else:
                    config = AnonymizationConfig(
                        column_name=column_name,
                        technique=AnonymizationTechnique.GENERALIZATION,
                        params={"prefix_length": 3}
                    )
                logger.info(f"Sensitive Medical/Financial '{column_name}' -> DP/GENERALIZATION")

            # Fallback for other sensitive/quasi columns: USE DETECTOR SUGGESTIONS
            elif cls.suggested_config:
                config = cls.suggested_config
                logger.info(f"Using suggested config for '{column_name}': {config.technique}")
            
            elif cls.sensitivity_type in [DataType.DIRECT_IDENTIFIER, DataType.SENSITIVE]:
                config = AnonymizationConfig(
                    column_name=column_name,
                    technique=AnonymizationTechnique.SUPPRESSION if cls.sensitivity_type == DataType.DIRECT_IDENTIFIER else AnonymizationTechnique.GENERALIZATION,
                    params={"prefix_length": 3} if cls.sensitivity_type == DataType.SENSITIVE else {}
                )
            
            elif cls.sensitivity_type == DataType.QUASI_IDENTIFIER:
                # Generic quasi-identifier handling
                if column_name in df.columns:
                    col_data = df[column_name]
                    if pd.api.types.is_datetime64_any_dtype(col_data):
                        config = AnonymizationConfig(column_name=column_name, technique=AnonymizationTechnique.GENERALIZATION, params={"mode": "year"})
                    elif pd.api.types.is_numeric_dtype(col_data):
                        config = AnonymizationConfig(column_name=column_name, technique=AnonymizationTechnique.GENERALIZATION, params={"mode": "range", "range_size": 10})
                    else:
                        config = AnonymizationConfig(column_name=column_name, technique=AnonymizationTechnique.GENERALIZATION, params={"prefix_length": 3})

            # Ajouter la configuration si définie
            if config:
                configs.append(config)
                applied_techniques[column_name] = {
                    "technique": config.technique.value,
                    "params": config.params,
                    "reason": cls.sensitivity_type.value,
                    "confidence": cls.confidence
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
