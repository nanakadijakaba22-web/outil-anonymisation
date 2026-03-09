import unittest
from unittest.mock import MagicMock
from app.services.detector import SensitiveDataDetector
from app.models.schemas import DataType, Category

class TestLaw25Priority(unittest.TestCase):
    def setUp(self):
        self.db = MagicMock()
        self.detector = SensitiveDataDetector(self.db)

    def test_law25_priority_by_name(self):
        # Test categories defined in Law 25 by column name
        test_cases = [
            ("revenu_annuel", Category.FINANCIAL, DataType.SENSITIVE),
            ("medical_history", Category.HEALTH, DataType.SENSITIVE),
            ("orientation_sexuelle", Category.PERSONAL, DataType.SENSITIVE),
            ("religious_belief", Category.PERSONAL, DataType.SENSITIVE),
            ("political_opinion", Category.PERSONAL, DataType.SENSITIVE),
            ("ethnic_origin", Category.PERSONAL, DataType.SENSITIVE),
            ("biometrie_faciale", Category.HEALTH, DataType.SENSITIVE),
            ("gender", Category.PERSONAL, DataType.QUASI_IDENTIFIER),
            ("genre_client", Category.PERSONAL, DataType.QUASI_IDENTIFIER),
            ("sexe", Category.PERSONAL, DataType.QUASI_IDENTIFIER),
            ("age", Category.OTHER, DataType.QUASI_IDENTIFIER),
        ]
        for name, expected_cat, expected_type in test_cases:
            with self.subTest(name=name):
                res = self.detector.detect_column_type(name, [], 0.0, "object")
                self.assertEqual(res.sensitivity_type, expected_type)
                if expected_type == DataType.SENSITIVE:
                    self.assertEqual(res.category, expected_cat)
                    self.assertIn("Classification prioritaire selon la Loi 25 – ", res.justification)
                    # Check that a specific category name is present (not generic)
                    self.assertNotIn("catégorie sensitive", res.justification)
                elif expected_type == DataType.QUASI_IDENTIFIER:
                    self.assertTrue(res.confidence >= 50.0)

    def test_law25_priority_by_values(self):
        # Test detection by values when name is ambiguous
        test_cases = [
            ("info_1", ["catholique", "athee"], Category.PERSONAL, "Convictions religieuses et philosophiques"),
            ("info_2", ["homosexuel", "heterosexuel"], Category.PERSONAL, "Vie sexuelle et orientation"),
        ]
        for name, values, expected_cat, justif_snippet in test_cases:
            with self.subTest(name=name):
                res = self.detector.detect_column_type(name, values, 0.0, "object")
                self.assertEqual(res.sensitivity_type, DataType.SENSITIVE)
                self.assertEqual(res.category, expected_cat)
                self.assertIn(justif_snippet, res.justification)
                self.assertIn("Classification prioritaire selon la Loi 25 – ", res.justification)

    def test_direct_identifier_priority(self):
        # Test that Direct Identifiers stay Direct even if they might seem sensitive
        test_cases = [
            ("nom_usager", DataType.DIRECT_IDENTIFIER),
            ("email_medical", DataType.SENSITIVE), # Matches 'medical' keyword -> Sensitive priority
            ("id_nas_client", DataType.DIRECT_IDENTIFIER),
        ]
        for name, expected_type in test_cases:
            with self.subTest(name=name):
                res = self.detector.detect_column_type(name, [], 0.0, "object")
                self.assertEqual(res.sensitivity_type, expected_type)
                if expected_type == DataType.SENSITIVE:
                    self.assertIn("Classification prioritaire selon la Loi 25 – ", res.justification)
                else:
                    self.assertTrue(DataType.DIRECT_IDENTIFIER == res.sensitivity_type)
                    # The justification for direct identifiers might vary, but should mention "Sémantique" or "Sécurité"
                    self.assertTrue("Sémantique" in res.justification or "Sécurité" in res.justification or "Identifiant" in res.justification)

if __name__ == "__main__":
    unittest.main()
