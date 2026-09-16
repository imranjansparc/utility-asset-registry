"""In-memory shapes for a cleaned survey row and a rejected original row."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any


@dataclass(frozen=True)
class CleanedRecord:
    asset_id: str
    name: str
    asset_type: str
    latitude: float
    longitude: float
    elevation_m: float | None
    surveyed_on: date
    surveyor: str
    surveyor_key: str
    status: str
    condition_score: int
    condition_band: str
    attributes: Any
    original: dict[str, str] = field(compare=False)


@dataclass(frozen=True)
class RejectedRecord:
    original: dict[str, str]
    reason: str
