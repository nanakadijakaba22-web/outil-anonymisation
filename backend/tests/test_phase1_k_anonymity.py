"""
Unit Tests for Phase 1: k-anonymity and Minimum Residual Risk

Tests the critical corrections made in Phase 1:
1. k-anonymity calculation (replacing simple uniqueness ratio)
2. Minimum residual risk thresholds (preventing 0% risk)
3. Post-anonymization verification
"""

import pytest
import pandas as pd
from unittest.mock import Mock, AsyncMock, MagicMock
from uuid import uuid4

from app.services.risk_evaluator import RiskEvaluator, RiskLevel
from app.services.verification import PostAnonymizationVerifier, VerificationReport
from app.models.schemas import DataType


class TestKAnonymityCalculation:
    """Test k-anonymity calculation correctness."""

    def setup_method(self):
        """Create mock database session and evaluator."""
        self.mock_db = Mock()
        self.evaluator = RiskEvaluator(self.mock_db)

    def test_k_anonymity_perfect_case(self):
        """Test k-anonymity with perfect anonymization (all same group)."""
        # All records have same quasi-identifier values
        df = pd.DataFrame({
            "age": [30, 30, 30, 30, 30],
            "city": ["Montreal", "Montreal", "Montreal", "Montreal", "Montreal"],
            "income": [50000, 60000, 70000, 80000, 90000]  # Different sensitive values
        })

        quasi_ids = ["age", "city"]
        k_min, violations_pct = self.evaluator._calculate_k_anonymity(df, quasi_ids)

        # All 5 records are in one group → k=5, 0% violations
        assert k_min == 5
        assert violations_pct == 0.0

    def test_k_anonymity_worst_case(self):
        """Test k-anonymity with unique individuals (k=1)."""
        df = pd.DataFrame({
            "age": [25, 30, 35, 40, 45],
            "zip": ["H1A", "H2B", "H3C", "H4D", "H5E"],
            "income": [50000, 60000, 70000, 80000, 90000]
        })

        quasi_ids = ["age", "zip"]
        k_min, violations_pct = self.evaluator._calculate_k_anonymity(df, quasi_ids)

        # Each person is unique → k=1, 100% violations (all groups have k<5)
        assert k_min == 1
        assert violations_pct == 100.0

    def test_k_anonymity_mixed_groups(self):
        """Test k-anonymity with mixed group sizes."""
        df = pd.DataFrame({
            "age": [30, 30, 30, 30, 30,  # Group 1: k=5 ✓
                    25, 25, 25,            # Group 2: k=3 ✗
                    35, 35, 35, 35, 35, 35, 35],  # Group 3: k=7 ✓
            "city": ["MTL", "MTL", "MTL", "MTL", "MTL",
                     "QC", "QC", "QC",
                     "OTT", "OTT", "OTT", "OTT", "OTT", "OTT", "OTT"]
        })

        quasi_ids = ["age", "city"]
        k_min, violations_pct = self.evaluator._calculate_k_anonymity(df, quasi_ids)

        # Minimum k is 3 (Group 2)
        assert k_min == 3

        # 3 out of 15 records are in groups with k<5 → 20%
        assert violations_pct == pytest.approx(20.0, abs=0.1)

    def test_k_anonymity_threshold_boundary(self):
        """Test k-anonymity exactly at threshold (k=5)."""
        df = pd.DataFrame({
            "age": [30] * 5 + [25] * 5,  # Two groups of exactly k=5
            "city": ["MTL"] * 5 + ["QC"] * 5
        })

        quasi_ids = ["age", "city"]
        k_min, violations_pct = self.evaluator._calculate_k_anonymity(df, quasi_ids)

        # Both groups have k=5 → acceptable
        assert k_min == 5
        assert violations_pct == 0.0  # No violations (5 >= threshold)

    def test_k_anonymity_no_quasi_identifiers(self):
        """Test k-anonymity when no quasi-identifiers exist."""
        df = pd.DataFrame({
            "income": [50000, 60000, 70000],
            "balance": [1000, 2000, 3000]
        })

        quasi_ids = []
        k_min, violations_pct = self.evaluator._calculate_k_anonymity(df, quasi_ids)

        # Entire dataset is one equivalence class
        assert k_min == len(df)
        assert violations_pct == 0.0

    def test_k_anonymity_single_quasi_identifier(self):
        """Test k-anonymity with single quasi-identifier."""
        df = pd.DataFrame({
            "age_range": ["20-30", "20-30", "20-30", "30-40", "30-40"]
        })

        quasi_ids = ["age_range"]
        k_min, violations_pct = self.evaluator._calculate_k_anonymity(df, quasi_ids)

        # Smallest group has k=2
        assert k_min == 2
        # ALL records are in groups with k<5 (3 and 2) → 100%
        assert violations_pct == 100.0


