"""
Risk evaluation service for Quebec Law 25 compliance assessment.

Implements 3 key risk criteria:
1. Individualization - Can we isolate a single individual?
2. Correlation - Can data be linked to external sources?
3. Inference - Can we deduce information about individuals?
"""
from datetime import datetime
from typing import List, Tuple
from uuid import UUID

import pandas as pd
import numpy as np
from sqlalchemy.orm import Session

from app.models.database import RiskAssessment as RiskAssessmentModel, Dataset
from app.models.schemas import (
    RiskLevel,
    RiskScore,
    RiskAssessmentResponse,
    DataType,
)
from app.services.data_ingestion import DataIngestionService
from app.services.visualization import DataVisualizationService


class RiskEvaluator:
    """
    Evaluates datasets against Quebec Law 25 risk criteria.

    IMPORTANT: Perfect anonymization is theoretically impossible. Even fully
    anonymized data retains residual risk from:
    - Inference attacks (background knowledge)
    - Record linkage with public datasets
    - Statistical disclosure
    - Re-identification via composition attacks

    References:
    - Machanavajjhala et al. (2007): "Perfect anonymization is impossible"
    - EU GDPR Recital 26: "Anonymization should reduce risk to very low"
    - Quebec Law 25 Regulation (May 2024): Requires "très faible" risk, NOT zero
    """

    # Risk thresholds (percentage)
    THRESHOLDS = {
        "individualization": 15,  # >15% unique combinations = HIGH risk
        "correlation": 20,        # >20% linkable columns = HIGH risk
        "inference": 25,          # >25% strong correlations = HIGH risk
        "overall": 20,            # >20% overall = NON-COMPLIANT
        "k_anonymity": 5,         # k >= 5 acceptable (industry standard)
    }

    # Minimum residual risk thresholds (never below these values)
    # IMPORTANT: These values must be low enough to allow properly anonymized
    # datasets to achieve compliance (< 20% overall score)
    MINIMUM_RESIDUAL_RISK = 0.01  # 0.01% baseline (symbolic minimum)
    BASE_RESIDUAL_RISK = {
        "suppressed_quasi_ids": 0.05,    # Very low - proper suppression is effective
        "no_direct_ids": 0.03,
        "generalized_data": 0.08,
        "pseudonymized_data": 0.12,      # Higher due to hash vulnerability
        "k_anonymity": 0.02,
        "no_numeric_columns": 0.01,      # Metadata inference still possible
    }

    def __init__(self, db: Session):
        self.db = db
        self.ingestion_service = DataIngestionService(db)

    def _apply_minimum_threshold(self, score: float, context: str = "default") -> float:
        """
        Ensure risk score never falls below scientifically valid minimum.

        Even fully anonymized data has residual risk. This enforces honesty
        in risk reporting, preventing false confidence from 0% scores.

        Args:
            score: Calculated risk score
            context: Type of anonymization applied (affects minimum threshold)

        Returns:
            Score adjusted to minimum threshold if needed

        References:
            - Machanavajjhala et al. (2007): "Perfect anonymization is impossible"
            - Quebec Law 25: Requires "très faible" risk, not zero
        """
        if score < self.MINIMUM_RESIDUAL_RISK:
            # Use context-specific minimum if available, else baseline
            minimum = self.BASE_RESIDUAL_RISK.get(context, self.MINIMUM_RESIDUAL_RISK)
            return max(score, minimum)
        return score

    def _calculate_k_anonymity(
        self,
        df: pd.DataFrame,
        quasi_identifiers: List[str]
    ) -> Tuple[int, float]:
        """
        Calculate k-anonymity: minimum group size for quasi-identifier combinations.

        k-anonymity (Sweeney, 2002): Each record is indistinguishable from at
        least k-1 other records with respect to quasi-identifiers.

        Industry Standards:
        - k >= 5: Acceptable for most use cases
        - k >= 10: Recommended for sensitive data
        - k >= 100: Required for medical research (HIPAA)

        Args:
            df: Dataset to evaluate
            quasi_identifiers: List of quasi-identifier column names

        Returns:
            (k_min, percentage_at_risk) where:
            - k_min: Minimum group size (worst case)
            - percentage_at_risk: % of records in groups < threshold (k < 5)

        Example:
            Dataset with 100 rows:
            - Group (age=30, zip=H3B): 10 people
            - Group (age=25, zip=H2X): 5 people
            - Group (age=35, zip=H1A): 1 person  <- k=1 violation!
            → k_min = 1, percentage_at_risk = 1.0%
        """
        if not quasi_identifiers:
            # Entire dataset is one equivalence class
            return (len(df), 0.0)

        # Group by quasi-identifier combinations
        equivalence_classes = df.groupby(quasi_identifiers, dropna=False).size()

        # Find minimum k
        k_min = equivalence_classes.min()

        # Calculate % of records in groups smaller than threshold (k < 5)
        threshold = self.THRESHOLDS["k_anonymity"]
        small_groups = equivalence_classes[equivalence_classes < threshold]
        records_at_risk = small_groups.sum()
        percentage_at_risk = (records_at_risk / len(df)) * 100

        return (int(k_min), float(percentage_at_risk))

    async def evaluate_dataset(self, dataset_id: UUID) -> RiskAssessmentResponse:
        """
        Complete Law 25 risk assessment.

        Args:
            dataset_id: UUID of the dataset to evaluate

        Returns:
            RiskAssessmentResponse with all three criteria and overall compliance
        """
        # Load dataset
        dataset = self.ingestion_service.get_dataset(dataset_id)
        df = self.ingestion_service.load_dataframe(dataset_id)

        # Get column classifications
        direct_identifiers = [
            col.name for col in dataset.columns
            if col.sensitivity_type == DataType.DIRECT_IDENTIFIER.value
        ]
        quasi_identifiers = [
            col.name for col in dataset.columns
            if col.sensitivity_type == DataType.QUASI_IDENTIFIER.value
        ]
        sensitive_columns = [
            col.name for col in dataset.columns
            if col.sensitivity_type == DataType.SENSITIVE.value
        ]

        # Evaluate three criteria
        individualization = self._check_individualization(df, quasi_identifiers)
        correlation = self._check_correlation(
            df, direct_identifiers, quasi_identifiers, sensitive_columns
        )
        inference = self._check_inference(df, sensitive_columns)

        # Calculate k-anonymity for storage (used in individualization check)
        # Only calculate if quasi-identifiers exist
        k_value = None
        k_violations = None
        if quasi_identifiers:
            valid_qids = [qid for qid in quasi_identifiers if qid in df.columns]
            if valid_qids:
                k_value, k_violations = self._calculate_k_anonymity(df, valid_qids)

        # Calculate overall score (weighted average)
        overall_score = (
            individualization.score * 0.40 +  # 40% weight
            correlation.score * 0.35 +         # 35% weight
            inference.score * 0.25             # 25% weight
        )

        # Determine compliance
        is_compliant = overall_score < self.THRESHOLDS["overall"]

        # Generate recommendations
        recommendations = self._generate_recommendations(
            individualization, correlation, inference, is_compliant
        )

        # Generate compact visualization summary (Phase 3)
        visualization_summary = self._generate_compact_visualization_summary(dataset_id, df)
        # Convert all numpy types to Python natives for JSON serialization
        visualization_summary = self._convert_numpy_types(visualization_summary)

        # Save assessment
        assessment = RiskAssessmentModel(
            dataset_id=dataset_id,
            individualization_score=individualization.score,
            individualization_level=individualization.level.value,
            correlation_score=correlation.score,
            correlation_level=correlation.level.value,
            inference_score=inference.score,
            inference_level=inference.level.value,
            k_anonymity_value=k_value,
            k_anonymity_violations=k_violations,
            overall_score=overall_score,
            overall_level=self._score_to_level(overall_score).value,
            is_loi25_compliant=is_compliant,
            details={
                "individualization": {
                    "affected_columns": individualization.affected_columns,
                    "justification": individualization.justification
                },
                "correlation": {
                    "affected_columns": correlation.affected_columns,
                    "justification": correlation.justification
                },
                "inference": {
                    "affected_columns": inference.affected_columns,
                    "justification": inference.justification
                },
                "k_anonymity": {
                    "k_value": k_value,
                    "violations_percentage": k_violations
                } if k_value is not None else None
            },
            recommendations=recommendations,
            visualization_data=visualization_summary,  # Phase 3: Store compact visualization summary
        )
        self.db.add(assessment)

        # Update dataset compliance status
        dataset.risk_score = overall_score
        dataset.is_loi25_compliant = is_compliant

        self.db.commit()

        return RiskAssessmentResponse(
            dataset_id=dataset_id,
            assessed_at=assessment.assessed_at,
            individualization=individualization,
            correlation=correlation,
            inference=inference,
            overall_score=overall_score,
            overall_level=self._score_to_level(overall_score),
            is_loi25_compliant=is_compliant,
            recommendations=recommendations,
        )

    def _check_individualization(
        self,
        df: pd.DataFrame,
        quasi_identifiers: List[str]
    ) -> RiskScore:
        """
        Criterion 1: Individualization Risk

        Can we isolate a single individual?
        Method: k-anonymity (Sweeney, 2002) - measures minimum group size

        IMPORTANT: Previously used simple uniqueness ratio which was scientifically
        incorrect. Now uses k-anonymity which is the industry standard.
        """
        if not quasi_identifiers or len(quasi_identifiers) == 0:
            # No quasi-identifiers = low risk, but NOT zero
            score = self._apply_minimum_threshold(0, "suppressed_quasi_ids")
            return RiskScore(
                score=score,
                level=RiskLevel.LOW,
                justification=(
                    f"Aucun quasi-identifiant présent. "
                    f"Risque résiduel minimal: {score:.1f}% "
                    f"(attaques par inférence toujours possibles)"
                ),
                affected_columns=[],
            )

        # Filter quasi-identifiers that exist in dataframe
        valid_qids = [qid for qid in quasi_identifiers if qid in df.columns]

        if not valid_qids:
            # Quasi-IDs suppressed = low risk, but NOT zero
            score = self._apply_minimum_threshold(0, "suppressed_quasi_ids")
            return RiskScore(
                score=score,
                level=RiskLevel.LOW,
                justification=(
                    f"Quasi-identifiants supprimés ou absents. "
                    f"Risque résiduel minimal: {score:.1f}% "
                    f"(linkage avec données publiques reste possible)"
                ),
                affected_columns=[],
            )

        # Calculate k-anonymity
        k_min, percentage_at_risk = self._calculate_k_anonymity(df, valid_qids)

        # Risk score based on k-anonymity violations
        # Higher % at risk = Higher score
        score = percentage_at_risk

        # Apply minimum threshold (even k=100 has some residual risk)
        score = self._apply_minimum_threshold(score, "k_anonymity")

        level = self._score_to_level(score)

        # Build detailed justification
        justification = (
            f"k-anonymité: k={k_min} (minimum), "
            f"{percentage_at_risk:.1f}% des enregistrements dans des groupes < 5. "
        )

        if k_min < 5:
            justification += (
                f"RISQUE ÉLEVÉ: k={k_min} insuffisant. "
                f"Standard industriel: k≥5 (recommandé: k≥10). "
                f"Des individus peuvent être isolés."
            )
        elif k_min < 10:
            justification += (
                f"Risque modéré: k={k_min} acceptable mais amélioration recommandée. "
                f"Standard industriel pour données sensibles: k≥10."
            )
        else:
            justification += (
                f"Risque faible: k={k_min} satisfait les standards industriels. "
                f"Risque résiduel: {score:.1f}% (attaques sophistiquées restent possibles)."
            )

        return RiskScore(
            score=score,
            level=level,
            justification=justification,
            affected_columns=valid_qids,
        )

    def _check_correlation(
        self,
        df: pd.DataFrame,
        direct_identifiers: List[str],
        quasi_identifiers: List[str],
        sensitive_columns: List[str]
    ) -> RiskScore:
        """
        Criterion 2: Correlation Risk

        Can data be linked to external sources?
        Method: Identify columns that could serve as join keys
        """
        linkable_columns = []

        # Direct identifiers are highly linkable (if present)
        valid_direct = [col for col in direct_identifiers if col in df.columns]
        linkable_columns.extend(valid_direct)

        # Quasi-identifiers with high uniqueness are linkable
        for qid in quasi_identifiers:
            if qid in df.columns:
                uniqueness = df[qid].nunique() / len(df)
                if uniqueness > 0.5:  # >50% unique values
                    linkable_columns.append(qid)

        # Calculate risk score
        total_columns = len(df.columns)
        if total_columns == 0:
            score = 0
        else:
            score = (len(linkable_columns) / total_columns) * 100

        # Apply minimum threshold
        context = "no_direct_ids" if len(valid_direct) == 0 else "default"
        score = self._apply_minimum_threshold(score, context)

        level = self._score_to_level(score)

        justification = (
            f"{len(linkable_columns)} colonnes potentiellement liables sur {total_columns} "
            f"({score:.1f}%). "
        )

        if score > self.THRESHOLDS["correlation"]:
            justification += "RISQUE ÉLEVÉ: Nombreuses colonnes peuvent être utilisées pour lier les données."
        else:
            justification += "Risque acceptable: Peu de colonnes liables aux sources externes."

        return RiskScore(
            score=score,
            level=level,
            justification=justification,
            affected_columns=linkable_columns,
        )

    def _check_inference(
        self,
        df: pd.DataFrame,
        sensitive_columns: List[str]
    ) -> RiskScore:
        """
        Criterion 3: Inference Risk

        Can we deduce information about individuals?
        Method: Detect strong correlations between columns
        """
        # Only check numeric columns for correlation
        numeric_df = df.select_dtypes(include=[np.number])

        if numeric_df.empty or len(numeric_df.columns) < 2:
            # No numeric columns = low inference risk, but NOT zero
            # Metadata and column names still reveal information
            score = self._apply_minimum_threshold(0, "no_numeric_columns")
            return RiskScore(
                score=score,
                level=RiskLevel.LOW,
                justification=(
                    f"Pas assez de colonnes numériques pour analyser les corrélations. "
                    f"Risque résiduel minimal: {score:.1f}% (inférence via métadonnées possible)"
                ),
                affected_columns=[],
            )

        # Calculate correlation matrix
        corr_matrix = numeric_df.corr().abs()

        # Find strong correlations (>0.7) excluding diagonal
        strong_correlations = []
        n_pairs = 0

        for i in range(len(corr_matrix.columns)):
            for j in range(i + 1, len(corr_matrix.columns)):
                n_pairs += 1
                if corr_matrix.iloc[i, j] > 0.7:
                    col1 = corr_matrix.columns[i]
                    col2 = corr_matrix.columns[j]
                    strong_correlations.append((col1, col2, corr_matrix.iloc[i, j]))

        # Calculate risk score
        if n_pairs == 0:
            score = 0
        else:
            score = (len(strong_correlations) / n_pairs) * 100

        # Apply minimum threshold
        score = self._apply_minimum_threshold(score, "default")

        level = self._score_to_level(score)

        affected_columns = list(set([
            col for pair in strong_correlations
            for col in (pair[0], pair[1])
        ]))

        justification = (
            f"{len(strong_correlations)} corrélations fortes (>0.7) détectées sur "
            f"{n_pairs} paires possibles ({score:.1f}%). "
        )

        if score > self.THRESHOLDS["inference"]:
            justification += "RISQUE ÉLEVÉ: Nombreuses corrélations permettent de déduire des informations."
        else:
            justification += "Risque acceptable: Peu de corrélations exploitables."

        return RiskScore(
            score=score,
            level=level,
            justification=justification,
            affected_columns=affected_columns,
        )

    @staticmethod
    def _convert_numpy_types(obj):
        """
        Recursively convert numpy types to Python native types for JSON serialization.

        Args:
            obj: Object to convert (can be dict, list, numpy type, or primitive)

        Returns:
            Object with all numpy types converted to Python natives
        """
        if isinstance(obj, dict):
            return {key: RiskEvaluator._convert_numpy_types(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [RiskEvaluator._convert_numpy_types(item) for item in obj]
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return obj

    def _score_to_level(self, score: float) -> RiskLevel:
        """Convert numeric score to risk level."""
        if score < 10:
            return RiskLevel.LOW
        elif score < 25:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.HIGH

    def _generate_recommendations(
        self,
        individualization: RiskScore,
        correlation: RiskScore,
        inference: RiskScore,
        is_compliant: bool
    ) -> List[str]:
        """Generate actionable recommendations based on risk assessment."""
        recommendations = []

        if not is_compliant:
            recommendations.append(
                "⚠️ Dataset NON-CONFORME à la Loi 25 - Anonymisation requise avant utilisation"
            )

        if individualization.level == RiskLevel.HIGH:
            recommendations.append(
                f"Individualisation ({individualization.score:.1f}%): "
                f"Appliquer la généralisation ou la suppression sur les quasi-identifiants: "
                f"{', '.join(individualization.affected_columns[:3])}"
            )

        if correlation.level == RiskLevel.HIGH:
            recommendations.append(
                f"Corrélation ({correlation.score:.1f}%): "
                f"Supprimer ou pseudonymiser les identifiants directs: "
                f"{', '.join(correlation.affected_columns[:3])}"
            )

        if inference.level == RiskLevel.HIGH:
            recommendations.append(
                f"Inférence ({inference.score:.1f}%): "
                f"Généraliser les colonnes fortement corrélées: "
                f"{', '.join(inference.affected_columns[:3])}"
            )

        if is_compliant:
            recommendations.append(
                "✅ Dataset conforme à la Loi 25 - Peut être utilisé en toute sécurité"
            )

        return recommendations

    def _generate_compact_visualization_summary(
        self,
        dataset_id: UUID,
        df: pd.DataFrame
    ) -> dict:
        """
        Generate a compact visualization summary for storage in risk_assessments table.

        This creates a lightweight summary (not the full detailed statistics) that
        can be stored in the database and used for quick dashboard displays without
        re-computing expensive statistics.

        Args:
            dataset_id: UUID of the dataset
            df: DataFrame to analyze

        Returns:
            Compact dictionary with key metrics:
            - overview: Basic stats (rows, columns, memory)
            - distributions_summary: Count of numeric/categorical columns
            - correlations_summary: Count of strong correlations
            - outliers_summary: Count of columns with outliers
            - missing_data_summary: Total missing values

        Note: For full detailed statistics (with histograms, distributions, etc.),
        use DataVisualizationService.generate_statistics() directly.
        """
        try:
            viz_service = DataVisualizationService(self.db)

            # Get full statistics (we'll extract compact summary from it)
            full_stats = viz_service.generate_statistics(dataset_id)

            # Extract compact summary
            compact_summary = {
                "overview": {
                    "total_rows": full_stats.get("overview", {}).get("total_rows", 0),
                    "total_columns": full_stats.get("overview", {}).get("total_columns", 0),
                    "numeric_columns": full_stats.get("overview", {}).get("numeric_columns", 0),
                    "categorical_columns": full_stats.get("overview", {}).get("categorical_columns", 0),
                    "memory_usage_mb": full_stats.get("overview", {}).get("memory_usage_mb", 0),
                    "duplicate_rows": full_stats.get("overview", {}).get("duplicate_rows", 0),
                },
                "missing_data": {
                    "total_missing": full_stats.get("missing_data", {}).get("total_missing", 0),
                    "missing_percentage": full_stats.get("missing_data", {}).get("missing_percentage", 0),
                    "columns_with_missing_count": len(
                        full_stats.get("missing_data", {}).get("columns_with_missing", [])
                    ),
                },
                "distributions": {
                    "total_distributions": len(full_stats.get("distributions", {})),
                    # Store names of top 3 numeric and top 3 categorical for quick reference
                    "numeric_columns": [
                        col for col, data in list(full_stats.get("distributions", {}).items())[:3]
                        if data.get("type") == "numeric"
                    ],
                    "categorical_columns": [
                        col for col, data in list(full_stats.get("distributions", {}).items())[:3]
                        if data.get("type") == "categorical"
                    ],
                },
                "correlations": {
                    "strong_correlations_count": len(
                        full_stats.get("correlations", {}).get("strong_correlations", [])
                    ),
                    # Store top 3 strongest correlations for dashboard
                    "top_correlations": [
                        {
                            "column1": corr.get("column1"),
                            "column2": corr.get("column2"),
                            "correlation": corr.get("correlation"),
                        }
                        for corr in full_stats.get("correlations", {}).get("strong_correlations", [])[:3]
                    ],
                },
                "outliers": {
                    "columns_with_outliers_count": len([
                        col for col, data in full_stats.get("outliers", {}).items()
                        if data.get("count", 0) > 0
                    ]),
                    # Store columns with most outliers (top 3)
                    "top_outlier_columns": sorted(
                        [
                            {"column": col, "count": data.get("count", 0), "percentage": data.get("percentage", 0)}
                            for col, data in full_stats.get("outliers", {}).items()
                            if data.get("count", 0) > 0
                        ],
                        key=lambda x: x["count"],
                        reverse=True
                    )[:3],
                },
                "generated_at": datetime.now().isoformat(),
            }

            return compact_summary

        except Exception as e:
            # If visualization generation fails, return minimal summary
            # Don't let visualization errors block risk assessment
            return {
                "overview": {
                    "total_rows": len(df),
                    "total_columns": len(df.columns),
                },
                "error": f"Visualization summary failed: {str(e)}",
                "generated_at": datetime.now().isoformat(),
            }
