import unittest
from unittest.mock import MagicMock
from app.services.detector import SensitiveDataDetector
from app.models.schemas import DataType, Category, AnonymizationTechnique

class TestDetectorSuggestions(unittest.TestCase):
    def setUp(self):
        self.mock_db = MagicMock()
        self.detector = SensitiveDataDetector(self.mock_db)

    def test_suggest_prefix_for_postal_code(self):
        # Case: Postal code detected by pattern
        config = self.detector._get_suggested_config(
            column_name="generic_column",
            sensitivity_type=DataType.QUASI_IDENTIFIER,
            category=Category.PERSONAL,
            data_type="object",
            pattern_type="CODE_POSTAL_CA"
        )
        self.assertIsNotNone(config)
        self.assertEqual(config.technique, AnonymizationTechnique.GENERALIZATION)
        self.assertEqual(config.params["mode"], "prefix")
        self.assertEqual(config.params["prefix_length"], 3)

    def test_suggest_year_for_date_pattern(self):
        # Case: Date detected by pattern
        config = self.detector._get_suggested_config(
            column_name="generic_column",
            sensitivity_type=DataType.QUASI_IDENTIFIER,
            category=Category.PERSONAL,
            data_type="object",
            pattern_type="DATE"
        )
        self.assertIsNotNone(config)
        self.assertEqual(config.technique, AnonymizationTechnique.GENERALIZATION)
        self.assertEqual(config.params["mode"], "year")

    def test_suggest_year_for_date_type(self):
        # Case: Date detected by data type
        config = self.detector._get_suggested_config(
            column_name="generic_column",
            sensitivity_type=DataType.QUASI_IDENTIFIER,
            category=Category.PERSONAL,
            data_type="datetime64[ns]",
            pattern_type=None
        )
        self.assertIsNotNone(config)
        self.assertEqual(config.technique, AnonymizationTechnique.GENERALIZATION)
        self.assertEqual(config.params["mode"], "year")

    def test_suggest_bins_for_numeric(self):
        # Case: Numeric column (e.g. Age)
        config = self.detector._get_suggested_config(
            column_name="age",
            sensitivity_type=DataType.QUASI_IDENTIFIER,
            category=Category.PERSONAL,
            data_type="int64",
            pattern_type=None
        )
        self.assertIsNotNone(config)
        self.assertEqual(config.technique, AnonymizationTechnique.GENERALIZATION)
        self.assertEqual(config.params["mode"], "bins")
        self.assertEqual(config.params["bins"], 5)

    def test_suggest_prefix_for_text_fallback(self):
        # Case: Text column (e.g. City) with no pattern
        config = self.detector._get_suggested_config(
            column_name="city",
            sensitivity_type=DataType.QUASI_IDENTIFIER,
            category=Category.PERSONAL,
            data_type="object",
            pattern_type=None
        )
        self.assertIsNotNone(config)
        self.assertEqual(config.technique, AnonymizationTechnique.GENERALIZATION)
        self.assertEqual(config.params["mode"], "prefix")

if __name__ == '__main__':
    unittest.main()
