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


class SensitiveDataDetector:
    """
    Detects and classifies sensitive data in datasets.

    Classification follows Quebec Law 25 categories:
    - Direct identifiers: Unique identifiers (NAS, email, etc.)
    - Quasi-identifiers: Can re-identify when combined (DOB, postal code)
    - Sensitive: Financial, health, insurance data
    - Non-sensitive: General information
    """

    # Regex patterns for direct identifiers
    PATTERNS = {
        # Canadian Social Insurance Number (NAS/SIN): 123-456-789 or 123456789
        "NAS": r"^\d{3}[-\s]?\d{3}[-\s]?\d{3}$",

        # Email addresses
        "EMAIL": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",

        # Canadian phone numbers: (514) 555-1234, 514-555-1234, 514.555.1234
        "TELEPHONE_CA": r"^(\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}$",

        # Canadian postal code: H3B 1A1, H3B1A1
        "CODE_POSTAL_CA": r"^[A-Z]\d[A-Z][\s]?\d[A-Z]\d$",

        # Credit cards: Visa, Mastercard, Amex, Discover (with/without spaces/dashes)
        "CREDIT_CARD": r"^(?:\d{4}[-\s]?){3}\d{4}$|^\d{4}[-\s]?\d{6}[-\s]?\d{5}$",

        # Account numbers: 8-16 digits, but we verify with Luhn and keyword context
        "ACCOUNT_NUMBER": r"^\d{8,16}$",

        # Simplified date formats for initial regex, but will use pandas for validation
        "DATE": r"^\d{4}[-/]\d{2}[-/]\d{2}$|^\d{2}[-/]\d{2}[-/]\d{4}$|^\d{1,2}/\d{1,2}/\d{2,4}$",

        # Age format: 1-120 (basic numeric check for age)
        "AGE": r"^(?:[1-9][0-9]?|1[01][0-9]|120)$",
    }

    # Column name keywords for classification
    COLUMN_NAME_KEYWORDS = {
        # Direct identifiers
        "DIRECT": [
            "nom", "name", "surname", "lastname", "family_name",
            "prenom", "firstname", "given_name",
            "email", "courriel", "e-mail",
            "nas", "sin", "social_insurance",
            "telephone", "phone", "tel", "mobile", "cellulaire",
            "carte", "card", "credit_card", "carte_credit",
            "numero_compte", "account_number", "no_compte", "num_compte",
        ],

        # Quasi-identifiers
        "QUASI": [
            "date_naissance", "birthdate", "dob", "birth_date", "naissance",
            "age", "age_", "âge",
            "postal", "zip", "code_postal", "zip_code",
            "genre", "gender", "sexe", "sex",
            "adresse", "address", "rue", "street",
            "ville", "city", "province", "state", "lieu", "localisation", "location",
            "type_compte", "account_type", "type_account", "compte",
        ],

        # Financial data (sensitive) - AMOUNTS ONLY, not account identifiers
        "FINANCIAL": [
            "revenu", "income", "salary", "salaire", "wage",
            "solde", "balance", "montant", "amount",
            "prix", "price", "cout", "cost",
            "transaction", "paiement", "payment",
        ],

        # Health data (sensitive)
        "HEALTH": [
            "medical", "medicale", "sante", "health",
            "diagnostic", "diagnosis", "maladie", "disease",
            "traitement", "treatment", "medicament", "medication",
        ],

        # Insurance data (sensitive)
        "INSURANCE": [
            "assurance", "insurance", "police", "policy",
            "prime", "premium", "couverture", "coverage",
        ],

        # Categorical/Non-sensitive (type, status, category fields)
        "CATEGORICAL": [
            "type",
            "statut", "status", "etat", "state",
            "categorie", "category", "classe", "class",
            "niveau", "level", "grade",
        ],
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
            column.sensitivity_type = classification.sensitivity_type.value
            column.category = classification.category.value
            column.confidence = classification.confidence

        # Calculate summary statistics
        summary = {
            "direct_identifier": sum(
                1 for c in classifications.values()
                if c.sensitivity_type == DataType.DIRECT_IDENTIFIER
            ),
            "quasi_identifier": sum(
                1 for c in classifications.values()
                if c.sensitivity_type == DataType.QUASI_IDENTIFIER
            ),
            "sensitive": sum(
                1 for c in classifications.values()
                if c.sensitivity_type == DataType.SENSITIVE
            ),
            "non_sensitive": sum(
                1 for c in classifications.values()
                if c.sensitivity_type == DataType.NON_SENSITIVE
            ),
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
        Detect the sensitivity type of a single column.

        Args:
            column_name: Name of the column
            sample_values: Sample values from the column
            unique_ratio: Ratio of unique values to total rows
            data_type: Pandas data type

        Returns:
            ColumnClassification with sensitivity type and confidence
        """
        col_name_lower = column_name.lower()

        # Track confidence scores for each detection method
        scores = {
            DataType.DIRECT_IDENTIFIER: 0,
            DataType.QUASI_IDENTIFIER: 0,
            DataType.SENSITIVE: 0,
            DataType.NON_SENSITIVE: 50,  # Default baseline
        }

        category = Category.OTHER
        justification_parts = []

        # 1. Check column name heuristics
        name_check = self._check_column_name(col_name_lower)
        if name_check:
            sensitivity, cat, score = name_check
            scores[sensitivity] += score
            category = cat
            justification_parts.append(f"Nom de colonne suggère {cat.value}")

            # If detected by name, reduce NON_SENSITIVE baseline to avoid false negatives
            scores[DataType.NON_SENSITIVE] = 0

        # 2. Check pattern matching on values
        pattern_check = self._check_patterns(sample_values)
        if pattern_check:
            pattern_type, score = pattern_check
            if pattern_type == "NAS":
                scores[DataType.DIRECT_IDENTIFIER] += score
                category = Category.PERSONAL
                justification_parts.append("Format NAS détecté")
            elif pattern_type == "EMAIL":
                scores[DataType.DIRECT_IDENTIFIER] += score
                category = Category.PERSONAL
                justification_parts.append("Format email détecté")
            elif pattern_type == "TELEPHONE_CA":
                scores[DataType.DIRECT_IDENTIFIER] += score
                category = Category.PERSONAL
                justification_parts.append("Format téléphone détecté")
            elif pattern_type == "CREDIT_CARD":
                scores[DataType.DIRECT_IDENTIFIER] += score
                category = Category.FINANCIAL
                justification_parts.append("Format carte de crédit détecté")
            elif pattern_type == "ACCOUNT_NUMBER":
                # For account numbers, we only increase score if keywords match OR it passes Luhn
                keyword_match = any(kw in col_name_lower for kw in ["compte", "account", "iban", "rib"])
                luhn_valid = all(self._is_luhn_valid(str(v)) for v in sample_values[:5])
                if keyword_match or luhn_valid:
                    scores[DataType.DIRECT_IDENTIFIER] += score
                    category = Category.FINANCIAL
                    justification_parts.append("Format numéro de compte validé (heuristique/Luhn)")
            elif pattern_type == "CODE_POSTAL_CA":
                scores[DataType.QUASI_IDENTIFIER] += score
                category = Category.PERSONAL
                justification_parts.append("Format code postal détecté")
            elif pattern_type == "DATE":
                # Validate with pandas
                valid_dates = pd.to_datetime(sample_values, errors='coerce').notna().sum()
                if valid_dates / len(sample_values) > 0.5:
                    scores[DataType.QUASI_IDENTIFIER] += score
                    justification_parts.append("Format date validé par parsing")
            elif pattern_type == "AGE":
                # Age pattern is weak, so we only add score if column name also suggests age
                if any(kw in col_name_lower for kw in ["age", "naissance", "birth"]):
                    scores[DataType.QUASI_IDENTIFIER] += score
                    justification_parts.append("Format âge détecté")

        # 3. Statistical analysis - uniqueness
        if unique_ratio > 0.95:
            # Highly unique -> likely identifier
            scores[DataType.DIRECT_IDENTIFIER] += 20
            justification_parts.append(f"Haute unicité ({unique_ratio:.1%})")
        elif unique_ratio > 0.7:
            scores[DataType.QUASI_IDENTIFIER] += 15
        elif unique_ratio < 0.1:
            # Low uniqueness -> might be categorical
            # BUT: don't override if already detected by column name
            if not name_check:
                scores[DataType.NON_SENSITIVE] += 10
                justification_parts.append(f"Faible unicité ({unique_ratio:.1%})")

        # 4. Data type heuristics
        if "int64" in data_type or "float64" in data_type:
            # Numeric data - could be financial
            if any(kw in col_name_lower for kw in ["revenu", "income", "salary", "solde", "balance"]):
                scores[DataType.SENSITIVE] += 30
                category = Category.FINANCIAL

        # Determine final classification
        max_score = max(scores.values())
        if max_score < 60:
            # Not enough confidence, default to non-sensitive
            final_type = DataType.NON_SENSITIVE
            confidence = 50
        else:
            final_type = max(scores, key=scores.get)
            confidence = min(max_score, 100)

        # Build justification
        if not justification_parts:
            justification_parts.append("Classification basée sur analyse heuristique")

        # Calculate risk score based on sensitivity type
        # Using same weights as overall risk calculation
        risk_score_map = {
            DataType.DIRECT_IDENTIFIER: 40.0,
            DataType.QUASI_IDENTIFIER: 25.0,
            DataType.SENSITIVE: 20.0,
            DataType.NON_SENSITIVE: 0.0,
        }
        risk_score = risk_score_map.get(final_type, 0.0)

        return ColumnClassification(
            column_name=column_name,
            sensitivity_type=final_type,
            category=category,
            confidence=confidence,
            risk_score=risk_score,
            justification="; ".join(justification_parts),
        )

    def _check_column_name(self, col_name_lower: str) -> tuple[DataType, Category, float] | None:
        """Check if column name matches known patterns."""

        # Check direct identifiers (MOST SPECIFIC)
        for keyword in self.COLUMN_NAME_KEYWORDS["DIRECT"]:
            if keyword in col_name_lower:
                # Determine category based on keyword
                if keyword in ["carte", "card", "credit_card", "carte_credit",
                              "numero_compte", "account_number", "no_compte", "num_compte"]:
                    return (DataType.DIRECT_IDENTIFIER, Category.FINANCIAL, 60)
                else:
                    return (DataType.DIRECT_IDENTIFIER, Category.PERSONAL, 60)

        # Check quasi-identifiers
        for keyword in self.COLUMN_NAME_KEYWORDS["QUASI"]:
            if keyword in col_name_lower:
                return (DataType.QUASI_IDENTIFIER, Category.PERSONAL, 65)

        # Check financial
        for keyword in self.COLUMN_NAME_KEYWORDS["FINANCIAL"]:
            if keyword in col_name_lower:
                return (DataType.SENSITIVE, Category.FINANCIAL, 50)

        # Check health
        for keyword in self.COLUMN_NAME_KEYWORDS["HEALTH"]:
            if keyword in col_name_lower:
                return (DataType.SENSITIVE, Category.HEALTH, 50)

        # Check insurance
        for keyword in self.COLUMN_NAME_KEYWORDS["INSURANCE"]:
            if keyword in col_name_lower:
                return (DataType.SENSITIVE, Category.INSURANCE, 50)

        # Check categorical/non-sensitive (LEAST SPECIFIC - check last)
        for keyword in self.COLUMN_NAME_KEYWORDS["CATEGORICAL"]:
            if keyword in col_name_lower:
                return (DataType.NON_SENSITIVE, Category.OTHER, 70)

        return None

    def _is_luhn_valid(self, n: str) -> bool:
        """Check if a string of digits passes the Luhn algorithm."""
        digits = [int(d) for d in re.sub(r"\D", "", n)]
        if not digits:
            return False
        odd_digits = digits[-1::-2]
        even_digits = digits[-2::-2]
        total = sum(odd_digits)
        for d in even_digits:
            total += sum(divmod(2 * d, 10))
        return total % 10 == 0

    def _check_patterns(self, sample_values: List[Any]) -> tuple[str, float] | None:
        """
        Check if sample values match known patterns.

        Returns:
            Tuple of (pattern_type, confidence_score) or None
        """
        if not sample_values:
            return None

        # Convert to strings and filter out None values
        str_values = [str(v) for v in sample_values if v is not None]
        if not str_values:
            return None

        # Test each pattern
        for pattern_name, pattern_regex in self.PATTERNS.items():
            matches = 0
            total = len(str_values)

            for value in str_values[:min(20, total)]:  # Check first 20 values
                if re.match(pattern_regex, str(value).strip(), re.IGNORECASE):
                    matches += 1

            # If >70% match, consider it detected
            match_ratio = matches / min(20, total)
            if match_ratio > 0.7:
                confidence = min(match_ratio * 100, 100)
                return (pattern_name, confidence)

        return None
