"""
Unit Tests for Phase 2: Differential Privacy

Tests the differential privacy implementation:
1. Laplace and Gaussian noise mechanisms
2. Epsilon/delta privacy guarantees
3. Sensitivity calculation
4. Privacy budget tracking
"""

import pytest
import numpy as np
import pandas as pd
from unittest.mock import Mock

from app.services.differential_privacy import (
    DifferentialPrivacyEngine,
    DPMechanism,
    PrivacyLevel,
    get_recommended_epsilon
)


class TestDifferentialPrivacyEngine:
    """Test core differential privacy engine functionality."""

    def test_engine_initialization(self):
        """Test DP engine initialization with valid parameters."""
        engine = DifferentialPrivacyEngine(epsilon=1.0, delta=1e-5)

        assert engine.epsilon == 1.0
        assert engine.delta == 1e-5
        assert engine.privacy_level == PrivacyLevel.MODERATE

    def test_engine_initialization_invalid_epsilon(self):
        """Test that invalid epsilon raises ValueError."""
        with pytest.raises(ValueError, match="Epsilon must be > 0"):
            DifferentialPrivacyEngine(epsilon=0.0)

        with pytest.raises(ValueError, match="Epsilon must be > 0"):
            DifferentialPrivacyEngine(epsilon=-1.0)

    def test_engine_initialization_invalid_delta(self):
        """Test that invalid delta raises ValueError."""
        with pytest.raises(ValueError, match="Delta must be in"):
            DifferentialPrivacyEngine(epsilon=1.0, delta=0.0)

        with pytest.raises(ValueError, match="Delta must be in"):
            DifferentialPrivacyEngine(epsilon=1.0, delta=1.0)

    def test_privacy_level_classification_strong(self):
        """Test classification of strong privacy (ε < 0.1)."""
        engine = DifferentialPrivacyEngine(epsilon=0.05)
        assert engine.privacy_level == PrivacyLevel.STRONG

    def test_privacy_level_classification_moderate(self):
        """Test classification of moderate privacy (ε = 1.0)."""
        engine = DifferentialPrivacyEngine(epsilon=1.0)
        assert engine.privacy_level == PrivacyLevel.MODERATE

    def test_privacy_level_classification_weak(self):
        """Test classification of weak privacy (ε > 10)."""
        engine = DifferentialPrivacyEngine(epsilon=15.0)
        assert engine.privacy_level == PrivacyLevel.WEAK


class TestSensitivityCalculation:
    """Test sensitivity calculation for different query types."""

    def setup_method(self):
        """Create DP engine."""
        self.engine = DifferentialPrivacyEngine(epsilon=1.0)

    def test_sensitivity_count_query(self):
        """Test sensitivity for counting query (always 1)."""
        data = pd.Series([1, 2, 3, 4, 5])
        sensitivity = self.engine.calculate_sensitivity(data, "count")

        assert sensitivity == 1.0

    def test_sensitivity_identity_query(self):
        """Test sensitivity for identity query (max - min)."""
        data = pd.Series([10, 20, 30, 40, 50])
        sensitivity = self.engine.calculate_sensitivity(data, "identity")

        # Range = 50 - 10 = 40
        assert sensitivity == 40.0

    def test_sensitivity_mean_query(self):
        """Test sensitivity for mean query."""
        data = pd.Series([10, 20, 30, 40, 50])
        sensitivity = self.engine.calculate_sensitivity(data, "mean")

        # Range / n = (50 - 10) / 5 = 8.0
        assert sensitivity == 8.0

    def test_sensitivity_sum_query(self):
        """Test sensitivity for sum query."""
        data = pd.Series([10, 20, 30, 40, 50])
        sensitivity = self.engine.calculate_sensitivity(data, "sum")

        # Range = 50 - 10 = 40
        assert sensitivity == 40.0

    def test_sensitivity_with_nulls(self):
        """Test sensitivity calculation handles null values."""
        data = pd.Series([10, None, 30, None, 50])
        sensitivity = self.engine.calculate_sensitivity(data, "identity")

        # Should ignore nulls: range = 50 - 10 = 40
        assert sensitivity == 40.0


