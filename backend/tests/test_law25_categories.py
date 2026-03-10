import pytest
from app.models.schemas import Category, DataType
from app.services.detector import SensitiveDataDetector
from sqlalchemy.orm import Session

def test_law25_sensitive_categories_mapping(db_session: Session):
    """
    Verify that specific keywords map to the correct Law 25 sensitive categories.
    """
    detector = SensitiveDataDetector(db_session)
    
    test_cases = [
        # 1. Financial
        ("credit_score", ["800", "750", "600"], Category.FINANCIAL),
        ("revenu_annuel", ["50000", "75000"], Category.FINANCIAL),
        
        # 2. Genetic or Biometric
        ("biometrie_faciale", ["face_vector_123", "iris_scan"], Category.GENETIC_OR_BIOMETRIC),
        ("adn_profile", ["ATGC...", "sequence_id"], Category.GENETIC_OR_BIOMETRIC),
        ("empreinte_digitale", ["fingerprint_data"], Category.GENETIC_OR_BIOMETRIC),
        
        # 3. Health
        ("diagnostic_medical", ["diabete", "hypertension"], Category.HEALTH),
        ("dossier_patient", ["ID12345"], Category.HEALTH),
        
        # 4. Sexual life or orientation
        ("orientation_sexuelle", ["heterosexuel", "homosexuel"], Category.SEXUAL_LIFE_OR_ORIENTATION),
        
        # 5. Religious or philosophical beliefs
        ("religion", ["catholique", "musulman", "atheiste"], Category.RELIGIOUS_OR_PHILOSOPHICAL_BELIEFS),
        ("conviction_philosophique", ["humanisme", "existentialisme"], Category.RELIGIOUS_OR_PHILOSOPHICAL_BELIEFS),
        
        # 6. Political opinions
        ("parti_politique", ["Libéral", "Conservateur", "PQ"], Category.POLITICAL_OPINIONS),
        ("opinion_politique", ["favorable", "opposé"], Category.POLITICAL_OPINIONS),
        
        # 7. Ethnic or racial origin
        ("origine_ethnique", ["quebecois", "francais", "haitien"], Category.ETHNIC_OR_RACIAL_ORIGIN),
        ("race", ["blanc", "noir", "asiatique"], Category.ETHNIC_OR_RACIAL_ORIGIN),
    ]
    
    for col_name, samples, expected_category in test_cases:
        classification = detector.detect_column_type(
            column_name=col_name,
            sample_values=samples,
            unique_ratio=0.1,
            data_type="string"
        )
        
        assert classification.sensitivity_type == DataType.SENSITIVE, f"Failed sensitivity for {col_name}"
        assert classification.category == expected_category, f"Failed category for {col_name}: expected {expected_category}, got {classification.category}"

def test_law25_category_labels_in_report(db_session: Session):
    """
    Verify that the categories have the correct internal string values.
    """
    # These strings must match exactly what was requested for the backend logic
    assert Category.FINANCIAL.value == "financial"
    assert Category.GENETIC_OR_BIOMETRIC.value == "genetic_or_biometric"
    assert Category.HEALTH.value == "health"
    assert Category.SEXUAL_LIFE_OR_ORIENTATION.value == "sexual_life_or_orientation"
    assert Category.RELIGIOUS_OR_PHILOSOPHICAL_BELIEFS.value == "religious_or_philosophical_beliefs"
    assert Category.POLITICAL_OPINIONS.value == "political_opinions"
    assert Category.ETHNIC_OR_RACIAL_ORIGIN.value == "ethnic_or_racial_origin"
