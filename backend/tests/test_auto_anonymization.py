"""
Test Suite for Automatic Anonymization (Law 25 Rules)

Tests the automatic anonymization configuration generation:
1. Direct identifiers → Suppression
2. Quasi-identifiers → Generalization (text→prefix, numeric→bins, date→year)
3. Sensitive data → Differential Privacy (numeric) or Generalization (text)
4. Non-sensitive → No transformation

This ensures Quebec Law 25 compliant automatic anonymization.
"""

import pytest
import pandas as pd
from datetime import datetime
from uuid import uuid4
from unittest.mock import Mock, MagicMock, patch
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.anonymizer import Anonymizer
from app.models.schemas import (
    AnonymizationConfig,
    AnonymizationTechnique,
    DataType,
)


class TestGetGeneralizationParams:
    """Test _get_generalization_params method for automatic type detection."""

    @pytest.fixture
    def db_session(self) -> Session:
        """Get database session for tests."""
        db = next(get_db())
        try:
            yield db
        finally:
            db.rollback()
            db.close()

    @pytest.fixture
    def anonymizer(self, db_session: Session) -> Anonymizer:
        """Create Anonymizer instance."""
        return Anonymizer(db=db_session)

    def test_datetime_column_returns_year_params(self, anonymizer: Anonymizer):
        """Test that datetime columns get year extraction params."""
        print("\n=== Test: DateTime → Year extraction ===")

        df = pd.DataFrame({
            "date_naissance": pd.to_datetime([
                "1990-05-15", "1985-12-01", "2000-03-20"
            ])
        })

        params = anonymizer._get_generalization_params(df, "date_naissance")

        print(f"Column dtype: {df['date_naissance'].dtype}")
        print(f"Generated params: {params}")

        assert params["method"] == "year"
        assert "Date" in params.get("reason", "")
        print("✓ DateTime detection successful")

    def test_text_date_column_returns_year_params(self, anonymizer: Anonymizer):
        """Test that text columns with dates get year extraction params."""
        print("\n=== Test: Text dates → Year extraction ===")

        df = pd.DataFrame({
            "birthdate": ["1990-05-15", "1985-12-01", "2000-03-20", "1975-08-10"]
        })

        params = anonymizer._get_generalization_params(df, "birthdate")

        print(f"Column dtype: {df['birthdate'].dtype}")
        print(f"Sample values: {df['birthdate'].tolist()}")
        print(f"Generated params: {params}")

        assert params["method"] == "year"
        print("✓ Text date detection successful")

    def test_numeric_column_returns_bins_params(self, anonymizer: Anonymizer):
        """Test that numeric columns get binning params."""
        print("\n=== Test: Numeric → Bins ===")

        df = pd.DataFrame({
            "age": [25, 30, 45, 60, 22, 38]
        })

        params = anonymizer._get_generalization_params(df, "age")

        print(f"Column dtype: {df['age'].dtype}")
        print(f"Generated params: {params}")

        assert params["bins"] == 5
        assert "Numérique" in params.get("reason", "") or "tranches" in params.get("reason", "")
        print("✓ Numeric detection successful")

    def test_float_column_returns_bins_params(self, anonymizer: Anonymizer):
        """Test that float columns get binning params."""
        print("\n=== Test: Float → Bins ===")

        df = pd.DataFrame({
            "revenu": [45000.50, 62000.75, 38000.00, 85000.25]
        })

        params = anonymizer._get_generalization_params(df, "revenu")

        print(f"Column dtype: {df['revenu'].dtype}")
        print(f"Generated params: {params}")

        assert params["bins"] == 5
        print("✓ Float detection successful")

    def test_text_column_returns_prefix_params(self, anonymizer: Anonymizer):
        """Test that text columns get prefix params."""
        print("\n=== Test: Text → Prefix ===")

        df = pd.DataFrame({
            "ville": ["Montreal", "Quebec", "Toronto", "Vancouver"]
        })

        params = anonymizer._get_generalization_params(df, "ville")

        print(f"Column dtype: {df['ville'].dtype}")
        print(f"Generated params: {params}")

        assert params["prefix_length"] == 3
        assert "Texte" in params.get("reason", "") or "préfixe" in params.get("reason", "")
        print("✓ Text detection successful")

    def test_postal_code_returns_prefix_params(self, anonymizer: Anonymizer):
        """Test that postal codes (text) get prefix params."""
        print("\n=== Test: Postal Code → Prefix ===")

        df = pd.DataFrame({
            "code_postal": ["H3B 1A1", "G1X 3J4", "K1A 0B1", "V6B 2K8"]
        })

        params = anonymizer._get_generalization_params(df, "code_postal")

        print(f"Column dtype: {df['code_postal'].dtype}")
        print(f"Generated params: {params}")

        assert params["prefix_length"] == 3
        print("✓ Postal code detection successful")


