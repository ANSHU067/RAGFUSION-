"""FastAPI startup and HTTP contract tests."""

from fastapi.testclient import TestClient
from unittest.mock import AsyncMock

import pytest

from main import app

client = TestClient(app)


def test_docs_are_available() -> None:
    response = client.get("/docs")

    assert response.status_code == 200


@pytest.mark.parametrize("redis_available", [True, False])
def test_health_reports_dependencies(monkeypatch, redis_available) -> None:
    async def database_is_up() -> bool:
        return True

    monkeypatch.setattr("app.services.health.check_database_connection", database_is_up)
    redis = AsyncMock()
    redis.ping.return_value = redis_available
    monkeypatch.setattr(app.state.rate_limiter, "redis", redis, raising=False)

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok" if redis_available else "degraded",
        "database": True,
        "redis": redis_available,
    }
    assert response.headers["X-Request-ID"]
    redis.ping.assert_awaited_once()
    redis.aclose.assert_not_called()


def test_info_uses_settings_dependency() -> None:
    response = client.get("/api/v1/info")

    assert response.status_code == 200
    assert response.json()["name"] == "RAGFUSION API"


def test_application_sets_security_headers() -> None:
    response = client.get("/api/v1/info")

    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert "content-security-policy" in response.headers
