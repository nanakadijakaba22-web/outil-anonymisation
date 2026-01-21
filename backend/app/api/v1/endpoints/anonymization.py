"""
API endpoints for dataset anonymization.
"""
from uuid import UUID
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
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
    config: Optional[List[AnonymizationConfig]] = None,
    auto: bool = Query(False, description="Mode automatique: génère la config selon les règles Loi 25"),
    db: Session = Depends(get_db)
) -> AnonymizationResponse:
    """
    Anonymize a dataset using specified techniques or automatic rules.

    - **dataset_id**: UUID of the dataset to anonymize
    - **config**: List of anonymization configurations per column (optionnel si auto=true)
    - **auto**: Mode automatique - applique les règles Loi 25 par défaut

    ## Mode Automatique (auto=true)

    Génère automatiquement la configuration selon les types de sensibilité détectés:
    - **Identifiants directs** → Suppression (colonnes supprimées)
    - **Quasi-identifiants** → Généralisation (texte→préfixe, numérique→tranches, date→année)
    - **Données sensibles** → Confidentialité différentielle (Laplace, epsilon=0.1)

    **Prérequis**: Exécuter d'abord la détection (`POST /{dataset_id}/detect`)

    ## Mode Manuel (config fournie)

    Each configuration specifies:
    - **column_name**: Name of the column to anonymize
    - **technique**: masking, generalization, suppression, or differential_privacy
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

    **Differential Privacy (Sensitive numeric):**
    ```json
    {
        "column_name": "revenu",
        "technique": "differential_privacy",
        "params": {"epsilon": 0.1, "mechanism": "laplace"}
    }
    ```

    Returns:
    - Job ID
    - Anonymized dataset ID
    - Transformation details with before/after samples
    - Processing time
    """
    anonymizer = Anonymizer(db)

    # Mode automatique: générer la config selon les règles Loi 25
    if auto:
        try:
            config = anonymizer.generate_auto_config(dataset_id)
            if not config:
                raise HTTPException(
                    status_code=400,
                    detail="Aucune colonne sensible détectée. Exécutez d'abord POST /{dataset_id}/detect"
                )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    # Vérifier qu'une config existe
    if not config:
        raise HTTPException(
            status_code=400,
            detail="Configuration requise. Fournissez 'config' ou utilisez 'auto=true'"
        )

    return await anonymizer.anonymize_dataset(dataset_id, config)


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
