"""Standardise untidy handheld-export values before validation."""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from typing import Any

from utility_asset_registry.constants import ASSET_TYPES, STATUSES

_COORD_RE = re.compile(
    r"""
    ^\s*
    (?P<prefix>[NnSsEeWw])?
    \s*
    (?P<number>[+-]?\d+(?:\.\d+)?)
    \s*
    (?P<suffix>[NnSsEeWw])?
    \s*$
    """,
    re.VERBOSE,
)


def blank_to_none(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def collapse_spaces(value: str) -> str:
    return " ".join(value.split())


def tidy_description(value: object) -> str:
    """Trim, squeeze repeated spaces, and apply consistent capitalisation."""
    text = blank_to_none(value)
    if text is None:
        return ""
    return collapse_spaces(text).title()


def tidy_person_name(value: object) -> str:
    """Standardise a surveyor name so the same person is counted once."""
    text = blank_to_none(value)
    if text is None:
        return ""
    return collapse_spaces(text).title()


def surveyor_key(value: object) -> str:
    """Letter/digit key so 'A. Patnaik', 'a patnaik' and 'A  PATNAIK' match."""
    return re.sub(r"[^a-z0-9]", "", tidy_person_name(value).lower())


def normalise_asset_type(value: object) -> str | None:
    text = blank_to_none(value)
    if text is None:
        return None
    canonical = collapse_spaces(text).lower()
    return canonical if canonical in ASSET_TYPES else None


def normalise_status(value: object) -> str | None:
    text = blank_to_none(value)
    if text is None:
        return None
    canonical = collapse_spaces(text).lower()
    return canonical if canonical in STATUSES else None


def parse_coordinate(value: object) -> float | None:
    """Turn '28.6148 N' / '85.8 W' into a signed decimal, or None if unusable."""
    text = blank_to_none(value)
    if text is None:
        return None
    match = _COORD_RE.fullmatch(text)
    if match is None:
        return None
    if match.group("prefix") and match.group("suffix"):
        return None
    number = float(match.group("number"))
    compass = (match.group("prefix") or match.group("suffix") or "").upper()
    if compass in {"S", "W"}:
        return -abs(number)
    if compass in {"N", "E"}:
        return abs(number)
    return number


def parse_elevation(value: object) -> float | None:
    """Blank or non-numeric elevation is stored as not recorded, not rejected."""
    text = blank_to_none(value)
    if text is None:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def parse_condition_score(value: object) -> int | None:
    text = blank_to_none(value)
    if text is None:
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    if not number.is_integer():
        return None
    return int(number)


def parse_survey_date(value: object) -> date | None:
    text = blank_to_none(value)
    if text is None:
        return None
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        return None


def parse_attribute_json(value: object) -> tuple[Any | None, bool]:
    """Return (parsed, ok). ok is False when the snippet is not valid JSON."""
    text = blank_to_none(value)
    if text is None:
        return None, False
    try:
        return json.loads(text), True
    except json.JSONDecodeError:
        return None, False


def condition_band(score: int) -> str:
    if 8 <= score <= 10:
        return "GOOD"
    if 5 <= score <= 7:
        return "FAIR"
    if 3 <= score <= 4:
        return "POOR"
    return "CRITICAL"
