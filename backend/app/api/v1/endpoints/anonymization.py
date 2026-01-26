"""
API endpoints for dataset anonymization.
"""
from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.schemas import AnonymizationConfig, AnonymizationResponse
from app.services.anonymizer import Anonymizer
from app.services.data_ingestion import DataIngestionService

router = APIRouter()


@router.post("/{dataset_id}/anonymize", response_model=AnonymizationResponse)
async def anonymize_dataset(
    dataset_id: UUID,
    config: List[AnonymizationConfig],
    db: Session = Depends(get_db)
) -> AnonymizationResponse:
    """
    Anonymize a dataset using specified techniques.

    - **dataset_id**: UUID of the dataset to anonymize
    - **config**: List of anonymization configurations per column

    Each configuration specifies:
    - **column_name**: Name of the column to anonymize
    - **technique**: masking, generalization, suppression, or pseudonymization
    - **params**: Technique-specific parameters

    ## Examples:

    **Masking (Email/Phone):**
    ```json
    {
        "column_name": "email",
        "technique": "masking",
        "params": {"visible_chars": 2, "mask_char": "*"}
    }
    ```

    **Generalization (Age ranges):**
    ```json
    {
        "column_name": "age",
        "technique": "generalization",
        "params": {"method": "range", "range_size": 10}
    }
    ```

    **Suppression (Remove NAS):**
    ```json
    {
        "column_name": "nas",
        "technique": "suppression",
        "params": {}
    }
    ```

    **Pseudonymization (Names):**
    ```json
    {
        "column_name": "nom",
        "technique": "pseudonymization",
        "params": {"prefix": "PERSON_", "seed": 42}
    }
    ```

    Returns:
    - Job ID
    - Anonymized dataset ID
    - Transformation details with before/after samples
    - Processing time
    """
    anonymizer = Anonymizer(db)
    return await anonymizer.anonymize_dataset(dataset_id, config)


@router.post("/{dataset_id}/auto-anonymize", response_model=AnonymizationResponse)
async def auto_anonymize_dataset(
    dataset_id: UUID,
    db: Session = Depends(get_db)
) -> AnonymizationResponse:
    """
    Anonymisation automatique complète selon les règles de la Loi 25.

    Cette endpoint analyse automatiquement le dataset, détecte les données sensibles,
    et applique les techniques d'anonymisation appropriées sans configuration manuelle.

    ## Règles d'application automatique:

    **Identifiants directs:**
    - NAS, numéros de carte de crédit: **Suppression** (colonne retirée)
    - Email, téléphone, nom: **Masquage** (visible_chars=2)

    **Données sensibles numériques:**
    - Revenu, solde, montants: **Confidentialité différentielle** (ε=0.1, mécanisme Laplace)
    - Données sensibles textuelles: **Généralisation** (préfixe de 3 caractères)

    **Quasi-identifiants:**
    - Dates (naissance, etc.): **Généralisation** (extraction année uniquement)
    - Numériques (âge, code postal partiel): **Généralisation** (5 tranches/bins)
    - Texte (ville, adresse): **Généralisation** (préfixe de 3 caractères)

    ## Paramètres:
    - **dataset_id**: UUID du dataset à anonymiser

    ## Retourne:
    - Job ID de l'opération
    - ID du dataset anonymisé
    - Détails des transformations appliquées
    - Temps de traitement

    ## Exemple d'utilisation:
    ```
    POST /api/v1/anonymization/{dataset_id}/auto-anonymize
    ```

    Aucun corps de requête requis - la détection et configuration sont automatiques.
    """
    try:
        anonymizer = Anonymizer(db)
        return await anonymizer.auto_anonymize(dataset_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'anonymisation automatique: {str(e)}")


@router.get("/{dataset_id}/download")
async def download_dataset(
    dataset_id: UUID,
    db: Session = Depends(get_db)
) -> FileResponse:
    """
    Download a dataset as CSV file.

    - **dataset_id**: UUID of the dataset to download

    Works for both original and anonymized datasets.
    Returns the CSV file for download.
    """
    service = DataIngestionService(db)
    dataset = service.get_dataset(dataset_id)

    return FileResponse(
        path=dataset.file_path,
        media_type="text/csv",
        filename=dataset.filename,
    )
