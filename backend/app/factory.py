"""Application factory. Kept apart from main.py so tests can build apps after setting env."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.middleware.request_id import HEADER, RequestIdMiddleware


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    setup_logging(get_settings().log_level)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="supportdash", lifespan=lifespan)

    # Spec order, outermost first: CORS, then RequestId.
    # Starlette wraps the last middleware added on the outside, so add RequestId first.
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[HEADER],
    )

    app.include_router(health_router)
    return app
