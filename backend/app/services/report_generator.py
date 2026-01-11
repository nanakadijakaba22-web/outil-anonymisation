"""
PDF Report Generator for Law 25 Compliance Reports
Generates professional PDF reports with risk assessment and anonymization details.
"""

from datetime import datetime, timezone
from typing import Optional
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    Image,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.barcharts import VerticalBarChart, HorizontalBarChart
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics import renderPDF

from app.models.schemas import (
    DatasetResponse,
    DetectionReport,
    RiskAssessmentResponse,
    AnonymizationResponse,
)


class PDFReportGenerator:
    """Generates professional PDF compliance reports for Quebec Law 25."""

    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        """Create custom paragraph styles for the report."""
        # Title style
        self.styles.add(
            ParagraphStyle(
                name="CustomTitle",
                parent=self.styles["Heading1"],
                fontSize=24,
                textColor=colors.HexColor("#1e3a8a"),
                spaceAfter=30,
                alignment=TA_CENTER,
                fontName="Helvetica-Bold",
            )
        )

        # Subtitle style
        self.styles.add(
            ParagraphStyle(
                name="CustomSubtitle",
                parent=self.styles["Heading2"],
                fontSize=16,
                textColor=colors.HexColor("#3b82f6"),
                spaceAfter=12,
                spaceBefore=12,
                fontName="Helvetica-Bold",
            )
        )

        # Section header
        self.styles.add(
            ParagraphStyle(
                name="SectionHeader",
                parent=self.styles["Heading3"],
                fontSize=14,
                textColor=colors.HexColor("#1f2937"),
                spaceAfter=8,
                spaceBefore=16,
                fontName="Helvetica-Bold",
            )
        )

        # Compliance status
        self.styles.add(
            ParagraphStyle(
                name="ComplianceStatus",
                parent=self.styles["Normal"],
                fontSize=14,
                textColor=colors.white,
                alignment=TA_CENTER,
                fontName="Helvetica-Bold",
            )
        )

    def generate_compliance_report(
        self,
        dataset: DatasetResponse,
        detection_report: Optional[DetectionReport],
        risk_assessment: RiskAssessmentResponse,
        anonymization_response: Optional[AnonymizationResponse] = None,
        visualization_data: Optional[dict] = None,
    ) -> BytesIO:
        """
        Generate a comprehensive PDF compliance report.

        Args:
            dataset: Dataset metadata
            detection_report: Detection results (optional)
            risk_assessment: Risk assessment results
            anonymization_response: Anonymization details (optional)
            visualization_data: Statistical visualization data (optional)

        Returns:
            BytesIO: PDF file content
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72,
        )

        # Build content
        story = []

        # Title page
        story.extend(self._build_title_page(dataset, risk_assessment))
        story.append(PageBreak())

        # Executive summary
        story.extend(self._build_executive_summary(dataset, risk_assessment))
        story.append(Spacer(1, 0.3 * inch))

        # Risk assessment section
        story.extend(self._build_risk_assessment_section(risk_assessment))
        story.append(Spacer(1, 0.3 * inch))

        # Detection results (if available)
        if detection_report:
            story.extend(self._build_detection_section(detection_report))
            story.append(Spacer(1, 0.3 * inch))

        # Anonymization details (if available)
        if anonymization_response:
            story.extend(self._build_anonymization_section(anonymization_response))
            story.append(Spacer(1, 0.3 * inch))

        # Data visualization section (if available)
        if visualization_data:
            story.append(PageBreak())
            story.extend(self._build_visualization_section(visualization_data))
            story.append(Spacer(1, 0.3 * inch))

        # Recommendations
        story.extend(self._build_recommendations_section(risk_assessment))

        # Build PDF
        doc.build(story)
        buffer.seek(0)
        return buffer

    def _build_title_page(
        self, dataset: DatasetResponse, risk_assessment: RiskAssessmentResponse
    ) -> list:
        """Build the title page."""
        elements = []

        # Title
        title = Paragraph(
            "Rapport de Conformité<br/>Loi 25 du Québec",
            self.styles["CustomTitle"],
        )
        elements.append(Spacer(1, 1.5 * inch))
        elements.append(title)
        elements.append(Spacer(1, 0.5 * inch))

        # Compliance status box
        is_compliant = risk_assessment.is_loi25_compliant
        status_text = "CONFORME" if is_compliant else "NON-CONFORME"
        status_color = colors.HexColor("#10b981") if is_compliant else colors.HexColor("#ef4444")

        status_table = Table(
            [[Paragraph(status_text, self.styles["ComplianceStatus"])]],
            colWidths=[4 * inch],
            rowHeights=[0.6 * inch],
        )
        status_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), status_color),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 12),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                    ("TOPPADDING", (0, 0), (-1, -1), 12),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                ]
            )
        )
        elements.append(status_table)
        elements.append(Spacer(1, 0.8 * inch))

        # Dataset information
        info_data = [
            ["Fichier:", dataset.filename],
            ["Date d'analyse:", datetime.now(timezone.utc).strftime("%d/%m/%Y à %H:%M")],
            ["Nombre de lignes:", str(dataset.row_count)],
            ["Nombre de colonnes:", str(dataset.column_count)],
            [
                "Score de risque:",
                f"{risk_assessment.overall_score:.1f}% ({risk_assessment.overall_level})",
            ],
        ]

        info_table = Table(info_data, colWidths=[2 * inch, 3 * inch])
        info_table.setStyle(
            TableStyle(
                [
                    ("FONT", (0, 0), (0, -1), "Helvetica-Bold", 10),
                    ("FONT", (1, 0), (1, -1), "Helvetica", 10),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        elements.append(info_table)

        return elements

    def _build_executive_summary(
        self, dataset: DatasetResponse, risk_assessment: RiskAssessmentResponse
    ) -> list:
        """Build executive summary section."""
        elements = []

        elements.append(Paragraph("Sommaire Exécutif", self.styles["CustomSubtitle"]))

        summary_text = f"""
        Ce rapport présente l'analyse de conformité du fichier <b>{dataset.filename}</b>
        selon les exigences de la Loi 25 du Québec sur la protection des renseignements
        personnels. L'évaluation a été réalisée le {datetime.now(timezone.utc).strftime("%d/%m/%Y")}.
        """

        if risk_assessment.is_loi25_compliant:
            summary_text += """<br/><br/>
            <b>Résultat:</b> Le dataset est <font color="#10b981"><b>CONFORME</b></font>
            aux exigences de la Loi 25. Le risque global de réidentification est faible
            et le dataset peut être utilisé en toute sécurité.
            """
        else:
            summary_text += """<br/><br/>
            <b>Résultat:</b> Le dataset est <font color="#ef4444"><b>NON-CONFORME</b></font>
            aux exigences de la Loi 25. Des mesures d'anonymisation sont recommandées avant
            toute utilisation ou partage des données.
            """

        elements.append(Paragraph(summary_text, self.styles["BodyText"]))

        return elements

    def _build_risk_assessment_section(self, risk_assessment: RiskAssessmentResponse) -> list:
        """Build risk assessment section."""
        elements = []

        elements.append(
            Paragraph("Évaluation des Risques", self.styles["CustomSubtitle"])
        )

        # Risk criteria table
        risk_data = [
            ["Critère", "Score", "Niveau", "Justification"],
            [
                "Individualisation",
                f"{risk_assessment.individualization.score:.1f}%",
                risk_assessment.individualization.level.upper(),
                risk_assessment.individualization.justification[:60] + "...",
            ],
            [
                "Corrélation",
                f"{risk_assessment.correlation.score:.1f}%",
                risk_assessment.correlation.level.upper(),
                risk_assessment.correlation.justification[:60] + "...",
            ],
            [
                "Inférence",
                f"{risk_assessment.inference.score:.1f}%",
                risk_assessment.inference.level.upper(),
                risk_assessment.inference.justification[:60] + "...",
            ],
            [
                "GLOBAL",
                f"{risk_assessment.overall_score:.1f}%",
                risk_assessment.overall_level.upper(),
                "Score pondéré des trois critères",
            ],
        ]

        risk_table = Table(
            risk_data, colWidths=[1.5 * inch, 0.8 * inch, 0.8 * inch, 3.4 * inch]
        )

        # Color coding based on risk level
        def get_risk_color(level: str) -> colors.Color:
            if level.lower() == "faible":
                return colors.HexColor("#d1fae5")
            elif level.lower() == "moyen":
                return colors.HexColor("#fef3c7")
            else:
                return colors.HexColor("#fee2e2")

        risk_table.setStyle(
            TableStyle(
                [
                    # Header
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a8a")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 10),
                    # Data rows
                    ("FONT", (0, 1), (-1, -2), "Helvetica", 9),
                    ("FONT", (0, -1), (-1, -1), "Helvetica-Bold", 10),
                    # Risk level colors
                    (
                        "BACKGROUND",
                        (0, 1),
                        (-1, 1),
                        get_risk_color(risk_assessment.individualization.level),
                    ),
                    (
                        "BACKGROUND",
                        (0, 2),
                        (-1, 2),
                        get_risk_color(risk_assessment.correlation.level),
                    ),
                    (
                        "BACKGROUND",
                        (0, 3),
                        (-1, 3),
                        get_risk_color(risk_assessment.inference.level),
                    ),
                    (
                        "BACKGROUND",
                        (0, 4),
                        (-1, 4),
                        get_risk_color(risk_assessment.overall_level),
                    ),
                    # General styling
                    ("ALIGN", (1, 1), (2, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("GRID", (0, 0), (-1, -1), 1, colors.grey),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )

        elements.append(risk_table)

        return elements

    def _build_detection_section(self, detection_report: DetectionReport) -> list:
        """Build sensitive data detection section."""
        elements = []

        elements.append(
            Paragraph("Détection des Données Sensibles", self.styles["CustomSubtitle"])
        )

        # Summary
        summary = detection_report.summary
        summary_text = f"""
        L'analyse a identifié <b>{summary.get('direct_identifier', 0)}</b> identifiants directs,
        <b>{summary.get('quasi_identifier', 0)}</b> quasi-identifiants, <b>{summary.get('sensitive', 0)}</b>
        données sensibles et <b>{summary.get('non_sensitive', 0)}</b> colonnes non-sensibles.
        """
        elements.append(Paragraph(summary_text, self.styles["BodyText"]))
        elements.append(Spacer(1, 0.2 * inch))

        # Top sensitive columns
        sensitive_columns = [
            (name, classification)
            for name, classification in detection_report.columns.items()
            if classification.sensitivity_type
            in ["direct_identifier", "quasi_identifier", "sensitive"]
        ]

        if sensitive_columns:
            elements.append(
                Paragraph("Colonnes Sensibles Détectées", self.styles["SectionHeader"])
            )

            column_data = [["Colonne", "Type", "Catégorie", "Confiance"]]
            for name, classification in sensitive_columns[:15]:  # Limit to 15
                column_data.append(
                    [
                        name,
                        self._format_sensitivity_type(
                            classification.sensitivity_type
                        ),
                        classification.category,
                        f"{classification.confidence:.0f}%",
                    ]
                )

            column_table = Table(
                column_data, colWidths=[2 * inch, 1.8 * inch, 1.2 * inch, 0.8 * inch]
            )
            column_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3b82f6")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9),
                        ("FONT", (0, 1), (-1, -1), "Helvetica", 8),
                        ("ALIGN", (3, 1), (3, -1), "CENTER"),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f4f6")]),
                        ("LEFTPADDING", (0, 0), (-1, -1), 6),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ]
                )
            )
            elements.append(column_table)

        return elements

    def _build_anonymization_section(
        self, anonymization_response: AnonymizationResponse
    ) -> list:
        """Build anonymization details section."""
        elements = []

        elements.append(
            Paragraph("Transformations Appliquées", self.styles["CustomSubtitle"])
        )

        transform_text = f"""
        Au total, <b>{len(anonymization_response.transformations)}</b> colonnes ont été
        anonymisées pour réduire le risque de réidentification.
        """
        elements.append(Paragraph(transform_text, self.styles["BodyText"]))
        elements.append(Spacer(1, 0.2 * inch))

        # Transformations table
        transform_data = [["Colonne", "Technique", "Valeurs affectées", "Exemple"]]

        for transform in anonymization_response.transformations[:15]:  # Limit to 15
            example = ""
            if transform.sample_transformations:
                sample = transform.sample_transformations[0]
                example = f"{sample.original[:20]} → {sample.anonymized[:20]}"

            transform_data.append(
                [
                    transform.column_name,
                    self._format_technique(transform.technique),
                    str(transform.values_affected),
                    example,
                ]
            )

        transform_table = Table(
            transform_data, colWidths=[1.5 * inch, 1.3 * inch, 1 * inch, 2.7 * inch]
        )
        transform_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3b82f6")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9),
                    ("FONT", (0, 1), (-1, -1), "Helvetica", 8),
                    ("ALIGN", (2, 1), (2, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f4f6")]),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        elements.append(transform_table)

        return elements

    def _build_recommendations_section(self, risk_assessment: RiskAssessmentResponse) -> list:
        """Build recommendations section."""
        elements = []

        elements.append(Paragraph("Recommandations", self.styles["CustomSubtitle"]))

        for i, recommendation in enumerate(risk_assessment.recommendations, 1):
            rec_text = f"<b>{i}.</b> {recommendation}"
            elements.append(Paragraph(rec_text, self.styles["BodyText"]))
            elements.append(Spacer(1, 0.1 * inch))

        # Footer note
        elements.append(Spacer(1, 0.3 * inch))
        footer_text = """
        <i>Ce rapport a été généré automatiquement par Annoy - Data Anonymization Tool.
        Pour toute question concernant la conformité à la Loi 25, veuillez consulter un
        expert juridique spécialisé en protection des données personnelles.</i>
        """
        elements.append(Paragraph(footer_text, self.styles["Italic"]))

        return elements

    def _format_sensitivity_type(self, sensitivity_type: str) -> str:
        """Format sensitivity type for display."""
        mapping = {
            "direct_identifier": "Identifiant direct",
            "quasi_identifier": "Quasi-identifiant",
            "sensitive": "Sensible",
            "non_sensitive": "Non-sensible",
        }
        return mapping.get(sensitivity_type, sensitivity_type)

    def _format_technique(self, technique: str) -> str:
        """Format anonymization technique for display."""
        mapping = {
            "masking": "Masquage",
            "generalization": "Généralisation",
            "suppression": "Suppression",
            "pseudonymization": "Pseudonymisation",
            "differential_privacy": "Confidentialité Différentielle",
        }
        return mapping.get(technique, technique)

    def _build_visualization_section(self, visualization_data: dict) -> list:
        """Build data visualization section with charts and statistics."""
        elements = []

        elements.append(
            Paragraph("Visualisation et Analyse des Données", self.styles["CustomSubtitle"])
        )

        # Overview statistics
        if "overview" in visualization_data:
            elements.extend(self._build_overview_stats(visualization_data["overview"]))
            elements.append(Spacer(1, 0.2 * inch))

        # Missing data summary
        if "missing_data" in visualization_data:
            elements.extend(self._build_missing_data_stats(visualization_data["missing_data"]))
            elements.append(Spacer(1, 0.2 * inch))

        # Numeric statistics with histograms
        if "distributions" in visualization_data:
            elements.extend(self._build_distributions_section(visualization_data["distributions"]))
            elements.append(Spacer(1, 0.2 * inch))

        # Correlation analysis
        if "correlations" in visualization_data:
            elements.extend(self._build_correlation_section(visualization_data["correlations"]))
            elements.append(Spacer(1, 0.2 * inch))

        # Outliers detection
        if "outliers" in visualization_data:
            elements.extend(self._build_outliers_section(visualization_data["outliers"]))

        return elements

    def _build_overview_stats(self, overview: dict) -> list:
        """Build overview statistics table."""
        elements = []

        elements.append(Paragraph("Aperçu des Données", self.styles["SectionHeader"]))

        overview_data = [
            ["Métrique", "Valeur"],
            ["Nombre de lignes", f"{overview.get('total_rows', 0):,}"],
            ["Nombre de colonnes", f"{overview.get('total_columns', 0)}"],
            ["Colonnes numériques", f"{overview.get('numeric_columns', 0)}"],
            ["Colonnes catégorielles", f"{overview.get('categorical_columns', 0)}"],
            ["Utilisation mémoire", f"{overview.get('memory_usage_mb', 0):.2f} MB"],
            ["Lignes dupliquées", f"{overview.get('duplicate_rows', 0):,} ({overview.get('duplicate_percentage', 0):.1f}%)"],
        ]

        overview_table = Table(overview_data, colWidths=[3 * inch, 2.5 * inch])
        overview_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3b82f6")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 10),
                ("FONT", (0, 1), (-1, -1), "Helvetica", 9),
                ("ALIGN", (1, 1), (1, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f4f6")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ])
        )

        elements.append(overview_table)
        return elements

    def _build_missing_data_stats(self, missing_data: dict) -> list:
        """Build missing data statistics."""
        elements = []

        total_missing = missing_data.get("total_missing", 0)
        missing_pct = missing_data.get("missing_percentage", 0)

        if total_missing > 0:
            elements.append(Paragraph("Données Manquantes", self.styles["SectionHeader"]))

            missing_text = f"""
            Le dataset contient <b>{total_missing:,}</b> valeurs manquantes
            (<b>{missing_pct:.2f}%</b> du total).
            """
            elements.append(Paragraph(missing_text, self.styles["BodyText"]))
            elements.append(Spacer(1, 0.1 * inch))

            # Table of columns with missing data
            columns_with_missing = missing_data.get("columns_with_missing", [])
            if columns_with_missing and len(columns_with_missing) > 0:
                missing_cols_data = [["Colonne", "Valeurs manquantes", "Pourcentage"]]

                for col in columns_with_missing[:10]:  # Top 10
                    missing_cols_data.append([
                        col["column"],
                        f"{col['missing_count']:,}",
                        f"{col['missing_percentage']:.1f}%"
                    ])

                missing_table = Table(missing_cols_data, colWidths=[2.5 * inch, 1.8 * inch, 1.2 * inch])
                missing_table.setStyle(
                    TableStyle([
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#ef4444")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9),
                        ("FONT", (0, 1), (-1, -1), "Helvetica", 8),
                        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fee2e2")]),
                        ("LEFTPADDING", (0, 0), (-1, -1), 6),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ])
                )
                elements.append(missing_table)

        return elements

    def _build_distributions_section(self, distributions: dict) -> list:
        """Build distributions section with histograms and frequency charts."""
        elements = []

        elements.append(Paragraph("Distributions des Données", self.styles["SectionHeader"]))

        # Limit to first 3 distributions for PDF space
        dist_items = list(distributions.items())[:3]

        for col_name, dist_data in dist_items:
            dist_type = dist_data.get("type", "")

            if dist_type == "numeric":
                # Create histogram
                elements.append(Spacer(1, 0.1 * inch))
                elements.append(Paragraph(f"<b>Distribution: {col_name}</b>", self.styles["BodyText"]))
                elements.append(Spacer(1, 0.05 * inch))

                chart = self._create_histogram(col_name, dist_data.get("histogram", {}))
                if chart:
                    elements.append(chart)

            elif dist_type == "categorical":
                # Create bar chart
                elements.append(Spacer(1, 0.1 * inch))
                elements.append(Paragraph(f"<b>Fréquences: {col_name}</b>", self.styles["BodyText"]))
                elements.append(Spacer(1, 0.05 * inch))

                chart = self._create_bar_chart(col_name, dist_data.get("frequencies", []))
                if chart:
                    elements.append(chart)

            elements.append(Spacer(1, 0.15 * inch))

        if len(distributions) > 3:
            note = f"<i>Note: {len(distributions) - 3} distribution(s) supplémentaire(s) non affichée(s) pour économiser de l'espace.</i>"
            elements.append(Paragraph(note, self.styles["Italic"]))

        return elements

    def _create_histogram(self, column_name: str, histogram_data: dict) -> Optional[Drawing]:
        """Create a histogram chart for numeric distribution."""
        try:
            counts = histogram_data.get("counts", [])
            bin_edges = histogram_data.get("bin_edges", [])

            if not counts or not bin_edges:
                return None

            # Create drawing
            drawing = Drawing(400, 200)
            chart = VerticalBarChart()
            chart.x = 50
            chart.y = 50
            chart.height = 125
            chart.width = 300

            # Data
            chart.data = [counts]
            chart.categoryAxis.categoryNames = [
                f"{bin_edges[i]:.1f}" if i < len(bin_edges) else ""
                for i in range(len(counts))
            ]

            # Styling
            chart.bars[0].fillColor = colors.HexColor("#3b82f6")
            chart.valueAxis.valueMin = 0
            chart.valueAxis.valueMax = max(counts) * 1.1 if counts else 10
            chart.categoryAxis.labels.boxAnchor = 'ne'
            chart.categoryAxis.labels.dx = -5
            chart.categoryAxis.labels.dy = -5
            chart.categoryAxis.labels.angle = 30
            chart.categoryAxis.labels.fontSize = 7

            drawing.add(chart)
            return drawing

        except Exception:
            return None

    def _create_bar_chart(self, column_name: str, frequencies: list) -> Optional[Drawing]:
        """Create a bar chart for categorical frequencies."""
        try:
            if not frequencies or len(frequencies) == 0:
                return None

            # Limit to top 10
            freq_data = frequencies[:10]
            labels = [item.get("label", "")[:15] for item in freq_data]  # Truncate long labels
            counts = [item.get("count", 0) for item in freq_data]

            # Create drawing
            drawing = Drawing(400, 200)
            chart = HorizontalBarChart()
            chart.x = 100
            chart.y = 20
            chart.height = 150
            chart.width = 250

            # Data
            chart.data = [counts]
            chart.categoryAxis.categoryNames = labels

            # Styling
            chart.bars[0].fillColor = colors.HexColor("#10b981")
            chart.valueAxis.valueMin = 0
            chart.valueAxis.valueMax = max(counts) * 1.1 if counts else 10
            chart.categoryAxis.labels.fontSize = 7

            drawing.add(chart)
            return drawing

        except Exception:
            return None

    def _build_correlation_section(self, correlations: dict) -> list:
        """Build correlation analysis section."""
        elements = []

        strong_corrs = correlations.get("strong_correlations", [])

        if strong_corrs and len(strong_corrs) > 0:
            elements.append(Paragraph("Corrélations Fortes Détectées", self.styles["SectionHeader"]))

            corr_text = f"""
            <b>{len(strong_corrs)}</b> corrélation(s) forte(s) (|r| > 0.7) détectée(s) entre colonnes.
            Cela peut indiquer des relations prévisibles augmentant le risque d'inférence.
            """
            elements.append(Paragraph(corr_text, self.styles["BodyText"]))
            elements.append(Spacer(1, 0.1 * inch))

            # Table of strong correlations
            corr_data = [["Colonne 1", "Colonne 2", "Corrélation", "Force"]]

            for corr in strong_corrs[:10]:  # Top 10
                corr_data.append([
                    corr.get("column1", ""),
                    corr.get("column2", ""),
                    f"{corr.get('correlation', 0):.3f}",
                    corr.get("strength", "")
                ])

            corr_table = Table(corr_data, colWidths=[1.5 * inch, 1.5 * inch, 1.2 * inch, 1.3 * inch])
            corr_table.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#8b5cf6")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9),
                    ("FONT", (0, 1), (-1, -1), "Helvetica", 8),
                    ("ALIGN", (2, 1), (2, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f4f6")]),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ])
            )
            elements.append(corr_table)
        else:
            note = "<i>Aucune corrélation forte (|r| > 0.7) détectée.</i>"
            elements.append(Paragraph(note, self.styles["Italic"]))

        return elements

    def _build_outliers_section(self, outliers: dict) -> list:
        """Build outliers detection section."""
        elements = []

        # Filter columns with outliers
        cols_with_outliers = {
            col: data for col, data in outliers.items()
            if data.get("count", 0) > 0
        }

        if cols_with_outliers:
            elements.append(Paragraph("Détection des Valeurs Aberrantes", self.styles["SectionHeader"]))

            outlier_text = f"""
            <b>{len(cols_with_outliers)}</b> colonne(s) contiennent des valeurs aberrantes
            détectées par la méthode IQR (Interquartile Range).
            """
            elements.append(Paragraph(outlier_text, self.styles["BodyText"]))
            elements.append(Spacer(1, 0.1 * inch))

            # Table of outliers
            outlier_data = [["Colonne", "Nombre", "Pourcentage", "Borne inf.", "Borne sup."]]

            for col, data in list(cols_with_outliers.items())[:10]:  # Top 10
                outlier_data.append([
                    col,
                    f"{data.get('count', 0):,}",
                    f"{data.get('percentage', 0):.1f}%",
                    f"{data.get('lower_bound', 0):.1f}",
                    f"{data.get('upper_bound', 0):.1f}"
                ])

            outlier_table = Table(outlier_data, colWidths=[1.5 * inch, 0.9 * inch, 1.1 * inch, 1.1 * inch, 1.1 * inch])
            outlier_table.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f59e0b")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9),
                    ("FONT", (0, 1), (-1, -1), "Helvetica", 8),
                    ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fef3c7")]),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ])
            )
            elements.append(outlier_table)
        else:
            note = "<i>Aucune valeur aberrante détectée par la méthode IQR.</i>"
            elements.append(Paragraph(note, self.styles["Italic"]))

        return elements
