"""In-memory summary cache. Expires after 60 seconds and on any asset write."""

from __future__ import annotations

import threading
import time
from typing import Any

from sqlalchemy.orm import Session

from utility_asset_registry.geo import bounding_box
from utility_asset_registry.persist import all_cleaned
from utility_asset_registry.reports import type_stats

SUMMARY_CACHE_SECONDS = 60

_lock = threading.Lock()
_cached_payload: dict[str, Any] | None = None
_cached_at: float = 0.0


def invalidate_summary_cache() -> None:
    global _cached_payload, _cached_at
    with _lock:
        _cached_payload = None
        _cached_at = 0.0


def build_summary(session: Session) -> dict[str, Any]:
    records = all_cleaned(session)
    extent = bounding_box(records)
    return {
        "by_type": [
            {
                "asset_type": item.asset_type,
                "count": item.count,
                "average_condition": item.average_condition,
                "worst_asset_id": item.worst_asset_id,
                "worst_condition": item.worst_condition,
            }
            for item in type_stats(records)
        ],
        "extent": None
        if extent is None
        else {
            "south": extent.south,
            "north": extent.north,
            "west": extent.west,
            "east": extent.east,
        },
        "total": len(records),
    }


def get_summary(session: Session) -> dict[str, Any]:
    """Return cached summary figures when still fresh; otherwise recompute."""
    global _cached_payload, _cached_at
    now = time.monotonic()
    with _lock:
        if _cached_payload is not None and (now - _cached_at) < SUMMARY_CACHE_SECONDS:
            payload = dict(_cached_payload)
            payload["cached"] = True
            return payload

    fresh = build_summary(session)
    with _lock:
        _cached_payload = dict(fresh)
        _cached_at = time.monotonic()
    fresh["cached"] = False
    return fresh
