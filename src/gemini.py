import json
import os
import threading
import time
from typing import Any, Dict, List, Tuple

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

# ── Gemini client pool (one client per unique API key) ────────────────────────
_clients: Dict[str, genai.Client] = {}
_exhausted_keys: set = set()       # keys that hit daily/per-day quota
_keys_lock = threading.Lock()

# All env-var names that may carry a Gemini key (duplicates are deduplicated)
_ALL_GEMINI_KEY_VARS = [
    "GEMINI_API_KEY",
    "GEMINI_API_KEY_2",
    "GEMINI_API_KEY_BECKUP",
    "GEMINI_API_KEY_BECKUP2",
    "GEMINI_API_KEY_BECKUP3",
    "GEMINI_API_KEY_3",
    "GEMINI_API_KEY_4",
]

_call_sequence: int = 0
_seq_lock = threading.Lock()

# Zero-usage sentinel returned when metadata is absent
_ZERO_USAGE: Dict[str, int] = {"input_tokens": 0, "output_tokens": 0, "cached_tokens": 0}


def _next_seq() -> int:
    global _call_sequence
    with _seq_lock:
        _call_sequence += 1
        return _call_sequence


def _get_available_gemini_keys() -> List[str]:
    """Return unique, non-empty Gemini keys collected from all env-var slots."""
    seen: set = set()
    keys: List[str] = []
    for var in _ALL_GEMINI_KEY_VARS:
        v = os.environ.get(var, "").strip()
        if v and v not in seen:
            seen.add(v)
            keys.append(v)
    return keys


def _get_gemini_client(key: str) -> genai.Client:
    with _keys_lock:
        if key not in _clients:
            _clients[key] = genai.Client(api_key=key)
        return _clients[key]


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


# ── Gemini (primary) ─────────────────────────────────────────────────────────

