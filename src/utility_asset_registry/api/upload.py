"""Administrator bulk CSV upload over the network."""

from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy.orm import Session

from utility_asset_registry.api.deps import get_db, require_admin
from utility_asset_registry.api.errors import invalid_payload
from utility_asset_registry.cache import invalidate_summary_cache
from utility_asset_registry.models import User
from utility_asset_registry.persist import save_cleaned_many
from utility_asset_registry.pipeline import MissingColumnsError, process_csv

router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.post("/upload")
def upload_csv(
    file: UploadFile,
    session: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    filename = file.filename or ""
    if not filename.lower().endswith(".csv"):
        return invalid_payload({"file": "Upload a CSV file"})
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as handle:
        handle.write(file.file.read())
        temp_path = Path(handle.name)
    try:
        result = process_csv(temp_path)
    except MissingColumnsError as exc:
        return invalid_payload(
            {"file": str(exc)},
            message="CSV is missing required column(s)",
        )
    finally:
        temp_path.unlink(missing_ok=True)

    save_cleaned_many(session, result.accepted)
    session.flush()
    invalidate_summary_cache()
    return {
        "rows_read": result.rows_read,
        "accepted": len(result.accepted),
        "rejected": len(result.rejected),
        "rejects": [
            {
                "asset_id": item.original.get("asset_id", ""),
                "reason": item.reason,
            }
            for item in result.rejected
        ],
    }
