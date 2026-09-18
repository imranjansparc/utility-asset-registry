"""Database engine and sessions. URL comes from the environment."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from utility_asset_registry.config import get_settings


class Base(DeclarativeBase):
    pass


def _sqlite_connect_args(url: str) -> dict[str, bool]:
    if url.startswith("sqlite"):
        return {"check_same_thread": False}
    return {}


def make_engine(url: str | None = None) -> Engine:
    database_url = url if url is not None else get_settings().database_url
    engine = create_engine(database_url, future=True, connect_args=_sqlite_connect_args(database_url))
    if database_url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def _enable_foreign_keys(dbapi_connection, _connection_record) -> None:  # type: ignore[no-untyped-def]
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def init_db(engine: Engine) -> None:
    from utility_asset_registry import models as _models  # noqa: F401

    Base.metadata.create_all(engine)


@contextmanager
def session_scope() -> Iterator[Session]:
    engine = make_engine()
    init_db(engine)
    session = make_session_factory(engine)()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
        engine.dispose()
