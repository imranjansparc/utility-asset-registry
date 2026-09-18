"""Save cleaned survey records and query stored assets."""

from __future__ import annotations

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, selectinload

from utility_asset_registry.models import Asset, Visit
from utility_asset_registry.records import CleanedRecord
from utility_asset_registry.cleaning import surveyor_key as make_surveyor_key


DEFAULT_PAGE_SIZE = 25
MAX_PAGE_SIZE = 100


def cleaned_from_asset(asset: Asset) -> CleanedRecord:
    return CleanedRecord(
        asset_id=asset.asset_id,
        name=asset.name,
        asset_type=asset.asset_type,
        latitude=asset.latitude,
        longitude=asset.longitude,
        elevation_m=asset.elevation_m,
        surveyed_on=asset.surveyed_on,
        surveyor=asset.surveyor,
        surveyor_key=asset.surveyor_key,
        status=asset.status,
        condition_score=asset.condition_score,
        condition_band=asset.condition_band,
        attributes=asset.attributes,
        original={},
    )


def apply_snapshot(asset: Asset, record: CleanedRecord) -> None:
    asset.name = record.name
    asset.asset_type = record.asset_type
    asset.latitude = record.latitude
    asset.longitude = record.longitude
    asset.elevation_m = record.elevation_m
    asset.surveyed_on = record.surveyed_on
    asset.surveyor = record.surveyor
    asset.surveyor_key = record.surveyor_key
    asset.status = record.status
    asset.condition_score = record.condition_score
    asset.condition_band = record.condition_band
    asset.attributes = record.attributes


def _visit_from(record: CleanedRecord) -> Visit:
    return Visit(
        visited_on=record.surveyed_on,
        surveyor=record.surveyor,
        condition_score=record.condition_score,
        notes=record.name,
    )


def get_by_code(session: Session, asset_id: str) -> Asset | None:
    return session.scalar(
        select(Asset).options(selectinload(Asset.visits)).where(Asset.asset_id == asset_id)
    )


def save_cleaned(session: Session, record: CleanedRecord, *, add_visit: bool = True) -> Asset:
    """Insert a new asset or update it. Repeat surveys append visit history."""
    existing = get_by_code(session, record.asset_id)
    if existing is None:
        asset = Asset(asset_id=record.asset_id)
        apply_snapshot(asset, record)
        asset.visits.append(_visit_from(record))
        session.add(asset)
        return asset
    apply_snapshot(existing, record)
    if add_visit:
        existing.visits.append(_visit_from(record))
    return existing


def save_cleaned_many(session: Session, records: list[CleanedRecord]) -> int:
    for record in records:
        save_cleaned(session, record)
    return len(records)


def delete_asset(session: Session, asset: Asset) -> None:
    session.delete(asset)


def clamp_page(limit: int | None, offset: int | None) -> tuple[int, int]:
    size = DEFAULT_PAGE_SIZE if limit is None else limit
    size = max(1, min(size, MAX_PAGE_SIZE))
    start = 0 if offset is None else max(0, offset)
    return size, start


def filtered_select(
    *,
    asset_type: str | None = None,
    status: str | None = None,
    surveyor: str | None = None,
    condition_min: int | None = None,
    condition_max: int | None = None,
    q: str | None = None,
) -> Select[tuple[Asset]]:
    stmt = select(Asset)
    if asset_type:
        stmt = stmt.where(Asset.asset_type == asset_type.lower())
    if status:
        stmt = stmt.where(Asset.status == status.lower())
    if surveyor:
        key = make_surveyor_key(surveyor)
        stmt = stmt.where(
            (Asset.surveyor_key == key) | (func.lower(Asset.surveyor).like(f"%{surveyor.lower()}%"))
        )
    if condition_min is not None:
        stmt = stmt.where(Asset.condition_score >= condition_min)
    if condition_max is not None:
        stmt = stmt.where(Asset.condition_score <= condition_max)
    if q:
        stmt = stmt.where(func.lower(Asset.name).like(f"%{q.lower()}%"))
    return stmt.order_by(Asset.asset_id)


def list_assets(
    session: Session,
    *,
    asset_type: str | None = None,
    status: str | None = None,
    surveyor: str | None = None,
    condition_min: int | None = None,
    condition_max: int | None = None,
    q: str | None = None,
    limit: int | None = None,
    offset: int | None = None,
) -> tuple[list[Asset], int]:
    size, start = clamp_page(limit, offset)
    filtered = filtered_select(
        asset_type=asset_type,
        status=status,
        surveyor=surveyor,
        condition_min=condition_min,
        condition_max=condition_max,
        q=q,
    )
    total = session.scalar(select(func.count()).select_from(filtered.subquery())) or 0
    rows = list(session.scalars(filtered.offset(start).limit(size)).all())
    return rows, total


def most_visited(session: Session, limit: int = 10) -> list[tuple[Asset, int]]:
    size = max(1, min(limit, MAX_PAGE_SIZE))
    counts = (
        select(Visit.asset_pk, func.count(Visit.id).label("visit_count"))
        .group_by(Visit.asset_pk)
        .subquery()
    )
    stmt = (
        select(Asset, counts.c.visit_count)
        .join(counts, counts.c.asset_pk == Asset.id)
        .order_by(counts.c.visit_count.desc(), Asset.asset_id)
        .limit(size)
    )
    return [(row[0], int(row[1])) for row in session.execute(stmt).all()]


def all_cleaned(session: Session) -> list[CleanedRecord]:
    assets = list(session.scalars(select(Asset).order_by(Asset.asset_id)).all())
    return [cleaned_from_asset(asset) for asset in assets]
