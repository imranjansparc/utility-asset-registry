"""Network reports the web map and supervisors can read as JSON."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from utility_asset_registry.api.deps import get_current_user, get_db
from utility_asset_registry.api.schemas import asset_to_out
from utility_asset_registry.cache import get_summary
from utility_asset_registry.geo import nearest_asset
from utility_asset_registry.persist import all_cleaned, most_visited
from utility_asset_registry.reports import assets_needing_repair, surveyors_on

router = APIRouter(
    prefix="/reports",
    tags=["reports"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/summary")
def summary_report(session: Session = Depends(get_db)) -> dict:
    """Figures for the web map. Cached up to 60 seconds; dropped on any write."""
    return get_summary(session)


@router.get("/repairs")
def repair_list(session: Session = Depends(get_db)) -> dict:
    records = assets_needing_repair(all_cleaned(session))
    return {
        "items": [
            {
                "asset_id": row.asset_id,
                "name": row.name,
                "asset_type": row.asset_type,
                "condition_score": row.condition_score,
                "condition_band": row.condition_band,
                "status": row.status,
            }
            for row in records
        ]
    }


@router.get("/most-visited")
def frequently_visited(
    limit: int = Query(default=10, ge=1, le=100),
    session: Session = Depends(get_db),
) -> dict:
    rows = most_visited(session, limit=limit)
    return {
        "items": [
            {"asset": asset_to_out(asset).model_dump(mode="json"), "visit_count": count}
            for asset, count in rows
        ]
    }


@router.get("/nearest")
def nearest(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    session: Session = Depends(get_db),
) -> dict:
    found = nearest_asset(all_cleaned(session), latitude, longitude)
    if found is None:
        return {"asset": None, "distance_km": None}
    record, km = found
    return {
        "asset_id": record.asset_id,
        "name": record.name,
        "distance_km": round(km, 3),
    }


@router.get("/surveyors")
def surveyors_for_day(
    on_date: date = Query(..., alias="date"),
    session: Session = Depends(get_db),
) -> dict:
    names = surveyors_on(all_cleaned(session), on_date)
    return {"date": on_date.isoformat(), "surveyors": names}
