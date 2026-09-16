"""Phase 2: cleaning, validation, and reject handling — every rule and boundary."""

from __future__ import annotations

import csv
from datetime import date, timedelta
from pathlib import Path

import pytest

from utility_asset_registry.cleaning import (
    condition_band,
    normalise_asset_type,
    parse_coordinate,
    parse_elevation,
    surveyor_key,
    tidy_description,
    tidy_person_name,
)
from utility_asset_registry.constants import EXPECTED_COLUMNS
from utility_asset_registry.pipeline import (
    MissingColumnsError,
    process_csv,
    process_rows,
    require_columns,
    write_rejects,
)
from utility_asset_registry.validation import collect_row_errors, to_cleaned_record

from factories import VALID_ROW, make_row


class TestTidyDescription:
    def test_trims_leading_and_trailing_spaces(self):
        assert tidy_description("  north feeder pole  ") == "North Feeder Pole"

    def test_collapses_repeated_internal_spaces(self):
        assert tidy_description("north   feeder    pole") == "North Feeder Pole"

    def test_applies_consistent_capitalisation(self):
        assert tidy_description("NORTH feeder POLE") == "North Feeder Pole"

    def test_blank_becomes_empty_string(self):
        assert tidy_description("   ") == ""
        assert tidy_description(None) == ""

    def test_length_boundaries_after_tidying(self):
        assert len(tidy_description("ab")) == 2
        assert len(tidy_description("abc")) == 3
        assert len(tidy_description("x" * 120)) == 120
        assert len(tidy_description("x" * 121)) == 121


class TestCoordinates:
    def test_plain_decimal_is_unchanged(self):
        assert parse_coordinate("20.2961") == pytest.approx(20.2961)

    def test_north_suffix_stays_positive(self):
        assert parse_coordinate("28.6148 N") == pytest.approx(28.6148)
        assert parse_coordinate("28.6148N") == pytest.approx(28.6148)

    def test_north_prefix_stays_positive(self):
        assert parse_coordinate("N 28.6148") == pytest.approx(28.6148)

    def test_south_becomes_negative(self):
        assert parse_coordinate("15.5 S") == pytest.approx(-15.5)
        assert parse_coordinate("S15.5") == pytest.approx(-15.5)

    def test_east_stays_positive(self):
        assert parse_coordinate("85.8245 E") == pytest.approx(85.8245)

    def test_west_becomes_negative(self):
        assert parse_coordinate("85.8245 W") == pytest.approx(-85.8245)

    def test_signed_number_without_compass_is_kept(self):
        assert parse_coordinate("-20.5") == pytest.approx(-20.5)

    def test_south_uses_absolute_value_then_negates(self):
        assert parse_coordinate("-15.5 S") == pytest.approx(-15.5)

    def test_not_a_number_returns_none(self):
        assert parse_coordinate("east of temple") is None
        assert parse_coordinate("20.2 N 85.8") is None
        assert parse_coordinate("") is None
        assert parse_coordinate(None) is None

    def test_latitude_range_boundaries(self):
        assert collect_row_errors(make_row(latitude="90"), set()) == []
        assert collect_row_errors(make_row(latitude="-90"), set()) == []
        errors = collect_row_errors(make_row(latitude="90.0001"), set())
        assert any("latitude" in item and "outside" in item for item in errors)
        errors = collect_row_errors(make_row(latitude="-90.1"), set())
        assert any("latitude" in item and "outside" in item for item in errors)

    def test_longitude_range_boundaries(self):
        assert collect_row_errors(make_row(longitude="180"), set()) == []
        assert collect_row_errors(make_row(longitude="-180"), set()) == []
        errors = collect_row_errors(make_row(longitude="180.1"), set())
        assert any("longitude" in item and "outside" in item for item in errors)
        errors = collect_row_errors(make_row(longitude="-180.1 W"), set())
        assert any("longitude" in item and "outside" in item for item in errors)

    def test_non_numeric_longitude_is_rejected(self):
        errors = collect_row_errors(make_row(longitude="not a number"), set())
        assert any("longitude" in item and "not a number" in item for item in errors)


class TestAssetTypeAndStatus:
    @pytest.mark.parametrize("raw", ["pole", "POLE", "Pole", " pOlE "])
    def test_asset_type_matched_regardless_of_case(self, raw):
        assert normalise_asset_type(raw) == "pole"
        assert collect_row_errors(make_row(asset_type=raw), set()) == []

    @pytest.mark.parametrize("canonical", ["pole", "valve", "manhole", "transformer"])
    def test_each_recognised_asset_type_is_accepted(self, canonical):
        assert collect_row_errors(make_row(asset_type=canonical), set()) == []

    def test_unrecognised_asset_type_is_rejected(self):
        errors = collect_row_errors(make_row(asset_type="pump"), set())
        assert any("asset_type" in item and "pump" in item for item in errors)

    @pytest.mark.parametrize("raw,expected", [("ACTIVE", "active"), (" Decommissioned ", "decommissioned")])
    def test_status_normalised_to_lowercase(self, raw, expected):
        record = to_cleaned_record(make_row(status=raw, condition_score="1"))
        assert record.status == expected

    def test_unknown_status_is_rejected(self):
        errors = collect_row_errors(make_row(status="broken"), set())
        assert any("status" in item for item in errors)


