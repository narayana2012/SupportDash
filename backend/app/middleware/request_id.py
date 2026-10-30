"""N3: every HTTP response carries X-Request-ID.

A caller's value is echoed when it is 1-128 characters from A-Za-z0-9._:-.
Anything else is replaced with a new UUID. The id is bound to the logs for the
request, including 404 and 500 responses.
"""

import logging
import re
import uuid

from starlette.datastructures import Headers, MutableHeaders
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.logging import log_context

HEADER = "X-Request-ID"
_VALID_ID = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")

logger = logging.getLogger(__name__)


def _request_id_from(headers: Headers) -> str:
    supplied = headers.get(HEADER)
    if supplied is not None and _VALID_ID.fullmatch(supplied):
        return supplied
    return str(uuid.uuid4())


class RequestIdMiddleware:
    """Pure ASGI middleware, so the header is also set on unhandled 500 responses."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = _request_id_from(Headers(scope=scope))
        response_started = False

        async def send_with_request_id(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
                MutableHeaders(scope=message)[HEADER] = request_id
            await send(message)

        with log_context(request_id=request_id):
            try:
                await self.app(scope, receive, send_with_request_id)
            except Exception:
                logger.exception("unhandled error")
                if response_started:
                    raise
                response = JSONResponse(
                    {"detail": "Internal server error"},
                    status_code=500,
                    headers={HEADER: request_id},
                )
                await response(scope, receive, send)
