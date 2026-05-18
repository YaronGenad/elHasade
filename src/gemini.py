import json
import os
import threading
import time
from typing import Any, Dict, Tuple

import structlog
from google import genai
from google.genai import types

from .config import (
    GEMINI_MAX_RETRIES,
    GEMINI_MAX_OUTPUT_TOKENS,
    GEMINI_MODEL,
    GEMINI_MODEL_FALLBACK_CHAIN,
    GEMINI_RATE_LIMIT_BACKOFF_BASE,
)

log = structlog.get_logger(__name__)

_client_k1: genai.Client | None = None
_client_k2: genai.Client | None = None
_client_lock = threading.Lock()

_call_sequence: int = 0
_seq_lock = threading.Lock()

# Zero-usage sentinel returned when metadata is absent
_ZERO_USAGE: Dict[str, int] = {"input_tokens": 0, "output_tokens": 0, "cached_tokens": 0}


def _next_seq() -> int:
    global _call_sequence
    with _seq_lock:
        _call_sequence += 1
        return _call_sequence


def _get_gemini_client(seq: int) -> genai.Client:
    global _client_k1, _client_k2
    key1 = os.environ.get("GEMINI_API_KEY")
    key2 = os.environ.get("GEMINI_API_KEY_2")
    if not key1:
        raise ValueError("GEMINI_API_KEY not found. Check your .env file.")
    use_key2 = bool(key2) and (seq % 2 == 1)
    with _client_lock:
        if use_key2:
            if _client_k2 is None:
                _client_k2 = genai.Client(api_key=key2)
            return _client_k2
        else:
            if _client_k1 is None:
                _client_k1 = genai.Client(api_key=key1)
            return _client_k1


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
    """Kept for reference; not called in normal operation."""
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


def _is_daily_quota_error(err_str: str) -> bool:
    """True when the model's quota is exhausted and retrying won't help.
    Catches both daily-limit messages and the generic free-tier exhaustion message."""
    lower = err_str.lower()
    has_rpm_signal = "per_minute" in lower or "rate limit" in lower or "per minute" in lower
    return (
        "PerDay" in err_str
        or "per_day" in lower
        or "GenerateRequestsPerDay" in err_str
        or "daily" in lower
        or "exceeded your current quota" in lower
        or "check your plan and billing" in lower
        or (("RESOURCE_EXHAUSTED" in err_str or "resource_exhausted" in lower) and not has_rpm_signal)
    )


def _call_gemini(
    prompt: str, max_retries: int = GEMINI_MAX_RETRIES
) -> Tuple[Dict[str, Any], Dict[str, int]]:
    seq = _next_seq()
    client = _get_gemini_client(seq)
    # Disable thinking tokens: flash models consume output budget on internal reasoning;
    # we need all output tokens for JSON.
    config = types.GenerateContentConfig(
        max_output_tokens=GEMINI_MAX_OUTPUT_TOKENS,
        thinking_config=types.ThinkingConfig(thinking_budget=0),
    )

    models = list(GEMINI_MODEL_FALLBACK_CHAIN)
    last_exc: Exception = Exception(f"No models available (seq={seq})")

    for model in models:
        quota_exhausted = False
        for attempt in range(max_retries):
            log.info(
                "gemini_request",
                seq=seq,
                attempt=attempt + 1,
                max_retries=max_retries,
                model=model,
                key_slot=1 + (seq % 2),
                prompt_chars=len(prompt),
            )
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=config,
                )
                usage = _extract_usage(response)
                log.info(
                    "gemini_response_ok",
                    seq=seq,
                    attempt=attempt + 1,
                    model=model,
                    input_tokens=usage["input_tokens"],
                    output_tokens=usage["output_tokens"],
                    cached_tokens=usage["cached_tokens"],
                )
                text = response.text.strip()
                return _parse_json(text), usage

            except json.JSONDecodeError as e:
                text_val = locals().get("text", "")
                log.warning(
                    "gemini_json_parse_error",
                    seq=seq,
                    attempt=attempt + 1,
                    model=model,
                    error=str(e),
                    response_tail=text_val[-300:] if len(text_val) > 300 else text_val,
                )
                last_exc = e
                if attempt == max_retries - 1:
                    raise

            except Exception as e:
                err_str = str(e)
                last_exc = e
                is_quota = "429" in err_str or "quota" in err_str.lower() or "RESOURCE_EXHAUSTED" in err_str

                if is_quota:
                    if _is_daily_quota_error(err_str):
                        # Daily limit — no point retrying; try next model immediately
                        log.warning(
                            "gemini_daily_quota_exhausted",
                            seq=seq,
                            model=model,
                            next_model=models[models.index(model) + 1] if model != models[-1] else "none",
                            error=err_str[:300],
                        )
                        quota_exhausted = True
                        break  # exit attempt loop → move to next model
                    else:
                        # Per-minute rate limit — wait and retry same model
                        wait = GEMINI_RATE_LIMIT_BACKOFF_BASE * (attempt + 1)
                        log.warning(
                            "gemini_rate_limit",
                            seq=seq,
                            attempt=attempt + 1,
                            model=model,
                            wait_seconds=wait,
                            error=err_str[:300],
                        )
                        time.sleep(wait)
                else:
                    log.error(
                        "gemini_api_error",
                        seq=seq,
                        attempt=attempt + 1,
                        model=model,
                        error_type=type(e).__name__,
                        error=err_str[:300],
                    )
                    if attempt == max_retries - 1:
                        raise

        if quota_exhausted:
            continue  # try next model in chain

    raise last_exc


def call_gemini(
    prompt: str, max_retries: int = GEMINI_MAX_RETRIES
) -> Tuple[Dict[str, Any], Dict[str, int]]:
    """Public entry point. Returns (result_dict, usage_dict)."""
    return _call_gemini(prompt, max_retries)
