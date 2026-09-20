"""Pytest configuration. Each test gets a throwaway database and a bootstrap admin."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from utility_asset_registry.api.app import create_app
from utility_asset_registry.config import get_settings

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin-pass-123"
SURVEYOR_USERNAME = "surveyor"
SURVEYOR_PASSWORD = "surveyor-pass-123"


@pytest.fixture(autouse=True)
def isolated_settings(monkeypatch, tmp_path):
    monkeypatch.setenv("JWT_SECRET", "test-secret-not-for-production")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///" + (tmp_path / "test.db").resolve().as_posix())
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5173")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_USERNAME", ADMIN_USERNAME)
    monkeypatch.setenv("BOOTSTRAP_ADMIN_PASSWORD", ADMIN_PASSWORD)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def client():
    with TestClient(create_app()) as test_client:
        yield test_client


def login(client: TestClient, username: str, password: str) -> str:
    response = client.post("/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["token"]


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers(client: TestClient) -> dict[str, str]:
    return auth_headers(login(client, ADMIN_USERNAME, ADMIN_PASSWORD))


@pytest.fixture
def surveyor_headers(client: TestClient, admin_headers: dict[str, str]) -> dict[str, str]:
    created = client.post(
        "/auth/users",
        headers=admin_headers,
        json={
            "username": SURVEYOR_USERNAME,
            "password": SURVEYOR_PASSWORD,
            "role": "surveyor",
        },
    )
    assert created.status_code == 201, created.text
    return auth_headers(login(client, SURVEYOR_USERNAME, SURVEYOR_PASSWORD))
