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
_call_sequence: int = 0  # global counter across all calls in this process

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


def _parse_json(text: str) -> Dict[str, Any]:
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    # raw_decode stops at the end of the first valid JSON object,
    # ignoring any trailing text the model may have appended.
    result, _ = json.JSONDecoder().raw_decode(text)
    return result


def _call_anthropic(
    prompt: str, max_retries: int = GEMINI_MAX_RETRIES, seq: int = 0
) -> Tuple[Dict[str, Any], Dict[str, int]]:
    import anthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    client = anthropic.Anthropic(api_key=api_key)
    model = "claude-haiku-4-5-20251001"

    for attempt in range(max_retries):
        log.info(
            "llm_request",
            provider="anthropic",
            model=model,
            seq=seq,
            attempt=attempt + 1,
            max_retries=max_retries,
            prompt_chars=len(prompt),
        )
        try:
            message = client.messages.create(
                model=model,
                max_tokens=8192,
                messages=[{"role": "user", "content": prompt}],
            )
            usage = {
                "input_tokens": message.usage.input_tokens,
                "output_tokens": message.usage.output_tokens,
                "cached_tokens": 0,
            }
            log.info(
                "llm_response_ok",
                provider="anthropic",
                seq=seq,
                attempt=attempt + 1,
                input_tokens=usage["input_tokens"],
                output_tokens=usage["output_tokens"],
            )
            text = message.content[0].text
            return _parse_json(text), usage

        except json.JSONDecodeError as e:
            log.warning(
                "llm_json_parse_error",
                provider="anthropic",
                seq=seq,
                attempt=attempt + 1,
                error=str(e),
                response_tail=text[-300:] if len(text) > 300 else text,
            )
            if attempt == max_retries - 1:
                raise
        except Exception as e:
            err_str = str(e)
            log.error(
                "llm_api_error",
                provider="anthropic",
                seq=seq,
                attempt=attempt + 1,
                error_type=type(e).__name__,
                error=err_str,
            )
            if attempt == max_retries - 1:
                raise

    raise Exception(f"Failed after {max_retries} retries (seq={seq})")


def _call_gemini(
    prompt: str, max_retries: int = GEMINI_MAX_RETRIES
) -> Tuple[Dict[str, Any], Dict[str, int]]:
    global _call_sequence
    _call_sequence += 1
    seq = _call_sequence

    # Use Anthropic if key is present — bypasses all Gemini quota issues
    if os.environ.get("ANTHROPIC_API_KEY"):
        return _call_anthropic(prompt, max_retries, seq)

    client = _get_gemini_client()
    # Disable thinking tokens: gemini-3-flash-preview is a thinking model that spends
    # ~4000 tokens on internal reasoning, leaving almost nothing for JSON output.
    config = types.GenerateContentConfig(
        max_output_tokens=GEMINI_MAX_OUTPUT_TOKENS,
        thinking_config=types.ThinkingConfig(thinking_budget=0),
    )

    for attempt in range(max_retries):
        log.info(
            "gemini_request",
            seq=seq,
            attempt=attempt + 1,
            max_retries=max_retries,
            model=GEMINI_MODEL,
            prompt_chars=len(prompt),
        )
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=config,
            )
            usage = _extract_usage(response)
            log.info(
                "gemini_response_ok",
                seq=seq,
                attempt=attempt + 1,
                input_tokens=usage["input_tokens"],
                output_tokens=usage["output_tokens"],
                cached_tokens=usage["cached_tokens"],
            )

            text = response.text.strip()
            return _parse_json(text), usage

        except json.JSONDecodeError as e:
            log.warning(
                "gemini_json_parse_error",
                seq=seq,
                attempt=attempt + 1,
                max_retries=max_retries,
                error=str(e),
                response_tail=text[-300:] if len(text) > 300 else text,
            )
            if attempt == max_retries - 1:
                raise
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "quota" in err_str.lower() or "RESOURCE_EXHAUSTED" in err_str:
                wait = GEMINI_RATE_LIMIT_BACKOFF_BASE * (attempt + 1)
                log.warning(
                    "gemini_rate_limit",
                    seq=seq,
                    attempt=attempt + 1,
                    wait_seconds=wait,
                    error=err_str,
                )
                time.sleep(wait)
            else:
                log.error(
                    "gemini_api_error",
                    seq=seq,
                    attempt=attempt + 1,
                    max_retries=max_retries,
                    error_type=type(e).__name__,
                    error=err_str,
                )
                if attempt == max_retries - 1:
                    raise

    raise Exception(f"Failed after {max_retries} retries (seq={seq})")


def call_gemini(
    prompt: str, max_retries: int = GEMINI_MAX_RETRIES
) -> Tuple[Dict[str, Any], Dict[str, int]]:
    """Public entry point. Returns (result_dict, usage_dict)."""
    return _call_gemini(prompt, max_retries)
