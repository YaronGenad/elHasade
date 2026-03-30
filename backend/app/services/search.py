"""
Search service (Sprint 4.5) — Postgres-native BM25 + pgvector.

Replaces the rank-bm25 / pickle / Redis-index approach with:
  1. BM25 via Postgres tsvector + GIN index  (search_exact)
  2. Cosine similarity via pgvector hnsw     (search_similar)

Both functions return lightweight dicts so callers never import Material
directly from this module.

plainto_tsquery is used instead of to_tsquery so that arbitrary multi-word
Hebrew / Arabic text works without manual operator injection.
"""
import re
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.services.cache import CacheService
from app.services.embeddings import embed_text, embedding_to_pg_literal

log = get_logger("app.services.search")

# ── constants ─────────────────────────────────────────────────────────────────

DEFAULT_SIMILARITY_THRESHOLD = 0.15  # cosine distance (lower = more similar)
DEFAULT_TOP_K = 5


# ── text helpers ──────────────────────────────────────────────────────────────

def normalize_query(text_: str) -> str:
    text_ = text_.lower().strip()
    return re.sub(r"\s+", " ", text_)


def build_query_text(subject: str, topic: str, grade: str, rounds: int) -> str:
    """Canonical query string (kept for search endpoint compatibility)."""
    return normalize_query(f"{subject} {topic} {grade} {rounds}")


# ── search functions ──────────────────────────────────────────────────────────

def search_exact(
    subject: str,
    topic: str,
    grade: str,
    db: Session,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """
    BM25 full-text search via Postgres tsvector.

    Returns up to *limit* materials whose fts_vector matches the query,
    sorted by BM25 rank DESC then approval_count DESC.
    """
    search_text = normalize_query(f"{subject} {topic} {grade}")
    if not search_text:
        return []

    try:
        rows = db.execute(
            text(
                """
                SELECT
                    m.id            AS material_id,
                    m.subject,
                    m.topic,
                    m.grade,
                    m.version,
                    m.approval_count,
                    m.times_served,
                    m.file_paths,
                    m.query_id,
                    ts_rank(m.fts_vector, plainto_tsquery('simple', :q)) AS rank
                FROM materials m
                WHERE m.fts_vector IS NOT NULL
                  AND m.fts_vector @@ plainto_tsquery('simple', :q)
                ORDER BY rank DESC, m.approval_count DESC
                LIMIT :lim
                """
            ),
            {"q": search_text, "lim": limit},
        ).fetchall()
    except (OperationalError, ProgrammingError) as exc:
        log.error("search_exact_sql_failed", query=search_text, error=str(exc))
        return []
    except Exception as exc:
        log.error("search_exact_unexpected_error", query=search_text, error=str(exc))
        return []

    return [
        {
            "material_id": r.material_id,
            "subject": r.subject,
            "topic": r.topic,
            "grade": r.grade,
            "version": r.version,
            "approval_count": r.approval_count,
            "times_served": r.times_served,
            "query_id": r.query_id,
            "bm25_rank": float(r.rank),
        }
        for r in rows
    ]


def search_similar(
    embedding_vector: List[float],
    db: Session,
    threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    """
    Semantic similarity search via pgvector cosine distance.

    Returns materials where cosine distance < *threshold*, sorted
    by ascending distance (closest first).
    """
    vec_literal = embedding_to_pg_literal(embedding_vector)

    try:
        rows = db.execute(
            text(
                """
                SELECT
                    m.id            AS material_id,
                    m.subject,
                    m.topic,
                    m.grade,
                    m.version,
                    m.approval_count,
                    m.times_served,
                    m.query_id,
                    m.embedding <=> CAST(:vec AS vector) AS distance
                FROM materials m
                WHERE m.embedding IS NOT NULL
                  AND m.embedding <=> CAST(:vec AS vector) < :threshold
                ORDER BY distance
                LIMIT :lim
                """
            ),
            {"vec": vec_literal, "threshold": threshold, "lim": limit},
        ).fetchall()
    except (OperationalError, ProgrammingError) as exc:
        log.error("search_similar_sql_failed", error=str(exc))
        return []
    except Exception as exc:
        log.error("search_similar_unexpected_error", error=str(exc))
        return []

    return [
        {
            "material_id": r.material_id,
            "subject": r.subject,
            "topic": r.topic,
            "grade": r.grade,
            "version": r.version,
            "approval_count": r.approval_count,
            "times_served": r.times_served,
            "query_id": r.query_id,
            "distance": float(r.distance),
        }
        for r in rows
    ]


# ── main search service ───────────────────────────────────────────────────────

class SearchService:
    """
    Stateless search service.

    Router order (per sprint 4.5 spec):
      Redis unit cache → BM25 tsvector → pgvector similarity
    """

    def __init__(self, cache_service: CacheService):
        self.cache = cache_service

    def find_exact(
        self, subject: str, topic: str, grade: str, db: Session
    ) -> List[Dict[str, Any]]:
        return search_exact(subject, topic, grade, db)

    def find_similar_by_text(
        self,
        subject: str,
        topic: str,
        grade: str,
        db: Session,
        threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    ) -> List[Dict[str, Any]]:
        """Embed the query text then run pgvector similarity search."""
        text_ = normalize_query(f"{subject} {topic} {grade}")
        embedding = embed_text(text_)
        if not embedding:
            return []
        return search_similar(embedding, db, threshold=threshold)

    def find_similar_for_search_endpoint(
        self,
        query_text: str,
        db: Session,
        top_k: int = DEFAULT_TOP_K,
        threshold: float = 0.3,
    ) -> List[Dict[str, Any]]:
        """
        Used by the /search endpoint.
        Runs BM25 first; if not enough results, also runs pgvector.
        Returns combined, de-duplicated list limited to top_k.
        """
        # Pass the full query_text as-is so multi-word Hebrew subjects/topics
        # are not mangled by splitting.  search_exact normalises internally.
        bm25_results = search_exact(query_text, "", "", db, limit=top_k)
        seen_ids = {r["material_id"] for r in bm25_results}

        # Fill remaining slots with pgvector results
        remaining = top_k - len(bm25_results)
        vec_results: List[Dict[str, Any]] = []
        if remaining > 0:
            embedding = embed_text(query_text)
            if embedding:
                vec_results = [
                    r for r in search_similar(
                        embedding, db, threshold=threshold, limit=remaining
                    )
                    if r["material_id"] not in seen_ids
                ]

        combined = bm25_results + vec_results
        # Add a unified score for the caller
        for r in bm25_results:
            r["similarity_score"] = round(r.get("bm25_rank", 0.0), 4)
        for r in vec_results:
            r["similarity_score"] = round(1.0 - r.get("distance", 1.0), 4)

        return combined[:top_k]


# ── dependency factories ──────────────────────────────────────────────────────

def create_cache_service() -> CacheService:
    return CacheService()


def create_search_service() -> SearchService:
    return SearchService(CacheService())