class TestGenerateAutoConfig:
    """Test generate_auto_config method for Law 25 rules."""

    @pytest.fixture
    def db_session(self) -> Session:
        """Get database session for tests."""
        db = next(get_db())
        try:
            yield db
        finally:
            db.rollback()
            db.close()

    @pytest.fixture
    def anonymizer(self, db_session: Session) -> Anonymizer:
        """Create Anonymizer instance."""
        return Anonymizer(db=db_session)

    def test_direct_identifier_generates_suppression(self, anonymizer: Anonymizer):
        """Test that direct identifiers generate suppression config."""
        print("\n=== Test: Direct Identifier → Suppression ===")

        # Mock column with direct_identifier sensitivity
        mock_column = Mock()
        mock_column.name = "email"
        mock_column.sensitivity_type = DataType.DIRECT_IDENTIFIER.value

        # Mock DataFrame
        df = pd.DataFrame({
            "email": ["test@example.com", "user@domain.com"]
        })

        # Mock database query
        with patch.object(anonymizer.db, 'query') as mock_query:
            mock_query.return_value.filter.return_value.all.return_value = [mock_column]
            with patch.object(anonymizer.ingestion_service, 'load_dataframe', return_value=df):
                configs = anonymizer.generate_auto_config(uuid4())

        print(f"Generated configs: {configs}")

        assert len(configs) == 1
        assert configs[0].column_name == "email"
        assert configs[0].technique == AnonymizationTechnique.SUPPRESSION
        print("✓ Direct identifier → Suppression successful")

    def test_quasi_identifier_generates_generalization(self, anonymizer: Anonymizer):
        """Test that quasi-identifiers generate generalization config."""
        print("\n=== Test: Quasi-Identifier → Generalization ===")

        # Mock column with quasi_identifier sensitivity
        mock_column = Mock()
        mock_column.name = "age"
        mock_column.sensitivity_type = DataType.QUASI_IDENTIFIER.value

        # Mock DataFrame with numeric data
        df = pd.DataFrame({
            "age": [25, 30, 45, 60]
        })

        with patch.object(anonymizer.db, 'query') as mock_query:
            mock_query.return_value.filter.return_value.all.return_value = [mock_column]
            with patch.object(anonymizer.ingestion_service, 'load_dataframe', return_value=df):
                configs = anonymizer.generate_auto_config(uuid4())

        print(f"Generated configs: {configs}")

        assert len(configs) == 1
        assert configs[0].column_name == "age"
        assert configs[0].technique == AnonymizationTechnique.GENERALIZATION
        assert "bins" in configs[0].params or "prefix_length" in configs[0].params
        print("✓ Quasi-identifier → Generalization successful")

    def test_sensitive_numeric_generates_differential_privacy(self, anonymizer: Anonymizer):
        """Test that sensitive numeric data generates DP config."""
        print("\n=== Test: Sensitive Numeric → Differential Privacy ===")

        # Mock column with sensitive type
        mock_column = Mock()
        mock_column.name = "revenu"
        mock_column.sensitivity_type = DataType.SENSITIVE.value

        # Mock DataFrame with numeric data
        df = pd.DataFrame({
            "revenu": [45000, 62000, 38000, 85000]
        })

        with patch.object(anonymizer.db, 'query') as mock_query:
            mock_query.return_value.filter.return_value.all.return_value = [mock_column]
            with patch.object(anonymizer.ingestion_service, 'load_dataframe', return_value=df):
                configs = anonymizer.generate_auto_config(uuid4())

        print(f"Generated configs: {configs}")

        assert len(configs) == 1
        assert configs[0].column_name == "revenu"
        assert configs[0].technique == AnonymizationTechnique.DIFFERENTIAL_PRIVACY
        assert configs[0].params["epsilon"] == 0.1  # High security
        assert configs[0].params["mechanism"] == "laplace"
        print("✓ Sensitive numeric → DP (epsilon=0.1) successful")

    def test_sensitive_text_generates_generalization(self, anonymizer: Anonymizer):
        """Test that sensitive text data generates generalization config."""
        print("\n=== Test: Sensitive Text → Generalization ===")

        # Mock column with sensitive type
        mock_column = Mock()
        mock_column.name = "diagnostic"
        mock_column.sensitivity_type = DataType.SENSITIVE.value

        # Mock DataFrame with text data
        df = pd.DataFrame({
            "diagnostic": ["Diabète", "Hypertension", "Asthme"]
        })

        with patch.object(anonymizer.db, 'query') as mock_query:
            mock_query.return_value.filter.return_value.all.return_value = [mock_column]
            with patch.object(anonymizer.ingestion_service, 'load_dataframe', return_value=df):
                configs = anonymizer.generate_auto_config(uuid4())

        print(f"Generated configs: {configs}")

        assert len(configs) == 1
        assert configs[0].column_name == "diagnostic"
        assert configs[0].technique == AnonymizationTechnique.GENERALIZATION
        assert configs[0].params["prefix_length"] == 2  # Aggressive for sensitive
        print("✓ Sensitive text → Generalization (prefix=2) successful")

    def test_non_sensitive_generates_no_config(self, anonymizer: Anonymizer):
        """Test that non-sensitive columns generate no config."""
        print("\n=== Test: Non-Sensitive → No Config ===")

        # Mock column with non_sensitive type
        mock_column = Mock()
        mock_column.name = "description"
        mock_column.sensitivity_type = DataType.NON_SENSITIVE.value

        df = pd.DataFrame({
            "description": ["Product A", "Product B"]
        })

        with patch.object(anonymizer.db, 'query') as mock_query:
            mock_query.return_value.filter.return_value.all.return_value = [mock_column]
            with patch.object(anonymizer.ingestion_service, 'load_dataframe', return_value=df):
                configs = anonymizer.generate_auto_config(uuid4())

        print(f"Generated configs: {configs}")

        assert len(configs) == 0
        print("✓ Non-sensitive → No config successful")

    def test_mixed_sensitivity_types(self, anonymizer: Anonymizer):
        """Test config generation with multiple sensitivity types."""
        print("\n=== Test: Mixed Sensitivity Types ===")

        # Mock columns with different sensitivity types
        mock_columns = [
            Mock(name="nas", sensitivity_type=DataType.DIRECT_IDENTIFIER.value),
            Mock(name="age", sensitivity_type=DataType.QUASI_IDENTIFIER.value),
            Mock(name="revenu", sensitivity_type=DataType.SENSITIVE.value),
            Mock(name="notes", sensitivity_type=DataType.NON_SENSITIVE.value),
        ]
        # Fix Mock name attribute
        mock_columns[0].name = "nas"
        mock_columns[1].name = "age"
        mock_columns[2].name = "revenu"
        mock_columns[3].name = "notes"

        df = pd.DataFrame({
            "nas": ["123-456-789", "987-654-321"],
            "age": [25, 30],
            "revenu": [50000, 60000],
            "notes": ["Note 1", "Note 2"]
        })

        with patch.object(anonymizer.db, 'query') as mock_query:
            mock_query.return_value.filter.return_value.all.return_value = mock_columns
            with patch.object(anonymizer.ingestion_service, 'load_dataframe', return_value=df):
                configs = anonymizer.generate_auto_config(uuid4())

        print(f"Generated {len(configs)} configs:")
        for c in configs:
            print(f"  - {c.column_name}: {c.technique.value}")

        # Should have 3 configs (nas, age, revenu) - not notes (non-sensitive)
        assert len(configs) == 3

        config_dict = {c.column_name: c for c in configs}

        assert config_dict["nas"].technique == AnonymizationTechnique.SUPPRESSION
        assert config_dict["age"].technique == AnonymizationTechnique.GENERALIZATION
        assert config_dict["revenu"].technique == AnonymizationTechnique.DIFFERENTIAL_PRIVACY

        print("✓ Mixed sensitivity types successful")

    def test_empty_columns_raises_error(self, anonymizer: Anonymizer):
        """Test that empty columns list raises ValueError."""
        print("\n=== Test: Empty Columns → Error ===")

        with patch.object(anonymizer.db, 'query') as mock_query:
            mock_query.return_value.filter.return_value.all.return_value = []

            with pytest.raises(ValueError, match="Aucune colonne trouvée"):
                anonymizer.generate_auto_config(uuid4())

        print("✓ Empty columns error handling successful")