class TestLaplaceNoise:
    """Test Laplace noise mechanism (pure DP)."""

    def setup_method(self):
        """Create DP engine with fixed seed for reproducibility."""
        self.engine = DifferentialPrivacyEngine(epsilon=1.0, seed=42)

    def test_laplace_noise_scalar(self):
        """Test Laplace noise on scalar value."""
        original_value = 100.0
        sensitivity = 10.0

        noisy_value = self.engine.add_laplace_noise(original_value, sensitivity)

        # Noise should be added (not equal)
        assert noisy_value != original_value

        # Should be within reasonable bounds (scale = sensitivity/epsilon = 10)
        # With high probability, noise is within ~3*scale
        assert abs(noisy_value - original_value) < 30

    def test_laplace_noise_series(self):
        """Test Laplace noise on pandas Series."""
        data = pd.Series([10, 20, 30, 40, 50])
        sensitivity = 40.0

        noisy_data = self.engine.add_laplace_noise(data, sensitivity)

        # Should return Series of same length
        assert len(noisy_data) == len(data)

        # Values should be different
        assert not np.allclose(noisy_data.values, data.values)

    def test_laplace_noise_scale(self):
        """Test Laplace noise respects epsilon scaling."""
        data = pd.Series([100] * 100)  # Constant values
        sensitivity = 10.0

        # Low epsilon = more noise
        engine_low = DifferentialPrivacyEngine(epsilon=0.1, seed=42)
        noisy_low = engine_low.add_laplace_noise(data, sensitivity)

        # High epsilon = less noise
        engine_high = DifferentialPrivacyEngine(epsilon=10.0, seed=42)
        noisy_high = engine_high.add_laplace_noise(data, sensitivity)

        # Low epsilon should have higher variance
        std_low = noisy_low.std()
        std_high = noisy_high.std()

        assert std_low > std_high


class TestGaussianNoise:
    """Test Gaussian noise mechanism (approximate DP)."""

    def setup_method(self):
        """Create DP engine with Gaussian mechanism."""
        self.engine = DifferentialPrivacyEngine(epsilon=1.0, delta=1e-5, seed=42)

    def test_gaussian_noise_scalar(self):
        """Test Gaussian noise on scalar value."""
        original_value = 100.0
        sensitivity = 10.0

        noisy_value = self.engine.add_gaussian_noise(original_value, sensitivity)

        # Noise should be added
        assert noisy_value != original_value

    def test_gaussian_noise_series(self):
        """Test Gaussian noise on pandas Series."""
        data = pd.Series([10, 20, 30, 40, 50])
        sensitivity = 40.0

        noisy_data = self.engine.add_gaussian_noise(data, sensitivity)

        assert len(noisy_data) == len(data)
        assert not np.allclose(noisy_data.values, data.values)

    def test_gaussian_vs_laplace(self):
        """Test that Gaussian and Laplace produce different noise."""
        data = pd.Series([100] * 100)
        sensitivity = 10.0

        engine = DifferentialPrivacyEngine(epsilon=1.0, delta=1e-5, seed=42)

        laplace = engine.add_laplace_noise(data.copy(), sensitivity)
        gaussian = engine.add_gaussian_noise(data.copy(), sensitivity)

        # Should be different mechanisms
        assert not np.allclose(laplace.values, gaussian.values)


