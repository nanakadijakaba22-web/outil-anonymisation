"""
Post-anonymization verification service.

This is a CRITICAL safety check - analogous to medical "double-check" protocols.
After anonymization, this service re-runs detection to catch:
1. Direct identifiers still present (masking failures)
2. Quasi-identifiers with k < 5
3. New patterns created by anonymization

References:
- Quebec Law 25: Requires demonstrable risk reduction
- Academic best practice: Always verify anonymization effectiveness
"""
from datetime import datetime
from typing import List, Dict, Any
from uuid import UUID

from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.models.database import Dataset, VerificationLog as VerificationLogModel
from app.models.schemas import DataType
from app.services.detector import SensitiveDataDetector
from app.services.risk_evaluator import RiskEvaluator


class VerificationReport(BaseModel):
    """Result of post-anonymization verification."""
    dataset_id: UUID
    job_id: UUID
    verified_at: datetime
    passed: bool

    # Failure indicators
    direct_ids_detected: List[str]  # Column names with direct identifiers
    k_anonymity_value: int | None   # Minimum k-anonymity
    k_violations_percentage: float | None  # % records in groups < 5
    overall_risk_score: float

    # Recommendations for fixing
    recommendations: List[str]

    # Pass/fail reason
    failure_reason: str | None


class PostAnonymizationVerifier:
    """
    Verifies anonymized datasets for residual direct identifiers.

    This is a CRITICAL safety check to prevent:
    - False confidence from incorrect anonymization
    - Data leaks due to masked-but-still-identifiable values
    - k-anonymity violations (k < 5)

    Failure modes detected:
    1. Direct IDs still present (email patterns, phone numbers, NAS)
    2. Quasi-IDs with insufficient k-anonymity
    3. New patterns inadvertently created by transformations
    """

    # Verification thresholds
    MIN_K_ANONYMITY = 5  # Industry standard
    MAX_RISK_ALLOWED = 20.0  # Law 25 compliance threshold

    def __init__(self, db: Session):
        self.db = db
        self.detector = SensitiveDataDetector(db)
        self.risk_evaluator = RiskEvaluator(db)

    async def verify_anonymization(
        self,
        anonymized_dataset_id: UUID,
        original_job_id: UUID
    ) -> VerificationReport:
        """
        Re-run detection on anonymized dataset to catch residual PII.

        Args:
            anonymized_dataset_id: UUID of the anonymized dataset
            original_job_id: UUID of the anonymization job

        Returns:
            VerificationReport with pass/fail status and recommendations

        Example:
            verifier = PostAnonymizationVerifier(db)
            report = await verifier.verify_anonymization(anon_id, job_id)

            if not report.passed:
                # Block "CONFORME" status
                # Alert user
                # Log failure
        """
        # Re-detect sensitive data on anonymized dataset
        detection = await self.detector.analyze_dataset(anonymized_dataset_id)

        # Re-evaluate risk
        assessment = await self.risk_evaluator.evaluate_dataset(anonymized_dataset_id)

        # Extract direct identifiers
        direct_ids = [
            col_name
            for col_name, col_data in detection.columns.items()
            if col_data.sensitivity_type == DataType.DIRECT_IDENTIFIER
        ]

        # Extract k-anonymity metrics
        k_value = assessment.details.get("k_anonymity", {}).get("k_value") if assessment.details else None
        k_violations = assessment.details.get("k_anonymity", {}).get("violations_percentage") if assessment.details else None

        # Determine pass/fail
        failure_reason = None
        passed = True

        # Check 1: Direct identifiers must be ZERO
        if len(direct_ids) > 0:
            passed = False
            failure_reason = (
                f"ÉCHEC CRITIQUE: {len(direct_ids)} identifiants directs détectés après anonymisation: "
                f"{', '.join(direct_ids[:5])}"
            )

        # Check 2: k-anonymity must be >= 5 (if quasi-IDs exist)
        elif k_value is not None and k_value < self.MIN_K_ANONYMITY:
            passed = False
            failure_reason = (
                f"ÉCHEC: k-anonymité insuffisante (k={k_value}). "
                f"Minimum requis: k>={self.MIN_K_ANONYMITY}. "
                f"{k_violations:.1f}% des enregistrements dans des groupes trop petits."
            )

        # Check 3: Overall risk must be below compliance threshold
        elif assessment.overall_score >= self.MAX_RISK_ALLOWED:
            passed = False
            failure_reason = (
                f"ÉCHEC: Risque global toujours élevé ({assessment.overall_score:.1f}%). "
                f"Seuil de conformité: <{self.MAX_RISK_ALLOWED}%."
            )

        # Generate recommendations
        recommendations = self._generate_fix_recommendations(
            direct_ids,
            k_value,
            k_violations,
            assessment.overall_score
        )

        # Save verification log to database
        verification_log = VerificationLogModel(
            job_id=original_job_id,
            dataset_id=anonymized_dataset_id,
            verified_at=datetime.utcnow(),
            passed=passed,
            failure_reason=failure_reason,
            direct_ids_found=direct_ids,
            k_value=k_value,
            k_violations_percentage=k_violations,
            overall_risk_score=assessment.overall_score,
            recommendations=recommendations
        )
        self.db.add(verification_log)
        self.db.commit()

        return VerificationReport(
            dataset_id=anonymized_dataset_id,
            job_id=original_job_id,
            verified_at=verification_log.verified_at,
            passed=passed,
            direct_ids_detected=direct_ids,
            k_anonymity_value=k_value,
            k_violations_percentage=k_violations,
            overall_risk_score=assessment.overall_score,
            recommendations=recommendations,
            failure_reason=failure_reason
        )

    def _generate_fix_recommendations(
        self,
        direct_ids: List[str],
        k_value: int | None,
        k_violations: float | None,
        overall_risk: float
    ) -> List[str]:
        """Generate actionable recommendations for fixing verification failures."""
        recommendations = []

        if len(direct_ids) > 0:
            recommendations.append(
                f"🔴 CRITIQUE: Supprimer ou pseudonymiser les identifiants directs restants: "
                f"{', '.join(direct_ids)}"
            )
            recommendations.append(
                "Vérifier que le masquage n'a pas laissé trop de caractères visibles"
            )

        if k_value is not None and k_value < 5:
            recommendations.append(
                f"⚠️ Appliquer une généralisation plus agressive sur les quasi-identifiants "
                f"pour augmenter k={k_value} vers k>=5"
            )
            if k_violations and k_violations > 50:
                recommendations.append(
                    f"Considérer la suppression de certains quasi-identifiants "
                    f"({k_violations:.1f}% des enregistrements ont k<5)"
                )

        if overall_risk >= 20:
            recommendations.append(
                f"Risque global: {overall_risk:.1f}%. Appliquer des techniques supplémentaires "
                f"pour réduire en dessous de 20%"
            )

        if not recommendations:
            recommendations.append(
                "✅ Vérification réussie! Dataset anonymisé de manière satisfaisante."
            )

        return recommendations