class TestMinimumResidualRisk:
    """Test minimum residual risk threshold application."""

    def setup_method(self):
        """Create mock database session and evaluator."""
        self.mock_db = Mock()
        self.evaluator = RiskEvaluator(self.mock_db)

    def test_minimum_threshold_zero_input(self):
        """Test that 0% risk is elevated to minimum threshold."""
        result = self.evaluator._apply_minimum_threshold(0.0, "default")

        # Should be elevated to MINIMUM_RESIDUAL_RISK (0.1%)
        assert result >= self.evaluator.MINIMUM_RESIDUAL_RISK
        assert result > 0

    def test_minimum_threshold_context_specific(self):
        """Test context-specific minimum thresholds."""
        # Suppressed quasi-IDs should have 0.5% minimum
        result_suppressed = self.evaluator._apply_minimum_threshold(0.0, "suppressed_quasi_ids")
        assert result_suppressed == 0.5

        # No direct IDs should have 0.3% minimum
        result_no_direct = self.evaluator._apply_minimum_threshold(0.0, "no_direct_ids")
        assert result_no_direct == 0.3

        # k-anonymity should have 0.5% minimum
        result_k_anon = self.evaluator._apply_minimum_threshold(0.0, "k_anonymity")
        assert result_k_anon == 0.5

    def test_minimum_threshold_preserves_high_scores(self):
        """Test that scores above minimum are preserved."""
        high_score = 25.0
        result = self.evaluator._apply_minimum_threshold(high_score, "default")

        # Should remain unchanged
        assert result == high_score

    def test_minimum_threshold_preserves_medium_scores(self):
        """Test that scores between minimum and threshold are preserved."""
        medium_score = 5.0
        result = self.evaluator._apply_minimum_threshold(medium_score, "k_anonymity")

        # Should remain unchanged (5.0 > 0.2)
        assert result == medium_score

    def test_minimum_threshold_boundary(self):
        """Test threshold at exact boundary."""
        boundary_score = 0.1  # Exactly at MINIMUM_RESIDUAL_RISK
        result = self.evaluator._apply_minimum_threshold(boundary_score, "default")

        # Should remain unchanged
        assert result == boundary_score


class TestIndividualizationWithKAnonymity:
    """Test individualization check using k-anonymity."""

    def setup_method(self):
        """Create mock database session and evaluator."""
        self.mock_db = Mock()
        self.evaluator = RiskEvaluator(self.mock_db)

    def test_individualization_no_quasi_identifiers(self):
        """Test individualization when quasi-IDs are suppressed."""
        df = pd.DataFrame({
            "income": [50000, 60000, 70000],
            "balance": [1000, 2000, 3000]
        })

        result = self.evaluator._check_individualization(df, [])

        # Should have LOW risk with residual minimum
        assert result.level == RiskLevel.LOW
        assert result.score >= 0.5  # suppressed_quasi_ids threshold
        assert "résiduel minimal" in result.justification.lower()

    def test_individualization_high_k_anonymity(self):
        """Test individualization with good k-anonymity (k>=10)."""
        # Create dataset with k=10
        df = pd.DataFrame({
            "age": [30] * 10 + [25] * 10,
            "city": ["MTL"] * 10 + ["QC"] * 10
        })

        result = self.evaluator._check_individualization(df, ["age", "city"])

        # Should have LOW risk
        assert result.level == RiskLevel.LOW
        assert "satisfait les standards industriels" in result.justification.lower()

    def test_individualization_low_k_anonymity(self):
        """Test individualization with insufficient k-anonymity (k<5)."""
        # Create dataset with k=2
        df = pd.DataFrame({
            "age": [30, 30, 25, 25, 35, 35],
            "city": ["MTL", "MTL", "QC", "QC", "OTT", "OTT"]
        })

        result = self.evaluator._check_individualization(df, ["age", "city"])

        # Should have HIGH risk
        assert result.level == RiskLevel.HIGH
        assert "risque élevé" in result.justification.lower()
        assert "k=2" in result.justification.lower()

    def test_individualization_moderate_k_anonymity(self):
        """Test individualization with moderate k-anonymity (5<=k<10)."""
        # Create dataset with k=7
        df = pd.DataFrame({
            "age": [30] * 7,
            "city": ["MTL"] * 7
        })

        result = self.evaluator._check_individualization(df, ["age", "city"])

        # Should have LOW to MEDIUM risk
        assert result.level in [RiskLevel.LOW, RiskLevel.MEDIUM]
        assert "k=7" in result.justification.lower()


