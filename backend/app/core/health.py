"""Readiness checks based on configuration only.

No connection is opened here. A check passes when its service is configured.
Details name the setting to fix. They never include a URL, password, or key.
"""

from dataclasses import dataclass
from typing import Literal

from app.core.config import Settings


@dataclass(frozen=True)
class CheckResult:
    status: Literal["ok", "error"]
    detail: str | None = None

    def as_dict(self) -> dict[str, str]:
        if self.detail is None:
            return {"status": self.status}
        return {"status": self.status, "detail": self.detail}


OK = CheckResult("ok")


def readiness_checks(settings: Settings) -> dict[str, CheckResult]:
    return {
        "database": _database(settings),
        "redis": _redis(settings),
        "vector_store": _vector_store(settings),
        "llm": _llm(settings),
    }


def _database(settings: Settings) -> CheckResult:
    if settings.database_url.strip():
        return OK
    return CheckResult("error", "DATABASE_URL is not set")


def _redis(settings: Settings) -> CheckResult:
    if settings.use_fake_redis or settings.redis_url.strip():
        return OK
    return CheckResult("error", "REDIS_URL is not set and USE_FAKE_REDIS is false")


def _vector_store(settings: Settings) -> CheckResult:
    if settings.vector_store == "memory":
        return OK
    if settings.qdrant_url.strip():
        return OK
    return CheckResult("error", "QDRANT_URL is not set for VECTOR_STORE=qdrant")


def _llm(settings: Settings) -> CheckResult:
    if settings.llm_provider == "fake":
        return OK
    if settings.llm_api_key is not None and settings.llm_api_key.get_secret_value():
        return OK
    return CheckResult("error", f"LLM_API_KEY is not set for LLM_PROVIDER={settings.llm_provider}")
