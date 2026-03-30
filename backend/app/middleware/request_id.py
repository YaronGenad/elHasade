"""
Request ID middleware (Sprint 5).

Generates a UUID for every incoming request and:
- stores it on ``request.state.request_id``
- adds the ``X-Request-ID`` response header
- binds it into structlog context so every log line carries the ID
"""
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

import structlog


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        # Accept an incoming X-Request-ID (e.g. from a gateway) or generate one
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id

        # Bind to structlog context so every log emitted during this
        # request automatically includes request_id
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        response: Response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
