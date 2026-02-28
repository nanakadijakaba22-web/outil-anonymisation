import unittest
from unittest.mock import MagicMock


from app.services.detector import SensitiveDataDetector
from app.models.schemas import DataType, Category

class TestSensitiveDataDetector(unittest.TestCase):
    def setUp(self):
        self.db = MagicMock()
        self.detector = SensitiveDataDetector(self.db)

    def test_detect_column_type_by_name_direct(self):
        # Test direct identifier detection by name (various forms)
        test_cases = [
            ("nom_complet", DataType.DIRECT_IDENTIFIER),
            ("firstName", DataType.DIRECT_IDENTIFIER),
            ("LAST_NAME", DataType.DIRECT_IDENTIFIER),
            ("prénom", DataType.DIRECT_IDENTIFIER),
            ("courriel", DataType.DIRECT_IDENTIFIER),
            ("email_address", DataType.DIRECT_IDENTIFIER),
            ("téléphone", DataType.DIRECT_IDENTIFIER),
            ("phoneNumber", DataType.DIRECT_IDENTIFIER),
        ]
        for name, expected in test_cases:
            with self.subTest(name=name):
                res = self.detector.detect_column_type(name, [], 0.0, "object")
                self.assertEqual(res.sensitivity_type, expected, f"Failed for {name}")

    def test_detect_column_type_by_name_quasi(self):
        # Test quasi-identifier detection by name
        test_cases = [
            ("code_postal", DataType.QUASI_IDENTIFIER),
            ("postalCode", DataType.QUASI_IDENTIFIER),
            ("DateNaissance", DataType.QUASI_IDENTIFIER),
            ("birth_date", DataType.QUASI_IDENTIFIER),
            ("genre", DataType.QUASI_IDENTIFIER),
            ("gender", DataType.QUASI_IDENTIFIER),
            ("âge", DataType.QUASI_IDENTIFIER),
        ]
        for name, expected in test_cases:
            with self.subTest(name=name):
                res = self.detector.detect_column_type(name, [], 0.0, "object")
                self.assertEqual(res.sensitivity_type, expected, f"Failed for {name}")
        
    def test_detect_column_type_by_name_sensitive(self):
        # Test sensitive data detection
        test_cases = [
            ("salaire_annuel", DataType.SENSITIVE, Category.FINANCIAL),
            ("annual_income", DataType.SENSITIVE, Category.FINANCIAL),
            ("diagnostic_médical", DataType.SENSITIVE, Category.HEALTH),
            ("medical_history", DataType.SENSITIVE, Category.HEALTH),
            ("opinion_politique", DataType.SENSITIVE, Category.OTHER),
            ("political_affiliation", DataType.SENSITIVE, Category.OTHER),
            ("religion", DataType.SENSITIVE, Category.OTHER),
        ]
        for name, expected_type, expected_cat in test_cases:
            with self.subTest(name=name):
                res = self.detector.detect_column_type(name, [], 0.0, "float")
                self.assertEqual(res.sensitivity_type, expected_type, f"Type failed for {name}")
                self.assertEqual(res.category, expected_cat, f"Category failed for {name}")

    def test_detect_column_type_by_pattern_nas(self):
        # Test pattern detection: NAS (valid Luhn)
        valid_nas = ["123 456 782", "123-456-782", "123456782"] 
        for nas in valid_nas:
            res = self.detector.detect_column_type("random_col", [nas], 0.0, "object")
            self.assertEqual(res.sensitivity_type, DataType.DIRECT_IDENTIFIER, f"Failed for NAS {nas}")

    def test_detect_column_type_non_sensitive_exclusion(self):
        # Test that non-sensitive contexts are excluded
        test_cases = [
            ("product_name", DataType.NON_SENSITIVE),
            ("company_nom", DataType.NON_SENSITIVE),
            ("item_id", DataType.NON_SENSITIVE), 
            ("order_status", DataType.NON_SENSITIVE),
            ("user_id", DataType.DIRECT_IDENTIFIER),
        ]
        for name, expected in test_cases:
            with self.subTest(name=name):
                res = self.detector.detect_column_type(name, ["A", "B"], 0.1, "object")
                self.assertEqual(res.sensitivity_type, expected, f"Failed for {name}")

    def test_nas_checksum(self):
        # Test Luhn algorithm for NAS
        self.assertTrue(self.detector._is_valid_nas("123456782"))
        self.assertFalse(self.detector._is_valid_nas("123456789"))

    def test_detect_column_type_with_normalization(self):
        # Test specific normalization scenarios
        name = "Date_De_Naissance-Client"
        res = self.detector.detect_column_type(name, [], 0.0, "object")
        self.assertEqual(res.sensitivity_type, DataType.QUASI_IDENTIFIER)
        self.assertTrue("date_naissance" in res.justification or "date_de_naissance" in res.justification)

if __name__ == "__main__":
    unittest.main()
