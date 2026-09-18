"""Throwaway-database tests for storage and the six network operations."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from factories import VALID_ROW, make_row, write_survey_csv
from utility_asset_registry.api.app import create_app
from utility_asset_registry.config import get_settings
from utility_asset_registry.ingest import resolve_paths, run_ingest


def _body(**overrides):
    payload = {
        "asset_id": "PL-0142",
        "name": "North feeder pole",
        "asset_type": "pole",
        "latitude": 20.2961,
        "longitude": 85.8245,
        "elevation_m": 45.2,
        "surveyed_on": "2026-09-10",
        "surveyor": "A. Patnaik",
        "status": "active",
        "condition_score": 8,
        "attribute_json": {"height_m": 9.1},
    }
    payload.update(overrides)
    return payload


@pytest.fixture
def client():
    with TestClient(create_app()) as test_client:
        yield test_client


class TestHealthAndDocs:
    def test_health_is_unprotected_and_ok(self, client: TestClient):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_openapi_docs_are_published(self, client: TestClient):
        docs = client.get("/docs")
        spec = client.get("/openapi.json")
        assert docs.status_code == 200
        assert spec.status_code == 200
        paths = spec.json()["paths"]
        assert "/assets" in paths
        assert "/health" in paths


class TestAssetOperations:
    def test_create_then_fetch_one_by_code(self, client: TestClient):
        created = client.post("/assets", json=_body())
        assert created.status_code == 201
        assert created.json()["outcome"] == "created"
        fetched = client.get("/assets/PL-0142")
        assert fetched.status_code == 200
        body = fetched.json()
        assert body["asset_id"] == "PL-0142"
        assert body["name"] == "North Feeder Pole"
        assert body["asset_type"] == "pole"
        assert body["attributes"]["height_m"] == pytest.approx(9.1)
        assert body["visit_count"] == 1

    def test_duplicate_create_is_refused_and_leaves_data(self, client: TestClient):
        client.post("/assets", json=_body())
        again = client.post("/assets", json=_body(name="Changed pole"))
        assert again.status_code == 409
        assert again.json()["outcome"] == "invalid"
        assert "already" in again.json()["message"].lower()
        stored = client.get("/assets/PL-0142").json()
        assert stored["name"] == "North Feeder Pole"

    def test_missing_asset_is_not_found_not_a_crash(self, client: TestClient):
        response = client.get("/assets/PL-9999")
        assert response.status_code == 404
        assert response.json()["outcome"] == "not_found"
        assert "PL-9999" in response.json()["message"]

    def test_invalid_fields_name_what_was_wrong(self, client: TestClient):
        response = client.post("/assets", json=_body(latitude=95, condition_score=14))
        assert response.status_code == 422
        payload = response.json()
        assert payload["outcome"] == "invalid"
        assert "latitude" in payload["fields"]
        assert "condition_score" in payload["fields"]

    def test_replace_in_full(self, client: TestClient):
        client.post("/assets", json=_body())
        response = client.put(
            "/assets/PL-0142",
            json=_body(name="Replaced pole", condition_score=6, surveyed_on="2026-09-11"),
        )
        assert response.status_code == 200
        assert response.json()["outcome"] == "replaced"
        assert response.json()["asset"]["name"] == "Replaced Pole"
        assert response.json()["asset"]["condition_score"] == 6

    def test_patch_corrects_selected_fields_only(self, client: TestClient):
        client.post("/assets", json=_body())
        response = client.patch("/assets/PL-0142", json={"name": "corrected  pole"})
        assert response.status_code == 200
        asset = response.json()["asset"]
        assert asset["name"] == "Corrected Pole"
        assert asset["condition_score"] == 8
        assert asset["visit_count"] == 1

    def test_delete_removes_asset_and_visit_history(self, client: TestClient):
        client.post("/assets", json=_body())
        client.put("/assets/PL-0142", json=_body(surveyed_on="2026-09-12", condition_score=7))
        assert len(client.get("/assets/PL-0142/visits").json()) == 2
        deleted = client.delete("/assets/PL-0142")
        assert deleted.status_code == 200
        assert deleted.json()["outcome"] == "deleted"
        assert client.get("/assets/PL-0142").status_code == 404
        assert client.get("/assets/PL-0142/visits").status_code == 404


class TestListFilterPage:
    def test_list_never_returns_every_row_unpaged(self, client: TestClient):
        for index in range(3):
            client.post("/assets", json=_body(asset_id=f"PL-000{index + 1}", name=f"Pole {index + 1}"))
        page = client.get("/assets", params={"limit": 1, "offset": 0})
        body = page.json()
        assert body["total"] == 3
        assert body["limit"] == 1
        assert len(body["items"]) == 1
        page2 = client.get("/assets", params={"limit": 1, "offset": 1})
        assert page2.json()["items"][0]["asset_id"] != body["items"][0]["asset_id"]

    def test_default_page_size_is_25_and_max_is_100(self, client: TestClient):
        empty = client.get("/assets")
        assert empty.json()["limit"] == 25
        too_big = client.get("/assets", params={"limit": 101})
        assert too_big.status_code == 422
        assert too_big.json()["outcome"] == "invalid"

    def test_filter_type_status_surveyor_and_condition_range(self, client: TestClient):
        client.post("/assets", json=_body(asset_id="PL-0001", asset_type="pole", status="active", condition_score=8, surveyor="A. Patnaik"))
        client.post("/assets", json=_body(asset_id="TR-0001", asset_type="transformer", status="active", condition_score=3, surveyor="R. Mishra"))
        client.post("/assets", json=_body(asset_id="PL-0002", asset_type="pole", status="proposed", condition_score=6, surveyor="A. Patnaik"))
        poles = client.get("/assets", params={"asset_type": "pole"}).json()
        assert poles["total"] == 2
        poor = client.get("/assets", params={"condition_min": 0, "condition_max": 4}).json()
        assert [item["asset_id"] for item in poor["items"]] == ["TR-0001"]
        by_surveyor = client.get("/assets", params={"surveyor": "a patnaik"}).json()
        assert by_surveyor["total"] == 2
        proposed = client.get("/assets", params={"status": "proposed"}).json()
        assert proposed["total"] == 1

    def test_search_is_case_insensitive_in_the_description(self, client: TestClient):
        client.post("/assets", json=_body(asset_id="PL-0001", name="North feeder pole"))
        client.post("/assets", json=_body(asset_id="PL-0002", name="South street light"))
        found = client.get("/assets", params={"q": "FEEDER"}).json()
        assert found["total"] == 1
        assert found["items"][0]["asset_id"] == "PL-0001"


class TestReportsAndPersistence:
    def test_summary_repairs_and_most_visited(self, client: TestClient):
        client.post("/assets", json=_body(asset_id="PL-0001", condition_score=4, name="Weak pole"))
        client.post("/assets", json=_body(asset_id="PL-0002", condition_score=9, name="New pole"))
        client.put("/assets/PL-0001", json=_body(asset_id="PL-0001", condition_score=3, surveyed_on="2026-09-11", name="Weak pole"))
        summary = client.get("/reports/summary")
        assert summary.status_code == 200
        assert summary.json()["total"] == 2
        assert summary.json()["extent"] is not None
        repairs = client.get("/reports/repairs").json()["items"]
        assert [item["asset_id"] for item in repairs] == ["PL-0001"]
        frequent = client.get("/reports/most-visited").json()["items"]
        assert frequent[0]["asset"]["asset_id"] == "PL-0001"
        assert frequent[0]["visit_count"] == 2

    def test_ingest_persists_and_survives_a_restart(self, tmp_path, monkeypatch, client: TestClient):
        csv_path = write_survey_csv(tmp_path / "survey.csv", [VALID_ROW, make_row(asset_id="TR-0009", asset_type="transformer")])
        paths = resolve_paths(
            csv_path,
            rejects=tmp_path / "rejects.csv",
            map_file=tmp_path / "assets.geojson",
            summary=tmp_path / "summary.txt",
            log_file=tmp_path / "ingest.log",
        )
        outcome = run_ingest(csv_path, paths)
        assert len(outcome.result.accepted) == 2
        listed = client.get("/assets").json()
        assert listed["total"] == 2
        monkeypatch.setenv("DATABASE_URL", get_settings().database_url)
        get_settings.cache_clear()
        with TestClient(create_app()) as restarted:
            assert restarted.get("/assets/PL-0142").status_code == 200
            visits = restarted.get("/assets/PL-0142/visits")
            assert visits.status_code == 200
            assert len(visits.json()) == 1
