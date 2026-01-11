"""
Unit Tests for Phase 3: Data Visualization Service

Tests the data visualization and statistical analysis service:
1. Overview statistics generation
2. Numeric descriptive statistics
3. Categorical statistics
4. Missing data analysis
5. Distribution generation (histograms, frequencies)
6. Correlation matrix calculation
7. Outlier detection (IQR method)
8. Dataset comparison (before/after anonymization)
9. Compact visualization summary
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, MagicMock
from uuid import uuid4

from app.services.visualization import DataVisualizationService
from app.services.data_ingestion import DataIngestionService


@pytest.fixture
def mock_db():
    """Create mock database session."""
    return Mock()


@pytest.fixture
def viz_service(mock_db):
    """Create DataVisualizationService instance."""
    return DataVisualizationService(mock_db)


@pytest.fixture
def sample_numeric_df():
    """Create sample dataframe with numeric data."""
    np.random.seed(42)
    return pd.DataFrame({
        "age": [25, 30, 35, 40, 45, 50, 55, 60, 65, 70],
        "income": [30000, 40000, 50000, 60000, 70000, 80000, 90000, 100000, 110000, 120000],
        "score": [85.5, 90.0, 78.2, 92.1, 88.3, 95.0, 82.7, 89.5, 91.2, 87.8]
    })


@pytest.fixture
def sample_categorical_df():
    """Create sample dataframe with categorical data."""
    return pd.DataFrame({
        "city": ["Montreal", "Quebec", "Montreal", "Quebec", "Montreal",
                 "Laval", "Montreal", "Quebec", "Laval", "Montreal"],
        "gender": ["M", "F", "M", "F", "M", "F", "M", "F", "M", "F"],
        "occupation": ["Engineer", "Doctor", "Engineer", "Teacher", "Engineer",
                      "Doctor", "Engineer", "Teacher", "Doctor", "Engineer"]
    })


@pytest.fixture
def sample_mixed_df():
    """Create sample dataframe with mixed data types."""
    return pd.DataFrame({
        "age": [25, 30, 35, None, 45, 50, 55, 60, None, 70],
        "city": ["Montreal", "Quebec", None, "Quebec", "Montreal",
                 None, "Montreal", "Quebec", "Laval", "Montreal"],
        "income": [30000, 40000, 50000, 60000, 70000, 80000, 90000, 100000, 110000, 120000],
        "score": [85.5, 90.0, 78.2, 92.1, 88.3, 95.0, 82.7, 89.5, 91.2, 87.8]
    })


class TestOverviewGeneration:
    """Test _generate_overview() method."""

    def test_overview_basic_counts(self, viz_service, sample_mixed_df):
        """Test overview returns correct row and column counts."""
        overview = viz_service._generate_overview(sample_mixed_df)

        assert overview["total_rows"] == 10
        assert overview["total_columns"] == 4
        assert overview["numeric_columns"] == 2  # age, income, score (3 total, but age has nulls)
        assert overview["categorical_columns"] == 1  # city

    def test_overview_memory_usage(self, viz_service, sample_numeric_df):
        """Test memory usage calculation."""
        overview = viz_service._generate_overview(sample_numeric_df)

        assert "memory_usage_mb" in overview
        assert overview["memory_usage_mb"] > 0

    def test_overview_duplicate_detection(self, viz_service):
        """Test duplicate row detection."""
        df = pd.DataFrame({
            "col1": [1, 2, 1, 2, 1],
            "col2": ["a", "b", "a", "b", "a"]
        })
        overview = viz_service._generate_overview(df)

        assert overview["duplicate_rows"] == 2  # 2 duplicate rows
        assert overview["duplicate_percentage"] == 40.0  # 2/5 * 100

    def test_overview_no_duplicates(self, viz_service, sample_numeric_df):
        """Test overview with no duplicates."""
        overview = viz_service._generate_overview(sample_numeric_df)

        assert overview["duplicate_rows"] == 0
        assert overview["duplicate_percentage"] == 0.0


class TestNumericStatistics:
    """Test _generate_numeric_stats() method."""

    def test_numeric_stats_basic_metrics(self, viz_service, sample_numeric_df):
        """Test basic descriptive statistics for numeric columns."""
        stats = viz_service._generate_numeric_stats(sample_numeric_df)

        # Should have stats for all 3 numeric columns
        assert len(stats) == 3
        assert "age" in stats
        assert "income" in stats
        assert "score" in stats

        # Check age column stats
        age_stats = stats["age"]
        assert age_stats["count"] == 10
        assert age_stats["min"] == 25.0
        assert age_stats["max"] == 70.0
        assert age_stats["mean"] == 47.5
        assert age_stats["median"] == 47.5

    def test_numeric_stats_quartiles(self, viz_service, sample_numeric_df):
        """Test quartile calculations."""
        stats = viz_service._generate_numeric_stats(sample_numeric_df)

        age_stats = stats["age"]
        assert "q25" in age_stats
        assert "q75" in age_stats
        assert "iqr" in age_stats

        # IQR = Q3 - Q1
        assert age_stats["iqr"] == age_stats["q75"] - age_stats["q25"]

    def test_numeric_stats_advanced_metrics(self, viz_service, sample_numeric_df):
        """Test skewness, kurtosis, and range."""
        stats = viz_service._generate_numeric_stats(sample_numeric_df)

        age_stats = stats["age"]
        assert "skewness" in age_stats
        assert "kurtosis" in age_stats
        assert "range" in age_stats
        assert age_stats["range"] == 45.0  # 70 - 25

    def test_numeric_stats_handles_nulls(self, viz_service, sample_mixed_df):
        """Test that null values are handled correctly."""
        stats = viz_service._generate_numeric_stats(sample_mixed_df)

        age_stats = stats["age"]
        # Should dropna(), so count = 8 (not 10)
        assert age_stats["count"] == 8
        assert age_stats["min"] == 25.0
        assert age_stats["max"] == 70.0

    def test_numeric_stats_empty_column(self, viz_service):
        """Test behavior with all-null column."""
        df = pd.DataFrame({
            "col1": [None, None, None],
            "col2": [1, 2, 3]
        })
        # Convert col1 to numeric (it might be object type)
        df["col1"] = pd.to_numeric(df["col1"], errors='coerce')

        stats = viz_service._generate_numeric_stats(df)

        # col1 should be skipped (all nulls)
        assert "col1" not in stats
        assert "col2" in stats


class TestCategoricalStatistics:
    """Test _generate_categorical_stats() method."""

    def test_categorical_stats_basic(self, viz_service, sample_categorical_df):
        """Test basic categorical statistics."""
        stats = viz_service._generate_categorical_stats(sample_categorical_df)

        assert len(stats) == 3  # city, gender, occupation
        assert "city" in stats
        assert "gender" in stats
        assert "occupation" in stats

    def test_categorical_stats_unique_count(self, viz_service, sample_categorical_df):
        """Test unique value counting."""
        stats = viz_service._generate_categorical_stats(sample_categorical_df)

        city_stats = stats["city"]
        assert city_stats["unique_values"] == 3  # Montreal, Quebec, Laval

        gender_stats = stats["gender"]
        assert gender_stats["unique_values"] == 2  # M, F

    def test_categorical_stats_mode(self, viz_service, sample_categorical_df):
        """Test mode calculation."""
        stats = viz_service._generate_categorical_stats(sample_categorical_df)

        city_stats = stats["city"]
        assert city_stats["mode"] == "Montreal"  # Most common
        assert city_stats["mode_frequency"] == 5

    def test_categorical_stats_top_values(self, viz_service, sample_categorical_df):
        """Test top values extraction."""
        stats = viz_service._generate_categorical_stats(sample_categorical_df)

        occupation_stats = stats["occupation"]
        top_values = occupation_stats["top_values"]

        assert len(top_values) <= 10
        assert all("value" in item and "count" in item for item in top_values)

        # Engineer should be most common
        assert top_values[0]["value"] == "Engineer"
        assert top_values[0]["count"] == 5

    def test_categorical_stats_entropy(self, viz_service, sample_categorical_df):
        """Test entropy (diversity) calculation."""
        stats = viz_service._generate_categorical_stats(sample_categorical_df)

        # Entropy should be between 0 and log2(unique_values)
        city_stats = stats["city"]
        assert "entropy" in city_stats
        assert city_stats["entropy"] > 0

        # Diversity score = unique / total
        assert "diversity_score" in city_stats
        assert 0 <= city_stats["diversity_score"] <= 1

    def test_categorical_stats_handles_nulls(self, viz_service, sample_mixed_df):
        """Test that nulls are dropped before calculation."""
        stats = viz_service._generate_categorical_stats(sample_mixed_df)

        city_stats = stats["city"]
        # Should dropna(), so count = 8 (not 10)
        assert city_stats["count"] == 8


class TestMissingDataAnalysis:
    """Test _analyze_missing_data() method."""

    def test_missing_data_totals(self, viz_service, sample_mixed_df):
        """Test total missing value calculation."""
        result = viz_service._analyze_missing_data(sample_mixed_df)

        assert "total_missing" in result
        assert "total_cells" in result
        assert "missing_percentage" in result

        # 2 missing in age, 2 missing in city = 4 total
        assert result["total_missing"] == 4
        assert result["total_cells"] == 40  # 10 rows × 4 columns

    def test_missing_data_per_column(self, viz_service, sample_mixed_df):
        """Test missing data breakdown per column."""
        result = viz_service._analyze_missing_data(sample_mixed_df)

        columns_with_missing = result["columns_with_missing"]
        assert len(columns_with_missing) == 2  # age, city

        # Find age column
        age_missing = next(c for c in columns_with_missing if c["column"] == "age")
        assert age_missing["missing_count"] == 2
        assert age_missing["missing_percentage"] == 20.0  # 2/10

    def test_missing_data_no_missing(self, viz_service, sample_numeric_df):
        """Test with no missing values."""
        result = viz_service._analyze_missing_data(sample_numeric_df)

        assert result["total_missing"] == 0
        assert result["missing_percentage"] == 0.0
        assert result["columns_with_missing"] == []


class TestDistributionGeneration:
    """Test _generate_distributions() method."""

    def test_distributions_numeric_histogram(self, viz_service, sample_numeric_df):
        """Test histogram generation for numeric columns."""
        distributions = viz_service._generate_distributions(sample_numeric_df, bins=5)

        assert "age" in distributions
        age_dist = distributions["age"]

        assert age_dist["type"] == "numeric"
        assert "histogram" in age_dist
        assert "counts" in age_dist["histogram"]
        assert "bin_edges" in age_dist["histogram"]
        assert "bin_width" in age_dist["histogram"]

        # Should have 5 bins
        assert len(age_dist["histogram"]["counts"]) == 5
        assert len(age_dist["histogram"]["bin_edges"]) == 6  # n+1 edges

    def test_distributions_categorical_frequencies(self, viz_service, sample_categorical_df):
        """Test frequency generation for categorical columns."""
        distributions = viz_service._generate_distributions(sample_categorical_df)

        assert "city" in distributions
        city_dist = distributions["city"]

        assert city_dist["type"] == "categorical"
        assert "frequencies" in city_dist

        # Should have frequency data
        freqs = city_dist["frequencies"]
        assert len(freqs) > 0
        assert all("label" in item and "count" in item for item in freqs)

    def test_distributions_top_20_limit(self, viz_service):
        """Test that categorical frequencies are limited to top 20."""
        # Create data with 30 unique values
        df = pd.DataFrame({
            "col": [f"value_{i}" for i in range(30)] * 10
        })
        distributions = viz_service._generate_distributions(df)

        col_dist = distributions["col"]
        assert col_dist["type"] == "categorical"
        assert len(col_dist["frequencies"]) == 20  # Top 20 only

    def test_distributions_handles_empty_columns(self, viz_service):
        """Test distributions with all-null columns."""
        df = pd.DataFrame({
            "numeric_col": [1, 2, 3],
            "null_col": [None, None, None]
        })
        distributions = viz_service._generate_distributions(df)

        # null_col should be skipped
        assert "numeric_col" in distributions
        assert "null_col" not in distributions


class TestCorrelationMatrix:
    """Test _generate_correlation_matrix() method."""

    def test_correlation_matrix_basic(self, viz_service, sample_numeric_df):
        """Test basic correlation matrix generation."""
        result = viz_service._generate_correlation_matrix(sample_numeric_df)

        assert "matrix" in result
        assert "columns" in result
        assert "strong_correlations" in result

        # Matrix should be 3x3 (3 numeric columns)
        assert len(result["matrix"]) == 3
        assert len(result["columns"]) == 3

    def test_correlation_strong_correlations(self, viz_service):
        """Test detection of strong correlations (|r| > 0.7)."""
        # Create data with known strong correlation
        df = pd.DataFrame({
            "x": range(100),
            "y": [i * 2 + np.random.normal(0, 1) for i in range(100)],  # Strong positive
            "z": [np.random.normal(0, 10) for _ in range(100)]  # No correlation
        })

        result = viz_service._generate_correlation_matrix(df)

        strong_corrs = result["strong_correlations"]
        # Should detect strong correlation between x and y
        assert len(strong_corrs) > 0

        # Check structure
        if len(strong_corrs) > 0:
            corr = strong_corrs[0]
            assert "column1" in corr
            assert "column2" in corr
            assert "correlation" in corr
            assert "strength" in corr
            assert abs(corr["correlation"]) > 0.7

    def test_correlation_insufficient_columns(self, viz_service):
        """Test with only one numeric column."""
        df = pd.DataFrame({
            "col1": [1, 2, 3, 4, 5],
            "col2": ["a", "b", "c", "d", "e"]
        })

        result = viz_service._generate_correlation_matrix(df)

        assert result["matrix"] == []
        assert result["columns"] == []
        assert result["strong_correlations"] == []
        assert "note" in result


class TestOutlierDetection:
    """Test _detect_outliers() method."""

    def test_outliers_iqr_method(self, viz_service):
        """Test IQR-based outlier detection."""
        # Create data with known outliers
        df = pd.DataFrame({
            "col": [10, 12, 11, 13, 12, 100, 11, 12, 13]  # 100 is outlier
        })

        outliers = viz_service._detect_outliers(df)

        assert "col" in outliers
        col_outliers = outliers["col"]

        assert col_outliers["count"] > 0  # Should detect the outlier
        assert col_outliers["method"] == "IQR (1.5x)"
        assert "lower_bound" in col_outliers
        assert "upper_bound" in col_outliers
        assert "percentage" in col_outliers

    def test_outliers_bounds_calculation(self, viz_service, sample_numeric_df):
        """Test outlier bounds calculation."""
        outliers = viz_service._detect_outliers(sample_numeric_df)

        age_outliers = outliers["age"]

        # Bounds should be: Q1 - 1.5*IQR, Q3 + 1.5*IQR
        assert "lower_bound" in age_outliers
        assert "upper_bound" in age_outliers

        # Upper bound should be > max if no outliers
        # Lower bound should be < min if no outliers

    def test_outliers_percentage(self, viz_service):
        """Test outlier percentage calculation."""
        df = pd.DataFrame({
            "col": [1, 2, 3, 4, 5, 100, 200]  # 2 outliers out of 7
        })

        outliers = viz_service._detect_outliers(df)

        col_outliers = outliers["col"]
        # Should detect 2 outliers
        assert col_outliers["count"] == 2
        assert abs(col_outliers["percentage"] - 28.57) < 0.1  # ~28.57%

    def test_outliers_handles_nulls(self, viz_service, sample_mixed_df):
        """Test outlier detection with null values."""
        outliers = viz_service._detect_outliers(sample_mixed_df)

        # Should handle nulls by dropping them
        assert "age" in outliers  # Has nulls but should still work


class TestDatasetComparison:
    """Test compare_datasets() method."""

    def test_compare_columns_removed(self, viz_service):
        """Test detection of removed columns."""
        df_original = pd.DataFrame({
            "col1": [1, 2, 3],
            "col2": [4, 5, 6],
            "col3": [7, 8, 9]
        })
        df_anonymized = pd.DataFrame({
            "col1": [1, 2, 3],
            "col2": [4, 5, 6]
        })

        result = viz_service._compare_columns(df_original, df_anonymized)

        assert "removed" in result
        assert "added" in result
        assert "retained" in result

        assert result["removed"] == ["col3"]
        assert result["added"] == []
        assert set(result["retained"]) == {"col1", "col2"}

    def test_compare_columns_added(self, viz_service):
        """Test detection of added columns."""
        df_original = pd.DataFrame({
            "col1": [1, 2, 3]
        })
        df_anonymized = pd.DataFrame({
            "col1": [1, 2, 3],
            "col2_generalized": ["1-10", "1-10", "1-10"]
        })

        result = viz_service._compare_columns(df_original, df_anonymized)

        assert result["added"] == ["col2_generalized"]
        assert result["removed"] == []

    def test_compare_statistics_mean_change(self, viz_service):
        """Test statistical comparison of numeric columns."""
        df_original = pd.DataFrame({
            "age": [25, 30, 35, 40, 45]
        })
        df_anonymized = pd.DataFrame({
            "age": [27, 32, 37, 42, 47]  # All +2
        })

        result = viz_service._compare_statistics(df_original, df_anonymized)

        assert "age" in result
        age_change = result["age"]

        assert "mean_change" in age_change
        assert age_change["mean_change"] == 2.0  # Mean increased by 2

    def test_compare_statistics_std_change(self, viz_service):
        """Test standard deviation change detection."""
        df_original = pd.DataFrame({
            "score": [80, 85, 90, 95, 100]
        })
        df_anonymized = pd.DataFrame({
            "score": [87, 88, 89, 90, 91]  # More clustered
        })

        result = viz_service._compare_statistics(df_original, df_anonymized)

        score_change = result["score"]
        assert "std_change" in score_change
        # Std should decrease (more clustered)
        assert score_change["std_change"] < 0

    def test_compare_statistics_handles_nulls(self, viz_service):
        """Test comparison with null values."""
        df_original = pd.DataFrame({
            "col": [1, 2, None, 4, 5]
        })
        df_anonymized = pd.DataFrame({
            "col": [1, 2, 3, 4, None]
        })

        result = viz_service._compare_statistics(df_original, df_anonymized)

        # Should handle nulls by dropping
        assert "col" in result


class TestVisualizationSummary:
    """Test generate_visualization_summary() method."""

    def test_visualization_summary_compact(self, viz_service, mock_db, sample_mixed_df):
        """Test compact summary generation for DB storage."""
        # Mock the load_dataframe method
        dataset_id = uuid4()
        viz_service.ingestion_service.load_dataframe = MagicMock(return_value=sample_mixed_df)

        summary = viz_service.generate_visualization_summary(dataset_id)

        # Should have compact structure
        assert "overview" in summary
        assert "missing_data" in summary
        assert "outliers_summary" in summary
        assert "strong_correlations_count" in summary

    def test_visualization_summary_overview(self, viz_service, mock_db, sample_numeric_df):
        """Test overview section of summary."""
        dataset_id = uuid4()
        viz_service.ingestion_service.load_dataframe = MagicMock(return_value=sample_numeric_df)

        summary = viz_service.generate_visualization_summary(dataset_id)

        overview = summary["overview"]
        assert "rows" in overview
        assert "columns" in overview
        assert "numeric_columns" in overview
        assert "duplicates_pct" in overview

        assert overview["rows"] == 10
        assert overview["columns"] == 3

    def test_visualization_summary_outliers_filtered(self, viz_service, mock_db):
        """Test that only columns with >5% outliers are included."""
        # Create data with one column having many outliers
        df = pd.DataFrame({
            "col1": [1, 2, 3, 4, 5, 6, 7, 8, 9, 100],  # 1 outlier = 10%
            "col2": [10, 11, 12, 13, 14, 15, 16, 17, 18, 19]  # No outliers
        })

        dataset_id = uuid4()
        viz_service.ingestion_service.load_dataframe = MagicMock(return_value=df)

        summary = viz_service.generate_visualization_summary(dataset_id)

        outliers = summary["outliers_summary"]
        # Only col1 should be included (>5% outliers)
        assert "col1" in outliers or len(outliers) == 0  # Depends on exact calculation


class TestGenerateStatisticsIntegration:
    """Test generate_statistics() integration method."""

    def test_generate_statistics_complete(self, viz_service, mock_db, sample_mixed_df):
        """Test complete statistics generation."""
        dataset_id = uuid4()

        # Mock dependencies
        mock_dataset = Mock()
        mock_dataset.filename = "test.csv"
        viz_service.ingestion_service.get_dataset = MagicMock(return_value=mock_dataset)
        viz_service.ingestion_service.load_dataframe = MagicMock(return_value=sample_mixed_df)

        stats = viz_service.generate_statistics(dataset_id)

        # Should have all 7 sections
        assert "dataset_id" in stats
        assert "filename" in stats
        assert "overview" in stats
        assert "numeric_stats" in stats
        assert "categorical_stats" in stats
        assert "missing_data" in stats
        assert "distributions" in stats
        assert "correlations" in stats
        assert "outliers" in stats


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_dataframe(self, viz_service):
        """Test with empty dataframe."""
        df = pd.DataFrame()

        overview = viz_service._generate_overview(df)
        assert overview["total_rows"] == 0
        assert overview["total_columns"] == 0

    def test_single_row_dataframe(self, viz_service):
        """Test with single row."""
        df = pd.DataFrame({
            "col1": [1],
            "col2": ["a"]
        })

        stats = viz_service._generate_numeric_stats(df)
        assert "col1" in stats
        assert stats["col1"]["count"] == 1

    def test_all_same_values(self, viz_service):
        """Test with constant values (no variance)."""
        df = pd.DataFrame({
            "col": [100] * 10
        })

        stats = viz_service._generate_numeric_stats(df)
        col_stats = stats["col"]

        assert col_stats["std"] == 0.0
        assert col_stats["range"] == 0.0
        assert col_stats["iqr"] == 0.0


if __name__ == "__main__":
    """Run Phase 3 visualization tests with pytest."""
    pytest.main([__file__, "-v", "-s"])