class TestPostAnonymizationVerifier:
    """Test post-anonymization verification service."""

    def setup_method(self):
        """Create mock services."""
        self.mock_db = Mock()
        self.verifier = PostAnonymizationVerifier(self.mock_db)

        # Mock detector
        self.verifier.detector = Mock()
        self.verifier.detector.analyze_dataset = AsyncMock()

        # Mock risk evaluator
        self.verifier.risk_evaluator = Mock()
        self.verifier.risk_evaluator.evaluate_dataset = AsyncMock()

    @pytest.mark.asyncio
    async def test_verification_pass_clean_dataset(self):
        """Test verification passes for clean anonymized dataset."""
        dataset_id = uuid4()
        job_id = uuid4()

        # Mock detection: NO direct identifiers
        mock_detection = Mock()
        mock_detection.columns = {
            "age_range": Mock(sensitivity_type=DataType.QUASI_IDENTIFIER),
            "income_range": Mock(sensitivity_type=DataType.SENSITIVE)
        }
        self.verifier.detector.analyze_dataset.return_value = mock_detection

        # Mock assessment: Good k-anonymity and low risk
        mock_assessment = Mock()
        mock_assessment.overall_score = 5.0
        mock_assessment.details = {
            "k_anonymity": {
                "k_value": 10,
                "violations_percentage": 0.0
            }
        }
        self.verifier.risk_evaluator.evaluate_dataset.return_value = mock_assessment

        # Mock DB operations
        self.mock_db.add = Mock()
        self.mock_db.commit = Mock()

        # Run verification
        report = await self.verifier.verify_anonymization(dataset_id, job_id)

        # Should PASS
        assert report.passed is True
        assert report.failure_reason is None
        assert len(report.direct_ids_detected) == 0
        assert report.k_anonymity_value == 10
        assert "✅" in report.recommendations[0]

    @pytest.mark.asyncio
    async def test_verification_fail_direct_identifiers(self):
        """Test verification fails when direct IDs are still present."""
        dataset_id = uuid4()
        job_id = uuid4()

        # Mock detection: DIRECT IDENTIFIERS FOUND!
        mock_detection = Mock()
        mock_detection.columns = {
            "email": Mock(sensitivity_type=DataType.DIRECT_IDENTIFIER),
            "nas": Mock(sensitivity_type=DataType.DIRECT_IDENTIFIER),
            "age_range": Mock(sensitivity_type=DataType.QUASI_IDENTIFIER)
        }
        self.verifier.detector.analyze_dataset.return_value = mock_detection

        # Mock assessment
        mock_assessment = Mock()
        mock_assessment.overall_score = 15.0
        mock_assessment.details = {"k_anonymity": {"k_value": 5, "violations_percentage": 0.0}}
        self.verifier.risk_evaluator.evaluate_dataset.return_value = mock_assessment

        self.mock_db.add = Mock()
        self.mock_db.commit = Mock()

        # Run verification
        report = await self.verifier.verify_anonymization(dataset_id, job_id)

        # Should FAIL
        assert report.passed is False
        assert "ÉCHEC CRITIQUE" in report.failure_reason
        assert len(report.direct_ids_detected) == 2
        assert "email" in report.direct_ids_detected
        assert "nas" in report.direct_ids_detected

    @pytest.mark.asyncio
    async def test_verification_fail_insufficient_k_anonymity(self):
        """Test verification fails when k-anonymity is insufficient."""
        dataset_id = uuid4()
        job_id = uuid4()

        # Mock detection: No direct IDs
        mock_detection = Mock()
        mock_detection.columns = {
            "age_range": Mock(sensitivity_type=DataType.QUASI_IDENTIFIER)
        }
        self.verifier.detector.analyze_dataset.return_value = mock_detection

        # Mock assessment: BAD k-anonymity (k=2)
        mock_assessment = Mock()
        mock_assessment.overall_score = 15.0
        mock_assessment.details = {
            "k_anonymity": {
                "k_value": 2,
                "violations_percentage": 60.0
            }
        }
        self.verifier.risk_evaluator.evaluate_dataset.return_value = mock_assessment

        self.mock_db.add = Mock()
        self.mock_db.commit = Mock()

        # Run verification
        report = await self.verifier.verify_anonymization(dataset_id, job_id)

        # Should FAIL
        assert report.passed is False
        assert "k-anonymité insuffisante" in report.failure_reason
        assert report.k_anonymity_value == 2
        assert report.k_violations_percentage == 60.0

    @pytest.mark.asyncio
    async def test_verification_fail_high_overall_risk(self):
        """Test verification fails when overall risk is still too high."""
        dataset_id = uuid4()
        job_id = uuid4()

        # Mock detection: No direct IDs
        mock_detection = Mock()
        mock_detection.columns = {
            "age_range": Mock(sensitivity_type=DataType.QUASI_IDENTIFIER)
        }
        self.verifier.detector.analyze_dataset.return_value = mock_detection

        # Mock assessment: Good k but HIGH overall risk (correlation/inference issues)
        mock_assessment = Mock()
        mock_assessment.overall_score = 25.0  # Above 20% threshold
        mock_assessment.details = {
            "k_anonymity": {
                "k_value": 10,
                "violations_percentage": 0.0
            }
        }
        self.verifier.risk_evaluator.evaluate_dataset.return_value = mock_assessment

        self.mock_db.add = Mock()
        self.mock_db.commit = Mock()

        # Run verification
        report = await self.verifier.verify_anonymization(dataset_id, job_id)

        # Should FAIL
        assert report.passed is False
        assert "Risque global toujours élevé" in report.failure_reason
        assert report.overall_risk_score == 25.0

    @pytest.mark.asyncio
    async def test_verification_recommendations_direct_ids(self):
        """Test recommendations when direct IDs are found."""
        dataset_id = uuid4()
        job_id = uuid4()

        # Mock detection with direct IDs
        mock_detection = Mock()
        mock_detection.columns = {
            "email": Mock(sensitivity_type=DataType.DIRECT_IDENTIFIER),
            "phone": Mock(sensitivity_type=DataType.DIRECT_IDENTIFIER)
        }
        self.verifier.detector.analyze_dataset.return_value = mock_detection

        mock_assessment = Mock()
        mock_assessment.overall_score = 15.0
        mock_assessment.details = {"k_anonymity": None}
        self.verifier.risk_evaluator.evaluate_dataset.return_value = mock_assessment

        self.mock_db.add = Mock()
        self.mock_db.commit = Mock()

        report = await self.verifier.verify_anonymization(dataset_id, job_id)

        # Should have recommendations to fix direct IDs
        assert any("🔴 CRITIQUE" in rec for rec in report.recommendations)
        assert any("email" in rec for rec in report.recommendations)

    @pytest.mark.asyncio
    async def test_verification_saves_to_database(self):
        """Test that verification results are saved to verification_logs."""
        dataset_id = uuid4()
        job_id = uuid4()

        mock_detection = Mock()
        mock_detection.columns = {}
        self.verifier.detector.analyze_dataset.return_value = mock_detection

        mock_assessment = Mock()
        mock_assessment.overall_score = 5.0
        mock_assessment.details = {"k_anonymity": {"k_value": 10, "violations_percentage": 0.0}}
        self.verifier.risk_evaluator.evaluate_dataset.return_value = mock_assessment

        self.mock_db.add = Mock()
        self.mock_db.commit = Mock()

        await self.verifier.verify_anonymization(dataset_id, job_id)

        # Verify DB operations were called
        assert self.mock_db.add.called
        assert self.mock_db.commit.called


