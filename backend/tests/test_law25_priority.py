import unittest
from unittest.mock import MagicMock
import unicodedata
from app.services.detector import SensitiveDataDetector
from app.models.schemas import DataType, Category

def normalize_accents(text: str) -> str:
    """Normalize text by removing accents."""
    return "".join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn').lower()

class TestLaw25Priority(unittest.TestCase):
    def setUp(self):
        self.db = MagicMock()
        self.detector = SensitiveDataDetector(self.db)

    # ROBUST KEYWORDS MAPPING (Roots and partial terms for resilient testing)
    ROBUST_KEYWORDS = {
        Category.FINANCIAL: ["finan", "salair", "revenu", "solde", "compte", "dette", "loan", "income", "credit", "score"],
        Category.HEALTH: ["sant", "medic", "diagnost", "maladie", "patient", "clinical", "health"],
        Category.GENETIC_OR_BIOMETRIC: ["biomet", "genet", "adn", "dna", "facial", "faceid", "face_id", "iris", "empreint", "fingerprint", "reconnaissanc"],
        Category.SEXUAL_LIFE_OR_ORIENTATION: ["sexuel", "orientat", "priv", "intima", "vie_privee", "privacy", "intimacy"],
        Category.RELIGIOUS_OR_PHILOSOPHICAL_BELIEFS: ["relig", "philosoph", "conviction", "croyance", "belief", "faith"],
        Category.POLITICAL_OPINIONS: ["polit", "opinion", "vote", "parti", "party", "affiliat"],
        Category.ETHNIC_OR_RACIAL_ORIGIN: ["race", "ethni", "origin", "ancestr"],
        Category.INSURANCE: ["assuran", "insuran", "policy", "police", "claim", "coverag", "prime", "premium"],
        Category.PERSONAL: []
    }

    def test_law25_priority_by_name(self):
        # Test categories defined in Law 25 by column name
        test_cases = [
            ("income_annual", Category.FINANCIAL, DataType.SENSITIVE),
            ("medical_history", Category.HEALTH, DataType.SENSITIVE),
            ("orientation_sexuelle", Category.SEXUAL_LIFE_OR_ORIENTATION, DataType.SENSITIVE),
            ("religious_belief", Category.RELIGIOUS_OR_PHILOSOPHICAL_BELIEFS, DataType.SENSITIVE),
            ("political_opinion", Category.POLITICAL_OPINIONS, DataType.SENSITIVE),
            ("ethnic_origin", Category.ETHNIC_OR_RACIAL_ORIGIN, DataType.SENSITIVE),
            ("biometrie_faciale", Category.GENETIC_OR_BIOMETRIC, DataType.SENSITIVE),
            ("fingerprint_data", Category.GENETIC_OR_BIOMETRIC, DataType.SENSITIVE),
            ("iris_id", Category.GENETIC_OR_BIOMETRIC, DataType.SENSITIVE),
            ("face_recognition_score", Category.GENETIC_OR_BIOMETRIC, DataType.SENSITIVE),
            ("gender", Category.PERSONAL, DataType.QUASI_IDENTIFIER),
            ("genre_client", Category.PERSONAL, DataType.QUASI_IDENTIFIER),
            ("sexe", Category.PERSONAL, DataType.QUASI_IDENTIFIER),
            ("age", Category.OTHER, DataType.QUASI_IDENTIFIER),
            ("CreditScore", Category.FINANCIAL, DataType.SENSITIVE),
            ("MedicalRecord", Category.HEALTH, DataType.SENSITIVE),
            ("HealthcareExpenses", Category.HEALTH, DataType.SENSITIVE),
            ("AccountBalance", Category.FINANCIAL, DataType.SENSITIVE),
            ("Diagnosis", Category.HEALTH, DataType.SENSITIVE),
            ("Religion", Category.RELIGIOUS_OR_PHILOSOPHICAL_BELIEFS, DataType.SENSITIVE),
            ("PoliticalOpinion", Category.POLITICAL_OPINIONS, DataType.SENSITIVE),
            ("Ethnicity", Category.ETHNIC_OR_RACIAL_ORIGIN, DataType.SENSITIVE),
            ("Race", Category.ETHNIC_OR_RACIAL_ORIGIN, DataType.SENSITIVE),
            ("CustomerId", Category.PERSONAL, DataType.DIRECT_IDENTIFIER),
        ]
        for name, expected_cat, expected_type in test_cases:
            with self.subTest(name=name):
                res = self.detector.detect_column_type(name, [], 0.0, "object")
                self.assertEqual(res.sensitivity_type, expected_type)
                if expected_type == DataType.SENSITIVE:
                    self.assertEqual(res.category, expected_cat, f"Category mismatch for {name}")
                    # Robust check: Must cite the law and contain at least one related root
                    self.assertIn("Loi 25", res.justification)
                    
                    # Normalize justification for accent-insensitive matching
                    justif_norm = normalize_accents(res.justification)
                    roots = self.ROBUST_KEYWORDS.get(expected_cat, ["sensible"])
                    
                    self.assertTrue(
                        any(root in justif_norm for root in roots),
                        f"Justification for {name} does not contain any of the expected roots: {roots}. Found: {res.justification}"
                    )
                elif expected_type == DataType.QUASI_IDENTIFIER:
                    self.assertTrue(res.confidence >= 50.0)

    def test_law25_priority_by_values(self):
        # Test detection by values when name is ambiguous
        test_cases = [
            ("info_1", ["catholique", "athee"], Category.RELIGIOUS_OR_PHILOSOPHICAL_BELIEFS, ["relig", "philosoph", "conviction"]),
            ("info_2", ["homosexuel", "heterosexuel"], Category.SEXUAL_LIFE_OR_ORIENTATION, ["sexue", "orientat", "Loi 25"]),
        ]
        for name, values, expected_cat, roots in test_cases:
            with self.subTest(name=name):
                res = self.detector.detect_column_type(name, values, 0.0, "object")
                self.assertEqual(res.sensitivity_type, DataType.SENSITIVE)
                self.assertEqual(res.category, expected_cat)
                
                self.assertIn("Loi 25", res.justification)
                justif_norm = normalize_accents(res.justification)
                self.assertTrue(
                    any(root in justif_norm for root in roots),
                    f"Justification for {name} (values) does not contain expected roots {roots}. Found: {res.justification}"
                )

    def test_direct_identifier_priority(self):
        # Test that Direct Identifiers stay Direct even if they might seem sensitive
        test_cases = [
            ("nom_usager", DataType.DIRECT_IDENTIFIER),
            ("email_medical", DataType.DIRECT_IDENTIFIER), # IDENTIFIER > HEALTH priority
            ("id_nas_client", DataType.DIRECT_IDENTIFIER),
        ]
        for name, expected_type in test_cases:
            with self.subTest(name=name):
                res = self.detector.detect_column_type(name, [], 0.0, "object")
                self.assertEqual(res.sensitivity_type, expected_type)
                if expected_type == DataType.SENSITIVE:
                    self.assertIn("Loi 25", res.justification)
                else:
                    self.assertEqual(DataType.DIRECT_IDENTIFIER, res.sensitivity_type)
                    # The justification for direct identifiers should mention "Identifiant"
                    self.assertIn("Identifiant", res.justification)

if __name__ == "__main__":
    unittest.main()
