"""
Gemini Embeddings service (Sprint 4.5).

Computes 768-dimensional text embeddings via Gemini text-embedding-004.
Returns None gracefully when the API key is missing or the call fails so
callers can proceed without blocking generation.
"""
import os
from typing import List, Optional

from app.core.logging import get_logger

log = get_logger("app.services.embeddings")

_gemini_client = None


def _get_gemini_client():
    global _gemini_client
    if _gemini_client is None:
        try:
            from google import genai  # google-genai >= 1.0.0

            api_key = os.environ.get("GEMINI_API_KEY", "")
            if not api_key:
                log.warning("embed_gemini_key_missing")
                return None
            _gemini_client = genai.Client(api_key=api_key)
        except ImportError:
            log.warning("embed_google_genai_not_installed")
            return None
        except Exception as exc:
            log.error("embed_client_init_failed", exc_info=True)
            return None
    return _gemini_client


def embed_text(text: str) -> Optional[List[float]]:
    """
    Return a 768-float embedding for *text*, or None on any failure.

    The embedding is computed with Gemini text-embedding-004.
    Callers should treat None as "embedding unavailable" and skip
    pgvector features gracefully.
    """
    client = _get_gemini_client()
    if client is None:
        return None
    try:
        result = client.models.embed_content(
            model="models/text-embedding-004",
            contents=text,
        )
        return list(result.embeddings[0].values)
    except Exception as exc:
        log.error("embed_text_failed", text_preview=text[:80], error=str(exc))
        return None


def embedding_to_pg_literal(embedding: List[float]) -> str:
    """Convert a float list to the Postgres vector literal '[0.1,0.2,...]'."""
    if not embedding:
        log.warning("embedding_to_pg_literal_empty_input")
        return "[]"
    return "[" + ",".join(str(v) for v in embedding) + "]"
