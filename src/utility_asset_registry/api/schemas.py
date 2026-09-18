"""Request and response bodies for asset operations."""

from __future__ import annotations

import json
from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict

from utility_asset_registry.constants import EXPECTED_COLUMNS
from utility_asset_registry.models import Asset, Visit


class AssetIn(BaseModel):
    asset_id: str
    name: str
    asset_type: str
    latitude: str | float
    longitude: str | float
    elevation_m: str | float | None = None
    surveyed_on: str
    surveyor: str = ""
    status: str
    condition_score: str | int
    attribute_json: str | dict[str, Any] | list[Any] = "{}"


class AssetPatch(BaseModel):
    name: str | None = None
    asset_type: str | None = None
    latitude: str | float | None = None
    longitude: str | float | None = None
    elevation_m: str | float | None = None
    surveyed_on: str | None = None
    surveyor: str | None = None
    status: str | None = None
    condition_score: str | int | None = None
    attribute_json: str | dict[str, Any] | list[Any] | None = None


class VisitOut(BaseModel):
    visited_on: date
    surveyor: str
    condition_score: int
    notes: str | None = None


class AssetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    asset_id: str
    name: str
    asset_type: str
    latitude: float
    longitude: float
    elevation_m: float | None
    surveyed_on: date
    surveyor: str
    status: str
    condition_score: int
    condition_band: str
    attributes: Any
    visit_count: int = 0


class AssetPage(BaseModel):
    items: list[AssetOut]
    total: int
    limit: int
    offset: int


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value)
    return str(value)


def payload_to_row(data: dict[str, Any]) -> dict[str, str]:
    return {column: _stringify(data.get(column)) for column in EXPECTED_COLUMNS}


def asset_to_out(asset: Asset) -> AssetOut:
    return AssetOut(
        asset_id=asset.asset_id,
        name=asset.name,
        asset_type=asset.asset_type,
        latitude=asset.latitude,
        longitude=asset.longitude,
        elevation_m=asset.elevation_m,
        surveyed_on=asset.surveyed_on,
        surveyor=asset.surveyor,
        status=asset.status,
        condition_score=asset.condition_score,
        condition_band=asset.condition_band,
        attributes=asset.attributes,
        visit_count=len(asset.visits) if asset.visits is not None else 0,
    )


def visit_to_out(visit: Visit) -> VisitOut:
    return VisitOut(
        visited_on=visit.visited_on,
        surveyor=visit.surveyor,
        condition_score=visit.condition_score,
        notes=visit.notes,
    )


def asset_as_row(asset: Asset) -> dict[str, str]:
    attributes = asset.attributes if asset.attributes is not None else {}
    return {
        "asset_id": asset.asset_id,
        "name": asset.name,
        "asset_type": asset.asset_type,
        "latitude": str(asset.latitude),
        "longitude": str(asset.longitude),
        "elevation_m": "" if asset.elevation_m is None else str(asset.elevation_m),
        "surveyed_on": asset.surveyed_on.isoformat(),
        "surveyor": asset.surveyor,
        "status": asset.status,
        "condition_score": str(asset.condition_score),
        "attribute_json": json.dumps(attributes),
    }
