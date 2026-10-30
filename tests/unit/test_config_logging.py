"""P1-1: settings and JSON logging. Requirement IDs: F14 (settings hook), N3 (request id in logs)."""

import json
import logging

import pytest
from pydantic import ValidationError

from app.core.config import REDACTED, Settings, get_settings, redact_url
from app.core.logging import log_context, setup_logging


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch, tmp_path):
    # Run in an empty directory so no developer .env is read, and clear shell overrides.
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


# F14: settings read from the environment, offline defaults

def test_defaults_are_offline_and_safe():
    settings = Settings(_env_file=None)
    assert settings.demo_mode is False
    assert settings.llm_provider == "fake"
    assert settings.vector_store == "memory"
    assert settings.use_fake_redis is False
    assert settings.approval_required_for_refunds is True
    assert settings.max_refund_without_approval == 0


def test_reads_demo_mode_and_llm_provider_from_environment(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    settings = get_settings()
    assert settings.demo_mode is True
    assert settings.llm_provider == "fake"


def test_get_settings_is_cached_until_cleared(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    first = get_settings()
    assert get_settings() is first
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    assert get_settings().llm_provider == "fake"  # still the cached object
    get_settings.cache_clear()
    assert get_settings().llm_provider == "openai"


def test_cors_origins_accepts_comma_separated_list(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000, https://console.example.com")
    assert get_settings().cors_origins == [
        "http://localhost:3000",
        "https://console.example.com",
    ]


def test_demo_mode_is_rejected_in_prod():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, environment="prod", demo_mode=True)


def test_effective_jwt_secret_prefers_supabase_secret_when_set():
    base = Settings(_env_file=None, jwt_secret="local-secret")
    assert base.effective_jwt_secret.get_secret_value() == "local-secret"
    with_supabase = Settings(
        _env_file=None, jwt_secret="local-secret", supabase_jwt_secret="supabase-secret"
    )
    assert with_supabase.effective_jwt_secret.get_secret_value() == "supabase-secret"


# Secrets never appear in dumps; code still reads the real value

def test_model_dump_redacts_secrets_and_keeps_attribute_values(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "sk-test-do-not-leak")
    monkeypatch.setenv("JWT_SECRET", "jwt-do-not-leak")
    settings = get_settings()

    dumped = settings.model_dump()
    text = json.dumps(dumped, default=str)
    assert "sk-test-do-not-leak" not in text
    assert "jwt-do-not-leak" not in text
    assert dumped["llm_api_key"] == REDACTED
    assert settings.llm_api_key.get_secret_value() == "sk-test-do-not-leak"
    assert "sk-test-do-not-leak" not in repr(settings)


def test_model_dump_redacts_url_password_but_keeps_attribute(monkeypatch):
    url = "postgresql+asyncpg://svc:hunter2@db.example.com:5432/supportdash"
    monkeypatch.setenv("DATABASE_URL", url)
    settings = get_settings()

    assert "hunter2" not in json.dumps(settings.model_dump(), default=str)
    assert settings.database_url == url
    assert redact_url(url) == (
        "postgresql+asyncpg://svc:**********@db.example.com:5432/supportdash"
    )


def test_redact_url_leaves_urls_without_password_alone():
    assert redact_url("redis://redis:6379/0") == "redis://redis:6379/0"
    assert redact_url("") == ""


# N3 / F14: JSON logs with request_id and workflow_id

def test_log_line_is_json_with_null_ids_when_unset(root_logger_restored, capsys):
    setup_logging("INFO")
    logging.getLogger("test").info("hello")
    record = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert record["message"] == "hello"
    assert record["level"] == "INFO"
    assert record["logger"] == "test"
    assert record["request_id"] is None
    assert record["workflow_id"] is None
    assert "timestamp" in record


def test_log_context_binds_request_and_workflow_ids(root_logger_restored, capsys):
    setup_logging("INFO")
    with log_context(request_id="req-123", workflow_id="wf-456"):
        logging.getLogger("test").info("inside")
    logging.getLogger("test").info("outside")
    lines = capsys.readouterr().out.strip().splitlines()
    inside, outside = json.loads(lines[-2]), json.loads(lines[-1])
    assert (inside["request_id"], inside["workflow_id"]) == ("req-123", "wf-456")
    assert (outside["request_id"], outside["workflow_id"]) == (None, None)


def test_nested_log_context_restores_outer_values(root_logger_restored, capsys):
    setup_logging("INFO")
    with log_context(request_id="outer"):
        with log_context(request_id="inner", workflow_id="wf-1"):
            pass
        logging.getLogger("test").info("after inner")
    record = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert record["request_id"] == "outer"
    assert record["workflow_id"] is None


def test_setup_logging_is_idempotent(root_logger_restored, capsys):
    setup_logging("INFO")
    setup_logging("INFO")
    assert len(root_logger_restored.handlers) == 1
    logging.getLogger("test").info("once")
    assert len(capsys.readouterr().out.strip().splitlines()) == 1


def test_exception_is_included_in_json(root_logger_restored, capsys):
    setup_logging("INFO")
    try:
        raise RuntimeError("boom")
    except RuntimeError:
        logging.getLogger("test").exception("failed")
    record = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert "RuntimeError: boom" in record["exc_info"]


def test_uvicorn_loggers_use_root_json_handler(root_logger_restored, capsys):
    setup_logging("INFO")
    access = logging.getLogger("uvicorn.access")
    assert access.handlers == []
    assert access.propagate is True
    access.info('%s - "%s %s" %d', "127.0.0.1", "GET", "/health", 200)
    record = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert record["logger"] == "uvicorn.access"
    assert record["message"] == '127.0.0.1 - "GET /health" 200'
