"""Survey analysis and the printable supervisor summary."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from utility_asset_registry.constants import ASSET_TYPES
from utility_asset_registry.geo import BoundingBox, bounding_box
from utility_asset_registry.records import CleanedRecord


@dataclass(frozen=True)
class TypeStats:
    asset_type: str
    count: int
    average_condition: float | None
    worst_asset_id: str | None
    worst_condition: int | None


def type_stats(records: list[CleanedRecord]) -> list[TypeStats]:
    grouped: dict[str, list[CleanedRecord]] = {name: [] for name in sorted(ASSET_TYPES)}
    for record in records:
        grouped.setdefault(record.asset_type, []).append(record)

    stats: list[TypeStats] = []
    for asset_type in sorted(grouped):
        group = grouped[asset_type]
        if not group:
            stats.append(
                TypeStats(asset_type, 0, None, None, None)
            )
            continue
        worst = min(group, key=lambda row: (row.condition_score, row.asset_id))
        average = sum(row.condition_score for row in group) / len(group)
        stats.append(
            TypeStats(
                asset_type=asset_type,
                count=len(group),
                average_condition=average,
                worst_asset_id=worst.asset_id,
                worst_condition=worst.condition_score,
            )
        )
    return stats


def assets_needing_repair(records: list[CleanedRecord]) -> list[CleanedRecord]:
    """Still in service (active) with a condition rating below 5."""
    return [
        record
        for record in records
        if record.status == "active" and record.condition_score < 5
    ]


def surveyors_on(records: list[CleanedRecord], day: date) -> list[str]:
    """Distinct standardised surveyor names who worked on a given day."""
    seen: dict[str, str] = {}
    for record in records:
        if record.surveyed_on == day and record.surveyor_key not in seen:
            seen[record.surveyor_key] = record.surveyor
    return [seen[key] for key in sorted(seen)]


def format_summary(
    *,
    records: list[CleanedRecord],
    rows_read: int,
    rows_rejected: int,
    run_at: datetime,
    extent: BoundingBox | None,
) -> str:
    lines = [
        "Utility Asset Registry — survey ingest",
        f"Run at: {run_at.isoformat(sep=' ', timespec='seconds')}",
        "",
        f"{'Type':<14}{'Count':>8}{'Avg condition':>16}{'Worst asset':>22}",
    ]
    for item in type_stats(records):
        if item.count == 0:
            average = "—"
            worst = "—"
        else:
            average = f"{item.average_condition:.1f}"
            worst = f"{item.worst_asset_id} ({item.worst_condition})"
        lines.append(
            f"{item.asset_type:<14}{item.count:>8}{average:>16}{worst:>22}"
        )
    lines.append("")
    if extent is None:
        lines.append("Survey extent: no accepted assets")
    else:
        lines.append("Survey extent (bounding box the web map should open on):")
        lines.append(
            f"  south={extent.south:.6f}  north={extent.north:.6f}  "
            f"west={extent.west:.6f}  east={extent.east:.6f}"
        )
    lines.append("")
    lines.append(
        f"Totals: {rows_read} read, {len(records)} accepted, {rows_rejected} rejected"
    )
    lines.append("")
    return "\n".join(lines)


def write_summary(
    path: str | Path,
    *,
    records: list[CleanedRecord],
    rows_read: int,
    rows_rejected: int,
    run_at: datetime,
) -> None:
    summary_path = Path(path)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    text = format_summary(
        records=records,
        rows_read=rows_read,
        rows_rejected=rows_rejected,
        run_at=run_at,
        extent=bounding_box(records),
    )
    summary_path.write_text(text, encoding="utf-8")