class TestSurveyorNames:
    def test_same_person_typed_three_ways_shares_one_key(self):
        keys = {
            surveyor_key("A. Patnaik"),
            surveyor_key("a patnaik"),
            surveyor_key("A  PATNAIK"),
        }
        assert keys == {"apatnaik"}

    def test_display_name_is_title_case_with_single_spaces(self):
        assert tidy_person_name("  r. k.   mishra ") == "R. K. Mishra"

    def test_different_people_keep_different_keys(self):
        assert surveyor_key("A. Patnaik") != surveyor_key("R. Mishra")


class TestAttributeJsonAndElevation:
    def test_valid_json_object_is_available_as_ordinary_data(self):
        record = to_cleaned_record(make_row(attribute_json='{"height_m": 9.1, "material": "steel"}'))
        assert record.attributes["height_m"] == pytest.approx(9.1)
        assert record.attributes["material"] == "steel"

    def test_invalid_json_is_rejected(self):
        errors = collect_row_errors(make_row(attribute_json="{height: 9"), set())
        assert any("attribute_json" in item for item in errors)

    def test_blank_json_is_rejected(self):
        errors = collect_row_errors(make_row(attribute_json=""), set())
        assert any("attribute_json" in item for item in errors)

    def test_blank_elevation_is_stored_as_not_recorded(self):
        record = to_cleaned_record(make_row(elevation_m=""))
        assert record.elevation_m is None

    def test_non_numeric_elevation_is_stored_as_not_recorded_not_rejected(self):
        row = make_row(elevation_m="about 40")
        assert collect_row_errors(row, set()) == []
        assert to_cleaned_record(row).elevation_m is None
        assert parse_elevation("45.2") == pytest.approx(45.2)


class TestAssetIdNameDateCondition:
    def test_valid_asset_id_is_accepted(self):
        assert collect_row_errors(make_row(asset_id="TR-0001"), set()) == []

    def test_missing_asset_id_is_rejected(self):
        errors = collect_row_errors(make_row(asset_id=""), set())
        assert any("asset_id is missing" in item for item in errors)

    def test_asset_id_must_be_two_capitals_hyphen_four_digits(self):
        for bad in ("pl-0142", "PL-142", "PL0142", "P-0142", "PL-01421", "1L-0142"):
            errors = collect_row_errors(make_row(asset_id=bad), set())
            assert any("does not match" in item for item in errors), bad

    def test_duplicate_asset_id_is_rejected(self):
        errors = collect_row_errors(make_row(), {"PL-0142"})
        assert any("duplicated" in item for item in errors)

    def test_name_too_short_after_tidying_is_rejected(self):
        errors = collect_row_errors(make_row(name="  ab  "), set())
        assert any("name must be" in item for item in errors)

    def test_name_of_three_and_one_hundred_twenty_chars_is_accepted(self):
        assert collect_row_errors(make_row(name="abc"), set()) == []
        assert collect_row_errors(make_row(name="x" * 120), set()) == []

    def test_name_of_121_chars_is_rejected(self):
        errors = collect_row_errors(make_row(name="x" * 121), set())
        assert any("name must be" in item for item in errors)

    def test_future_survey_date_is_rejected(self):
        future = (date.today() + timedelta(days=1)).isoformat()
        errors = collect_row_errors(make_row(surveyed_on=future), set())
        assert any("future" in item for item in errors)

    def test_today_is_accepted(self):
        assert collect_row_errors(make_row(surveyed_on=date.today().isoformat()), set()) == []

    def test_invalid_date_is_rejected(self):
        errors = collect_row_errors(make_row(surveyed_on="10-09-2026"), set())
        assert any("surveyed_on" in item for item in errors)

    def test_condition_blank_is_rejected(self):
        errors = collect_row_errors(make_row(condition_score=""), set())
        assert any("condition_score is missing" in item for item in errors)

    def test_condition_14_is_rejected(self):
        errors = collect_row_errors(make_row(condition_score="14"), set())
        assert any("condition_score" in item for item in errors)

    def test_condition_0_and_10_are_accepted(self):
        assert collect_row_errors(make_row(condition_score="0"), set()) == []
        assert collect_row_errors(make_row(condition_score="10"), set()) == []

    def test_non_integer_condition_is_rejected(self):
        errors = collect_row_errors(make_row(condition_score="7.5"), set())
        assert any("condition_score" in item for item in errors)

    def test_decommissioned_may_not_have_condition_above_2(self):
        errors = collect_row_errors(
            make_row(status="decommissioned", condition_score="3"),
            set(),
        )
        assert any("decommissioned" in item for item in errors)

    def test_decommissioned_with_condition_2_is_accepted(self):
        assert (
            collect_row_errors(make_row(status="decommissioned", condition_score="2"), set())
            == []
        )


