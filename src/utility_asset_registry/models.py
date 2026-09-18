"""ORM models. Switching SQLite to PostgreSQL is a DATABASE_URL change only."""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import Date, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from utility_asset_registry.database import Base


class Asset(Base):
    __tablename__ = "assets"
    __table_args__ = (UniqueConstraint("asset_id", name="uq_assets_asset_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    asset_id: Mapped[str] = mapped_column(String(7), index=True)
    name: Mapped[str] = mapped_column(String(120))
    asset_type: Mapped[str] = mapped_column(String(20), index=True)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    elevation_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    surveyed_on: Mapped[date] = mapped_column(Date)
    surveyor: Mapped[str] = mapped_column(String(120), default="")
    surveyor_key: Mapped[str] = mapped_column(String(120), default="", index=True)
    status: Mapped[str] = mapped_column(String(20), index=True)
    condition_score: Mapped[int] = mapped_column(Integer)
    condition_band: Mapped[str] = mapped_column(String(12))
    attributes: Mapped[Any] = mapped_column(JSON, default=dict)

    visits: Mapped[list[Visit]] = relationship(
        back_populates="asset",
        cascade="all, delete-orphan",
        order_by="Visit.visited_on",
    )


class Visit(Base):
    __tablename__ = "visits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    asset_pk: Mapped[int] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), index=True)
    visited_on: Mapped[date] = mapped_column(Date)
    surveyor: Mapped[str] = mapped_column(String(120), default="")
    condition_score: Mapped[int] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(String(240), nullable=True)

    asset: Mapped[Asset] = relationship(back_populates="visits")
