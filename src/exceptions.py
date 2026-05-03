"""
Pipeline-level exceptions for the src package.

These are re-exported by backend/app/core/exceptions.py so the full
application has a single exception hierarchy.
"""


class LLMAPIError(Exception):
    """Raised when a call to Gemini (or any LLM) fails after retries."""

    def __init__(self, message: str = "LLM API call failed", detail: str = "") -> None:
        self.message: str = message
        self.detail: str = detail
        super().__init__(message)


class PDFRenderError(Exception):
    """Raised when PDF rendering or HTML file saving fails."""

    def __init__(self, message: str = "PDF rendering failed", detail: str = "") -> None:
        self.message: str = message
        self.detail: str = detail
        super().__init__(message)


class CostLimitExceededError(Exception):
    """Raised when a generation would exceed the per-request cost cap."""

    def __init__(self, message: str = "Cost limit exceeded", detail: str = "") -> None:
        self.message: str = message
        self.detail: str = detail
        super().__init__(message)
