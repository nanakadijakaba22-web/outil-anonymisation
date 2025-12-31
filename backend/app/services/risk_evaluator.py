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


class RiskEvaluator:
    """
    Evaluates datasets against Quebec Law 25 risk criteria.
    """

    # Risk thresholds (percentage)
    THRESHOLDS = {
        "individualization": 15,  # >15% unique combinations = HIGH risk
        "correlation": 20,        # >20% linkable columns = HIGH risk
        "inference": 25,          # >25% strong correlations = HIGH risk
        "overall": 20,            # >20% overall = NON-COMPLIANT
    }

    def __init__(self, db: Session):
        self.db = db
        self.ingestion_service = DataIngestionService(db)

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

        # Save assessment
        assessment = RiskAssessmentModel(
            dataset_id=dataset_id,
            individualization_score=individualization.score,
            individualization_level=individualization.level.value,
            correlation_score=correlation.score,
            correlation_level=correlation.level.value,
            inference_score=inference.score,
            inference_level=inference.level.value,
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
                }
            },
            recommendations=recommendations,
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
        Method: Calculate % of unique quasi-identifier combinations
        """
        if not quasi_identifiers or len(quasi_identifiers) == 0:
            return RiskScore(
                score=0,
                level=RiskLevel.LOW,
                justification="Aucun quasi-identifiant détecté",
                affected_columns=[],
            )

        # Filter quasi-identifiers that exist in dataframe
        valid_qids = [qid for qid in quasi_identifiers if qid in df.columns]

        if not valid_qids:
            return RiskScore(
                score=0,
                level=RiskLevel.LOW,
                justification="Quasi-identifiants supprimés ou absents",
                affected_columns=[],
            )

        # Calculate uniqueness of quasi-identifier combinations
        qid_combinations = df[valid_qids].drop_duplicates()
        unique_ratio = len(qid_combinations) / len(df) * 100

        # Determine risk level
        score = unique_ratio
        level = self._score_to_level(score)

        justification = (
            f"{len(qid_combinations)} combinaisons uniques sur {len(df)} lignes "
            f"({unique_ratio:.1f}%). "
        )

        if unique_ratio > self.THRESHOLDS["individualization"]:
            justification += "RISQUE ÉLEVÉ: Plus de 15% des individus peuvent être isolés."
        else:
            justification += "Risque acceptable: Moins de 15% d'individus isolables."

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
            return RiskScore(
                score=0,
                level=RiskLevel.LOW,
                justification="Pas assez de colonnes numériques pour analyser les corrélations",
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