class TestAutoAnonymizationEndpoint:
    """Test the anonymization endpoint with auto=true parameter."""

    @pytest.fixture
    def db_session(self) -> Session:
        """Get database session for tests."""
        db = next(get_db())
        try:
            yield db
        finally:
            db.rollback()
            db.close()

    def test_auto_config_structure(self, db_session: Session):
        """Test that auto-generated config has correct structure."""
        print("\n=== Test: Auto Config Structure ===")

        anonymizer = Anonymizer(db=db_session)

        # Mock a complete scenario
        mock_columns = [
            Mock(name="email", sensitivity_type=DataType.DIRECT_IDENTIFIER.value),
            Mock(name="code_postal", sensitivity_type=DataType.QUASI_IDENTIFIER.value),
        ]
        mock_columns[0].name = "email"
        mock_columns[1].name = "code_postal"

        df = pd.DataFrame({
            "email": ["test@example.com"],
            "code_postal": ["H3B 1A1"]
        })

        with patch.object(anonymizer.db, 'query') as mock_query:
            mock_query.return_value.filter.return_value.all.return_value = mock_columns
            with patch.object(anonymizer.ingestion_service, 'load_dataframe', return_value=df):
                configs = anonymizer.generate_auto_config(uuid4())

        # Verify config structure
        for config in configs:
            assert isinstance(config, AnonymizationConfig)
            assert isinstance(config.column_name, str)
            assert isinstance(config.technique, AnonymizationTechnique)
            assert isinstance(config.params, dict)

        print(f"Generated {len(configs)} valid AnonymizationConfig objects")
        print("✓ Config structure validation successful")


