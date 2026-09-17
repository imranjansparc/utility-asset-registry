"""Phase 3: CLI ingest, analysis, GeoJSON, summary and ingest log."""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

from factories import VALID_ROW, make_row, write_survey_csv
from utility_asset_registry.cli import ingest
from utility_asset_registry.geo import as_geojson, bounding_box, haversine_km, nearest_asset
from utility_asset_registry.ingest import resolve_paths, run_ingest
from utility_asset_registry.pipeline import process_rows
from utility_asset_registry.reports import (
    assets_needing_repair,
    format_summary,
    surveyors_on,
    type_stats,
)

runner = CliRunner()
cli_app = typer.Typer(add_completion=False)
cli_app.command()(ingest)


def _paths(tmp_path: Path):
    return resolve_paths(
        tmp_path / "survey.csv",
        rejects=tmp_path / "rejects.csv",
        map_file=tmp_path / "assets.geojson",
        summary=tmp_path / "summary.txt",
        log_file=tmp_path / "ingest.log",
    )


class TestHaversineAndExtent:
    def test_one_degree_longitude_on_equator_is_about_111_km(self):
        assert haversine_km(0.0, 0.0, 0.0, 1.0) == pytest.approx(111.19, rel=0.01)

    def test_distance_is_symmetric_and_zero_to_self(self):
        assert haversine_km(20.2961, 85.8245, 20.2961, 85.8245) == pytest.approx(0.0)
        a = haversine_km(20.2961, 85.8245, 20.3, 85.83)
        b = haversine_km(20.3, 85.83, 20.2961, 85.8245)
        assert a == pytest.approx(b)

    def test_bounding_box_is_the_rectangle_covering_every_accepted_asset(self):
        records = process_rows(
            [
                make_row(asset_id="PL-0001", latitude="20.0", longitude="85.0"),
                make_row(asset_id="PL-0002", latitude="21.5", longitude="86.2"),
                make_row(asset_id="PL-0003", latitude="20.4", longitude="85.1"),
            ]
        ).accepted
        box = bounding_box(records)
        assert box is not None
        assert box.south == pytest.approx(20.0)
        assert box.north == pytest.approx(21.5)
        assert box.west == pytest.approx(85.0)
        assert box.east == pytest.approx(86.2)

    def test_bounding_box_is_none_when_nothing_was_accepted(self):
        assert bounding_box([]) is None

    def test_nearest_asset_uses_earth_surface_distance(self):
        records = process_rows(
            [
                make_row(asset_id="PL-0001", latitude="20.2961", longitude="85.8245", name="Close pole"),
                make_row(asset_id="PL-0002", latitude="21.5000", longitude="86.9000", name="Far pole"),
            ]
        ).accepted
        found = nearest_asset(records, 20.2970, 85.8250)
        assert found is not None
        asset, km = found
        assert asset.asset_id == "PL-0001"
        assert km < 1.0


class TestAnalysis:
    def test_per_type_count_average_and_worst_asset(self):
        records = process_rows(
            [
                make_row(asset_id="PL-0001", asset_type="pole", condition_score="8"),
                make_row(asset_id="PL-0002", asset_type="pole", condition_score="4"),
                make_row(asset_id="TR-0001", asset_type="transformer", condition_score="6"),
            ]
        ).accepted
        by_type = {item.asset_type: item for item in type_stats(records)}
        assert by_type["pole"].count == 2
        assert by_type["pole"].average_condition == pytest.approx(6.0)
        assert by_type["pole"].worst_asset_id == "PL-0002"
        assert by_type["pole"].worst_condition == 4
        assert by_type["transformer"].count == 1
        assert by_type["valve"].count == 0
        assert by_type["manhole"].count == 0

    def test_repair_list_is_active_assets_below_condition_5(self):
        records = process_rows(
            [
                make_row(asset_id="PL-0001", status="active", condition_score="4"),
                make_row(asset_id="PL-0002", status="active", condition_score="5"),
                make_row(asset_id="PL-0003", status="decommissioned", condition_score="1"),
                make_row(asset_id="PL-0004", status="proposed", condition_score="3"),
            ]
        ).accepted
        repair_ids = [row.asset_id for row in assets_needing_repair(records)]
        assert repair_ids == ["PL-0001"]

    def test_distinct_surveyors_on_a_day_count_the_same_person_once(self):
        records = process_rows(
            [
                make_row(asset_id="PL-0001", surveyor="A. Patnaik", surveyed_on="2026-09-10"),
                make_row(asset_id="PL-0002", surveyor="a patnaik", surveyed_on="2026-09-10"),
                make_row(asset_id="PL-0003", surveyor="R. Mishra", surveyed_on="2026-09-10"),
                make_row(asset_id="PL-0004", surveyor="R. Mishra", surveyed_on="2026-09-11"),
            ]
        ).accepted
        names = surveyors_on(records, date(2026, 9, 10))
        assert set(names) == {"A. Patnaik", "R. Mishra"}
        assert surveyors_on(records, date(2026, 9, 12)) == []

    def test_summary_has_title_time_aligned_type_lines_extent_and_totals(self):
        records = process_rows([make_row()]).accepted
        run_at = datetime(2026, 9, 17, 12, 0, tzinfo=timezone.utc)
        text = format_summary(
            records=records,
            rows_read=2,
            rows_rejected=1,
            run_at=run_at,
            extent=bounding_box(records),
        )
        assert text.startswith("Utility Asset Registry — survey ingest")
        assert "2026-09-17 12:00:00" in text
        assert "pole" in text
        assert "south=" in text
        assert "Totals: 2 read, 1 accepted, 1 rejected" in text


