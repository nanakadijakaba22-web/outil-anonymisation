"""
AI-Enhanced sensitive data detection service using Ollama LLM.

This service extends the rule-based SensitiveDataDetector with AI capabilities
to improve detection accuracy for ambiguous cases.
"""
import json
import logging
from typing import Any, List
from uuid import UUID

import ollama
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.schemas import (
    DataType,
    Category,
    ColumnClassification,
    DetectionReport,
)
from app.services.detector import SensitiveDataDetector

logger = logging.getLogger(__name__)


class AIEnhancedDetector(SensitiveDataDetector):
    """
    Enhanced detector that combines rule-based heuristics with AI inference.

    Strategy:
    1. First use rule-based detection (fast, free)
    2. For low confidence columns (< threshold), use Ollama AI for verification
    3. Combine results intelligently
    """

    SYSTEM_PROMPT = """Tu es un expert senior en protection des données personnelles et en conformité à la Loi 25 du Québec.

Ton rôle est de classifier des colonnes de données avec une précision absolue. La Loi 25 exige une protection rigoureuse.

**Catégories de sensibilité (sensitivity_type)**:
1. "direct_identifier": Information qui permet d'identifier directement et de manière unique une personne.
   - Exemples: NAS, RAMQ, Nom complet, Email, Téléphone, No Passeport, No Permis, ID Client unique, Username.
2. "quasi_identifier": Information qui, seule, ne permet pas d'identifier, mais qui combinée à d'autres peut ré-identifier.
   - Exemples: Date de naissance, Code postal, Genre, Ville, Coordonnées GPS, Ethnie, Religion, Age.
3. "sensitive": Données dont la nature exige une haute protection (financier, médical, assurance).
   - Exemples: Revenu, Solde bancaire, Diagnostic médical, No de police d'assurance, Code de carte de crédit.
4. "non_sensitive": Données d'affaires générales ou publiques.

**Instructions de classification**:
- Sois CONSERVATEUR : Si tu as un doute entre deux catégories, choisis TOUJOURS la plus sensible.
- Analyse le nom technique de la colonne ET les échantillons de valeurs.
- Ignore les valeurs nulles ou vides dans ton analyse.
- La justification doit être courte, en français, et expliquer POURQUOI cette classification a été choisie selon la Loi 25.

Réponds UNIQUEMENT avec un objet JSON valide suivant cette structure:
{
  "sensitivity_type": "direct_identifier|quasi_identifier|sensitive|non_sensitive",
  "category": "personal|financial|health|insurance|other",
  "confidence": 0-100,
  "justification": "..."
}"""

    def __init__(self, db: Session):
        super().__init__(db)
        self.ollama_available = False
        self.ai_enabled = False

        # Initialize Ollama client with custom host
        self.ollama_client = ollama.Client(host=settings.OLLAMA_BASE_URL)

        # Check if Ollama is available
        if settings.ENABLE_AI_DETECTION:
            try:
                self._check_ollama_connection()
                self.ollama_available = True
                self.ai_enabled = True
                logger.info(f"Ollama AI detection initialized successfully (model: {settings.OLLAMA_MODEL})")
            except Exception as e:
                logger.warning(f"Failed to connect to Ollama: {e}. Falling back to rule-based detection.")
                self.ai_enabled = False

    def _check_ollama_connection(self):
        """
        Verify that Ollama is running and the model is available.

        Raises:
            Exception: If Ollama is not accessible or model is not available
        """
        try:
            # Test connection by listing available models
            models = self.ollama_client.list()
            model_names = [m.model for m in models.models]

            # Check if our configured model is available
            if settings.OLLAMA_MODEL not in model_names:
                logger.warning(
                    f"Model '{settings.OLLAMA_MODEL}' not found. Available models: {model_names}"
                )
                raise Exception(f"Model '{settings.OLLAMA_MODEL}' not available in Ollama")

            logger.info(f"Ollama connection verified. Model '{settings.OLLAMA_MODEL}' is available.")
        except Exception as e:
            logger.error(f"Ollama connection check failed: {e}")
            raise

    async def analyze_dataset(self, dataset_id: UUID) -> DetectionReport:
        """
        Analyze dataset with AI-enhanced detection.

        Uses hybrid approach: rule-based + AI for ambiguous cases.
        """
        # First, run the standard rule-based detection
        report = await super().analyze_dataset(dataset_id)

        # If AI is disabled or Ollama is not available, return standard report
        if not self.ai_enabled or not self.ollama_available:
            logger.info("AI detection disabled or Ollama unavailable, using rule-based detection only")
            return report

        # Load dataset for AI enhancement
        dataset = self.ingestion_service.get_dataset(dataset_id)
        df = self.ingestion_service.load_dataframe(dataset_id)

        # Track improvements
        improved_columns = 0

        # Enhance classifications with AI
        # Si OLLAMA_ANALYZE_ALL_COLUMNS est True, analyser TOUTES les colonnes
        # Sinon, seulement les colonnes à faible confiance
        for column_name, classification_obj in report.columns.items():
            # Robustly handle both dict and object (as BaseSchema might have converted it)
            classification = classification_obj if isinstance(classification_obj, dict) else classification_obj.model_dump()
            
            should_analyze = (
                settings.OLLAMA_ANALYZE_ALL_COLUMNS or
                classification["confidence"] < settings.AI_CONFIDENCE_THRESHOLD
            )
            if should_analyze:
                logger.info(
                    f"Low confidence ({classification['confidence']}%) for '{column_name}', "
                    f"using AI enhancement"
                )

                # Get sample values for this column (increased to 20 for better AI analysis)
                col_data = df[column_name]
                sample_values = col_data.dropna().head(20).tolist()

                # Get AI classification
                ai_classification = await self._classify_with_ai(
                    column_name=column_name,
                    sample_values=sample_values,
                    data_type=classification["category"].value if hasattr(classification["category"], "value") else classification["category"],
                    rule_based_result=classification,
                )

                if ai_classification:
                    # Combine rule-based and AI results
                    combined = self._combine_classifications(
                        rule_based=classification_obj,
                        ai_based=ai_classification,
                    )

                    # Update report
                    report.columns[column_name] = combined
                    improved_columns += 1

                    # Update column in database
                    for col in dataset.columns:
                        if col.name == column_name:
                            col.sensitivity_type = combined.sensitivity_type.value if hasattr(combined.sensitivity_type, "value") else combined.sensitivity_type
                            col.category = combined.category.value if hasattr(combined.category, "value") else combined.category
                            col.confidence = combined.confidence
                            break

        # Recalculate summary and risk score
        report = self._recalculate_report(report)

        if improved_columns > 0:
            dataset.risk_score = report.overall_risk_score
            self.db.commit()
            logger.info(f"AI improved classification for {improved_columns} columns")

        return report

    async def _classify_with_ai(
        self,
        column_name: str,
        sample_values: List[Any],
        data_type: str,
        rule_based_result: ColumnClassification,
    ) -> ColumnClassification | None:
        """
        Use Ollama AI to classify a column.

        Args:
            column_name: Name of the column
            sample_values: Sample values from the column
            data_type: Data type of the column
            rule_based_result: Result from rule-based detection

        Returns:
            AI-based classification or None if failed
        """
        if not self.ollama_available:
            return None

        # Prepare user prompt
        user_prompt = f"""Analyse cette colonne de données:

**Nom de la colonne**: {column_name}
**Type de données**: {data_type}
**Échantillons de valeurs** (20 premiers):
{json.dumps(sample_values[:20], ensure_ascii=False, indent=2)}

**Classification initiale (règles heuristiques)**:
- Type: {rule_based_result["sensitivity_type"].value if hasattr(rule_based_result["sensitivity_type"], "value") else rule_based_result["sensitivity_type"]}
- Catégorie: {rule_based_result["category"].value if hasattr(rule_based_result["category"], "value") else rule_based_result["category"]}
- Confiance: {rule_based_result["confidence"]}%
- Justification: {rule_based_result["justification"]}

Fournis ta classification en JSON avec cette structure exacte:
{{
  "sensitivity_type": "direct_identifier|quasi_identifier|sensitive|non_sensitive",
  "category": "personal|financial|health|insurance|other",
  "confidence": 0-100,
  "justification": "Explication courte en français"
}}"""

        try:
            # Call Ollama API with JSON format
            response = self.ollama_client.chat(
                model=settings.OLLAMA_MODEL,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                format="json",
                options={
                    "temperature": 0.1,  # Low temperature for consistent classification
                    "num_predict": 500,
                }
            )

            # Parse JSON response
            ai_result = json.loads(response['message']['content'])

            # Validate and convert to ColumnClassification
            return ColumnClassification(
                column_name=column_name,
                sensitivity_type=DataType(ai_result["sensitivity_type"]),
                category=Category(ai_result["category"]),
                confidence=float(ai_result["confidence"]),
                justification=f"[IA] {ai_result['justification']}",
            )

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response JSON: {e}")
            return None
        except KeyError as e:
            logger.error(f"Missing key in AI response: {e}")
            return None
        except Exception as e:
            logger.error(f"AI classification failed: {e}")
            return None

    def _combine_classifications(
        self,
        rule_based: Any,
        ai_based: Any,
    ) -> ColumnClassification:
        """
        Intelligently combine rule-based and AI classifications.

        Strategy:
        - If AI confidence is very high (>85), trust AI predominantly.
        - If both agree on sensitivity type, boost confidence significantly.
        - If AI detects an identifier (DIR/QUASI/SENS) that rules missed, follow AI but with caution.
        - Use a "most sensitive wins" approach when confidence is comparable.
        """
        # Ensure we work with dicts for uniform subscriptable access
        rb = rule_based if isinstance(rule_based, dict) else rule_based.model_dump()
        ab = ai_based if isinstance(ai_based, dict) else ai_based.model_dump()

        # High AI confidence -> trust AI
        if ab["confidence"] >= 85:
            return ColumnClassification(
                column_name=rb["column_name"],
                sensitivity_type=ab["sensitivity_type"],
                category=ab["category"],
                confidence=min(ab["confidence"] + 5, 100),
                justification=f"{ab['justification']} (validé par IA haute-fiance)",
            )

        # Both agree -> boost confidence
        if (rb["sensitivity_type"] == ab["sensitivity_type"]):
             # Agree on sensitivity type, use best category
            chosen_cat = ab["category"] if ab["confidence"] >= rb["confidence"] else rb["category"]
            combined_confidence = min(max(rb["confidence"], ab["confidence"]) + 10, 100)
            
            return ColumnClassification(
                column_name=rb["column_name"],
                sensitivity_type=rb["sensitivity_type"],
                category=chosen_cat,
                confidence=combined_confidence,
                justification=f"{rb['justification']} (confirmé par IA)",
            )

        # Disagree -> Conservatism: Prefer the most sensitive detected type if confidence is decent
        sensitivity_rank = {
            DataType.DIRECT_IDENTIFIER: 4,
            DataType.SENSITIVE: 3,
            DataType.QUASI_IDENTIFIER: 2,
            DataType.NON_SENSITIVE: 1
        }

        # Convert simple types to DataType if they are strings
        rb_type = rb["sensitivity_type"] if not isinstance(rb["sensitivity_type"], str) else DataType(rb["sensitivity_type"])
        ab_type = ab["sensitivity_type"] if not isinstance(ab["sensitivity_type"], str) else DataType(ab["sensitivity_type"])

        # If AI detected something more sensitive than rules, and AI confidence is > 60%
        if sensitivity_rank.get(ab_type, 0) > sensitivity_rank.get(rb_type, 0) and ab["confidence"] > 60:
            return ColumnClassification(
                column_name=rb["column_name"],
                sensitivity_type=ab["sensitivity_type"],
                category=ab["category"],
                confidence=ab["confidence"],
                justification=f"{ab['justification']} (Détecté par IA, manqué par règles)",
            )
        
        # Default to weighted average preferring higher confidence
        if rb["confidence"] > ab["confidence"]:
            chosen = rb
            justif = f"{rb['justification']} (IA suggérait {ab_type})"
        else:
            chosen = ab
            justif = f"{ab['justification']} (Règles suggéraient {rb_type})"

        return ColumnClassification(
            column_name=rb["column_name"],
            sensitivity_type=chosen["sensitivity_type"],
            category=chosen["category"],
            confidence=max(rb["confidence"], ab["confidence"]),
            justification=justif,
        )

    def _recalculate_report(self, report: DetectionReport) -> DetectionReport:
        """Recalculate summary and risk score after AI improvements."""
        # Recalculate summary
        summary = {
            "direct_identifier": sum(1 for c in report.columns.values() if c.sensitivity_type == DataType.DIRECT_IDENTIFIER),
            "quasi_identifier": sum(1 for c in report.columns.values() if c.sensitivity_type == DataType.QUASI_IDENTIFIER),
            "sensitive": sum(1 for c in report.columns.values() if c.sensitivity_type == DataType.SENSITIVE),
            "non_sensitive": sum(1 for c in report.columns.values() if c.sensitivity_type == DataType.NON_SENSITIVE),
        }

        # Recalculate risk score
        total_columns = len(report.columns)
        if total_columns > 0:
            risk_score = (
                (summary["direct_identifier"] * 40) +
                (summary["quasi_identifier"] * 25) +
                (summary["sensitive"] * 20)
            ) / total_columns
        else:
            risk_score = 0

        return DetectionReport(
            dataset_id=report.dataset_id,
            columns=report.columns,
            overall_risk_score=min(risk_score, 100),
            summary=summary,
        )
