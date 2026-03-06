"""
Sensitive data detection service for Quebec Law 25 compliance.

This service analyzes dataset columns to identify and classify sensitive information
using pattern matching, column name heuristics, and statistical analysis.
"""
import re
from typing import Any, Dict, List
from uuid import UUID

import pandas as pd
from sqlalchemy.orm import Session

from app.models.database import Dataset, DatasetColumn
from app.models.schemas import (
    DataType,
    Category,
    ColumnClassification,
    DetectionReport,
)
from app.services.data_ingestion import DataIngestionService
from app.core.text_utils import normalize_text


class SensitiveDataDetector:
    """
    Detects and classifies sensitive data in datasets.

    Classification follows Quebec Law 25 categories:
    - Direct identifiers: Unique identifiers (NAS, email, etc.)
    - Quasi-identifiers: Can re-identify when combined (DOB, postal code)
    - Sensitive: Financial, health, insurance data
    - Non-sensitive: General information
    """

    # Regex patterns for direct and quasi identifiers
    PATTERNS = {
        # Canadian Social Insurance Number (NAS/SIN)
        "NAS": r"^\d{3}[-\s]?\d{3}[-\s]?\d{3}$",

        # Quebec Health Insurance Number (RAMQ): ABCD 1234 5678
        "RAMQ": r"^[A-Z]{4}\s?\d{4}\s?\d{4}$",

        # Passport (CA): 2 letters + 6 digits
        "PASSPORT_CA": r"^[A-Z]{2}\d{6}$",

        # US Social Security Number (SSN)
        "SSN_US": r"^\d{3}-\d{2}-\d{4}$",

        # Email addresses
        "EMAIL": r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$",

        # Canadian phone numbers
        "TELEPHONE_CA": r"^(\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}$",

        # Canadian postal code: H3B 1A1, H3B1A1
        "CODE_POSTAL_CA": r"^[A-Z]\d[A-Z][\s]?\d[A-Z]\d$",

        # Date formats: YYYY-MM-DD, DD/MM/YYYY, etc.
        "DATE": r"^\d{4}[-/]\d{2}[-/]\d{2}$|^\d{2}[-/]\d{2}[-/]\d{4}$|^\d{1,2}[-/]\d{1,2}[-/]\d{2,4}$",

        # Credit Card (General)
        "CREDIT_CARD": r"^\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}$",

        # IBAN (International Bank Account Number)
        "IBAN": r"^[A-Z]{2}\d{2}[A-Z0-9]{4,30}$",

        # IP Address (v4 and v6)
        "IP_ADDRESS": r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$|^(?:[A-F0-9]{1,4}:){7}[A-F0-9]{1,4}$",

        # MAC Address
        "MAC_ADDRESS": r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$",

        # Quebec Driving License (Approximate)
        "PERMIS_QC": r"^[A-Z]\d{4}\d{6}\d{2}$",

        # GPS Coordinates
        "GPS_COORDS": r"^-?\d{1,3}\.\d+,\s?-?\d{1,3}\.\d+$",
    }

    # Column name keywords for classification (FR and EN)
    # Normalized versions only (no accents, lowercase, snake_case)
    COLUMN_NAME_KEYWORDS = {
        # Direct identifiers - Unique person identifier
        "DIRECT": [
            "nom", "name", "surname", "lastname", "family_name", "last_name", "full_name", "nom_complet",
            "prenom", "firstname", "given_name", "first_name", "middle_name", "fullname",
            "email", "courriel", "e_mail", "mail", "adresse_electronique",
            "telephone", "phone", "tel", "mobile", "cellulaire", "cell", "fax", "numero_telephone", "phone_number",
            "nas", "sin", "social_insurance", "assurance_sociale", "ssn", "social_security", "socialsecuritynumber",
            "ramq", "assurance_maladie", "health_insurance",
            "passport", "passeport", "no_passport", "passport_number", "numero_passeport",
            "permis", "license", "licence", "drivers_license", "permis_conduire",
            "id_client", "client_id", "customer_id", "user_id", "userid", "uid", "sid", "clientid", "customerid",
            "identifiant", "identifier", "numero_client", "customer_number",
            "account_id", "compte_id", "user_name", "username", "login", "pseudo", "nickname", "alias",
        ],

        # Quasi-identifiers - Can re-identify when combined
        "QUASI": [
            "date_naissance", "birthdate", "dob", "birth_date", "naissance", "born", "birthday", "dateofbirth",
            "age", "age_at", "tranche_age", "annee_naissance", "birth_year",
            "profession", "metier", "job", "occupation", "work", "title", "titre", "poste", "position",
            "employeur", "employer", "scolarite", "education", "degree", "diplome",
            "etat_civil", "marital_status", "statut_matrimonial", "mariage", "conjoint", "spouse",
            "postal", "zip", "code_postal", "zip_code", "postal_code", "pcode", "zipcode", "codepostal",
            "adresse", "address", "rue", "street", "civique", "apt", "suite", "local", "bureau",
            "ville", "city", "town", "locality", "province", "state", "etat", "pays", "country", "nation",
            "region", "coordonnees", "coordinates", "gps", "latitude", "longitude", "coords", "location", "lieu", "geography", "localisation",
            "date_", "time_", "timestamp", "horodatage",
        ],

        # Sensitive data - Nature is sensitive (Finance, Health, Criminal, Opinion, Law 25)
        # Note: Law 25 Article 110 defines sensitive information as:
        # medical, financial, biometric, or otherwise intimate info (religion, orientation, etc.)
        "SENSITIVE": [
            # Financial
            "revenu", "income", "salary", "salaire", "wage", "earnings", "remuneration",
            "solde", "balance", "montant", "amount", "valeur", "value",
            "compte_bancaire", "bank_account", "numero_compte", "account_number",
            "credit_score", "creditscore", "scorecredit", "cote_credit", "rating",
            "debt", "dette", "emprunt", "loan", "hypotheque",
            "expenses", "depenses", "medical_costs", "healthcare_expenses",
            # Health
            "medical", "health", "sante", "diagnostic", "maladie", "disease", "medical_condition",
            "condition", "pathology", "traitement", "treatment", "medicament", "medication", "drug",
            "ordonnance", "symptome", "resultat", "analyse", "test", "medecin", "doctor", "clinique", "hospital", "hospitalisation",
            # Biometric & Genetic
            "empreinte", "fingerprint", "visage", "facial", "biometric", "biometrie", "iris", "faceid", "adn", "dna", "genetic", "genetique",
            # Origin & Demographics (Sensitive under Law 25)
            "race", "ethnie", "ethnicity", "origine", "origin", "ancestry", "origine_ethnique", "ethnic_origin",
            # Intimate info & Opinions (Law 25)
            "genre", "gender", "sexe", "sex",
            "opinion", "politique", "political", "parti", "party", "vote", "affiliation", "political_opinion", "parti_politique", "political_affiliation",
            "philosophy", "philosophie", "religion", "croyance", "belief", "faith", "religious_belief",
            "vie_privee", "privacy", "intimacy", "sexual", "sexuel", "sexual_orientation", "orientation_sexuelle",
            # Insurance
            "assurance", "insurance", "police", "policy", "claim"
        ],
        
        # Non-sensitive data - Low risk
        "NON_SENSITIVE": [
            "transaction_count", "nombre_produits", "num_products", "order_status", "statut_commande",
            "categorie_produit", "product_category", "transaction_date", "date_transaction",
            "is_active", "active_member", "membre_actif", "status", "statut", "type", "category", "categorie"
        ]
    }

    def __init__(self, db: Session):
        self.db = db
        self.ingestion_service = DataIngestionService(db)

    async def analyze_dataset(self, dataset_id: UUID) -> DetectionReport:
        """
        Analyze all columns in a dataset and classify sensitive data.

        Args:
            dataset_id: UUID of the dataset to analyze

        Returns:
            DetectionReport with column classifications and risk score
        """
        # Load dataset and dataframe
        dataset = self.ingestion_service.get_dataset(dataset_id)
        df = self.ingestion_service.load_dataframe(dataset_id)

        # Analyze each column
        classifications: Dict[str, ColumnClassification] = {}

        for column in dataset.columns:
            col_data = df[column.name]
            classification = self.detect_column_type(
                column_name=column.name,
                sample_values=col_data.dropna().head(50).tolist(),
                unique_ratio=column.unique_count / dataset.row_count if dataset.row_count > 0 else 0,
                data_type=column.data_type,
            )
            classifications[column.name] = classification

            # Update column in database
            # Ensure we use .value for Enum types if they are Enums
            column.sensitivity_type = classification.sensitivity_type.value if hasattr(classification.sensitivity_type, "value") else classification.sensitivity_type
            column.category = classification.category.value if hasattr(classification.category, "value") else classification.category
            column.confidence = classification.confidence

        summary = {
            "direct_identifier": sum(1 for c in classifications.values() if c.sensitivity_type == DataType.DIRECT_IDENTIFIER),
            "quasi_identifier": sum(1 for c in classifications.values() if c.sensitivity_type == DataType.QUASI_IDENTIFIER),
            "sensitive": sum(1 for c in classifications.values() if c.sensitivity_type == DataType.SENSITIVE),
            "non_sensitive": sum(1 for c in classifications.values() if c.sensitivity_type == DataType.NON_SENSITIVE),
        }

        # Calculate overall risk score (0-100)
        # Higher weight for direct identifiers and sensitive data
        total_columns = len(classifications)
        if total_columns > 0:
            risk_score = (
                (summary["direct_identifier"] * 40) +
                (summary["quasi_identifier"] * 25) +
                (summary["sensitive"] * 20)
            ) / total_columns
        else:
            risk_score = 0

        # Update dataset
        dataset.risk_score = min(risk_score, 100)
        self.db.commit()

        return DetectionReport(
            dataset_id=dataset_id,
            columns=classifications,
            overall_risk_score=risk_score,
            summary=summary,
        )

    def detect_column_type(
        self,
        column_name: str,
        sample_values: List[Any],
        unique_ratio: float,
        data_type: str,
    ) -> ColumnClassification:
        """
        Detect the sensitivity type of a single column using combined heuristics.
        """
        # 0. Normalize column name
        normalized_name = normalize_text(column_name)
        
        # Track confidence scores for each detection method
        scores: Dict[DataType, float] = {
            DataType.DIRECT_IDENTIFIER: 0.0,
            DataType.QUASI_IDENTIFIER: 0.0,
            DataType.SENSITIVE: 0.0,
            DataType.NON_SENSITIVE: 40.0,  # Baseline
        }

        category = Category.OTHER
        justification_parts = []

        # 1. Check column name heuristics (primary)
        name_check = self._check_column_name(normalized_name)
        if name_check:
            sensitivity, cat, score = name_check
            scores[sensitivity] += score
            category = cat
            justification_parts.append(f"Nom normalisé '{normalized_name}' correspond à {cat.value}")

        # 2. Check pattern matching on values (secondary validation)
        pattern_check = self._check_patterns(sample_values)
        pattern_type = pattern_check[0] if pattern_check else None
        if pattern_check:
            p_type, score = pattern_check
            # Direct IDs patterns
            if p_type in ["NAS", "RAMQ", "PASSPORT_CA", "EMAIL", "TELEPHONE_CA", "PERMIS_QC", "SSN_US"]:
                scores[DataType.DIRECT_IDENTIFIER] += (score * 0.8)
                if category == Category.OTHER:
                    category = Category.HEALTH if p_type == "RAMQ" else Category.PERSONAL
                justification_parts.append(f"Format {p_type} détecté ({score:.0f}%)")
                
            # Financial patterns
            elif p_type in ["CREDIT_CARD", "IBAN"]:
                scores[DataType.SENSITIVE] += (score * 0.8)
                category = Category.FINANCIAL
                justification_parts.append(f"Format bancaire {p_type} détecté")
                
            # Quasi patterns
            elif p_type in ["CODE_POSTAL_CA", "IP_ADDRESS", "MAC_ADDRESS", "DATE", "GPS_COORDS"]:
                scores[DataType.QUASI_IDENTIFIER] += (score * 0.6)
                justification_parts.append(f"Motif technique {p_type} détecté")

        # 3. Statistical analysis - uniqueness
        if unique_ratio > 0.98 and len(sample_values) > 10:
            scores[DataType.DIRECT_IDENTIFIER] += 25
            justification_parts.append(f"Unicité critique ({unique_ratio:.1%})")
        elif unique_ratio > 0.8:
            scores[DataType.QUASI_IDENTIFIER] += 15

        # 4. Data type heuristics
        is_numeric = "int" in str(data_type).lower() or "float" in str(data_type).lower()
        if is_numeric:
            if scores[DataType.SENSITIVE] > 0 or scores[DataType.QUASI_IDENTIFIER] > 0:
                scores[DataType.SENSITIVE] += 10
                
        # Determine final classification
        final_type = max(scores.keys(), key=lambda k: scores[k])
        confidence = min(scores[final_type], 100.0)
        
        # If confidence is too low, default to NON_SENSITIVE
        if confidence < 50:
            final_type = DataType.NON_SENSITIVE
            confidence = 50.0

        return ColumnClassification(
            column_name=column_name,
            sensitivity_type=final_type,
            category=category,
            confidence=confidence,
            justification="; ".join(justification_parts) if justification_parts else "Analyse statistique par défaut",
            suggested_config=self._get_suggested_config(
                column_name=column_name,
                sensitivity_type=final_type,
                category=category,
                data_type=data_type,
                pattern_type=pattern_type
            ),
        )

    def _get_suggested_config(
        self,
        column_name: str,
        sensitivity_type: DataType,
        category: Category,
        data_type: str,
        pattern_type: str | None,
    ) -> Any | None:
        """
        Generate suggested anonymization configuration based on content and type.
        """
        from app.models.schemas import AnonymizationConfig, AnonymizationTechnique

        # Only suggest for sensitive data
        if sensitivity_type == DataType.NON_SENSITIVE:
            return None
        
        # 1. Direct Identifiers -> Masking or Suppression
        if sensitivity_type == DataType.DIRECT_IDENTIFIER:
            if pattern_type == "NAS":
                 return AnonymizationConfig(
                    column_name=column_name,
                    technique=AnonymizationTechnique.SUPPRESSION,
                    params={}
                )
            # Default to masking for other direct identifiers
            return AnonymizationConfig(
                column_name=column_name,
                technique=AnonymizationTechnique.MASKING,
                params={"visible_chars": 2}
            )

        # 2. Sensitive Data (Numeric) -> Differential Privacy
        is_numeric = "int" in str(data_type).lower() or "float" in str(data_type).lower()
        if sensitivity_type == DataType.SENSITIVE and is_numeric:
             return AnonymizationConfig(
                column_name=column_name,
                technique=AnonymizationTechnique.DIFFERENTIAL_PRIVACY,
                params={"epsilon": 1.0}
            )

        # 3. Generalization fallback (Quasi or Sensitive Text/Date)
        # Date -> Year
        if pattern_type == "DATE" or "datetime" in str(data_type).lower() or "date" in str(data_type).lower():
            return AnonymizationConfig(
                column_name=column_name,
                technique=AnonymizationTechnique.GENERALIZATION,
                params={"mode": "year"}
            )
        
        # Postal Code detection
        if pattern_type == "CODE_POSTAL_CA":
            return AnonymizationConfig(
                column_name=column_name,
                technique=AnonymizationTechnique.GENERALIZATION,
                params={"mode": "prefix", "prefix_length": 3}
            )

        # Numeric (Age/etc) -> Fixed Range (e.g. 10 years)
        if is_numeric:
            return AnonymizationConfig(
                column_name=column_name,
                technique=AnonymizationTechnique.GENERALIZATION,
                params={"mode": "range", "range_size": 10}
            )

        # Default for text or anything else -> Prefix
        return AnonymizationConfig(
            column_name=column_name,
            technique=AnonymizationTechnique.GENERALIZATION,
            params={"mode": "prefix", "prefix_length": 3}
        )

    def _check_column_name(self, normalized_name: str) -> tuple[DataType, Category, float] | None:
        """Match normalized column name against dictionaries."""
        
        # Check explicit non-sensitive first to avoid false positives (e.g., product_name)
        for keyword in self.COLUMN_NAME_KEYWORDS["NON_SENSITIVE"]:
            if keyword == normalized_name or f"_{keyword}" in normalized_name or f"{keyword}_" in normalized_name:
                return (DataType.NON_SENSITIVE, Category.OTHER, 90.0)

        # Check direct identifiers
        for keyword in self.COLUMN_NAME_KEYWORDS["DIRECT"]:
            if keyword == normalized_name or f"_{keyword}" in normalized_name or f"{keyword}_" in normalized_name:
                # Exclude if it also contains non-sensitive contexts
                if any(x in normalized_name for x in ["product", "item", "order", "company", "entreprise", "objet", "status", "statut"]):
                    continue
                return (DataType.DIRECT_IDENTIFIER, Category.PERSONAL, 85.0)

        # Check sensitive
        for keyword in self.COLUMN_NAME_KEYWORDS["SENSITIVE"]:
            if keyword == normalized_name or f"_{keyword}" in normalized_name or f"{keyword}_" in normalized_name:
                # Sub-categorization
                cat = Category.OTHER
                if any(k in normalized_name for k in ["revenu", "income", "salaire", "salary", "account", "compte", "bank", "bancaire", "credit", "debt", "dette", "expense", "depense"]):
                    cat = Category.FINANCIAL
                elif any(k in normalized_name for k in ["medical", "health", "sante", "maladie", "disease", "treatment", "traitement", "hospital"]):
                    cat = Category.HEALTH
                elif any(k in normalized_name for k in ["biometric", "biometrie", "empreinte", "fingerprint", "dna", "adn", "genetic", "faceid", "iris"]):
                    cat = Category.HEALTH # Biometrics categorized under Health/Personal
                elif any(k in normalized_name for k in ["religion", "political", "politique", "sexual", "orientation", "gender", "genre", "sexe", "race", "ethni", "origin"]):
                    cat = Category.PERSONAL # Law 25 Sensitive info (Intimate/Demographic)
                
                return (DataType.SENSITIVE, cat, 85.0)

        # Check quasi-identifiers
        for keyword in self.COLUMN_NAME_KEYWORDS["QUASI"]:
            if keyword == normalized_name or f"_{keyword}" in normalized_name or f"{keyword}_" in normalized_name:
                return (DataType.QUASI_IDENTIFIER, Category.OTHER, 80.0)

        return None

    def _check_patterns(self, sample_values: List[Any]) -> tuple[str, float] | None:
        """
        Check if sample values match known patterns.
        """
        if not sample_values:
            return None

        # Convert to strings and filter out None values, take first 20
        str_values: List[str] = [str(v).strip() for v in sample_values if v is not None][:20]
        if not str_values:
            return None

        total = len(str_values)

        # Test each pattern
        for pattern_name, pattern_regex in self.PATTERNS.items():
            matches = 0
            for value in str_values:
                if re.match(pattern_regex, value, re.IGNORECASE):
                    matches += 1

            # If >70% match, consider it detected
            match_ratio = matches / total
            if match_ratio > 0.7:
                confidence = float(min(match_ratio * 100, 100))
                
                # Further validation for NAS (checksum)
                if pattern_name == "NAS":
                    valid_nas_count = sum(1 for v in str_values if self._is_valid_nas(v))
                    if valid_nas_count > 0:
                        confidence = min(confidence + 15.0, 100.0)
                
                return (pattern_name, confidence)

        return None

    def _is_valid_nas(self, nas: str) -> bool:
        """
        Validate a Canadian Social Insurance Number (NAS/SIN) using the Luhn algorithm.
        """
        # Remove non-digits
        digits = re.sub(r"\D", "", nas)
        if len(digits) != 9:
            return False
        
        # Luhn algorithm
        try:
            numbers = [int(d) for d in digits]
            checksum = 0
            for i in range(9):
                if i % 2 == 1: # Even positions (0-indexed) are multiplied by 2
                    val = numbers[i] * 2
                    checksum += val if val < 10 else (val - 9)
                else:
                    checksum += numbers[i]
            return checksum % 10 == 0
        except ValueError:
            return False