class TestRegressionPrevention:
    """Test that Phase 1 fixes prevent regression to old bugs."""

    def setup_method(self):
        """Create mock database session and evaluator."""
        self.mock_db = Mock()
        self.evaluator = RiskEvaluator(self.mock_db)

    def test_no_zero_risk_after_full_anonymization(self):
        """
        REGRESSION TEST: Ensure risk never shows 0% after anonymization.

        This was the critical bug identified in the cahier de charges.
        """
        # Simulate fully anonymized dataset (all quasi-IDs suppressed)
        df = pd.DataFrame({
            "income_range": ["50k-100k", "50k-100k", "100k-150k"],
            "balance_range": ["0-10k", "10k-50k", "0-10k"]
        })

        # No quasi-identifiers (all suppressed)
        result = self.evaluator._check_individualization(df, [])

        # MUST NOT be 0%
        assert result.score > 0
        assert result.score >= 0.1  # At least minimum threshold

    def test_k_anonymity_used_not_uniqueness(self):
        """
        REGRESSION TEST: Ensure k-anonymity is used, not simple uniqueness ratio.

        Old bug: Used len(unique_combinations) / total_rows
        Correct: Use minimum group size (k-anonymity)
        """
        # Dataset with 50% unique combinations but k=1
        df = pd.DataFrame({
            "age": [25, 25, 30, 35, 40],  # 50% unique ages
            "city": ["MTL", "MTL", "QC", "OTT", "TOR"]
        })

        quasi_ids = ["age", "city"]
        k_min, violations_pct = self.evaluator._calculate_k_anonymity(df, quasi_ids)

        # Should detect k=1 (not just 50% uniqueness)
        assert k_min == 1
        assert violations_pct == 100.0  # All records in groups < 5


if __name__ == "__main__":
    """Run Phase 1 tests with pytest."""
    pytest.main([__file__, "-v", "-s"])