def _call_gemini(
    prompt: str, max_retries: int = GEMINI_MAX_RETRIES
) -> Tuple[Dict[str, Any], Dict[str, int]]:
    seq = _next_seq()
    # Disable thinking tokens: flash models consume output budget on internal reasoning;
    # we need all output tokens for JSON.
    # thinking_budget was added in google-genai ~1.7; guard against older versions.
    try:
        _thinking_cfg = types.ThinkingConfig(thinking_budget=0)
    except Exception:
        try:
            _thinking_cfg = types.ThinkingConfig()
        except Exception:
            _thinking_cfg = None
    config = types.GenerateContentConfig(
        max_output_tokens=GEMINI_MAX_OUTPUT_TOKENS,
        **({'thinking_config': _thinking_cfg} if _thinking_cfg is not None else {}),
    )

    models = list(GEMINI_MODEL_FALLBACK_CHAIN)
    last_exc: Exception = Exception(f"No models available (seq={seq})")

    for model in models:
        active_keys = [k for k in _get_available_gemini_keys() if k not in _exhausted_keys]
        if not active_keys:
            log.warning("gemini_all_keys_exhausted", seq=seq, model=model)
            break

        # Round-robin starting key for this seq; rotate through all active keys per model
        start = seq % len(active_keys)
        ordered_keys = active_keys[start:] + active_keys[:start]

        for key in ordered_keys:
            client = _get_gemini_client(key)
            key_prefix = key[:12]
            quota_exhausted = False

            for attempt in range(max_retries):
                log.info(
                    "gemini_request",
                    seq=seq,
                    attempt=attempt + 1,
                    max_retries=max_retries,
                    model=model,
                    key_prefix=key_prefix,
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
                        key_prefix=key_prefix,
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
                        key_prefix=key_prefix,
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
                            log.warning(
                                "gemini_daily_quota_exhausted",
                                seq=seq,
                                model=model,
                                key_prefix=key_prefix,
                                error=err_str[:300],
                            )
                            with _keys_lock:
                                _exhausted_keys.add(key)
                            quota_exhausted = True
                            break  # exit attempt loop → try next key
                        else:
                            # Per-minute rate limit — wait and retry same key/model
                            wait = GEMINI_RATE_LIMIT_BACKOFF_BASE * (attempt + 1)
                            log.warning(
                                "gemini_rate_limit",
                                seq=seq,
                                attempt=attempt + 1,
                                model=model,
                                key_prefix=key_prefix,
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
                            key_prefix=key_prefix,
                            error_type=type(e).__name__,
                            error=err_str[:300],
                        )
                        if attempt == max_retries - 1:
                            raise

            # If key hit daily quota, continue to next key (quota_exhausted flag set)
            # Otherwise all retries exhausted for this key — move to next key

    raise last_exc


# ── OpenAI fallback ───────────────────────────────────────────────────────────

def _call_openai(
    prompt: str, max_retries: int = 3
) -> Tuple[Dict[str, Any], Dict[str, int]]:
    from openai import OpenAI

    api_key = os.environ.get("GPT_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("GPT_API_KEY not set")

    client = OpenAI(api_key=api_key)
    model = "gpt-4o-mini"
    last_exc: Exception = Exception("OpenAI: no attempts made")

    for attempt in range(max_retries):
        log.info("openai_request", attempt=attempt + 1, model=model, prompt_chars=len(prompt))
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=8192,
                response_format={"type": "json_object"},
            )
            text = response.choices[0].message.content or ""
            usage_obj = response.usage
            usage: Dict[str, int] = {
                "input_tokens": getattr(usage_obj, "prompt_tokens", 0) or 0,
                "output_tokens": getattr(usage_obj, "completion_tokens", 0) or 0,
                "cached_tokens": 0,
            }
            log.info(
                "openai_response_ok",
                attempt=attempt + 1,
                model=model,
                input_tokens=usage["input_tokens"],
                output_tokens=usage["output_tokens"],
            )
            return _parse_json(text), usage

        except json.JSONDecodeError as e:
            log.warning("openai_json_parse_error", attempt=attempt + 1, error=str(e))
            last_exc = e
            if attempt == max_retries - 1:
                raise

        except Exception as e:
            err_str = str(e)
            last_exc = e
            log.warning(
                "openai_api_error",
                attempt=attempt + 1,
                error_type=type(e).__name__,
                error=err_str[:300],
            )
            if attempt == max_retries - 1:
                raise
            wait = 5 * (attempt + 1)
            time.sleep(wait)

    raise last_exc


# ── Anthropic fallback ────────────────────────────────────────────────────────

def _call_anthropic(
    prompt: str, max_retries: int = 3
) -> Tuple[Dict[str, Any], Dict[str, int]]:
    import anthropic as _anthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not set")

    client = _anthropic.Anthropic(api_key=api_key)
    model = "claude-haiku-4-5-20251001"
    system_prompt = (
        "You are a JSON generator. Always respond with valid JSON only — "
        "no markdown, no code fences, no explanation."
    )
    last_exc: Exception = Exception("Anthropic: no attempts made")

    for attempt in range(max_retries):
        log.info("anthropic_request", attempt=attempt + 1, model=model, prompt_chars=len(prompt))
        try:
            response = client.messages.create(
                model=model,
                max_tokens=8192,
                system=system_prompt,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text if response.content else ""
            usage_obj = response.usage
            usage: Dict[str, int] = {
                "input_tokens": getattr(usage_obj, "input_tokens", 0) or 0,
                "output_tokens": getattr(usage_obj, "output_tokens", 0) or 0,
                "cached_tokens": 0,
            }
            log.info(
                "anthropic_response_ok",
                attempt=attempt + 1,
                model=model,
                input_tokens=usage["input_tokens"],
                output_tokens=usage["output_tokens"],
            )
            return _parse_json(text), usage

        except json.JSONDecodeError as e:
            log.warning("anthropic_json_parse_error", attempt=attempt + 1, error=str(e))
            last_exc = e
            if attempt == max_retries - 1:
                raise

        except Exception as e:
            err_str = str(e)
            last_exc = e
            log.warning(
                "anthropic_api_error",
                attempt=attempt + 1,
                error_type=type(e).__name__,
                error=err_str[:300],
            )
            if attempt == max_retries - 1:
                raise
            wait = 5 * (attempt + 1)
            time.sleep(wait)

    raise last_exc


# ── Public entry point ────────────────────────────────────────────────────────

def call_gemini(
    prompt: str, max_retries: int = GEMINI_MAX_RETRIES
) -> Tuple[Dict[str, Any], Dict[str, int]]:
    """Try Gemini (all keys, round-robin) → OpenAI → Anthropic."""
    # Python 3 deletes `except X as var` after the block — save to plain vars.
    gemini_err: Exception = Exception("gemini not attempted")
    openai_err: Exception = Exception("openai not attempted")

    try:
        return _call_gemini(prompt, max_retries)
    except Exception as e:
        gemini_err = e
        log.warning(
            "gemini_all_keys_failed",
            error=str(e)[:300],
            trying_fallback="openai",
        )

    try:
        result, usage = _call_openai(prompt)
        log.info("openai_fallback_success")
        return result, usage
    except Exception as e:
        openai_err = e
        log.warning(
            "openai_fallback_failed",
            error=str(e)[:300],
            trying_fallback="anthropic",
        )

    try:
        result, usage = _call_anthropic(prompt)
        log.info("anthropic_fallback_success")
        return result, usage
    except Exception as e:
        log.error(
            "all_providers_failed",
            gemini=str(gemini_err)[:200],
            openai=str(openai_err)[:200],
            anthropic=str(e)[:200],
        )
        from .exceptions import LLMAPIError
        raise LLMAPIError(
            message="All LLM providers failed",
            detail=f"Gemini: {gemini_err} | OpenAI: {openai_err} | Anthropic: {e}",
        ) from e
