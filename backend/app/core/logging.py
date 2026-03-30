"""
Structured JSON logging — Sprint 5.

Usage:
    from app.core.logging import get_logger
    log = get_logger(__name__)
    log.info("cache_hit", teacher_id=teacher.id, unit_id=unit.id)
"""
import logging
import sys
from typing import Any

import structlog


def setup_logging(debug: bool = False) -> None:
    """Configure structlog for the application. Call once at startup."""
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if debug:
        # Human-readable output in development
        renderer = structlog.dev.ConsoleRenderer()
    else:
        # Machine-readable JSON in production
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=shared_processors + [renderer],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Route standard-library logging through structlog
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.DEBUG if debug else logging.INFO,
    )


def get_logger(name: str = "app") -> Any:
    """Return a structlog bound logger."""
    return structlog.get_logger(name)
