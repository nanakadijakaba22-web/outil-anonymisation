"""
Differential Privacy Service

Implements differential privacy mechanisms for mathematical privacy guarantees.

Differential Privacy (Dwork, 2006) provides formal guarantees that an individual's
data cannot be distinguished in the output, even with arbitrary background knowledge.

Key concept: Adding calibrated noise proportional to:
- Query sensitivity (how much one person affects the result)
- Privacy budget epsilon (ε) - smaller = more private

Privacy Levels (industry standards):
- Strong: ε < 0.1 (rare, very noisy)
- Moderate: ε = 1.0 (US Census 2020, balanced utility/privacy)
- Weak: ε > 10 (minimal noise, weaker guarantee)

References:
- Dwork, C. (2006). "Differential Privacy"
- NIST SP 800-188 (2023): "De-Identifying Government Datasets"
- US Census Bureau: Used ε=1.0 for 2020 census
- Apple: Uses local DP with ε≈2-4 for telemetry

IMPORTANT: This is OPTIONAL in Annoy. Differential Privacy adds noise to data,
which reduces utility. Use only when formal privacy guarantees are required.
"""

import numpy as np
import pandas as pd
from typing import Union, Tuple
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class DPMechanism(str, Enum):
    """Differential privacy mechanisms."""
    LAPLACE = "laplace"      # For continuous numeric data (pure DP)
    GAUSSIAN = "gaussian"    # For continuous numeric data (approximate DP)


class PrivacyLevel(str, Enum):
    """Standard privacy levels based on epsilon values."""
    STRONG = "strong"        # ε < 0.1
    MODERATE = "moderate"    # ε ≈ 1.0
    WEAK = "weak"           # ε > 10


