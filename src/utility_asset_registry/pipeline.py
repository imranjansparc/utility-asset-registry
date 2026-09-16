"""Turn raw survey rows into cleaned records or rejects with reasons."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

from utility_asset_registry.constants import EXPECTED_COLUMNS
from utility_asset_registry.records import CleanedRecord, RejectedRecord
from utility_asset_registry.validation import collect_row_errors, to_cleaned_record


class MissingColumnsError(ValueError):
    def __init__(self, missing: tuple[str, ...]) -> None:
        self.missing = missing
        listed = ", ".join(missing)
        super().__init__(f"CSV is missing required column(s): {listed}")


def require_columns(fieldnames: list[str] | None) -> None:
    present = {name.strip() for name in (fieldnames or []) if name}
    missing = tuple(column for column in EXPECTED_COLUMNS if column not in present)
    if missing:
        raise MissingColumnsError(missing)


def original_row(row: dict[str, str | None]) -> dict[str, str]:
    return {
        column: "" if row.get(column) is None else str(row.get(column))
        for column in EXPECTED_COLUMNS
    }


@dataclass
class PipelineResult:
    accepted: list[CleanedRecord] = field(default_factory=list)
    rejected: list[RejectedRecord] = field(default_factory=list)

    @property
    def rows_read(self) -> int:
        return len(self.accepted) + len(self.rejected)


def process_rows(rows: list[dict[str, str | None]]) -> PipelineResult:
    """Accept clean rows and set bad rows aside. One bad row never stops the run."""
    result = PipelineResult()
    seen_ids: set[str] = set()

    for row in rows:
        errors = collect_row_errors(row, seen_ids)
        if errors:
            result.rejected.append(
                RejectedRecord(original=original_row(row), reason="; ".join(errors))
            )
            asset_id = (row.get("asset_id") or "").strip()
            if asset_id:
                seen_ids.add(asset_id)
            continue

        cleaned = to_cleaned_record(row)
        seen_ids.add(cleaned.asset_id)
        result.accepted.append(cleaned)

    return result


def process_csv(path: str | Path) -> PipelineResult:
    csv_path = Path(path)
    with csv_path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        require_columns(reader.fieldnames)
        return process_rows(list(reader))


def write_rejects(path: str | Path, rejected: list[RejectedRecord]) -> None:
    """Write every refused row with its original values plus a reason column."""
    reject_path = Path(path)
    reject_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(EXPECTED_COLUMNS) + ["reason"]
    with reject_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for item in rejected:
            writer.writerow({**item.original, "reason": item.reason})