class TestApplyToColumn:
    """Test applying DP to dataframe columns."""

    def setup_method(self):
        """Create test dataframe and DP engine."""
        self.df = pd.DataFrame({
            "age": [25, 30, 35, 40, 45, 50, 55, 60, 65, 70],
            "income": [30000, 40000, 50000, 60000, 70000, 80000, 90000, 100000, 110000, 120000]
        })
        self.engine = DifferentialPrivacyEngine(epsilon=1.0, seed=42)

    def test_apply_laplace_to_column(self):
        """Test applying Laplace noise to a column."""
        original_ages = self.df["age"].copy()

        df_noisy, metadata = self.engine.apply_to_column(
            self.df.copy(),
            "age",
            mechanism=DPMechanism.LAPLACE
        )

        # Column should be modified
        assert not np.allclose(df_noisy["age"].values, original_ages.values)

        # Metadata should be returned
        assert metadata["mechanism"] == "laplace"
        assert metadata["epsilon"] == 1.0
        assert "sensitivity" in metadata
        assert "noise_magnitude" in metadata

    def test_apply_gaussian_to_column(self):
        """Test applying Gaussian noise to a column."""
        original_income = self.df["income"].copy()

        df_noisy, metadata = self.engine.apply_to_column(
            self.df.copy(),
            "income",
            mechanism=DPMechanism.GAUSSIAN
        )

        assert not np.allclose(df_noisy["income"].values, original_income.values)
        assert metadata["mechanism"] == "gaussian"

    def test_apply_with_clipping(self):
        """Test that clipping keeps values in original range."""
        df_noisy, metadata = self.engine.apply_to_column(
            self.df.copy(),
            "age",
            mechanism=DPMechanism.LAPLACE,
            clip_to_range=True
        )

        # All values should be within original range
        assert df_noisy["age"].min() >= self.df["age"].min()
        assert df_noisy["age"].max() <= self.df["age"].max()

        # Metadata should indicate clipping
        assert metadata["clipped"] is True
        assert "range" in metadata

    def test_apply_without_clipping(self):
        """Test DP without clipping allows values outside range."""
        # Use high noise (low epsilon)
        engine = DifferentialPrivacyEngine(epsilon=0.01, seed=42)

        df_noisy, metadata = engine.apply_to_column(
            self.df.copy(),
            "age",
            mechanism=DPMechanism.LAPLACE,
            clip_to_range=False
        )

        # Some values might be outside original range
        # (not guaranteed, but likely with high noise)
        # Just check that clipping flag is false
        assert "clipped" not in metadata or metadata["clipped"] is False

    def test_apply_invalid_column(self):
        """Test applying DP to non-existent column raises error."""
        with pytest.raises(ValueError, match="Column .* not found"):
            self.engine.apply_to_column(
                self.df,
                "nonexistent_column",
                mechanism=DPMechanism.LAPLACE
            )


class TestPrivacyBudgetTracking:
    """Test privacy budget composition and tracking."""

    def test_single_query_budget(self):
        """Test privacy budget for single query."""
        engine = DifferentialPrivacyEngine(epsilon=1.0)

        loss = engine.estimate_privacy_loss(n_queries=1)

        assert loss["queries"] == 1
        assert loss["epsilon_per_query"] == 1.0
        assert loss["total_epsilon"] == 1.0
        assert loss["privacy_level"] == "moderate"

    def test_multiple_queries_budget(self):
        """Test privacy budget composition for multiple queries."""
        engine = DifferentialPrivacyEngine(epsilon=1.0)

        loss = engine.estimate_privacy_loss(n_queries=10)

        # Sequential composition: total = n * epsilon
        assert loss["total_epsilon"] == 10.0
        assert loss["privacy_level"] == "weak"  # 10 > weak threshold

    def test_budget_warning_for_high_consumption(self):
        """Test that high budget consumption generates warning."""
        engine = DifferentialPrivacyEngine(epsilon=5.0)

        loss = engine.estimate_privacy_loss(n_queries=10)

        # Total = 50, should be weak and have warning
        assert loss["total_epsilon"] == 50.0
        assert "⚠️" in loss["recommendation"]

    def test_budget_success_for_low_consumption(self):
        """Test that low budget consumption is confirmed."""
        engine = DifferentialPrivacyEngine(epsilon=0.01)

        loss = engine.estimate_privacy_loss(n_queries=5)

        # Total = 0.05, still strong
        assert loss["total_epsilon"] == 0.05
        assert "✅" in loss["recommendation"]


