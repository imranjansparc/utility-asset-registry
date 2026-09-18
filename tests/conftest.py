"""Pytest configuration. Each test gets a throwaway database."""

from __future__ import annotations

import pytest

from utility_asset_registry.config import get_settings


@pytest.fixture(autouse=True)
def isolated_settings(monkeypatch, tmp_path):
    monkeypatch.setenv("JWT_SECRET", "test-secret-not-for-production")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///" + (tmp_path / "test.db").resolve().as_posix())
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
