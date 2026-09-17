"""Earth-distance and GeoJSON helpers for accepted survey points."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from utility_asset_registry.records import CleanedRecord

EARTH_RADIUS_KM = 6371.0


@dataclass(frozen=True)
class BoundingBox:
    south: float
    north: float
    west: float
    east: float


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """True distance over the curved surface of the earth, in kilometres."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(min(1.0, math.sqrt(a)))


def bounding_box(records: list[CleanedRecord]) -> BoundingBox | None:
    if not records:
        return None
    lats = [row.latitude for row in records]
    lons = [row.longitude for row in records]
    return BoundingBox(south=min(lats), north=max(lats), west=min(lons), east=max(lons))


def nearest_asset(
    records: list[CleanedRecord], latitude: float, longitude: float
) -> tuple[CleanedRecord, float] | None:
    if not records:
        return None
    best = records[0]
    best_km = haversine_km(latitude, longitude, best.latitude, best.longitude)
    for row in records[1:]:
        distance = haversine_km(latitude, longitude, row.latitude, row.longitude)
        if distance < best_km:
            best = row
            best_km = distance
    return best, best_km


def _properties(record: CleanedRecord) -> dict[str, Any]:
    return {
        "asset_id": record.asset_id,
        "name": record.name,
        "asset_type": record.asset_type,
        "elevation_m": record.elevation_m,
        "surveyed_on": record.surveyed_on.isoformat(),
        "surveyor": record.surveyor,
        "status": record.status,
        "condition_score": record.condition_score,
        "condition_band": record.condition_band,
        "attributes": record.attributes,
    }


def as_geojson(records: list[CleanedRecord]) -> dict[str, Any]:
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [record.longitude, record.latitude],
                },
                "properties": _properties(record),
            }
            for record in records
        ],
    }


def write_geojson(path: str | Path, records: list[CleanedRecord]) -> None:
    map_path = Path(path)
    map_path.parent.mkdir(parents=True, exist_ok=True)
    map_path.write_text(json.dumps(as_geojson(records), indent=2), encoding="utf-8")
