"""
Similarity-search endpoint (Sprint 4.5).

GET /search/?q=<text>&top_k=5&threshold=0.3
Returns materials similar to the query via BM25 tsvector + pgvector.

Replaces the old rank-bm25 / rebuild-index approach.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.logging import get_logger
from app.db.session import get_db
from app.models.user import User
from app.services.search import (
    DEFAULT_SIMILARITY_THRESHOLD,
    DEFAULT_TOP_K,
    SearchService,
    build_query_text,
    create_search_service,
    normalize_query,
)

router = APIRouter()
log = get_logger("app.api.search")


@router.get("/")
def search_similar(
    q: str = Query(..., min_length=1, description="Free-text query"),
    subject: str = Query(default="", description="Filter: subject"),
    topic: str = Query(default="", description="Filter: topic"),
    grade: str = Query(default="", description="Filter: grade"),
    rounds: int = Query(default=4, ge=1, le=10),
    top_k: int = Query(default=DEFAULT_TOP_K, ge=1, le=20),
    threshold: float = Query(default=DEFAULT_SIMILARITY_THRESHOLD, ge=0.0, le=1.0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    search_service: SearchService = Depends(create_search_service),
):
    """
    Find past materials similar to the provided query.

    Pass `q` as a free-text string OR use `subject`/`topic`/`grade` which will
    be concatenated automatically.  Results combine BM25 and pgvector ranking.
    """
    if subject or topic or grade:
        query_text = build_query_text(subject, topic, grade, rounds)
    else:
        query_text = normalize_query(q)

    results = search_service.find_similar_for_search_endpoint(
        query_text=query_text,
        db=db,
        top_k=top_k,
        threshold=threshold,
    )

    log.info("search_complete", query=query_text, results_count=len(results), top_k=top_k, threshold=threshold)
    return {
        "query": query_text,
        "threshold": threshold,
        "count": len(results),
        "results": results,
    }
