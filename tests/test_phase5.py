"""Phase 5: JWT sign-in, roles, bulk upload, and CORS."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from conftest import ADMIN_PASSWORD, ADMIN_USERNAME, auth_headers, login
from factories import VALID_ROW, make_row, write_survey_csv


class TestLogin:
    def test_successful_sign_in_returns_bearer_token(self, client: TestClient):
        response = client.post(
            "/auth/login",
            json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["token_type"] == "bearer"
        assert body["role"] == "admin"
        assert body["username"] == ADMIN_USERNAME
        assert body["token"]
        assert "password" not in body
        assert body["expires_in"] > 0

    def test_wrong_password_is_unauthenticated_not_forbidden(self, client: TestClient):
        response = client.post(
            "/auth/login",
            json={"username": ADMIN_USERNAME, "password": "wrong-password"},
        )
        assert response.status_code == 401
        assert response.json()["outcome"] == "unauthenticated"

    def test_asset_without_token_is_unauthenticated(self, client: TestClient):
        response = client.get("/assets")
        assert response.status_code == 401
        assert response.json()["outcome"] == "unauthenticated"

    def test_health_stays_open(self, client: TestClient):
        assert client.get("/health").status_code == 200


class TestRoles:
    def test_surveyor_may_read_add_and_correct(
        self, client: TestClient, surveyor_headers: dict[str, str]
    ):
        created = client.post(
            "/assets",
            headers=surveyor_headers,
            json={
                "asset_id": "PL-0200",
                "name": "Surveyor pole",
                "asset_type": "pole",
                "latitude": 20.3,
                "longitude": 85.8,
                "surveyed_on": "2026-09-10",
                "surveyor": "A. Patnaik",
                "status": "active",
                "condition_score": 7,
                "attribute_json": {"height_m": 8},
            },
        )
        assert created.status_code == 201
        patched = client.patch(
            "/assets/PL-0200",
            headers=surveyor_headers,
            json={"name": "corrected by surveyor"},
        )
        assert patched.status_code == 200
        assert patched.json()["asset"]["name"] == "Corrected By Surveyor"
        listed = client.get("/assets", headers=surveyor_headers)
        assert listed.status_code == 200

    def test_surveyor_is_refused_deletion(
        self, client: TestClient, admin_headers: dict[str, str], surveyor_headers: dict[str, str]
    ):
        client.post(
            "/assets",
            headers=admin_headers,
            json={
                "asset_id": "PL-0201",
                "name": "Keep this pole",
                "asset_type": "pole",
                "latitude": 20.3,
                "longitude": 85.8,
                "surveyed_on": "2026-09-10",
                "surveyor": "A. Patnaik",
                "status": "active",
                "condition_score": 7,
                "attribute_json": {},
            },
        )
        refused = client.delete("/assets/PL-0201", headers=surveyor_headers)
        assert refused.status_code == 403
        assert refused.json()["outcome"] == "not_permitted"
        assert client.get("/assets/PL-0201", headers=admin_headers).status_code == 200

    def test_surveyor_cannot_create_users(
        self, client: TestClient, surveyor_headers: dict[str, str]
    ):
        response = client.post(
            "/auth/users",
            headers=surveyor_headers,
            json={"username": "other", "password": "password123", "role": "surveyor"},
        )
        assert response.status_code == 403
        assert response.json()["outcome"] == "not_permitted"

    def test_admin_can_create_a_surveyor(self, client: TestClient, admin_headers: dict[str, str]):
        response = client.post(
            "/auth/users",
            headers=admin_headers,
            json={"username": "fieldcrew", "password": "password123", "role": "surveyor"},
        )
        assert response.status_code == 201
        assert response.json()["outcome"] == "created"
        assert response.json()["user"]["role"] == "surveyor"
        assert "password" not in response.json()["user"]
        token = login(client, "fieldcrew", "password123")
        assert token


class TestBulkUpload:
    def test_admin_upload_reports_accepted_and_rejected(
        self, client: TestClient, admin_headers: dict[str, str], tmp_path: Path
    ):
        csv_path = write_survey_csv(
            tmp_path / "day.csv",
            [VALID_ROW, make_row(asset_id="PL-0002", condition_score="14")],
        )
        with csv_path.open("rb") as handle:
            response = client.post(
                "/ingest/upload",
                headers=admin_headers,
                files={"file": ("day.csv", handle, "text/csv")},
            )
        assert response.status_code == 200
        body = response.json()
        assert body["rows_read"] == 2
        assert body["accepted"] == 1
        assert body["rejected"] == 1
        assert client.get("/assets/PL-0142", headers=admin_headers).status_code == 200

    def test_surveyor_cannot_upload(
        self, client: TestClient, surveyor_headers: dict[str, str], tmp_path: Path
    ):
        csv_path = write_survey_csv(tmp_path / "day.csv", [VALID_ROW])
        with csv_path.open("rb") as handle:
            response = client.post(
                "/ingest/upload",
                headers=surveyor_headers,
                files={"file": ("day.csv", handle, "text/csv")},
            )
        assert response.status_code == 403
        assert response.json()["outcome"] == "not_permitted"


class TestCors:
    def test_permitted_map_origin_receives_cors_headers(self, client: TestClient):
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.status_code in {200, 204}
        assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"

    def test_other_origin_is_not_reflected(self, client: TestClient):
        response = client.get("/health", headers={"Origin": "http://evil.example"})
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") != "http://evil.example"
