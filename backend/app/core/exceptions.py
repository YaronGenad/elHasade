"""
Custom application exceptions (Sprint 3).

Hierarchy:
    AppError
    ├── GenerationFailedError   — pipeline / generation service failures
    ├── LLMAPIError             — Gemini API call failures
    ├── PDFRenderError          — PDF generation / HTML save failures
    ├── CacheUnavailableError   — Redis connection / operation failures
    └── SearchError             — BM25 / pgvector query failures
"""


class AppError(Exception):
    """Base exception for all application errors."""

    http_status_code: int = 400

    def __init__(self, message: str, error_code: str = "APP_ERROR", detail: str = ""):
        self.message = message
        self.error_code = error_code
        self.detail = detail
        super().__init__(message)

    def to_dict(self) -> dict:
        return {
            "error": self.message,
            "error_code": self.error_code,
            "detail": self.detail,
        }


class GenerationFailedError(AppError):
    """Raised when the generation pipeline fails."""

    http_status_code = 500

    def __init__(self, message: str = "Generation failed", detail: str = ""):
        super().__init__(message, error_code="GENERATION_FAILED", detail=detail)


class LLMAPIError(AppError):
    """Raised when a call to Gemini (or any LLM) fails."""

    http_status_code = 502

    def __init__(self, message: str = "LLM API call failed", detail: str = ""):
        super().__init__(message, error_code="LLM_API_ERROR", detail=detail)


class PDFRenderError(AppError):
    """Raised when PDF rendering or HTML file saving fails."""

    http_status_code = 500

    def __init__(self, message: str = "PDF rendering failed", detail: str = ""):
        super().__init__(message, error_code="PDF_RENDER_ERROR", detail=detail)


class CacheUnavailableError(AppError):
    """Raised when Redis is unavailable or a cache operation fails."""

    http_status_code = 503

    def __init__(self, message: str = "Cache unavailable", detail: str = ""):
        super().__init__(message, error_code="CACHE_UNAVAILABLE", detail=detail)


class SearchError(AppError):
    """Raised when a BM25 or pgvector search query fails."""

    http_status_code = 500

    def __init__(self, message: str = "Search failed", detail: str = ""):
        super().__init__(message, error_code="SEARCH_ERROR", detail=detail)


class CostLimitExceededError(AppError):
    """Raised when a generation would exceed the per-request cost cap."""

    http_status_code = 402

    def __init__(self, message: str = "Cost limit exceeded", detail: str = ""):
        super().__init__(message, error_code="COST_LIMIT_EXCEEDED", detail=detail)
