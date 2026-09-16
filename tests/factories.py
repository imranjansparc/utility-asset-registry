"""Shared sample rows for Phase 2 tests."""

from __future__ import annotations

from copy import deepcopy

VALID_ROW: dict[str, str] = {
    "asset_id": "PL-0142",
    "name": "North feeder pole",
    "asset_type": "pole",
    "latitude": "20.2961",
    "longitude": "85.8245",
    "elevation_m": "45.2",
    "surveyed_on": "2026-09-10",
    "surveyor": "A. Patnaik",
    "status": "active",
    "condition_score": "8",
    "attribute_json": '{"height_m": 9.1}',
}


def make_row(**overrides: str) -> dict[str, str]:
    row = deepcopy(VALID_ROW)
    row.update(overrides)
    return row