class TestGeojsonAndIngestRun:
    def test_geojson_is_a_feature_collection_of_points(self):
        records = process_rows([make_row()]).accepted
        payload = as_geojson(records)
        assert payload["type"] == "FeatureCollection"
        feature = payload["features"][0]
        assert feature["geometry"]["type"] == "Point"
        assert feature["geometry"]["coordinates"] == [records[0].longitude, records[0].latitude]
        assert feature["properties"]["asset_id"] == "PL-0142"
        assert feature["properties"]["attributes"]["height_m"] == pytest.approx(9.1)

    def test_run_writes_rejects_map_summary_and_appends_log(self, tmp_path: Path):
        csv_path = write_survey_csv(
            tmp_path / "survey.csv",
            [VALID_ROW, make_row(asset_id="PL-0002", condition_score="14")],
        )
        paths = _paths(tmp_path)
        outcome = run_ingest(csv_path, paths)
        assert len(outcome.result.accepted) == 1
        assert len(outcome.result.rejected) == 1
        assert paths.rejects.exists()
        assert paths.map_file.exists()
        assert paths.summary.exists()
        assert '"FeatureCollection"' in paths.map_file.read_text(encoding="utf-8")
        log_text = paths.log_file.read_text(encoding="utf-8")
        assert "status=ok" in log_text
        assert "read=2" in log_text
        assert "accepted=1" in log_text
        assert "rejected=1" in log_text
        run_ingest(csv_path, paths)
        assert paths.log_file.read_text(encoding="utf-8").count("csv=") == 2

    def test_strict_mode_aborts_without_map_or_summary(self, tmp_path: Path):
        csv_path = write_survey_csv(
            tmp_path / "survey.csv",
            [VALID_ROW, make_row(asset_id="PL-0002", condition_score="14")],
        )
        paths = _paths(tmp_path)
        outcome = run_ingest(csv_path, paths, strict=True)
        assert outcome.aborted_strict is True
        assert paths.rejects.exists()
        assert not paths.map_file.exists()
        assert not paths.summary.exists()
        assert "aborted_strict" in paths.log_file.read_text(encoding="utf-8")

    def test_missing_column_names_what_is_missing_and_writes_no_map(self, tmp_path: Path):
        csv_path = write_survey_csv(
            tmp_path / "survey.csv",
            [VALID_ROW],
            fieldnames=["asset_id", "name", "asset_type"],
        )
        paths = _paths(tmp_path)
        outcome = run_ingest(csv_path, paths)
        assert "latitude" in outcome.missing_columns
        assert not paths.map_file.exists()
        assert "missing_columns" in paths.log_file.read_text(encoding="utf-8")


class TestCli:
    def test_help_explains_usage(self):
        result = runner.invoke(cli_app, ["--help"])
        assert result.exit_code == 0
        assert "handheld" in result.stdout.lower() or "csv" in result.stdout.lower()
        assert "--rejects" in result.stdout
        assert "--map" in result.stdout
        assert "--summary" in result.stdout
        assert "--strict" in result.stdout

    def test_prints_counts_and_rejects_path(self, tmp_path: Path):
        csv_path = write_survey_csv(
            tmp_path / "survey.csv",
            [VALID_ROW, make_row(asset_id="BAD", name="x")],
        )
        result = runner.invoke(
            cli_app,
            [
                str(csv_path),
                "--rejects",
                str(tmp_path / "rejects.csv"),
                "--map",
                str(tmp_path / "assets.geojson"),
                "--summary",
                str(tmp_path / "summary.txt"),
                "--log",
                str(tmp_path / "ingest.log"),
            ],
        )
        assert result.exit_code == 0
        assert "Rows read:      2" in result.stdout
        assert "Rows accepted:  1" in result.stdout
        assert "Rows rejected:  1" in result.stdout
        assert "Rejects file:" in result.stdout

    def test_strict_exits_nonzero_when_a_row_is_rejected(self, tmp_path: Path):
        csv_path = write_survey_csv(
            tmp_path / "survey.csv",
            [make_row(condition_score="14")],
        )
        result = runner.invoke(
            cli_app,
            [
                str(csv_path),
                "--strict",
                "--rejects",
                str(tmp_path / "rejects.csv"),
                "--map",
                str(tmp_path / "assets.geojson"),
                "--summary",
                str(tmp_path / "summary.txt"),
                "--log",
                str(tmp_path / "ingest.log"),
            ],
        )
        assert result.exit_code == 1
        assert "aborted" in result.stdout.lower()

    def test_missing_column_exits_nonzero_and_names_the_column(self, tmp_path: Path):
        csv_path = write_survey_csv(
            tmp_path / "short.csv",
            [VALID_ROW],
            fieldnames=["asset_id", "name"],
        )
        result = runner.invoke(
            cli_app,
            [
                str(csv_path),
                "--log",
                str(tmp_path / "ingest.log"),
            ],
        )
        assert result.exit_code == 1
        assert "missing required column" in result.stdout.lower()
        assert "latitude" in result.stdout

    def test_near_and_on_date_print_analysis(self, tmp_path: Path):
        csv_path = write_survey_csv(tmp_path / "survey.csv", [VALID_ROW])
        result = runner.invoke(
            cli_app,
            [
                str(csv_path),
                "--rejects",
                str(tmp_path / "rejects.csv"),
                "--map",
                str(tmp_path / "assets.geojson"),
                "--summary",
                str(tmp_path / "summary.txt"),
                "--log",
                str(tmp_path / "ingest.log"),
                "--near",
                "20.2961,85.8245",
                "--on-date",
                "2026-09-10",
            ],
        )
        assert result.exit_code == 0
        assert "PL-0142" in result.stdout
        assert "A. Patnaik" in result.stdout
