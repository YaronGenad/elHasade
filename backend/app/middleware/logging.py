"""
Request / response logging middleware (Sprint 5).

Logs every HTTP request with: method, path, status_code, duration_ms, user_id.
Skips noisy endpoints (/health, /metrics) at INFO level — logged at DEBUG only.
"""
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import get_logger

log = get_logger("app.middleware.logging")

_QUIET_PATHS = {"/health", "/metrics", "/"}


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()

        response: Response = await call_next(request)

        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        user_id = getattr(request.state, "user_id", None)
        request_id = getattr(request.state, "request_id", None)

        log_kwargs = {
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
            "user_id": user_id,
            "request_id": request_id,
        }

        if request.url.path in _QUIET_PATHS:
            log.debug("http_request", **log_kwargs)
        else:
            log.info("http_request", **log_kwargs)

        return response
