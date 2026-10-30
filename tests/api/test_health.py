"""P1-2: health routes and request-id middleware. Requirement IDs: F14 (offline ready), N3 (X-Request-ID)."""

import json
import logging
import uuid

import pytest
from fastapi.testclient import TestClient

import app.api.health as health_api
from app.core.config import Settings, get_settings
from app.core.logging import setup_logging
from app.factory import create_app


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch, tmp_path):
    # Empty working directory (no .env read), no shell overrides, fresh settings cache.
    monkeypatch.chdir(tmp_path)
    for name in Settings.model_fields:
        monkeypatch.delenv(name.upper(), raising=False)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def root_logger_restored():
    root = logging.getLogger()
    handlers, level = list(root.handlers), root.level
    yield root
    root.handlers[:] = handlers
    root.setLevel(level)


@pytest.fixture
def client():
    return TestClient(create_app())


# /health and /health/live (F14, N3)

def test_health_reports_service_and_environment(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "test")
    response = TestClient(create_app()).get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "supportdash"
    assert body["environment"] == "test"
    assert body["version"]


def test_live_is_alive_and_skips_readiness_checks(monkeypatch, client):
    # Liveness must not depend on configuration or services, so it never calls the checks.
    def fail_if_called(_settings):
        raise AssertionError("readiness checks must not run for /health/live")

    monkeypatch.setattr(health_api, "readiness_checks", fail_if_called)
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


# /health/ready (configuration checks only)

def test_ready_is_degraded_when_redis_is_not_configured(client):
    response = client.get("/health/ready")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "degraded"
    assert body["checks"]["database"] == {"status": "ok"}
    assert body["checks"]["vector_store"] == {"status": "ok"}
    assert body["checks"]["llm"] == {"status": "ok"}
    assert body["checks"]["redis"]["status"] == "error"
    assert "USE_FAKE_REDIS" in body["checks"]["redis"]["detail"]


def test_ready_is_ok_in_offline_demo_configuration(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    monkeypatch.setenv("VECTOR_STORE", "memory")
    monkeypatch.setenv("USE_FAKE_REDIS", "true")
    response = TestClient(create_app()).get("/health/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert set(body["checks"]) == {"database", "redis", "vector_store", "llm"}
    assert all(check == {"status": "ok"} for check in body["checks"].values())


def test_ready_details_never_leak_urls_passwords_or_keys(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://svc:db-pass-123@db.internal/x")
    monkeypatch.setenv("REDIS_URL", "redis://:redis-pass-456@cache.internal:6379/0")
    monkeypatch.setenv("VECTOR_STORE", "qdrant")
    monkeypatch.setenv("QDRANT_API_KEY", "qdrant-key-789")
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("LLM_API_KEY", "")
    response = TestClient(create_app()).get("/health/ready")
    text = response.text
    for secret in ("db-pass-123", "redis-pass-456", "qdrant-key-789", "cache.internal"):
        assert secret not in text
    assert response.json()["checks"]["vector_store"]["status"] == "error"
    assert response.json()["checks"]["llm"]["status"] == "error"


# N3: X-Request-ID on every response

def test_valid_request_id_is_echoed(client):
    response = client.get("/health", headers={"X-Request-ID": "abc-123.XYZ:9_ok"})
    assert response.headers["X-Request-ID"] == "abc-123.XYZ:9_ok"


@pytest.mark.parametrize("supplied", ["has spaces", "x" * 129, "bad/slash", ""])
def test_invalid_request_id_is_replaced_with_uuid(client, supplied):
    response = client.get("/health", headers={"X-Request-ID": supplied})
    generated = response.headers["X-Request-ID"]
    assert generated != supplied
    assert uuid.UUID(generated).version == 4


def test_request_id_is_generated_when_absent(client):
    response = client.get("/health/live")
    assert uuid.UUID(response.headers["X-Request-ID"]).version == 4


def test_request_id_is_on_404(client):
    response = client.get("/no-such-route", headers={"X-Request-ID": "missing-1"})
    assert response.status_code == 404
    assert response.headers["X-Request-ID"] == "missing-1"


def test_request_id_is_on_unhandled_500():
    app = create_app()

    @app.get("/boom")
    async def boom():
        raise RuntimeError("kaboom")

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/boom", headers={"X-Request-ID": "err-500"})
    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error"}
    assert response.headers["X-Request-ID"] == "err-500"


def test_cors_exposes_request_id_header(client):
    response = client.get("/health/live", headers={"Origin": "http://localhost:3000"})
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert "X-Request-ID" in response.headers["access-control-expose-headers"]


def test_logs_written_during_request_carry_request_id(root_logger_restored, capsys):
    app = create_app()

    @app.get("/log-here")
    async def log_here():
        logging.getLogger("test.route").info("inside request")
        return {"ok": True}

    with TestClient(app) as client:  # runs lifespan, which configures JSON logging
        response = client.get("/log-here", headers={"X-Request-ID": "log-req-1"})

    assert response.headers["X-Request-ID"] == "log-req-1"
    records = [json.loads(line) for line in capsys.readouterr().out.splitlines() if line.strip()]
    inside = next(record for record in records if record["message"] == "inside request")
    assert inside["request_id"] == "log-req-1"
    assert inside["workflow_id"] is None
