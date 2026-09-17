"""Command-line ingest tool for a night-shift operator who does not know Python."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import typer

from utility_asset_registry.geo import nearest_asset
from utility_asset_registry.ingest import resolve_paths, run_ingest
from utility_asset_registry.reports import surveyors_on


def _parse_near(value: str | None) -> tuple[float, float] | None:
    if value is None:
        return None
    parts = [item.strip() for item in value.split(",")]
    if len(parts) != 2:
        raise typer.BadParameter("Use --near LATITUDE,LONGITUDE")
    try:
        return float(parts[0]), float(parts[1])
    except ValueError as exc:
        raise typer.BadParameter("Use --near LATITUDE,LONGITUDE") from exc


def _parse_on_date(value: str | None) -> date | None:
    if value is None:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise typer.BadParameter("Use --on-date YYYY-MM-DD") from exc


def ingest(
    csv_path: Path = typer.Argument(
        ...,
        exists=True,
        readable=True,
        help="Path of the handheld GPS CSV export.",
    ),
    rejects: Path | None = typer.Option(
        None,
        "--rejects",
        help="Where to write the rejects file (original columns plus reason).",
    ),
    map_file: Path | None = typer.Option(
        None,
        "--map",
        help="Where to write the GeoJSON map file of accepted assets.",
    ),
    summary: Path | None = typer.Option(
        None,
        "--summary",
        help="Where to write the printable summary report.",
    ),
    log_file: Path | None = typer.Option(
        None,
        "--log",
        help="Log file to which this run appends one dated line.",
    ),
    strict: bool = typer.Option(
        False,
        "--strict",
        help="Abort the whole run if any row is rejected (for already-cleaned files).",
    ),
    near: str | None = typer.Option(
        None,
        "--near",
        help="LATITUDE,LONGITUDE — print the nearest accepted asset in kilometres.",
    ),
    on_date: str | None = typer.Option(
        None,
        "--on-date",
        help="YYYY-MM-DD — list distinct surveyors who worked that day.",
    ),
) -> None:
    """Load one day's field export, clean it, and write rejects, map and summary."""
    paths = resolve_paths(
        csv_path,
        rejects=rejects,
        map_file=map_file,
        summary=summary,
        log_file=log_file,
    )
    outcome = run_ingest(csv_path, paths, strict=strict)

    if outcome.missing_columns:
        missing = ", ".join(outcome.missing_columns)
        typer.echo(f"CSV is missing required column(s): {missing}")
        raise typer.Exit(code=1)

    result = outcome.result
    typer.echo(f"Rows read:      {result.rows_read}")
    typer.echo(f"Rows accepted:  {len(result.accepted)}")
    typer.echo(f"Rows rejected:  {len(result.rejected)}")
    typer.echo(f"Rejects file:   {paths.rejects}")

    if outcome.aborted_strict:
        typer.echo(
            "Strict mode: a rejected row aborted the whole run. "
            "Map and summary were not written."
        )
        raise typer.Exit(code=1)

    typer.echo(f"Map file:       {paths.map_file}")
    typer.echo(f"Summary report: {paths.summary}")

    position = _parse_near(near)
    if position is not None:
        found = nearest_asset(result.accepted, position[0], position[1])
        if found is None:
            typer.echo("Nearest asset:  none (no accepted rows)")
        else:
            asset, km = found
            typer.echo(f"Nearest asset:  {asset.asset_id} ({asset.name}) at {km:.3f} km")

    day = _parse_on_date(on_date)
    if day is not None:
        names = surveyors_on(result.accepted, day)
        listed = ", ".join(names) if names else "(none)"
        typer.echo(f"Surveyors on {day.isoformat()}: {listed}")


def run() -> None:
    typer.run(ingest)
