"""Consistent JSON error and success envelopes for the web map vendor."""

from __future__ import annotations

from fastapi.responses import JSONResponse


def invalid_payload(fields: dict[str, str], message: str = "Request contents are invalid") -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"outcome": "invalid", "message": message, "fields": fields},
    )


def not_found(asset_id: str) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={
            "outcome": "not_found",
            "message": f"No asset with code {asset_id}",
            "asset_id": asset_id,
        },
    )


def created(body: dict) -> JSONResponse:
    return JSONResponse(status_code=201, content={"outcome": "created", **body})


def deleted(asset_id: str) -> JSONResponse:
    return JSONResponse(
        status_code=200,
        content={
            "outcome": "deleted",
            "message": f"Asset {asset_id} and its visit history were removed",
            "asset_id": asset_id,
        },
    )


def fields_from_reasons(reasons: list[str]) -> dict[str, str]:
    fields: dict[str, str] = {}
    for reason in reasons:
        if reason.startswith("decommissioned"):
            fields["condition_score"] = reason
            continue
        key = reason.split()[0]
        fields[key] = reason
    return fields
