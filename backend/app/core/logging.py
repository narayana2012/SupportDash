"""JSON logging. Every line carries request_id and workflow_id (null when unset)."""

import json
import logging
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime

_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
_workflow_id: ContextVar[str | None] = ContextVar("workflow_id", default=None)
_UVICORN_LOGGERS = ("uvicorn", "uvicorn.error", "uvicorn.access")


@contextmanager
def log_context(
    request_id: str | None = None,
    workflow_id: str | None = None,
) -> Iterator[None]:
    """Bind request and workflow ids for the logs written inside the block."""
    request_token = _request_id.set(request_id) if request_id is not None else None
    workflow_token = _workflow_id.set(workflow_id) if workflow_id is not None else None
    try:
        yield
    finally:
        if workflow_token is not None:
            _workflow_id.reset(workflow_token)
        if request_token is not None:
            _request_id.reset(request_token)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": _request_id.get(),
            "workflow_id": _workflow_id.get(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def setup_logging(level: str = "INFO") -> None:
    """Send root logs to stdout as JSON. Calling it again replaces the handler."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    for existing in list(root.handlers):
        root.removeHandler(existing)
    root.addHandler(handler)
    root.setLevel(level.upper())

    # uvicorn sets up its own text handlers. Send its records through the root JSON handler.
    for name in _UVICORN_LOGGERS:
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers.clear()
        uvicorn_logger.propagate = True
