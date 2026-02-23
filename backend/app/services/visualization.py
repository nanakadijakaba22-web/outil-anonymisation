"""
Data Visualization Service

Generates statistical summaries and visualization data for datasets.
Helps users understand data distributions, correlations, and anomalies.

This service addresses the "limited data visualization" issue from the cahier de charges.
"""

import logging
from typing import Dict, List, Any, Tuple, Optional
from uuid import UUID

import pandas as pd
import numpy as np
from sqlalchemy.orm import Session

from app.services.data_ingestion import DataIngestionService
from app.models.database import Dataset, DatasetColumn

logger = logging.getLogger(__name__)


class DataVisualizationService:
    """
    Generates visualization data and statistical summaries for datasets.

    Provides:
    - Descriptive statistics (mean, median, std, quartiles)
    - Distribution histograms
    - Correlation matrices
    - Outlier detection
    - Before/after comparison for anonymization
    """

    def __init__(self, db: Session):
        self.db = db
        self.ingestion_service = DataIngestionService(db)

    def generate_statistics(self, dataset_id: UUID) -> Dict[str, Any]:
        """
        Generate comprehensive statistics for a dataset.

        Returns:
            Dictionary containing:
            - overview: Basic dataset info
            - numeric_stats: Statistics for numeric columns
            - categorical_stats: Statistics for categorical columns
            - missing_data: Missing value analysis
            - distributions: Histogram data for all columns
            - correlations: Correlation matrix for numeric columns
            - outliers: Outlier detection results
        """
        dataset = self.ingestion_service.get_dataset(dataset_id)
        df = self.ingestion_service.load_dataframe(dataset_id)

        stats = {
            "dataset_id": str(dataset_id),
            "filename": dataset.filename,
            "overview": self._generate_overview(df),
            "numeric_stats": self._generate_numeric_stats(df),
            "categorical_stats": self._generate_categorical_stats(df),
            "missing_data": self._analyze_missing_data(df),
            "distributions": self._generate_distributions(df),
            "correlations": self._generate_correlation_matrix(df),
            "outliers": self._detect_outliers(df),
        }

        return stats

    def _generate_overview(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Generate basic overview statistics."""
        return {
            "total_rows": len(df),
            "total_columns": len(df.columns),
            "numeric_columns": len(df.select_dtypes(include=[np.number]).columns),
            "categorical_columns": len(df.select_dtypes(include=['object']).columns),
            "memory_usage_mb": df.memory_usage(deep=True).sum() / (1024 * 1024),
            "duplicate_rows": df.duplicated().sum(),
            "duplicate_percentage": (df.duplicated().sum() / len(df)) * 100,
        }

    def _generate_numeric_stats(self, df: pd.DataFrame) -> Dict[str, Dict[str, float]]:
        """
        Generate descriptive statistics for numeric columns.

        For each numeric column, computes:
        - count, mean, std, min, max
        - quartiles (25%, 50%, 75%)
        - skewness, kurtosis
        """
        numeric_df = df.select_dtypes(include=[np.number])
        stats = {}

        for col in numeric_df.columns:
            col_data = numeric_df[col].dropna()

            if len(col_data) == 0:
                continue

            stats[col] = {
                "count": len(col_data),
                "mean": float(col_data.mean()),
                "std": float(col_data.std()),
                "min": float(col_data.min()),
                "max": float(col_data.max()),
                "q25": float(col_data.quantile(0.25)),
                "median": float(col_data.quantile(0.50)),
                "q75": float(col_data.quantile(0.75)),
                "skewness": float(col_data.skew()),
                "kurtosis": float(col_data.kurtosis()),
                "range": float(col_data.max() - col_data.min()),
                "iqr": float(col_data.quantile(0.75) - col_data.quantile(0.25)),
            }

        return stats

    def _generate_categorical_stats(self, df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
        """
        Generate statistics for categorical columns.

        For each categorical column, computes:
        - unique values count
        - most common values
        - mode
        - entropy (measure of diversity)
        """
        categorical_df = df.select_dtypes(include=['object'])
        stats = {}

        for col in categorical_df.columns:
            col_data = categorical_df[col].dropna()

            if len(col_data) == 0:
                continue

            # Value counts
            value_counts = col_data.value_counts()

            # Top 10 most common values
            top_values = [
                {"value": str(val), "count": int(count)}
                for val, count in value_counts.head(10).items()
            ]

            # Calculate entropy (measure of diversity)
            probabilities = value_counts / len(col_data)
            entropy = -np.sum(probabilities * np.log2(probabilities + 1e-10))

            stats[col] = {
                "count": len(col_data),
                "unique_values": int(col_data.nunique()),
                "mode": str(col_data.mode()[0]) if len(col_data.mode()) > 0 else None,
                "mode_frequency": int(value_counts.iloc[0]) if len(value_counts) > 0 else 0,
                "top_values": top_values,
                "entropy": float(entropy),
                "diversity_score": float(col_data.nunique() / len(col_data)),  # 0-1
            }

        return stats

    def _analyze_missing_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze missing data patterns.

        Returns:
            - total_missing: Total missing values
            - missing_percentage: Overall percentage
            - columns_with_missing: Details per column
        """
        missing_counts = df.isnull().sum()
        total_missing = missing_counts.sum()
        total_cells = df.shape[0] * df.shape[1]

        columns_with_missing = [
            {
                "column": col,
                "missing_count": int(count),
                "missing_percentage": float((count / len(df)) * 100)
            }
            for col, count in missing_counts.items()
            if count > 0
        ]

        return {
            "total_missing": int(total_missing),
            "total_cells": total_cells,
            "missing_percentage": float((total_missing / total_cells) * 100),
            "columns_with_missing": columns_with_missing,
        }

    def _generate_distributions(
        self,
        df: pd.DataFrame,
        bins: int = 20
    ) -> Dict[str, Dict[str, Any]]:
        """
        Generate histogram data for all columns.

        For numeric columns: histogram with bin edges and counts
        For categorical: top N value frequencies

        Args:
            bins: Number of bins for numeric histograms

        Returns:
            Dictionary with distribution data per column
        """
        distributions = {}

        # Numeric columns: histograms
        numeric_df = df.select_dtypes(include=[np.number])
        for col in numeric_df.columns:
            col_data = numeric_df[col].dropna()

            if len(col_data) == 0:
                continue

            # Compute histogram
            counts, bin_edges = np.histogram(col_data, bins=bins)

            distributions[col] = {
                "type": "numeric",
                "histogram": {
                    "counts": counts.tolist(),
                    "bin_edges": bin_edges.tolist(),
                    "bin_width": float(bin_edges[1] - bin_edges[0]) if len(bin_edges) > 1 else 0,
                }
            }

        # Categorical columns: top frequencies
        categorical_df = df.select_dtypes(include=['object'])
        for col in categorical_df.columns:
            col_data = categorical_df[col].dropna()

            if len(col_data) == 0:
                continue

            # Top 20 values
            value_counts = col_data.value_counts().head(20)

            distributions[col] = {
                "type": "categorical",
                "frequencies": [
                    {"label": str(val), "count": int(count)}
                    for val, count in value_counts.items()
                ]
            }

        return distributions

    def _generate_correlation_matrix(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Generate correlation matrix for numeric columns.

        Returns:
            - matrix: Correlation values
            - columns: Column names
            - strong_correlations: List of highly correlated pairs (|r| > 0.7)
        """
        numeric_df = df.select_dtypes(include=[np.number])

        if numeric_df.shape[1] < 2:
            return {
                "matrix": [],
                "columns": [],
                "strong_correlations": [],
                "note": "Insufficient numeric columns for correlation analysis"
            }

        # Compute Pearson correlation matrix
        corr_matrix = numeric_df.corr()

        # Find strong correlations (excluding diagonal)
        strong_correlations = []
        for i in range(len(corr_matrix.columns)):
            for j in range(i + 1, len(corr_matrix.columns)):
                col1 = corr_matrix.columns[i]
                col2 = corr_matrix.columns[j]
                corr_value = corr_matrix.iloc[i, j]

                if abs(corr_value) > 0.7:
                    strong_correlations.append({
                        "column1": col1,
                        "column2": col2,
                        "correlation": float(corr_value),
                        "strength": "strong positive" if corr_value > 0.7 else "strong negative"
                    })

        return {
            "matrix": corr_matrix.values.tolist(),
            "columns": corr_matrix.columns.tolist(),
            "strong_correlations": strong_correlations,
        }

    def _detect_outliers(
        self,
        df: pd.DataFrame,
        method: str = "iqr"
    ) -> Dict[str, Dict[str, Any]]:
        """
        Detect outliers in numeric columns.

        Method:
            - IQR (Interquartile Range): Values < Q1 - 1.5*IQR or > Q3 + 1.5*IQR

        Returns:
            Dictionary with outlier counts and percentages per column
        """
        numeric_df = df.select_dtypes(include=[np.number])
        outliers = {}

        for col in numeric_df.columns:
            col_data = numeric_df[col].dropna()

            if len(col_data) == 0:
                continue

            # IQR method
            Q1 = col_data.quantile(0.25)
            Q3 = col_data.quantile(0.75)
            IQR = Q3 - Q1

            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR

            outlier_mask = (col_data < lower_bound) | (col_data > upper_bound)
            outlier_count = outlier_mask.sum()

            outliers[col] = {
                "count": int(outlier_count),
                "percentage": float((outlier_count / len(col_data)) * 100),
                "lower_bound": float(lower_bound),
                "upper_bound": float(upper_bound),
                "method": "IQR (1.5x)",
            }

        return outliers

    def compare_datasets(
        self,
        original_id: UUID,
        anonymized_id: UUID
    ) -> Dict[str, Any]:
        """
        Compare original and anonymized datasets.

        Useful for understanding impact of anonymization on data utility.

        Returns:
            - column_changes: Columns added/removed
            - statistical_changes: Changes in mean, std, etc.
            - distribution_changes: KS test results
            - correlation_changes: Changes in correlations
        """
        df_original = self.ingestion_service.load_dataframe(original_id)
        df_anonymized = self.ingestion_service.load_dataframe(anonymized_id)

        comparison = {
            "original_dataset_id": str(original_id),
            "anonymized_dataset_id": str(anonymized_id),
            "column_changes": self._compare_columns(df_original, df_anonymized),
            "statistical_changes": self._compare_statistics(df_original, df_anonymized),
            "row_count_change": len(df_anonymized) - len(df_original),
        }

        return comparison

    def _compare_columns(
        self,
        df_original: pd.DataFrame,
        df_anonymized: pd.DataFrame
    ) -> Dict[str, List[str]]:
        """Compare columns between original and anonymized datasets."""
        original_cols = set(df_original.columns)
        anonymized_cols = set(df_anonymized.columns)

        return {
            "removed": list(original_cols - anonymized_cols),
            "added": list(anonymized_cols - original_cols),
            "retained": list(original_cols & anonymized_cols),
        }

    def _compare_statistics(
        self,
        df_original: pd.DataFrame,
        df_anonymized: pd.DataFrame
    ) -> Dict[str, Dict[str, Any]]:
        """
        Compare statistical properties of common numeric columns.

        For each common column, compute:
        - Mean change
        - Std change
        - Range change
        """
        changes = {}

        # Find common numeric columns
        original_numeric = set(df_original.select_dtypes(include=[np.number]).columns)
        anonymized_numeric = set(df_anonymized.select_dtypes(include=[np.number]).columns)
        common_numeric = original_numeric & anonymized_numeric

        for col in common_numeric:
            orig_data = df_original[col].dropna()
            anon_data = df_anonymized[col].dropna()

            if len(orig_data) == 0 or len(anon_data) == 0:
                continue

            orig_mean = orig_data.mean()
            anon_mean = anon_data.mean()

            orig_std = orig_data.std()
            anon_std = anon_data.std()

            changes[col] = {
                "mean_change": float(anon_mean - orig_mean),
                "mean_change_percent": float(((anon_mean - orig_mean) / orig_mean) * 100) if orig_mean != 0 else 0,
                "std_change": float(anon_std - orig_std),
                "range_original": float(orig_data.max() - orig_data.min()),
                "range_anonymized": float(anon_data.max() - anon_data.min()),
            }

        return changes

    def generate_visualization_summary(self, dataset_id: UUID) -> Dict[str, Any]:
        """
        Generate compact visualization summary for embedding in risk assessment.

        This is a lightweight version of generate_statistics() suitable for
        storing in the database (visualization_data JSON field).

        Returns:
            Compact dict with key metrics and chart data
        """
        df = self.ingestion_service.load_dataframe(dataset_id)

        return {
            "overview": {
                "rows": len(df),
                "columns": len(df.columns),
                "numeric_columns": len(df.select_dtypes(include=[np.number]).columns),
                "duplicates_pct": float((df.duplicated().sum() / len(df)) * 100),
            },
            "missing_data": {
                "total_pct": float((df.isnull().sum().sum() / (df.shape[0] * df.shape[1])) * 100),
                "columns_affected": int((df.isnull().sum() > 0).sum()),
            },
            "outliers_summary": {
                col: data["percentage"]
                for col, data in self._detect_outliers(df).items()
                if data["percentage"] > 5  # Only columns with >5% outliers
            },
            "strong_correlations_count": len(self._generate_correlation_matrix(df)["strong_correlations"]),
        }
