"""Phase 6: summary cache, rate limit, and request timing."""

from __future__ import annotations

from fastapi.testclient import TestClient

from utility_asset_registry.cache import invalidate_summary_cache


class TestSummaryCache:
    def test_second_summary_is_served_from_cache(
        self, client: TestClient, admin_headers: dict[str, str]
    ):
        invalidate_summary_cache()
        client.post(
            "/assets",
            headers=admin_headers,
            json={
                "asset_id": "PL-0601",
                "name": "Cache pole",
                "asset_type": "pole",
                "latitude": 20.3,
                "longitude": 85.8,
                "surveyed_on": "2026-09-10",
                "surveyor": "A. Patnaik",
                "status": "active",
                "condition_score": 8,
                "attribute_json": {},
            },
        )
        first = client.get("/reports/summary", headers=admin_headers)
        second = client.get("/reports/summary", headers=admin_headers)
        assert first.status_code == 200
        assert second.status_code == 200
        assert first.json()["cached"] is False
        assert second.json()["cached"] is True
        assert first.json()["total"] == second.json()["total"]

    def test_cache_is_dropped_after_a_write(
        self, client: TestClient, admin_headers: dict[str, str]
    ):
        invalidate_summary_cache()
        client.post(
            "/assets",
            headers=admin_headers,
            json={
                "asset_id": "PL-0602",
                "name": "First pole",
                "asset_type": "pole",
                "latitude": 20.3,
                "longitude": 85.8,
                "surveyed_on": "2026-09-10",
                "surveyor": "A. Patnaik",
                "status": "active",
                "condition_score": 8,
                "attribute_json": {},
            },
        )
        warm = client.get("/reports/summary", headers=admin_headers)
        assert warm.json()["cached"] is False
        assert client.get("/reports/summary", headers=admin_headers).json()["cached"] is True

        client.post(
            "/assets",
            headers=admin_headers,
            json={
                "asset_id": "PL-0603",
                "name": "Second pole",
                "asset_type": "pole",
                "latitude": 20.31,
                "longitude": 85.81,
                "surveyed_on": "2026-09-10",
                "surveyor": "A. Patnaik",
                "status": "active",
                "condition_score": 5,
                "attribute_json": {},
            },
        )
        refreshed = client.get("/reports/summary", headers=admin_headers)
        assert refreshed.json()["cached"] is False
        assert refreshed.json()["total"] == warm.json()["total"] + 1


class TestRateLimit:
    def test_caller_is_refused_after_limit_with_retry_after(
        self, client: TestClient, admin_headers: dict[str, str], monkeypatch
    ):
        monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "5")
        from utility_asset_registry.config import get_settings

        get_settings.cache_clear()

        # Rebuild app so middleware reads the new limit.
        from utility_asset_registry.api.app import create_app

        with TestClient(create_app()) as limited:
            token = limited.post(
                "/auth/login",
                json={"username": "admin", "password": "admin-pass-123"},
            ).json()["token"]
            headers = {"Authorization": f"Bearer {token}"}
            statuses = []
            for _ in range(6):
                statuses.append(limited.get("/assets", headers=headers).status_code)
            assert 429 in statuses
            refused = limited.get("/assets", headers=headers)
            assert refused.status_code == 429
            body = refused.json()
            assert body["outcome"] == "rate_limited"
            assert "retry_after_seconds" in body
            assert refused.headers.get("Retry-After")

            # Health stays exempt.
            assert limited.get("/health").status_code == 200

        get_settings.cache_clear()


class TestRequestTiming:
    def test_response_includes_duration_header(
        self, client: TestClient, admin_headers: dict[str, str]
    ):
        response = client.get("/assets", headers=admin_headers)
        assert response.status_code == 200
        assert "X-Response-Time-Ms" in response.headers
        assert float(response.headers["X-Response-Time-Ms"]) >= 0
