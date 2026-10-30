"""Health probes. Unprefixed and unauthenticated: /health, /health/live, /health/ready."""

from importlib.metadata import PackageNotFoundError, version

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.health import readiness_checks

router = APIRouter(tags=["health"])

SERVICE_NAME = "supportdash"


def _app_version() -> str:
    try:
        return version(SERVICE_NAME)
    except PackageNotFoundError:
        return "0.0.0"


@router.get("/health")
async def health() -> dict[str, str]:
    settings = get_settings()
    return {
        "status": "ok",
        "service": SERVICE_NAME,
        "version": _app_version(),
        "environment": settings.environment,
    }


@router.get("/health/live")
async def live() -> dict[str, str]:
    # No I/O. Probes use this to decide whether the process is alive.
    return {"status": "alive"}


@router.get("/health/ready")
def ready() -> JSONResponse:
    checks = readiness_checks(get_settings())
    ok = all(check.status == "ok" for check in checks.values())
    body = {
        "status": "ready" if ok else "degraded",
        "checks": {name: check.as_dict() for name, check in checks.items()},
    }
    return JSONResponse(body, status_code=200 if ok else 503)
