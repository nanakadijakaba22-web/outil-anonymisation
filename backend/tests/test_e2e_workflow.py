"""
End-to-End Test Suite for Annoy - Data Anonymization Tool

Tests the complete workflow from CSV upload to PDF report generation,
validating Quebec Law 25 compliance throughout the process.
"""

import os
import pytest
from pathlib import Path
from httpx import AsyncClient, ASGITransport
from sqlalchemy.orm import Session

from app.main import app
from app.core.database import get_db


class TestE2EWorkflow:
    """Test complete anonymization workflow end-to-end."""

    @pytest.fixture
    def test_csv_path(self) -> Path:
        """Path to test CSV file."""
        return Path(__file__).parent / "fixtures" / "test_data.csv"

    @pytest.mark.asyncio
    async def test_complete_workflow(self, test_csv_path: Path):
        """
        Test complete workflow:
        1. Upload CSV file
        2. Detect sensitive data
        3. Anonymize dataset
        4. Assess risk (before and after)
        5. Download anonymized CSV
        6. Generate PDF compliance report
        """
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Step 1: Upload CSV file
            print("\n=== Step 1: Upload CSV ===")
            with open(test_csv_path, "rb") as f:
                upload_response = await client.post(
                    "/api/v1/datasets/upload",
                    files={"file": ("test_data.csv", f, "text/csv")},
                )

            assert upload_response.status_code == 201
            dataset = upload_response.json()
            dataset_id = dataset["id"]

            print(f"✓ Dataset uploaded: {dataset_id}")
            print(f"  - Rows: {dataset['row_count']}")
            print(f"  - Columns: {dataset['column_count']}")

            assert dataset["row_count"] == 10
            assert dataset["column_count"] == 13
            assert dataset["is_anonymized"] is False

            # Step 2: Detect sensitive data
            print("\n=== Step 2: Detect Sensitive Data ===")
            detection_response = await client.post(
                f"/api/v1/datasets/{dataset_id}/detect"
            )

            assert detection_response.status_code == 200
            detection = detection_response.json()

            print(f"✓ Detection completed:")
            print(f"  - Direct identifiers: {detection['summary']['direct_identifier']}")
            print(f"  - Quasi-identifiers: {detection['summary']['quasi_identifier']}")
            print(f"  - Sensitive: {detection['summary']['sensitive']}")
            print(f"  - Overall risk: {detection['overall_risk_score']:.1f}%")

            # Verify expected detections
            assert detection["summary"]["direct_identifier"] >= 4  # NAS, email, phone, names
            assert detection["summary"]["quasi_identifier"] >= 2  # DOB, postal code
            assert detection["overall_risk_score"] > 20  # Should be non-compliant

            # Step 3: Assess risk before anonymization
            print("\n=== Step 3: Assess Risk (Before) ===")
            risk_before_response = await client.get(
                f"/api/v1/datasets/{dataset_id}/risk-assessment"
            )

            assert risk_before_response.status_code == 200
            risk_before = risk_before_response.json()

            print(f"✓ Risk assessment (before):")
            print(f"  - Overall score: {risk_before['overall_score']:.1f}%")
            print(f"  - Individualization: {risk_before['individualization']['score']:.1f}%")
            print(f"  - Correlation: {risk_before['correlation']['score']:.1f}%")
            print(f"  - Inference: {risk_before['inference']['score']:.1f}%")
            print(f"  - Law 25 compliant: {risk_before['is_loi25_compliant']}")

            # Should be non-compliant
            assert risk_before["is_loi25_compliant"] is False

            # Step 4: Anonymize dataset
            print("\n=== Step 4: Anonymize Dataset ===")
            anonymization_config = [
                {"column_name": "nom", "technique": "pseudonymization", "params": {"prefix": "PERSON_"}},
                {"column_name": "prenom", "technique": "pseudonymization", "params": {"prefix": "PERSON_"}},
                {"column_name": "email", "technique": "masking", "params": {"visible_chars": 2}},
                {"column_name": "telephone", "technique": "masking", "params": {"visible_chars": 2}},
                {"column_name": "nas", "technique": "suppression", "params": {}},
                {"column_name": "date_naissance", "technique": "generalization", "params": {"bins": 5}},
                {"column_name": "code_postal", "technique": "generalization", "params": {"bins": 5}},
                {"column_name": "revenu_annuel", "technique": "generalization", "params": {"bins": 5}},
                {"column_name": "solde_compte", "technique": "generalization", "params": {"bins": 5}},
            ]

            anonymization_response = await client.post(
                f"/api/v1/datasets/{dataset_id}/anonymize",
                json=anonymization_config,
            )

            assert anonymization_response.status_code == 200
            anonymization = anonymization_response.json()
            anonymized_dataset_id = anonymization["anonymized_dataset_id"]

            print(f"✓ Dataset anonymized: {anonymized_dataset_id}")
            print(f"  - Transformations: {len(anonymization['transformations'])}")

            # Verify transformations
            assert len(anonymization["transformations"]) == 9
            assert anonymized_dataset_id != dataset_id

            # Step 5: Assess risk after anonymization
            print("\n=== Step 5: Assess Risk (After) ===")
            risk_after_response = await client.get(
                f"/api/v1/datasets/{anonymized_dataset_id}/risk-assessment"
            )

            assert risk_after_response.status_code == 200
            risk_after = risk_after_response.json()

            print(f"✓ Risk assessment (after):")
            print(f"  - Overall score: {risk_after['overall_score']:.1f}%")
            print(f"  - Individualization: {risk_after['individualization']['score']:.1f}%")
            print(f"  - Correlation: {risk_after['correlation']['score']:.1f}%")
            print(f"  - Inference: {risk_after['inference']['score']:.1f}%")
            print(f"  - Law 25 compliant: {risk_after['is_loi25_compliant']}")

            # Should be compliant after anonymization
            assert risk_after["is_loi25_compliant"] is True
            assert risk_after["overall_score"] < risk_before["overall_score"]
            assert risk_after["overall_score"] < 20  # Compliance threshold

            # Step 6: Download anonymized CSV
            print("\n=== Step 6: Download Anonymized CSV ===")
            download_response = await client.get(
                f"/api/v1/datasets/{anonymized_dataset_id}/download"
            )

            assert download_response.status_code == 200
            csv_content = download_response.content

            print(f"✓ CSV downloaded: {len(csv_content)} bytes")

            # Verify CSV content
            csv_text = csv_content.decode("utf-8")
            lines = csv_text.strip().split("\n")
            assert len(lines) == 11  # Header + 10 data rows

            # Verify NAS column is removed (suppression)
            header = lines[0]
            assert "nas" not in header.lower()

            # Verify pseudonymization (PERSON_ prefix)
            assert "PERSON_" in csv_text

            # Step 7: Generate PDF compliance report
            print("\n=== Step 7: Generate PDF Compliance Report ===")
            report_response = await client.get(
                f"/api/v1/datasets/{anonymized_dataset_id}/report"
            )

            assert report_response.status_code == 200
            pdf_content = report_response.content

            print(f"✓ PDF report generated: {len(pdf_content)} bytes")

            # Verify PDF header
            assert pdf_content.startswith(b"%PDF")
            assert len(pdf_content) > 1000  # Should be substantial

            # Verify content-disposition header
            assert "attachment" in report_response.headers.get("content-disposition", "")
            assert "rapport_loi25" in report_response.headers.get("content-disposition", "")

            # Final summary
            print("\n=== Workflow Summary ===")
            print(f"✓ Original dataset: {dataset_id}")
            print(f"  - Risk score: {risk_before['overall_score']:.1f}% (NON-COMPLIANT)")
            print(f"✓ Anonymized dataset: {anonymized_dataset_id}")
            print(f"  - Risk score: {risk_after['overall_score']:.1f}% (COMPLIANT)")
            print(f"✓ Risk reduction: {risk_before['overall_score'] - risk_after['overall_score']:.1f}%")
            print(f"✓ CSV exported: {len(csv_content)} bytes")
            print(f"✓ PDF report: {len(pdf_content)} bytes")
            print("\n✅ Complete E2E workflow successful!")

    @pytest.mark.asyncio
    async def test_workflow_with_preview(self, test_csv_path: Path):
        """Test workflow including data preview."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Upload
            with open(test_csv_path, "rb") as f:
                upload_response = await client.post(
                    "/api/v1/datasets/upload",
                    files={"file": ("test_data.csv", f, "text/csv")},
                )

            dataset_id = upload_response.json()["id"]

            # Preview data
            preview_response = await client.get(
                f"/api/v1/datasets/{dataset_id}/preview",
                params={"n_rows": 5},
            )

            assert preview_response.status_code == 200
            preview = preview_response.json()

            assert preview["dataset_id"] == dataset_id
            assert len(preview["data"]) == 5
            assert preview["columns"] is not None

    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling for invalid operations."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Invalid dataset ID
            invalid_id = "00000000-0000-0000-0000-000000000000"

            response = await client.get(f"/api/v1/datasets/{invalid_id}")
            assert response.status_code == 404

            # Invalid detection request
            response = await client.post(f"/api/v1/datasets/{invalid_id}/detect")
            assert response.status_code == 404

            # Invalid anonymization request
            response = await client.post(
                f"/api/v1/datasets/{invalid_id}/anonymize",
                json=[{"column_name": "test", "technique": "masking", "params": {}}],
            )
            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_dataset_deletion(self, test_csv_path: Path):
        """Test dataset deletion."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Upload dataset
            with open(test_csv_path, "rb") as f:
                upload_response = await client.post(
                    "/api/v1/datasets/upload",
                    files={"file": ("test_data.csv", f, "text/csv")},
                )

            dataset_id = upload_response.json()["id"]

            # Delete dataset
            delete_response = await client.delete(f"/api/v1/datasets/{dataset_id}")
            assert delete_response.status_code == 204

            # Verify deletion
            get_response = await client.get(f"/api/v1/datasets/{dataset_id}")
            assert get_response.status_code == 404


if __name__ == "__main__":
    """Run E2E tests with pytest."""
    pytest.main([__file__, "-v", "-s"])
