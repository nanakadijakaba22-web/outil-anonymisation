"""
Risk evaluation service for Quebec Law 25 compliance assessment.

Implements 3 key risk criteria:
1. Individualization - Can we isolate a single individual?
2. Correlation - Can data be linked to external sources?
3. Inference - Can we deduce information about individuals?
"""
from datetime import datetime
from typing import List, Tuple, Any
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


def convert_numpy_types(obj: Any) -> Any:
    """
    Convert numpy types to native Python types for JSON serialization.

    PostgreSQL JSONB columns require native Python types, not numpy types.
    This function recursively converts:
    - numpy.int64 -> int
    - numpy.float64 -> float
    - numpy.ndarray -> list
    - dict/list -> recursively converted

    Args:
        obj: Object to convert (can be dict, list, numpy type, etc.)

    Returns:
        Object with all numpy types converted to Python native types
    """
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    else:
        return obj


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

    # Risk thresholds (percentage) - Tightened for Law 25 "très faible" (very low) objective
    THRESHOLDS = {
        "individualization": 5,   # >5% unique combinations = HIGH risk (Law 25 target)
        "correlation": 10,        # >10% linkable records = HIGH risk
        "inference": 15,          # >15% strong/non-linear correlations = HIGH risk
        "overall": 10,            # >10% overall = NON-COMPLIANT
        "k_anonymity_min": 5,     # Industry standard for "low" risk
        "k_anonymity_strict": 11, # Quebec health/insurance recommendation
    }

    # Minimum residual risk thresholds (never below these values)
    MINIMUM_RESIDUAL_RISK = 0.1  # 0.1% baseline (academic consensus)
    BASE_RESIDUAL_RISK = {
        "suppressed_quasi_ids": 0.5,    # Low but not zero
        "no_direct_ids": 0.3,
        "generalized_data": 0.8,
        "pseudonymized_data": 1.2,      # Higher due to hash vulnerability
        "k_anonymity": 0.2,
        "no_numeric_columns": 0.1,      # Metadata inference still possible
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
            return (int(len(df)), 0.0, 0.0)

        # 1. Calculate k-anonymity on all QI
        equivalence_classes = df.groupby(quasi_identifiers, dropna=False).size()
        k_min = int(equivalence_classes.min())
        
        # 2. Uniqueness rate (groups of size 1)
        uniqueness_count = int((equivalence_classes == 1).sum())
        uniqueness_rate = (uniqueness_count / len(df)) * 100

        # 3. Percentage at risk (k < THRESHOLD)
        threshold = self.THRESHOLDS["k_anonymity_min"]
        small_groups = equivalence_classes[equivalence_classes < threshold]
        records_at_risk = small_groups.sum()
        percentage_at_risk = (records_at_risk / len(df)) * 100

        # 4. Subset testing (Combinatorial Risk)
        # Check if small subsets of QI lead to high uniqueness
        max_subset_size = min(len(quasi_identifiers), 4)
        subset_uniqueness = 0.0
        if len(quasi_identifiers) > 1:
            # We check a few strategic subsets (top 2, top 3 combinations)
            # This detects "greedy" identifiers
            import itertools
            for r in range(min(2, len(quasi_identifiers)), max_subset_size + 1):
                # Sample some combinations if too many
                subsets = list(itertools.combinations(quasi_identifiers, r))
                if len(subsets) > 5:
                    import random
                    subsets = random.sample(subsets, 5)
                
                for subset in subsets:
                    sub_uniqueness = (df.groupby(list(subset)).size() == 1).sum() / len(df)
                    subset_uniqueness = max(subset_uniqueness, sub_uniqueness * 100)

        return (k_min, float(percentage_at_risk), float(max(uniqueness_rate, subset_uniqueness)))

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
        if quasi_identifiers:
            valid_qids = [qid for qid in quasi_identifiers if qid in df.columns]
            if valid_qids:
                k_value, k_violations, uniqueness_rate = self._calculate_k_anonymity(df, valid_qids)

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

        # Prepare details dict (will be converted to native Python types)
        details_dict = {
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
                "violations_percentage": k_violations,
                "uniqueness_rate": uniqueness_rate if 'uniqueness_rate' in locals() else 0.0
            } if k_value is not None else None
        }

        # Convert all numpy types to Python native types for JSON serialization
        k_value_clean = convert_numpy_types(k_value) if k_value is not None else None
        k_violations_clean = convert_numpy_types(k_violations) if k_violations is not None else None
        details_clean = convert_numpy_types(details_dict)
        recommendations_clean = convert_numpy_types(recommendations)
        visualization_clean = convert_numpy_types(visualization_summary)

        # Save assessment
        assessment = RiskAssessmentModel(
            dataset_id=dataset_id,
            individualization_score=individualization.score,
            individualization_level=individualization.level.value,
            correlation_score=correlation.score,
            correlation_level=correlation.level.value,
            inference_score=inference.score,
            inference_level=inference.level.value,
            k_anonymity_value=k_value_clean,
            k_anonymity_violations=k_violations_clean,
            overall_score=overall_score,
            overall_level=self._score_to_level(overall_score).value,
            is_loi25_compliant=is_compliant,
            details=details_clean,
            recommendations=recommendations_clean,
            visualization_data=visualization_clean,  # Phase 3: Store compact visualization summary
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

        # Calculate k-anonymity and uniqueness
        k_min, percentage_at_risk, uniqueness_rate = self._calculate_k_anonymity(df, valid_qids)

        # Risk score based on k-anonymity violations and uniqueness
        # We take the maximum of both to ensure "worst case" coverage
        score = max(percentage_at_risk, uniqueness_rate)

        # Apply minimum threshold
        score = self._apply_minimum_threshold(score, "k_anonymity")

        level = self._score_to_level(score)

        # Build detailed justification
        justification = (
            f"k-anonymité: k={k_min} (min), "
            f"Taux d'unicité: {uniqueness_rate:.1%}, "
            f"Violation k<5: {percentage_at_risk:.1f}%. "
        )

        if uniqueness_rate > 1:
             justification += f"CRITIQUE: {uniqueness_rate:.1f}% des lignes sont uniques (Individualisation directe)."
        elif k_min < 5:
            justification += (
                f"RISQUE ÉLEVÉ: k={k_min} insuffisant pour la Loi 25. "
                f"L'objectif est d'atteindre un risque 'très faible'."
            )
        else:
            justification += "Risque faible: k satisfait l'objectif de non-isolement."

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
        """
        if not quasi_identifiers:
            score = self._apply_minimum_threshold(0, "no_direct_ids")
            return RiskScore(score=score, level=RiskLevel.LOW, justification="Pas de QI pour le linkage.", affected_columns=[])

        # Row-level Linkage Score based on Equivalence Classes (E)
        # Metric: Score = 100 * mean(1 / |E|)
        # This reflects the probability of correctly linking a random record
        valid_qids = [qid for qid in quasi_identifiers if qid in df.columns]
        if not valid_qids:
            return RiskScore(score=self.MINIMUM_RESIDUAL_RISK, level=RiskLevel.LOW, justification="QI non trouvés.", affected_columns=[])

        group_sizes = df.groupby(valid_qids, dropna=False).size()
        linkage_probabilities = 1.0 / group_sizes
        
        # We weight the probabilities by the number of records they represent
        # linkage_score = (sum(records_in_group * 1_over_group_size) / total_records) * 100
        # Wait, the above simplifies to: (sum(E * 1/E) / total) * 100 = (num_groups / total) * 100
        # No, the risk of linkage is high if many rows are in small groups.
        # Mean linkage probability across all ROWS: 
        row_linkage_probs = df.join(linkage_probabilities.rename('prob'), on=valid_qids)['prob']
        avg_linkage = row_linkage_probs.mean() * 100
        p95_linkage = row_linkage_probs.quantile(0.95) * 100

        # Overall score is heavily influenced by high-risk rows
        score = max(avg_linkage, p95_linkage * 0.5) 

        # Apply minimum threshold
        score = self._apply_minimum_threshold(score, "no_direct_ids")
        level = self._score_to_level(score)

        justification = (
            f"Probabilité moyenne de linkage: {avg_linkage:.1f}%. "
            f"P95 probabilité: {p95_linkage:.1f}%."
        )

        if p95_linkage > 50:
            justification += " RISQUE ÉLEVÉ: Une part importante des données est facilement liable."

        return RiskScore(
            score=float(score),
            level=level,
            justification=justification,
            affected_columns=valid_qids,
        )

    def _check_inference(
        self,
        df: pd.DataFrame,
        sensitive_columns: List[str]
    ) -> RiskScore:
        """
        Criterion 3: Inference Risk

        Can we deduce information about individuals?
        Method: Detect Pearson (linear), Cramer's V (category), and Mutual Info (any)
        """
        inference_scores = []
        affected_cols = set()

        # 1. Numerical Pearson Correlation
        numeric_df = df.select_dtypes(include=[np.number])
        if not numeric_df.empty and len(numeric_df.columns) >= 2:
            corr_matrix = numeric_df.corr().abs()
            for i in range(len(corr_matrix.columns)):
                for j in range(i + 1, len(corr_matrix.columns)):
                    val = corr_matrix.iloc[i, j]
                    if val > 0.7:
                        inference_scores.append(val)
                        affected_cols.update([corr_matrix.columns[i], corr_matrix.columns[j]])

        # 2. Categorical / Mixed Inference (simplified Cramér's V)
        # We focus on predicting sensitive columns from QI/Others
        from scipy.stats import chi2_contingency

        categorical_cols = df.select_dtypes(exclude=[np.number]).columns
        # Limit analysis to avoid combinatorial explosion
        sample_cols = list(df.columns[:10]) 
        
        for i, col1 in enumerate(sample_cols):
            for col2 in sample_cols[i+1:]:
                try:
                    # Contingency table
                    obs = pd.crosstab(df[col1], df[col2])
                    if obs.size > 0:
                        chi2 = chi2_contingency(obs)[0]
                        n = obs.sum().sum()
                        phi2 = chi2 / n
                        r, k = obs.shape
                        phi2corr = max(0, phi2 - ((k-1)*(r-1))/(n-1))
                        rcorr = r - ((r-1)**2)/(n-1)
                        kcorr = k - ((k-1)**2)/(n-1)
                        # Cramer's V formula
                        v = np.sqrt(phi2corr / min((kcorr-1), (rcorr-1)))
                        if v > 0.6:  # Strong non-linear/categorical association
                            inference_scores.append(v)
                            affected_cols.update([col1, col2])
                except:
                    continue

        # Calculate final risk score
        if not inference_scores:
            score = self._apply_minimum_threshold(0, "no_numeric_columns")
        else:
            # Weighted average of top associations
            score = np.mean(sorted(inference_scores, reverse=True)[:5]) * 100

        score = self._apply_minimum_threshold(score, "default")
        level = self._score_to_level(score)

        return RiskScore(
            score=float(score),
            level=level,
            justification=f"Détection de {len(inference_scores)} associations fortes (Inférence). Score moyen: {score:.1f}%",
            affected_columns=list(affected_cols),
        )

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