class TestRecommendedEpsilon:
    """Test epsilon recommendation function."""

    def test_low_sensitivity_general(self):
        """Test recommendation for low sensitivity data."""
        epsilon = get_recommended_epsilon("low", "general")
        assert epsilon == 10.0

    def test_moderate_census(self):
        """Test US Census 2020 standard."""
        epsilon = get_recommended_epsilon("moderate", "census")
        assert epsilon == 1.0

    def test_high_medical(self):
        """Test strong privacy for medical data."""
        epsilon = get_recommended_epsilon("high", "medical")
        assert epsilon == 0.1

    def test_default_fallback(self):
        """Test default fallback for unknown combination."""
        epsilon = get_recommended_epsilon("unknown", "unknown")
        assert epsilon == 1.0  # Default moderate


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_zero_variance_data(self):
        """Test DP on data with zero variance (all same values)."""
        data = pd.Series([100] * 10)
        engine = DifferentialPrivacyEngine(epsilon=1.0, seed=42)

        # Sensitivity should be 0 for constant data
        sensitivity = engine.calculate_sensitivity(data, "identity")
        assert sensitivity == 0.0

        # Adding noise with 0 sensitivity should still work
        noisy, metadata = engine.add_noise(data, mechanism=DPMechanism.LAPLACE)
        # Noise will be very small (scale = 0 / epsilon = 0)
        assert len(noisy) == len(data)

    def test_single_value_series(self):
        """Test DP on single-value Series."""
        data = pd.Series([42])
        engine = DifferentialPrivacyEngine(epsilon=1.0)

        noisy, metadata = engine.add_noise(data, mechanism=DPMechanism.LAPLACE)

        assert len(noisy) == 1
        assert metadata["sensitivity"] == 0.0  # Only one value, no range

    def test_all_null_series(self):
        """Test DP on Series with all null values."""
        data = pd.Series([None, None, None])
        engine = DifferentialPrivacyEngine(epsilon=1.0)

        sensitivity = engine.calculate_sensitivity(data, "identity")
        # Should default to 1.0 when no valid data
        assert sensitivity == 1.0


class TestDifferentialPrivacyIntegration:
    """Test integration with anonymization pipeline."""

    def test_dp_reduces_utility_but_preserves_distribution(self):
        """Test that DP preserves statistical properties (approximately)."""
        # Create large dataset
        np.random.seed(42)
        data = pd.Series(np.random.normal(100, 15, 1000))

        engine = DifferentialPrivacyEngine(epsilon=1.0, seed=42)

        noisy_data, metadata = engine.add_noise(
            data,
            mechanism=DPMechanism.LAPLACE,
            clip_to_range=False
        )

        # Mean should be approximately preserved
        original_mean = data.mean()
        noisy_mean = noisy_data.mean()

        # With epsilon=1.0 and large n, mean should be close
        assert abs(noisy_mean - original_mean) < 5  # Within 5 units

    def test_privacy_accuracy_tradeoff(self):
        """Test fundamental privacy-accuracy tradeoff."""
        data = pd.Series([100] * 100)
        sensitivity = 10.0

        # Strong privacy (low epsilon) = high noise
        strong = DifferentialPrivacyEngine(epsilon=0.1, seed=42)
        noisy_strong = strong.add_laplace_noise(data.copy(), sensitivity)

        # Weak privacy (high epsilon) = low noise
        weak = DifferentialPrivacyEngine(epsilon=10.0, seed=42)
        noisy_weak = weak.add_laplace_noise(data.copy(), sensitivity)

        # Strong privacy should have higher error
        error_strong = np.abs(noisy_strong - data).mean()
        error_weak = np.abs(noisy_weak - data).mean()

        assert error_strong > error_weak


if __name__ == "__main__":
    """Run Phase 2 DP tests with pytest."""
    pytest.main([__file__, "-v", "-s"])
