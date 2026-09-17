"""Shared sample rows for tests."""

from __future__ import annotations

import csv
from copy import deepcopy
from pathlib import Path

from utility_asset_registry.constants import EXPECTED_COLUMNS

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


def write_survey_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str] | None = None) -> Path:
    names = fieldnames if fieldnames is not None else list(EXPECTED_COLUMNS)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=names, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return path