class TestLaw25ComplianceRules:
    """Test that auto-anonymization follows Law 25 compliance rules."""

    @pytest.fixture
    def db_session(self) -> Session:
        """Get database session for tests."""
        db = next(get_db())
        try:
            yield db
        finally:
            db.rollback()
            db.close()

    @pytest.fixture
    def anonymizer(self, db_session: Session) -> Anonymizer:
        """Create Anonymizer instance."""
        return Anonymizer(db=db_session)

    def test_direct_identifiers_always_suppressed(self, anonymizer: Anonymizer):
        """
        Law 25 Rule: Direct identifiers must be suppressed or fully masked.
        Our implementation uses suppression for maximum safety.
        """
        print("\n=== Test: Law 25 - Direct Identifiers Suppression ===")

        direct_id_columns = ["nas", "email", "telephone", "nom", "prenom"]

        for col_name in direct_id_columns:
            mock_column = Mock()
            mock_column.name = col_name
            mock_column.sensitivity_type = DataType.DIRECT_IDENTIFIER.value

            df = pd.DataFrame({col_name: ["test_value"]})

            with patch.object(anonymizer.db, 'query') as mock_query:
                mock_query.return_value.filter.return_value.all.return_value = [mock_column]
                with patch.object(anonymizer.ingestion_service, 'load_dataframe', return_value=df):
                    configs = anonymizer.generate_auto_config(uuid4())

            assert configs[0].technique == AnonymizationTechnique.SUPPRESSION, \
                f"Direct identifier '{col_name}' should be suppressed"

        print(f"✓ All {len(direct_id_columns)} direct identifiers correctly suppressed")

    def test_dp_uses_strong_epsilon(self, anonymizer: Anonymizer):
        """
        Law 25 Rule: Sensitive data should use high security (low epsilon).
        Our implementation uses epsilon=0.1 for strong privacy.
        """
        print("\n=== Test: Law 25 - Strong Epsilon for Sensitive Data ===")

        mock_column = Mock()
        mock_column.name = "salaire"
        mock_column.sensitivity_type = DataType.SENSITIVE.value

        df = pd.DataFrame({"salaire": [50000, 60000, 70000]})

        with patch.object(anonymizer.db, 'query') as mock_query:
            mock_query.return_value.filter.return_value.all.return_value = [mock_column]
            with patch.object(anonymizer.ingestion_service, 'load_dataframe', return_value=df):
                configs = anonymizer.generate_auto_config(uuid4())

        assert configs[0].params["epsilon"] == 0.1, \
            "Epsilon should be 0.1 (strong privacy)"
        assert configs[0].params["mechanism"] == "laplace", \
            "Should use Laplace mechanism"

        print("✓ DP uses epsilon=0.1 (strong privacy) with Laplace mechanism")

    def test_quasi_identifiers_generalized_appropriately(self, anonymizer: Anonymizer):
        """
        Law 25 Rule: Quasi-identifiers should be generalized to prevent re-identification.
        """
        print("\n=== Test: Law 25 - Quasi-Identifier Generalization ===")

        test_cases = [
            ("age", [25, 30, 45], "bins"),  # Numeric → bins
            ("code_postal", ["H3B 1A1", "G1X 3J4"], "prefix_length"),  # Text → prefix
        ]

        for col_name, values, expected_param in test_cases:
            mock_column = Mock()
            mock_column.name = col_name
            mock_column.sensitivity_type = DataType.QUASI_IDENTIFIER.value

            df = pd.DataFrame({col_name: values})

            with patch.object(anonymizer.db, 'query') as mock_query:
                mock_query.return_value.filter.return_value.all.return_value = [mock_column]
                with patch.object(anonymizer.ingestion_service, 'load_dataframe', return_value=df):
                    configs = anonymizer.generate_auto_config(uuid4())

            assert configs[0].technique == AnonymizationTechnique.GENERALIZATION
            assert expected_param in configs[0].params, \
                f"'{col_name}' should have '{expected_param}' param"

            print(f"  ✓ {col_name}: generalization with {expected_param}")

        print("✓ Quasi-identifiers correctly generalized")
