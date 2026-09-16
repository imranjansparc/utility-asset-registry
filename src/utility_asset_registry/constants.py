"""Shared field names and allowed values for survey records."""

EXPECTED_COLUMNS = (
    "asset_id",
    "name",
    "asset_type",
    "latitude",
    "longitude",
    "elevation_m",
    "surveyed_on",
    "surveyor",
    "status",
    "condition_score",
    "attribute_json",
)

ASSET_TYPES = frozenset({"pole", "valve", "manhole", "transformer"})
STATUSES = frozenset({"active", "decommissioned", "proposed"})

ASSET_ID_PATTERN = r"^[A-Z]{2}-\d{4}$"

NAME_MIN_LENGTH = 3
NAME_MAX_LENGTH = 120

CONDITION_MIN = 0
CONDITION_MAX = 10
DECOMMISSIONED_MAX_CONDITION = 2