class TestConditionBands:
    @pytest.mark.parametrize("score,band", [(10, "GOOD"), (8, "GOOD"), (7, "FAIR"), (5, "FAIR"), (4, "POOR"), (3, "POOR"), (2, "CRITICAL"), (0, "CRITICAL")])
    def test_bands(self, score, band):
        assert condition_band(score) == band
        assert to_cleaned_record(make_row(condition_score=str(score))).condition_band == band


class TestPipelineAndRejects:
    def test_valid_row_is_accepted_and_standardised(self):
        messy = make_row(
            name="  NORTH   feeder pole ",
            asset_type="Pole",
            latitude="20.2961 N",
            longitude="85.8245 E",
            surveyor="a  patnaik",
            status="ACTIVE",
        )
        result = process_rows([messy])
        assert result.rows_read == 1
        assert len(result.accepted) == 1
        assert result.rejected == []
        record = result.accepted[0]
        assert record.name == "North Feeder Pole"
        assert record.asset_type == "pole"
        assert record.latitude == pytest.approx(20.2961)
        assert record.longitude == pytest.approx(85.8245)
        assert record.surveyor == "A Patnaik"
        assert record.surveyor_key == "apatnaik"
        assert record.status == "active"

    def test_one_bad_row_does_not_stop_the_run(self):
        bad = make_row(asset_id="PL-0001", latitude="95")
        good = make_row(asset_id="PL-0002")
        result = process_rows([bad, good])
        assert result.rows_read == 2
        assert [row.asset_id for row in result.accepted] == ["PL-0002"]
        assert len(result.rejected) == 1
        assert "latitude" in result.rejected[0].reason

    def test_duplicate_code_on_second_row_is_rejected(self):
        first = make_row(asset_id="PL-0142", name="First pole")
        second = make_row(asset_id="PL-0142", name="Second pole")
        result = process_rows([first, second])
        assert len(result.accepted) == 1
        assert result.accepted[0].name == "First Pole"
        assert "duplicated" in result.rejected[0].reason

    def test_rejected_row_keeps_original_values_and_reason(self):
        raw = make_row(name="  messy   name ", condition_score="14")
        result = process_rows([raw])
        rejected = result.rejected[0]
        assert rejected.original["name"] == "  messy   name "
        assert rejected.original["condition_score"] == "14"
        assert "condition_score" in rejected.reason

    def test_multiple_faults_are_all_named_in_the_reason(self):
        raw = make_row(asset_id="", latitude="99", condition_score="", attribute_json="{")
        result = process_rows([raw])
        reason = result.rejected[0].reason
        assert "asset_id" in reason
        assert "latitude" in reason
        assert "condition_score" in reason
        assert "attribute_json" in reason

    def test_no_row_is_discarded_silently(self):
        rows = [
            make_row(asset_id="PL-0001"),
            make_row(asset_id="", name="x"),
            make_row(asset_id="PL-0003", asset_type="pump"),
        ]
        result = process_rows(rows)
        assert result.rows_read == 3
        assert len(result.accepted) + len(result.rejected) == 3
        assert all(item.reason for item in result.rejected)

    def test_write_rejects_adds_reason_column_and_keeps_originals(self, tmp_path: Path):
        result = process_rows([make_row(condition_score="14")])
        out = tmp_path / "rejects.csv"
        write_rejects(out, result.rejected)
        with out.open(newline="", encoding="utf-8") as handle:
            loaded = list(csv.DictReader(handle))
        assert loaded[0]["asset_id"] == VALID_ROW["asset_id"]
        assert loaded[0]["condition_score"] == "14"
        assert "reason" in loaded[0]
        assert "condition_score" in loaded[0]["reason"]
        assert list(loaded[0].keys()) == list(EXPECTED_COLUMNS) + ["reason"]

    def test_missing_column_stops_before_processing(self, tmp_path: Path):
        path = tmp_path / "short.csv"
        path.write_text("asset_id,name\nPL-0001,Pole\n", encoding="utf-8")
        with pytest.raises(MissingColumnsError) as raised:
            process_csv(path)
        assert "latitude" in raised.value.missing
        assert "CSV is missing required column(s)" in str(raised.value)

    def test_require_columns_passes_when_every_expected_column_is_present(self):
        require_columns(list(EXPECTED_COLUMNS))

    def test_process_csv_accepts_a_clean_file(self, tmp_path: Path):
        path = tmp_path / "survey.csv"
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(EXPECTED_COLUMNS))
            writer.writeheader()
            writer.writerow(VALID_ROW)
            writer.writerow(make_row(asset_id="TR-0009", asset_type="transformer", condition_score="4"))
        result = process_csv(path)
        assert result.rows_read == 2
        assert len(result.accepted) == 2
        assert result.rejected == []
