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

        # Name pattern: Alphabetic with possible spaces/hyphens (e.g., Jean-Marie, O'Connor)
        "NAME": r"^[a-zàâçéèêëîïôûùÿñæœ]+(?:[-'\s][a-zàâçéèêëîïôûùÿñæœ]+)*$",

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
        # Direct identifiers - Unique person identifier
        "DIRECT": [
            "nom", "name", "surname", "lastname", "family_name", "last_name", "full_name", "nom_complet",
            "prenom", "firstname", "given_name", "first_name", "middle_name", "fullname", "first", "last",
            "email", "courriel", "e_mail", "mail", "adresse_electronique",
            "telephone", "phone", "tel", "mobile", "cellulaire", "cell", "fax", "numero_telephone", "phone_number",
            "nas", "sin", "social_insurance", "assurance_sociale", "ssn", "social_security", "socialsecuritynumber",
            "ramq", "assurance_maladie", "health_insurance",
            "passport", "passeport", "no_passport", "passport_number", "numero_passeport",
            "permis", "license", "licence", "drivers_license", "permis_conduire", "drivers",
            "maiden", "nom_jeune_fille",
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
            "postal", "zip", "code_postal", "zip_code", "postal_code", "pcode", "zipcode", "codepostal",
            "adresse", "address", "rue", "street", "civique", "apt", "suite", "local", "bureau",
            "ville", "city", "town", "locality", "province", "state", "etat", "pays", "country", "nation",
            "region", "coordonnees", "coordinates", "gps", "latitude", "longitude", "coords", "location", "lieu", "geography", "localisation", "lat", "lon",
            "date_", "time_", "timestamp", "horodatage",
        ],

        # Sensitive data - Nature is sensitive (Finance, Health, Criminal, Opinion, Law 25)
        "SENSITIVE": [
            # Financial
            "revenu", "income", "salary", "salaire", "wage", "earnings", "remuneration",
            "solde", "balance",
            "compte_bancaire", "bank_account", "numero_compte", "account_number",
            "credit_score", "creditscore", "scorecredit", "cote_credit", "rating",
            "debt", "dette", "emprunt", "loan", "hypotheque",
            "expenses", "depenses", "medical_costs", "healthcare_expenses", "healthcare_coverage",
            # Health
            "medical", "health", "sante", "diagnostic", "maladie", "disease", "medical_condition",
            "condition", "pathology", "traitement", "treatment", "medicament", "medication", "drug",
            "ordonnance", "symptome", "resultat", "analyse", "test", "medecin", "doctor", "clinique", "hospital", "hospitalisation",
            # Biometric & Genetic
            "empreinte", "fingerprint", "visage", "facial", "biometric", "biometrie", "iris", "faceid", "adn", "dna", "genetic", "genetique",
            # Origin & Demographics (Sensitive under Law 25)
            "race", "ethnie", "ethnicity", "origine", "origin", "ancestry", "origine_ethnique", "ethnic_origin",
            # Intimate info & Opinions (Law 25)
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
            "is_active", "active_member", "membre_actif", "status", "statut", "type", "category", "categorie",
            "item_id", "product_id", "prefix", "suffix", "marital", "county", "birthplace", "prefixe", "suffixe"
        ],

        # Intrinsically Sensitive Domains (Always SENSITIVE)
        "INTRINSIC_SENSITIVE": [
            "credit_score", "score_credit", "income", "revenu", "salary", "salaire", "wage", "earnings",
            "loan", "dette", "debt", "balance", "solde", "amount", "montant", "expense", "depense",
            "medical", "health", "sante", "insurance", "assurance", "coverage", "premium", "prime",
            "religion", "belief", "croyance", "political", "politique", "sexual", "orientation",
            "biometric", "biometrie", "biométrie", "facial", "face_id", "faceid", "fingerprint", "empreinte", "iris", "reconnaissance", "dna", "adn", "genetic", "genetique"
        ]
    }

    # Loi 25 Priority Categories (Quebec Law 25 - Official Article 110 & Definitions)
    # These 7 categories are explicitly defined as sensitive information by Law 25.
    # Order matters for priority within detection logic.
    LAW25_PRIORITY_CATEGORIES = {
        "BIOMETRIQUE": ["biometrie", "biometric", "biométrie", "facial", "face_id", "faceid", "fingerprint", "empreinte", "iris", "reconnaissance", "face", "reconnaissanc"],
        "GENETIQUE": ["adn", "dna", "genetique", "genetic"],
        "SANTE": ["medical", "health", "sante", "patient", "diagnosis", "disease", "clinical", "traitement", "diagnostic", "record", "medic", "diagnost", "clinical", "sant", "healthcare_expenses", "healthcare_coverage"],
        "FINANCE": ["credit", "score", "salary", "income", "loan", "balance", "account", "payment", "debt", "salaire", "revenu", "solde", "compte", "finan", "salair", "dette"],
        "VIE SEXUELLE": ["vie_privee", "privacy", "intimacy", "sexuel", "priv", "intima", "sexual_life"],
        "ORIENTATION SEXUELLE": ["sexual", "orientation", "orientat", "lgbt", "gay", "lesbien", "hetero", "bi", "genre", "gender", "sexe", "sex"],
        "RELIGION": ["religion", "croyance", "belief", "faith", "relig", "conviction", "belief", "spiritual", "athe"],
        "PHILOSOPHIE": ["philosophie", "philosophy", "philosoph"],
        "ORIGINE_RACIALE": ["race", "ethnicity", "ethnie", "racial", "ancestry", "origine", "origin", "ancestr", "ethnic", "origine_ethnique", "ethnic_origin"],
        "ASSURANCE": ["assurance", "insurance", "policy", "police", "claim", "coverage", "premium", "prime"],
    }

    # Display names for Law 25 categories
    LAW25_DISPLAY_NAMES = {
        "BIOMETRIQUE": "Biométrique",
        "GENETIQUE": "Génétique",
        "SANTE": "Santé",
        "FINANCE": "Financier",
        "VIE SEXUELLE": "Vie sexuelle",
        "ORIENTATION SEXUELLE": "Orientation sexuelle",
        "RELIGION": "Religion",
        "PHILOSOPHIE": "Philosophie",
        "POLITIQUE": "Politique",
        "ETHNIQUE": "Ethnique",
        "RACIALE": "Raciale",
        "ORIGINE_RACIALE": "Origine ethnique ou raciale",
        "ASSURANCE": "Assurance",
        "PERSONAL": "Personnel"
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
            if column.name not in df.columns:
                classification = ColumnClassification(
                    column_name=column.name,
                    sensitivity_type=DataType.NON_SENSITIVE,
                    category=Category.OTHER,
                    confidence=0.0,
                    justification="Erreur : Colonne introuvable dans les données.",
                    suggested_config=None,
                )
            else:
                try:
                    col_data = df[column.name]
                    classification = self.detect_column_type(
                        column_name=column.name,
                        sample_values=col_data.dropna().head(50).tolist(),
                        unique_ratio=column.unique_count / dataset.row_count if dataset.row_count > 0 else 0,
                        data_type=column.data_type,
                    )
                except Exception as e:
                    classification = ColumnClassification(
                        column_name=column.name,
                        sensitivity_type=DataType.NON_SENSITIVE,
                        category=Category.OTHER,
                        confidence=0.0,
                        justification=f"Erreur d'analyse : {str(e)}",
                        suggested_config=None,
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
        Detect the sensitivity type of a single column using a triple-layer weighted scoring system:
        Level 1: Semantic Analysis (Name/Roots) - 40%
        Level 2: Structural Analysis (Patterns/Types) - 40%
        Level 3: Statistical Analysis (Uniqueness/Cardinality) - 20%
        """
        # 0. Normalize column name
        normalized_name = normalize_text(column_name)
        
        # 0.1 DIRECT IDENTIFIER PRIORITY (HIGHEST)
        # Check by name first, with content validation for short/ambiguous names
        # print(f"DEBUG: Checking direct identifier for {normalized_name}")
        if self._is_direct_identifier_name(normalized_name, sample_values):
             return ColumnClassification(
                column_name=column_name,
                sensitivity_type=DataType.DIRECT_IDENTIFIER,
                category=Category.PERSONAL,
                confidence=95.0,
                justification=f"Identifiant direct : Reconnu par son nom de colonne '{column_name}' et validé par le contenu",
                suggested_config=self._get_suggested_config(
                    column_name, DataType.DIRECT_IDENTIFIER, Category.PERSONAL, data_type, None
                ),
            )

        # 0.2 LAW 25 PRIORITY RULE (ABSOLUTE PRIORITY FOR TRULY SENSITIVE DOMAINS)
        law25_match = self._check_law25_priority(normalized_name, sample_values)
        if law25_match:
            category, justification = law25_match
            # For these priority domains, always force SENSITIVE
            return ColumnClassification(
                column_name=column_name,
                sensitivity_type=DataType.SENSITIVE,
                category=category,
                confidence=100.0,
                justification=justification,
                suggested_config=self._get_suggested_config(
                    column_name, DataType.SENSITIVE, category, data_type, None
                ),
            )

        # 0.2 Initial Scores
        layer_scores: Dict[DataType, float] = {
            DataType.DIRECT_IDENTIFIER: 0.0,
            DataType.QUASI_IDENTIFIER: 0.0,
            DataType.SENSITIVE: 0.0,
            DataType.NON_SENSITIVE: 0.0,
        }
        
        category = Category.OTHER
        justification_parts = []
        pattern_type = None

        # --- LEVEL 1: SEMANTIC ANALYSIS (Weight: 40%) ---
        name_check = self._check_column_name(normalized_name, sample_values)
        if name_check:
            sensitivity, cat, score = name_check
            # Scale score to 40 max
            layer_scores[sensitivity] += (score / 100.0) * 40.0
            category = cat
            display_name = self.LAW25_DISPLAY_NAMES.get(cat.value, cat.value)
            justification_parts.append(f"Analyse Sémantique : '{normalized_name}' identifié comme {display_name}")
        else:
            layer_scores[DataType.NON_SENSITIVE] += 20.0 # Baseline if name unknown

        # --- LEVEL 2: STRUCTURAL ANALYSIS (Weight: 40%) ---
        pattern_check = self._check_patterns(sample_values)
        if pattern_check:
            p_type, score = pattern_check
            pattern_type = p_type
            contribution = (score / 100.0) * 40.0
            
            if p_type in ["NAS", "RAMQ", "PASSPORT_CA", "EMAIL", "TELEPHONE_CA", "PERMIS_QC", "SSN_US"]:
                layer_scores[DataType.DIRECT_IDENTIFIER] += contribution
                if category == Category.OTHER:
                    category = Category.HEALTH if p_type == "RAMQ" else Category.PERSONAL
            elif p_type in ["CREDIT_CARD", "IBAN"]:
                layer_scores[DataType.SENSITIVE] += contribution
                category = Category.FINANCIAL
            elif p_type in ["CODE_POSTAL_CA", "IP_ADDRESS", "MAC_ADDRESS", "DATE", "GPS_COORDS"]:
                layer_scores[DataType.QUASI_IDENTIFIER] += contribution
            
            justification_parts.append(f"Analyse Structurelle : Motif {p_type} détecté ({score:.0f}%)")
        else:
            # Data type impact
            is_numeric = any(t in str(data_type).lower() for t in ["int", "float", "decimal"])
            if is_numeric and category == Category.FINANCIAL:
                layer_scores[DataType.SENSITIVE] += 15.0
            layer_scores[DataType.NON_SENSITIVE] += 10.0

        # --- LEVEL 3: STATISTICAL ANALYSIS (Weight: 20%) ---
        # Uniqueness & Cardinality
        if unique_ratio > 0.98 and len(sample_values) > 10:
            layer_scores[DataType.DIRECT_IDENTIFIER] += 20.0
            justification_parts.append(f"Analyse Statistique : Unicité critique ({unique_ratio:.1%})")
        elif unique_ratio > 0.7:
            layer_scores[DataType.QUASI_IDENTIFIER] += 15.0
            justification_parts.append(f"Analyse Statistique : Haute cardinalité")
        else:
            layer_scores[DataType.NON_SENSITIVE] += 10.0

        # --- FINAL AGGREGATION ---
        # Base confidence for non-sensitive if nothing else found
        if all(v == 0 for k, v in layer_scores.items() if k != DataType.NON_SENSITIVE):
            final_type = DataType.NON_SENSITIVE
            confidence = 60.0 # Standard baseline
        else:
            final_type = max(layer_scores.keys(), key=lambda k: layer_scores[k])
            confidence = min(layer_scores[final_type], 100.0)

        # 1. FINAL JUSTIFICATION ASSEMBLY
        final_justification = "; ".join(justification_parts) if justification_parts else "Classification par défaut"

        # 2. SECURITY & NATURE OVERLAYS
        if final_type == DataType.DIRECT_IDENTIFIER:
             final_justification = f"Identifiant direct : {final_justification}"
        else:
            is_intrinsically_sensitive = any(keyword in normalized_name for keyword in self.COLUMN_NAME_KEYWORDS["INTRINSIC_SENSITIVE"])
            if is_intrinsically_sensitive and final_type != DataType.SENSITIVE:
                final_type = DataType.SENSITIVE
                confidence = max(confidence, 85.0)
                justification_parts.insert(0, "Nature : Donnée intrinsèquement sensible (Loi 25)")
                final_justification = "; ".join(justification_parts)
            
            # Clarify for SENSITIVE/QUASI data
            if final_type == DataType.SENSITIVE:
                 final_justification = f"Sensible par nature (non directement identifiant) : {final_justification}"
            elif final_type == DataType.QUASI_IDENTIFIER:
                 final_justification = f"Quasi-identifiant (risque de ré-identification par combinaison) : {final_justification}"

        return ColumnClassification(
            column_name=column_name,
            sensitivity_type=final_type,
            category=category,
            confidence=max(confidence, 50.0),
            justification=final_justification,
            suggested_config=self._get_suggested_config(
                column_name, final_type, category, data_type, pattern_type
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
        lower_name = column_name.lower()
        
        if (sensitivity_type == DataType.SENSITIVE or 
            any(k in lower_name for k in ["expense", "coverage", "revenu", "salaire", "montant"])) and is_numeric:
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
        # Special check for column names like 'city' or 'ville'
        lower_name = column_name.lower()
        if "ville" in lower_name or "city" in lower_name or "town" in lower_name or "local" in lower_name:
             return AnonymizationConfig(
                column_name=column_name,
                technique=AnonymizationTechnique.GENERALIZATION,
                params={"mode": "prefix", "prefix_length": 3}
            )

        return AnonymizationConfig(
            column_name=column_name,
            technique=AnonymizationTechnique.GENERALIZATION,
            params={"mode": "prefix", "prefix_length": 3}
        )

    def _check_column_name(self, normalized_name: str, sample_values: List[Any]) -> tuple[DataType, Category, float] | None:
        """Match normalized column name against dictionaries."""
        
        # Check explicit non-sensitive first to avoid false positives (e.g., product_name)
        for keyword in self.COLUMN_NAME_KEYWORDS["NON_SENSITIVE"]:
            if keyword == normalized_name or f"_{keyword}" in normalized_name or f"{keyword}_" in normalized_name:
                return (DataType.NON_SENSITIVE, Category.OTHER, 90.0)

        # Check direct identifiers using the content-aware logic
        if self._is_direct_identifier_name(normalized_name, sample_values):
            return (DataType.DIRECT_IDENTIFIER, Category.PERSONAL, 85.0)

        # Check sensitive
        for keyword in self.COLUMN_NAME_KEYWORDS["SENSITIVE"]:
            # Generalize matching: check if keyword is a significant part of the column name
            if keyword in normalized_name:
                # Sub-categorization with Priority
                cat = Category.OTHER
                if any(k in normalized_name for k in ["medical", "health", "sante", "patient", "diagnosis", "disease", "clinical", "healthcare"]):
                    cat = Category.SANTE
                elif any(k in normalized_name for k in ["credit", "score", "salary", "income", "loan", "balance", "account", "payment", "debt"]):
                    cat = Category.FINANCE
                elif any(k in normalized_name for k in ["assurance", "insurance", "policy", "police", "claim", "coverage", "premium", "prime"]):
                    cat = Category.ASSURANCE
                elif any(k in normalized_name for k in ["biometric", "biometrie", "empreinte", "fingerprint", "faceid", "iris"]):
                    cat = Category.BIOMETRIQUE
                elif any(k in normalized_name for k in ["dna", "adn", "genetic", "genetique"]):
                    cat = Category.GENETIQUE
                elif any(k in normalized_name for k in ["religion", "belief", "croyance"]):
                    cat = Category.RELIGION
                elif any(k in normalized_name for k in ["political", "politique", "vote", "parti", "party"]):
                    cat = Category.POLITIQUE
                elif any(k in normalized_name for k in ["sexual", "orientation"]):
                    cat = Category.ORIENTATION_SEXUELLE
                elif any(k in normalized_name for k in ["vie_privee", "privacy", "intimacy", "sexuel", "sexual_life"]):
                    cat = Category.VIE_SEXUELLE
                elif any(k in normalized_name for k in ["race", "ancestry", "ethnic", "ethnie", "racial", "origin"]):
                    cat = Category.ETHNIC_OR_RACIAL_ORIGIN
                elif any(k in normalized_name for k in ["philosophy", "philosophie", "philosoph"]):
                    cat = Category.PHILOSOPHIE
                elif any(k in normalized_name for k in self.COLUMN_NAME_KEYWORDS["DIRECT"] + self.COLUMN_NAME_KEYWORDS["QUASI"]):
                    cat = Category.PERSONAL
                
                return (DataType.SENSITIVE, cat, 85.0)

        # Check quasi-identifiers
        for keyword in self.COLUMN_NAME_KEYWORDS["QUASI"]:
            if keyword == normalized_name or f"_{keyword}" in normalized_name or f"{keyword}_" in normalized_name:
                return (DataType.QUASI_IDENTIFIER, Category.PERSONAL, 80.0)

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

    def _check_law25_priority(self, normalized_name: str, sample_values: List[Any]) -> tuple[Category, str] | None:
        """
        Check if column belongs to Law 25 priority sensitive categories.
        
        Returns (Category, justification) if matched, else None.
        """
        # 1. Check column name (normalized)
        for cat_name, keywords in self.LAW25_PRIORITY_CATEGORIES.items():
            # Robust matching: check for exact match, underscore prefix/suffix, OR specific combined terms
            if any(
                k == normalized_name or 
                f"_{k}" in normalized_name or 
                f"{k}_" in normalized_name or
                (k in normalized_name and len(k) > 4) or # Substring match for longer keywords
                (k in ["score", "credit"] and ("score" in normalized_name and "credit" in normalized_name))
                for k in keywords
            ):
                # Map internal cat_name to Category enum
                category = self._map_law25_to_category(cat_name)
                display_name = self.LAW25_DISPLAY_NAMES.get(cat_name, cat_name)
                return (category, f"Catégorie sensible selon la Loi 25 : {display_name}")

        # 2. Check sample values for specific keywords (intimate info/beliefs)
        str_values = [str(v).lower() for v in sample_values if v is not None]
        
        # Check religious keywords
        religions = ["catholique", "protestant", "musulman", "juif", "bouddhiste", "hindou", "sikh", "athee"]
        if any(any(r in val for r in religions) for val in str_values):
            return (Category.RELIGION, "Donnée sensible (Loi 25 - convictions religieuses)")
    
        # Check sexual orientation keywords
        orientations = ["homosexuel", "heterosexuel", "bisexuel", "lesbienne", "gay", "transgenre"]
        if any(any(o in val for o in orientations) for val in str_values):
            return (Category.ORIENTATION_SEXUELLE, "Donnée sensible (Loi 25 - vie privée)")

        return None

    def _map_law25_to_category(self, cat_name: str) -> Category:
        """Map Law 25 category name to Category enum."""
        try:
            # First try direct mapping from Enum if cat_name is already a label
            return Category(cat_name)
        except ValueError:
            # Fallback mapping for internal logic
            mapping = {
                "financial": Category.FINANCE,
                "FINANCE": Category.FINANCE,
                "genetic": Category.GENETIQUE,
                "biometric": Category.BIOMETRIQUE,
                "health": Category.SANTE,
                "SANTE": Category.SANTE,
                "sexual_life": Category.VIE_SEXUELLE,
                "orientation": Category.ORIENTATION_SEXUELLE,
                "religion": Category.RELIGION,
                "philosophy": Category.PHILOSOPHIE,
                "politics": Category.POLITIQUE,
                "ethnic": Category.ETHNIC_OR_RACIAL_ORIGIN,
                "racial": Category.ETHNIC_OR_RACIAL_ORIGIN,
                "RACIALE": Category.ETHNIC_OR_RACIAL_ORIGIN,
                "ORIGINE_RACIALE": Category.ETHNIC_OR_RACIAL_ORIGIN,
                "ETHNIQUE": Category.ETHNIC_OR_RACIAL_ORIGIN,
                "insurance": Category.ASSURANCE,
                "personal": Category.PERSONAL,
                "PERSONAL": Category.PERSONAL
            }
            return mapping.get(cat_name, Category.OTHER)

    def _is_direct_identifier_name(self, normalized_name: str, sample_values: List[Any]) -> bool:
        """Check if normalized name belongs to Direct Identifiers with content verification."""
        # Simple check against the DIRECT keywords list
        for keyword in self.COLUMN_NAME_KEYWORDS["DIRECT"]:
            if keyword == normalized_name or f"_{keyword}" in normalized_name or f"{keyword}_" in normalized_name:
                # Exclude if it also contains non-sensitive contexts
                if any(x in normalized_name for x in ["product", "item", "order", "company", "entreprise", "objet", "status", "statut"]):
                    continue
                
                # Content verification for short/generic names like "first", "last", "id"
                if keyword in ["first", "last", "id"]:
                    if not sample_values:
                        return True # Default to sensitive if no samples
                    
                    # Convert samples to strings
                    str_samples = [str(s).strip() for s in sample_values if s is not None]
                    if not str_samples:
                        return True
                    
                    # If it's a numeric column named "first" or "last", it's likely not a name
                    if keyword in ["first", "last"]:
                        # Check if samples look like names
                        name_pattern = self.PATTERNS["NAME"]
                        match_count = sum(1 for s in str_samples if re.match(name_pattern, s, re.IGNORECASE))
                        # print(f"DEBUG: {normalized_name} match_count={match_count}/{len(str_samples)}")
                        # If less than 20% match names but it's purely numeric/id-like/date-like, it's NOT a name
                        if match_count / len(str_samples) < 0.2:
                             # Check if purely numeric
                             if all(re.match(r"^\d+$", s) for s in str_samples):
                                 return False
                             # Check if looks like a date
                             if all(re.match(r"^\d{4}[-/]\d{2}[-/]\d{2}$", s) for s in str_samples):
                                 return False
                    
                    if keyword == "id":
                        # ID is only direct if it's broad or looks like a UUID/Complex hash
                        # Simple integers are often not direct identifiers on their own
                        if all(re.match(r"^\d+$", s) for s in str_samples):
                            return False

                return True
        return False
