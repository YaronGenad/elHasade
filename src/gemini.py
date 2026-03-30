import json
import os
import time
from typing import Any, Dict

import structlog
from google import genai

from .config import GEMINI_MAX_RETRIES, GEMINI_MODEL, GEMINI_RATE_LIMIT_BACKOFF_BASE

log = structlog.get_logger(__name__)

_gemini_client: genai.Client | None = None


def _get_gemini_client() -> genai.Client:
    global _gemini_client
    if _gemini_client is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found. Check your .env file.")
        _gemini_client = genai.Client(api_key=api_key)
    return _gemini_client


def _call_gemini(prompt: str, max_retries: int = GEMINI_MAX_RETRIES) -> Dict[str, Any]:
    client = _get_gemini_client()
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
            )
            text = response.text.strip()
            if text.startswith("```json"):
                text = text[7:]
            elif text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            return json.loads(text.strip())
        except json.JSONDecodeError as e:
            log.warning("gemini_json_parse_error", attempt=attempt + 1, max_retries=max_retries, error=str(e))
            if attempt == max_retries - 1:
                raise
        except Exception as e:
            if "429" in str(e) or "quota" in str(e).lower():
                wait = GEMINI_RATE_LIMIT_BACKOFF_BASE * (attempt + 1)
                log.warning("gemini_rate_limit", wait_seconds=wait, attempt=attempt + 1)
                time.sleep(wait)
            else:
                log.error("gemini_api_error", attempt=attempt + 1, max_retries=max_retries, error=str(e))
                if attempt == max_retries - 1:
                    raise
    raise Exception("Failed after retries")


def call_gemini(prompt: str, max_retries: int = GEMINI_MAX_RETRIES) -> Dict[str, Any]:
    return _call_gemini(prompt, max_retries)
