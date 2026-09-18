"""Six distinct asset operations plus visit history."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from utility_asset_registry.api.deps import get_db
from utility_asset_registry.api.errors import created, deleted, fields_from_reasons, invalid_payload, not_found
from utility_asset_registry.api.schemas import (
    AssetIn,
    AssetOut,
    AssetPage,
    AssetPatch,
    VisitOut,
    asset_as_row,
    asset_to_out,
    payload_to_row,
    visit_to_out,
)
from utility_asset_registry.persist import (
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    clamp_page,
    delete_asset,
    get_by_code,
    list_assets,
    save_cleaned,
)
from utility_asset_registry.validation import collect_row_errors, to_cleaned_record

router = APIRouter(prefix="/assets", tags=["assets"])


def _validate_row(row: dict[str, str]) -> list[str]:
    return collect_row_errors(row, set())


@router.get("", response_model=AssetPage)
def list_stored_assets(
    asset_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    surveyor: str | None = Query(default=None),
    condition_min: int | None = Query(default=None, ge=0, le=10),
    condition_max: int | None = Query(default=None, ge=0, le=10),
    q: str | None = Query(default=None, description="Case-insensitive word in the description"),
    limit: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_db),
) -> AssetPage:
    size, start = clamp_page(limit, offset)
    rows, total = list_assets(
        session,
        asset_type=asset_type,
        status=status,
        surveyor=surveyor,
        condition_min=condition_min,
        condition_max=condition_max,
        q=q,
        limit=size,
        offset=start,
    )
    return AssetPage(
        items=[asset_to_out(row) for row in rows],
        total=total,
        limit=size,
        offset=start,
    )


@router.get("/{asset_id}", response_model=AssetOut)
def get_asset(asset_id: str, session: Session = Depends(get_db)) -> AssetOut | object:
    asset = get_by_code(session, asset_id)
    if asset is None:
        return not_found(asset_id)
    return asset_to_out(asset)


@router.post("", response_model=None, status_code=201)
def add_asset(payload: AssetIn, session: Session = Depends(get_db)):
    row = payload_to_row(payload.model_dump())
    reasons = _validate_row(row)
    if reasons:
        return invalid_payload(fields_from_reasons(reasons))
    if get_by_code(session, payload.asset_id.strip()) is not None:
        return JSONResponse(
            status_code=409,
            content={
                "outcome": "invalid",
                "message": "An asset with this code already exists; stored data was not changed",
                "fields": {"asset_id": f"asset_id '{payload.asset_id}' is already in use"},
            },
        )
    asset = save_cleaned(session, to_cleaned_record(row))
    session.flush()
    return created({"asset": asset_to_out(asset).model_dump(mode="json")})


@router.put("/{asset_id}")
def replace_asset(asset_id: str, payload: AssetIn, session: Session = Depends(get_db)):
    asset = get_by_code(session, asset_id)
    if asset is None:
        return not_found(asset_id)
    if payload.asset_id.strip() != asset_id:
        return invalid_payload(
            {"asset_id": "Path code and body asset_id must match for a full replace"}
        )
    row = payload_to_row(payload.model_dump())
    reasons = _validate_row(row)
    if reasons:
        return invalid_payload(fields_from_reasons(reasons))
    updated = save_cleaned(session, to_cleaned_record(row))
    session.flush()
    return {"outcome": "replaced", "asset": asset_to_out(updated).model_dump(mode="json")}


@router.patch("/{asset_id}")
def patch_asset(asset_id: str, payload: AssetPatch, session: Session = Depends(get_db)):
    asset = get_by_code(session, asset_id)
    if asset is None:
        return not_found(asset_id)
    merged = asset_as_row(asset)
    updates = {key: value for key, value in payload.model_dump(exclude_unset=True).items()}
    if not updates:
        return invalid_payload({"body": "No fields were supplied to correct"})
    merged.update(payload_to_row({**merged, **updates}))
    merged["asset_id"] = asset_id
    reasons = _validate_row(merged)
    if reasons:
        return invalid_payload(fields_from_reasons(reasons))
    survey_fields = {"surveyed_on", "surveyor", "condition_score"}
    updated = save_cleaned(
        session,
        to_cleaned_record(merged),
        add_visit=bool(survey_fields & set(updates)),
    )
    session.flush()
    return {"outcome": "corrected", "asset": asset_to_out(updated).model_dump(mode="json")}


@router.delete("/{asset_id}")
def remove_asset(asset_id: str, session: Session = Depends(get_db)):
    asset = get_by_code(session, asset_id)
    if asset is None:
        return not_found(asset_id)
    delete_asset(session, asset)
    session.flush()
    return deleted(asset_id)


@router.get("/{asset_id}/visits", response_model=list[VisitOut])
def list_visits(asset_id: str, session: Session = Depends(get_db)):
    asset = get_by_code(session, asset_id)
    if asset is None:
        return not_found(asset_id)
    return [visit_to_out(visit) for visit in asset.visits]
