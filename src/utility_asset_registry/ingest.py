"""Run one ingest: clean the CSV, write rejects/map/summary, append the log."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from utility_asset_registry.geo import write_geojson
from utility_asset_registry.pipeline import (
    MissingColumnsError,
    PipelineResult,
    process_csv,
    write_rejects,
)
from utility_asset_registry.reports import write_summary


@dataclass(frozen=True)
class IngestPaths:
    rejects: Path
    map_file: Path
    summary: Path
    log_file: Path


@dataclass
class IngestOutcome:
    result: PipelineResult
    paths: IngestPaths
    aborted_strict: bool = False
    missing_columns: tuple[str, ...] = ()


def resolve_paths(
    csv_path: Path,
    *,
    rejects: Path | None = None,
    map_file: Path | None = None,
    summary: Path | None = None,
    log_file: Path | None = None,
    output_dir: Path | None = None,
) -> IngestPaths:
    out = output_dir if output_dir is not None else Path("outputs")
    return IngestPaths(
        rejects=rejects if rejects is not None else out / "rejects.csv",
        map_file=map_file if map_file is not None else out / "assets.geojson",
        summary=summary if summary is not None else out / "summary.txt",
        log_file=log_file if log_file is not None else out / "ingest.log",
    )


def append_ingest_log(
    path: Path,
    *,
    csv_path: Path,
    rows_read: int,
    accepted: int,
    rejected: int,
    rejects_path: Path,
    status: str,
    run_at: datetime,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = (
        f"{run_at.isoformat(timespec='seconds')}  "
        f"csv={csv_path}  status={status}  "
        f"read={rows_read}  accepted={accepted}  rejected={rejected}  "
        f"rejects={rejects_path}\n"
    )
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line)


def run_ingest(
    csv_path: Path,
    paths: IngestPaths,
    *,
    strict: bool = False,
    run_at: datetime | None = None,
) -> IngestOutcome:
    stamp = run_at or datetime.now(timezone.utc)
    try:
        result = process_csv(csv_path)
    except MissingColumnsError as exc:
        append_ingest_log(
            paths.log_file,
            csv_path=csv_path,
            rows_read=0,
            accepted=0,
            rejected=0,
            rejects_path=paths.rejects,
            status=f"missing_columns:{','.join(exc.missing)}",
            run_at=stamp,
        )
        outcome = IngestOutcome(
            result=PipelineResult(),
            paths=paths,
            missing_columns=exc.missing,
        )
        return outcome

    write_rejects(paths.rejects, result.rejected)
    aborted = bool(strict and result.rejected)
    status = "aborted_strict" if aborted else "ok"
    append_ingest_log(
        paths.log_file,
        csv_path=csv_path,
        rows_read=result.rows_read,
        accepted=len(result.accepted),
        rejected=len(result.rejected),
        rejects_path=paths.rejects,
        status=status,
        run_at=stamp,
    )
    if not aborted:
        write_geojson(paths.map_file, result.accepted)
        write_summary(
            paths.summary,
            records=result.accepted,
            rows_read=result.rows_read,
            rows_rejected=len(result.rejected),
            run_at=stamp,
        )
        from utility_asset_registry.database import session_scope
        from utility_asset_registry.persist import save_cleaned_many

        with session_scope() as session:
            save_cleaned_many(session, result.accepted)
    return IngestOutcome(result=result, paths=paths, aborted_strict=aborted)
