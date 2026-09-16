"""Field rules that every record must pass before it may be stored."""

from __future__ import annotations

import re
from datetime import date
from typing import Any

from utility_asset_registry.cleaning import (
    blank_to_none,
    condition_band,
    normalise_asset_type,
    normalise_status,
    parse_attribute_json,
    parse_condition_score,
    parse_coordinate,
    parse_elevation,
    parse_survey_date,
    surveyor_key,
    tidy_description,
    tidy_person_name,
)
from utility_asset_registry.constants import (
    ASSET_ID_PATTERN,
    ASSET_TYPES,
    CONDITION_MAX,
    CONDITION_MIN,
    DECOMMISSIONED_MAX_CONDITION,
    NAME_MAX_LENGTH,
    NAME_MIN_LENGTH,
    STATUSES,
)
from utility_asset_registry.records import CleanedRecord

_ASSET_ID_RE = re.compile(ASSET_ID_PATTERN)


def validate_asset_id(value: object, seen_ids: set[str]) -> list[str]:
    text = blank_to_none(value)
    if text is None:
        return ["asset_id is missing"]
    errors: list[str] = []
    if _ASSET_ID_RE.fullmatch(text) is None:
        errors.append(
            f"asset_id '{text}' does not match the required format AA-0000 "
            "(two capital letters, a hyphen, four digits)"
        )
        return errors
    if text in seen_ids:
        errors.append(f"asset_id '{text}' is duplicated")
    return errors


def collect_row_errors(row: dict[str, Any], seen_ids: set[str]) -> list[str]:
    """Return every reason this row cannot be trusted. Empty means accept."""
    errors: list[str] = []

    errors.extend(validate_asset_id(row.get("asset_id"), seen_ids))

    name = tidy_description(row.get("name"))
    if not (NAME_MIN_LENGTH <= len(name) <= NAME_MAX_LENGTH):
        errors.append(
            f"name must be {NAME_MIN_LENGTH} to {NAME_MAX_LENGTH} characters after tidying"
        )

    raw_type = blank_to_none(row.get("asset_type"))
    asset_type = normalise_asset_type(row.get("asset_type"))
    if asset_type is None:
        shown = raw_type if raw_type is not None else ""
        errors.append(
            f"asset_type '{shown}' is not recognised; "
            f"must be one of: {', '.join(sorted(ASSET_TYPES))}"
        )

    latitude = parse_coordinate(row.get("latitude"))
    if latitude is None:
        errors.append(f"latitude '{row.get('latitude', '')}' is not a number")
    elif not -90 <= latitude <= 90:
        errors.append(f"latitude {latitude} is outside the range -90 to 90")

    longitude = parse_coordinate(row.get("longitude"))
    if longitude is None:
        errors.append(f"longitude '{row.get('longitude', '')}' is not a number")
    elif not -180 <= longitude <= 180:
        errors.append(f"longitude {longitude} is outside the range -180 to 180")

    surveyed_on = parse_survey_date(row.get("surveyed_on"))
    if surveyed_on is None:
        errors.append(
            f"surveyed_on '{row.get('surveyed_on', '')}' is not a valid date in YYYY-MM-DD form"
        )
    elif surveyed_on > date.today():
        errors.append(f"surveyed_on '{surveyed_on.isoformat()}' is in the future")

    raw_status = blank_to_none(row.get("status"))
    status = normalise_status(row.get("status"))
    if status is None:
        shown = raw_status if raw_status is not None else ""
        errors.append(
            f"status '{shown}' is not recognised; "
            f"must be one of: {', '.join(sorted(STATUSES))}"
        )

    condition_score = parse_condition_score(row.get("condition_score"))
    if blank_to_none(row.get("condition_score")) is None:
        errors.append("condition_score is missing")
    elif condition_score is None or not (CONDITION_MIN <= condition_score <= CONDITION_MAX):
        errors.append(
            f"condition_score '{row.get('condition_score', '')}' must be a whole number "
            f"from {CONDITION_MIN} to {CONDITION_MAX}"
        )

    _attributes, json_ok = parse_attribute_json(row.get("attribute_json"))
    if not json_ok:
        errors.append("attribute_json is not valid JSON")

    if (
        status == "decommissioned"
        and condition_score is not None
        and condition_score > DECOMMISSIONED_MAX_CONDITION
    ):
        errors.append(
            "decommissioned assets may not have a condition_score above "
            f"{DECOMMISSIONED_MAX_CONDITION}"
        )

    return errors


def to_cleaned_record(row: dict[str, Any]) -> CleanedRecord:
    """Build a cleaned record. Call only after collect_row_errors is empty."""
    asset_id = blank_to_none(row.get("asset_id")) or ""
    name = tidy_description(row.get("name"))
    asset_type = normalise_asset_type(row.get("asset_type")) or ""
    latitude = parse_coordinate(row.get("latitude"))
    longitude = parse_coordinate(row.get("longitude"))
    surveyed_on = parse_survey_date(row.get("surveyed_on"))
    status = normalise_status(row.get("status")) or ""
    condition_score = parse_condition_score(row.get("condition_score"))
    attributes, _ = parse_attribute_json(row.get("attribute_json"))
    surveyor = tidy_person_name(row.get("surveyor"))

    if latitude is None or longitude is None or surveyed_on is None or condition_score is None:
        raise ValueError("to_cleaned_record called on a row that did not pass validation")

    original = {key: "" if row.get(key) is None else str(row.get(key)) for key in row}

    return CleanedRecord(
        asset_id=asset_id,
        name=name,
        asset_type=asset_type,
        latitude=latitude,
        longitude=longitude,
        elevation_m=parse_elevation(row.get("elevation_m")),
        surveyed_on=surveyed_on,
        surveyor=surveyor,
        surveyor_key=surveyor_key(surveyor),
        status=status,
        condition_score=condition_score,
        condition_band=condition_band(condition_score),
        attributes=attributes,
        original=original,
    )