class DifferentialPrivacyEngine:
    """
    Applies differential privacy mechanisms to numeric data.

    Differential privacy ensures that removing or adding a single individual
    to the dataset does not significantly change the output distribution.

    Mathematical guarantee (pure DP):
        P[M(D) ∈ S] ≤ e^ε × P[M(D') ∈ S]
    where D and D' differ by one record.

    Usage:
        engine = DifferentialPrivacyEngine(epsilon=1.0)
        noisy_column = engine.add_noise(df["age"], mechanism="laplace")
    """

    # Privacy level thresholds (epsilon values)
    EPSILON_THRESHOLDS = {
        PrivacyLevel.STRONG: 0.1,
        PrivacyLevel.MODERATE: 1.0,
        PrivacyLevel.WEAK: 10.0
    }

    def __init__(
        self,
        epsilon: float = 1.0,
        delta: float = 1e-5,
        seed: int = None
    ):
        """
        Initialize differential privacy engine.

        Args:
            epsilon: Privacy budget (ε). Lower = more private, more noise.
                     Typical values: 0.01 (strong), 1.0 (moderate), 10 (weak)
            delta: Failure probability for approximate DP (δ). Only used with Gaussian.
                   Should be << 1/n where n is dataset size. Typical: 1e-5.
            seed: Random seed for reproducibility (optional)

        Raises:
            ValueError: If epsilon <= 0 or delta not in (0, 1)
        """
        if epsilon <= 0:
            raise ValueError(f"Epsilon must be > 0, got {epsilon}")
        if not (0 < delta < 1):
            raise ValueError(f"Delta must be in (0, 1), got {delta}")

        self.epsilon = epsilon
        self.delta = delta
        self.privacy_level = self._classify_privacy_level(epsilon)

        # Set random seed for reproducibility
        if seed is not None:
            np.random.seed(seed)

        logger.info(
            f"Initialized DP engine: ε={epsilon}, δ={delta}, "
            f"privacy level={self.privacy_level.value}"
        )

    def _classify_privacy_level(self, epsilon: float) -> PrivacyLevel:
        """Classify epsilon into privacy strength category."""
        if epsilon < self.EPSILON_THRESHOLDS[PrivacyLevel.STRONG]:
            return PrivacyLevel.STRONG
        elif epsilon <= self.EPSILON_THRESHOLDS[PrivacyLevel.MODERATE]:
            return PrivacyLevel.MODERATE
        else:
            return PrivacyLevel.WEAK

    def calculate_sensitivity(
        self,
        data: pd.Series,
        query_type: str = "identity"
    ) -> float:
        """
        Calculate sensitivity of a query on the data.

        Sensitivity = maximum change in query output when one record changes.

        Args:
            data: Input data column
            query_type: Type of query:
                - "identity": Individual value (sensitivity = max - min)
                - "count": Counting query (sensitivity = 1)
                - "mean": Average (sensitivity = (max - min) / n)
                - "sum": Sum (sensitivity = max - min)

        Returns:
            Sensitivity value

        Example:
            ages = pd.Series([25, 30, 35, 40, 45])
            sensitivity = engine.calculate_sensitivity(ages, "identity")
            # Returns 20.0 (45 - 25)
        """
        if query_type == "count":
            return 1.0

        # For numeric queries, need range
        data_clean = data.dropna()
        if len(data_clean) == 0:
            return 1.0

        data_range = data_clean.max() - data_clean.min()

        if query_type == "identity":
            return data_range
        elif query_type == "mean":
            return data_range / len(data_clean)
        elif query_type == "sum":
            return data_range
        else:
            raise ValueError(f"Unknown query type: {query_type}")

    def add_laplace_noise(
        self,
        data: Union[pd.Series, float],
        sensitivity: float
    ) -> Union[pd.Series, float]:
        """
        Add Laplace noise for pure differential privacy.

        Laplace mechanism (Dwork et al., 2006):
            Noise ~ Laplace(0, sensitivity / ε)

        Pure DP guarantee: Pr[M(D) = x] / Pr[M(D') = x] ≤ e^ε

        Args:
            data: Input data (Series or scalar)
            sensitivity: Query sensitivity (∆f)

        Returns:
            Noisy data with same shape as input

        Example:
            # Add noise to age column
            noisy_ages = engine.add_laplace_noise(df["age"], sensitivity=20)
        """
        scale = sensitivity / self.epsilon

        if isinstance(data, pd.Series):
            noise = np.random.laplace(0, scale, size=len(data))
            return data + noise
        else:
            noise = np.random.laplace(0, scale)
            return data + noise

    def add_gaussian_noise(
        self,
        data: Union[pd.Series, float],
        sensitivity: float
    ) -> Union[pd.Series, float]:
        """
        Add Gaussian noise for approximate differential privacy.

        Gaussian mechanism:
            σ = (sensitivity / ε) × sqrt(2 × ln(1.25 / δ))
            Noise ~ N(0, σ²)

        Approximate DP: (ε, δ)-DP where δ is failure probability.

        More efficient than Laplace for large datasets, but weaker guarantee.

        Args:
            data: Input data (Series or scalar)
            sensitivity: Query sensitivity (∆f)

        Returns:
            Noisy data with same shape as input

        Example:
            # Add Gaussian noise to income
            noisy_income = engine.add_gaussian_noise(df["income"], sensitivity=100000)
        """
        # Standard deviation for Gaussian noise
        # Formula from Dwork & Roth (2014)
        sigma = (sensitivity / self.epsilon) * np.sqrt(2 * np.log(1.25 / self.delta))

        if isinstance(data, pd.Series):
            noise = np.random.normal(0, sigma, size=len(data))
            return data + noise
        else:
            noise = np.random.normal(0, sigma)
            return data + noise

    def add_noise(
        self,
        data: pd.Series,
        mechanism: DPMechanism = DPMechanism.LAPLACE,
        sensitivity: float = None,
        auto_sensitivity: str = "identity"
    ) -> Tuple[pd.Series, dict]:
        """
        Add differential privacy noise to a data column.

        Main entry point for applying DP to a column.

        Args:
            data: Input data column
            mechanism: Noise mechanism (laplace or gaussian)
            sensitivity: Manual sensitivity value (optional)
            auto_sensitivity: Auto-calculate sensitivity using this query type
                             (used if sensitivity=None)

        Returns:
            (noisy_data, metadata) where metadata contains:
                - epsilon, delta, mechanism
                - sensitivity used
                - noise_magnitude (std dev of noise added)

        Example:
            engine = DifferentialPrivacyEngine(epsilon=1.0)
            noisy_ages, meta = engine.add_noise(df["age"], mechanism="laplace")
            print(f"Added {meta['noise_magnitude']:.2f} noise to ages")
        """
        # Calculate sensitivity if not provided
        if sensitivity is None:
            sensitivity = self.calculate_sensitivity(data, auto_sensitivity)

        # Add noise based on mechanism
        if mechanism == DPMechanism.LAPLACE:
            noisy_data = self.add_laplace_noise(data, sensitivity)
            scale = sensitivity / self.epsilon
            noise_magnitude = scale * np.sqrt(2)  # Laplace std dev = scale * sqrt(2)
        elif mechanism == DPMechanism.GAUSSIAN:
            noisy_data = self.add_gaussian_noise(data, sensitivity)
            noise_magnitude = (sensitivity / self.epsilon) * np.sqrt(2 * np.log(1.25 / self.delta))
        else:
            raise ValueError(f"Unknown mechanism: {mechanism}")

        # Build metadata
        metadata = {
            "mechanism": mechanism.value,
            "epsilon": self.epsilon,
            "delta": self.delta,
            "sensitivity": sensitivity,
            "noise_magnitude": noise_magnitude,
            "privacy_level": self.privacy_level.value
        }

        logger.info(
            f"Applied {mechanism.value} noise: ε={self.epsilon}, "
            f"sensitivity={sensitivity:.2f}, noise_std={noise_magnitude:.2f}"
        )

        return noisy_data, metadata

    def apply_to_column(
        self,
        df: pd.DataFrame,
        column_name: str,
        mechanism: DPMechanism = DPMechanism.LAPLACE,
        sensitivity: float = None,
        clip_to_range: bool = True
    ) -> Tuple[pd.DataFrame, dict]:
        """
        Apply differential privacy to a specific column in-place.

        Convenience method for anonymization pipeline integration.

        Args:
            df: Input dataframe
            column_name: Column to add noise to
            mechanism: Laplace or Gaussian
            sensitivity: Manual sensitivity (optional, auto-calculated if None)
            clip_to_range: If True, clip noisy values to original [min, max]

        Returns:
            (modified_df, metadata)

        Example:
            df, meta = engine.apply_to_column(
                df, "age",
                mechanism="laplace",
                clip_to_range=True
            )
        """
        if column_name not in df.columns:
            raise ValueError(f"Column '{column_name}' not found in dataframe")

        original_data = df[column_name].copy()

        # Add noise
        noisy_data, metadata = self.add_noise(
            original_data,
            mechanism=mechanism,
            sensitivity=sensitivity
        )

        # Clip to original range if requested
        if clip_to_range:
            original_min = original_data.min()
            original_max = original_data.max()
            noisy_data = noisy_data.clip(lower=original_min, upper=original_max)
            metadata["clipped"] = True
            metadata["range"] = (original_min, original_max)

        # Update dataframe
        df[column_name] = noisy_data

        return df, metadata

    def estimate_privacy_loss(self, n_queries: int) -> dict:
        """
        Estimate cumulative privacy loss from multiple queries.

        Privacy budget (ε) is consumed with each query. Sequential composition:
            ε_total = Σ ε_i

        Args:
            n_queries: Number of queries to simulate

        Returns:
            Dictionary with:
                - total_epsilon: Cumulative privacy budget used
                - privacy_level: Resulting privacy level
                - recommendation: Guidance on budget

        Example:
            loss = engine.estimate_privacy_loss(n_queries=10)
            print(f"After 10 queries: ε={loss['total_epsilon']}")
        """
        total_epsilon = self.epsilon * n_queries
        privacy_level = self._classify_privacy_level(total_epsilon)

        recommendation = ""
        if privacy_level == PrivacyLevel.WEAK:
            recommendation = (
                f"⚠️ Total ε={total_epsilon:.2f} is weak. "
                "Consider reducing epsilon per query or limiting number of queries."
            )
        elif privacy_level == PrivacyLevel.MODERATE:
            recommendation = f"Moderate privacy with ε={total_epsilon:.2f}. Acceptable for most uses."
        else:
            recommendation = f"✅ Strong privacy maintained with ε={total_epsilon:.2f}."

        return {
            "queries": n_queries,
            "epsilon_per_query": self.epsilon,
            "total_epsilon": total_epsilon,
            "privacy_level": privacy_level.value,
            "recommendation": recommendation
        }


def get_recommended_epsilon(
    data_sensitivity: str = "moderate",
    use_case: str = "general"
) -> float:
    """
    Get recommended epsilon value for common scenarios.

    Args:
        data_sensitivity: "low", "moderate", "high"
        use_case: "general", "research", "census", "medical"

    Returns:
        Recommended epsilon value

    Examples:
        ε = get_recommended_epsilon("high", "medical")  # Returns 0.1
        ε = get_recommended_epsilon("moderate", "census")  # Returns 1.0
    """
    recommendations = {
        ("low", "general"): 10.0,
        ("low", "research"): 5.0,
        ("moderate", "general"): 1.0,    # US Census 2020 standard
        ("moderate", "research"): 0.5,
        ("moderate", "census"): 1.0,
        ("high", "general"): 0.5,
        ("high", "research"): 0.1,
        ("high", "medical"): 0.1,
        ("high", "census"): 0.5,
    }

    key = (data_sensitivity.lower(), use_case.lower())
    if key in recommendations:
        return recommendations[key]
    else:
        # Default to moderate
        logger.warning(
            f"No recommendation for {key}, defaulting to ε=1.0"
        )
        return 1.0
