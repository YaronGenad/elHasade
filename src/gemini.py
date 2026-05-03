import json
import os
import time
from typing import Any, Dict, Tuple

import structlog
from google import genai
from google.genai import types

from .config import (
    GEMINI_MAX_RETRIES,
    GEMINI_MAX_OUTPUT_TOKENS,
    GEMINI_MODEL,
    GEMINI_RATE_LIMIT_BACKOFF_BASE,
)

log = structlog.get_logger(__name__)

_gemini_client: genai.Client | None = None

# Zero-usage sentinel returned when metadata is absent
_ZERO_USAGE: Dict[str, int] = {"input_tokens": 0, "output_tokens": 0, "cached_tokens": 0}


def _get_gemini_client() -> genai.Client:
    global _gemini_client
    if _gemini_client is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found. Check your .env file.")
        _gemini_client = genai.Client(api_key=api_key)
    return _gemini_client


def _extract_usage(response: Any) -> Dict[str, int]:
    """Pull token counts from usage_metadata; return zeros if unavailable."""
    meta = getattr(response, "usage_metadata", None)
    if meta is None:
        return dict(_ZERO_USAGE)
    return {
        "input_tokens": getattr(meta, "prompt_token_count", 0) or 0,
        "output_tokens": getattr(meta, "candidates_token_count", 0) or 0,
        "cached_tokens": getattr(meta, "cached_content_token_count", 0) or 0,
    }


def _call_gemini(
    prompt: str, max_retries: int = GEMINI_MAX_RETRIES
) -> Tuple[Dict[str, Any], Dict[str, int]]:
    """
    Call Gemini and return (parsed_json_result, usage_dict).

    usage_dict keys: input_tokens, output_tokens, cached_tokens.
    """
    client = _get_gemini_client()
    config = types.GenerateContentConfig(max_output_tokens=GEMINI_MAX_OUTPUT_TOKENS)

    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=config,
            )
            usage = _extract_usage(response)
            log.debug(
                "gemini_usage",
                input_tokens=usage["input_tokens"],
                output_tokens=usage["output_tokens"],
                cached_tokens=usage["cached_tokens"],
            )

            text = response.text.strip()
            if text.startswith("```json"):
                text = text[7:]
            elif text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            return json.loads(text.strip()), usage

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


def call_gemini(
    prompt: str, max_retries: int = GEMINI_MAX_RETRIES
) -> Tuple[Dict[str, Any], Dict[str, int]]:
    """Public entry point. Returns (result_dict, usage_dict)."""
    return _call_gemini(prompt, max_retries)
