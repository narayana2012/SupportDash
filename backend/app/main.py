"""ASGI entry point: uvicorn app.main:app (run from backend/)."""

from app.factory import create_app

app = create_app()
