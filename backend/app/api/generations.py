import json
import os
import uuid
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.config import settings
from app.core.logging import get_logger
from app.db.session import SessionLocal, get_db
from app.models.material import Material
from app.models.query import Query
from app.models.user import User
from app.schemas.generation import (
    GenerationListResponse,
    GenerationRequest,
    GenerationResponse,
    GenerationStatusResponse,
)
from app.services.cache import CacheService
from app.services.embeddings import embed_text, embedding_to_pg_literal
from app.services.generation import GenerationService, create_generation_service
from app.services.audit import record_audit
from app.services.search import SearchService, build_query_text, create_search_service

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)
log = get_logger("app.api.generations")


def process_generation_task(
    query_id: str,
    user_input: dict,
    generation_service: GenerationService,
    query_hash: str,
) -> None:
    """
    Background task – runs the full generation pipeline.
    Creates its own DB session (request session is closed before this runs).
    On completion caches the result and invalidates the BM25 index.
    """
    db = SessionLocal()
    try:
        db_query = db.query(Query).filter(Query.id == query_id).first()
        if not db_query:
            log.warning("generation_task_query_not_found", query_id=query_id)
            return

        log.info("generation_task_start", query_id=query_id, subject=user_input.get("subject"), topic=user_input.get("topic"))
        db_query.status = "processing"
        db.commit()

        result = generation_service.generate_materials(user_input)

        db_query.status = result.get("status", "failed")
        db_query.result = json.dumps(result) if result.get("status") == "completed" else None
        db_query.error_message = result.get("error") if result.get("status") == "failed" else None

        if result.get("status") == "completed":
            log.info("generation_task_completed", query_id=query_id)
            db_query.completed_at = datetime.utcnow()
            material_id = str(uuid.uuid4())
            material = Material(
                id=material_id,
                query_id=query_id,
                content_json=json.dumps(result.get("results", {})),
                file_paths=json.dumps(result.get("files", {})),
                version=1,
                subject=user_input.get("subject", ""),
                topic=user_input.get("topic", ""),
                grade=user_input.get("grade", ""),
            )
            db.add(material)
            db.flush()  # trigger fires → fts_vector populated automatically

            log.info("generation_task_embedding_start", query_id=query_id, material_id=material_id)
            # Compute and store embedding (best-effort; non-blocking on failure)
            embed_input = (
                f"{user_input.get('subject', '')} "
                f"{user_input.get('topic', '')} "
                f"{user_input.get('grade', '')}"
            ).strip()
            embedding = embed_text(embed_input)
            if embedding:
                db.execute(
                    text(
                        "UPDATE materials SET embedding = CAST(:vec AS vector) "
                        "WHERE id = :mid"
                    ),
                    {"vec": embedding_to_pg_literal(embedding), "mid": material_id},
                )

            db.commit()

            log.info("generation_task_caching", query_id=query_id, query_hash=query_hash)
            cache = CacheService()
            cache.cache_query(query_hash, result)
            # Update unit cache so the next identical request hits Redis
            cache.set_unit_ids(
                user_input.get("subject", ""),
                user_input.get("topic", ""),
                user_input.get("grade", ""),
                [material_id],
            )
            cache.update_hot_units(
                user_input.get("subject", ""),
                user_input.get("topic", ""),
                user_input.get("grade", ""),
            )
        else:
            log.warning("generation_task_failed_result", query_id=query_id, error=result.get("error"))
            db.commit()

    except Exception as exc:
        log.error("generation_task_failed", query_id=query_id, error=str(exc), exc_info=True)
        try:
            db.rollback()
            db_query = db.query(Query).filter(Query.id == query_id).first()
            if db_query:
                db_query.status = "failed"
                db_query.error_message = str(exc)
                db.commit()
        except Exception as inner_exc:
            log.error("generation_task_persist_error_failed", query_id=query_id, error=str(inner_exc), exc_info=True)
    finally:
        db.close()


@router.post("/", response_model=GenerationResponse, status_code=status.HTTP_202_ACCEPTED)
@limiter.limit(settings.GENERATION_RATE_LIMIT)
async def create_generation(
    request: Request,
    generation_request: GenerationRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    generation_service: GenerationService = Depends(create_generation_service),
    search_service: SearchService = Depends(create_search_service),
):
    """
    Submit a generation request.

    Flow:
    1. Exact Redis cache hit  → return immediately (from_cache=True).
    2. BM25 similar queries   → returned as ``similar_queries`` suggestions.
    3. Queue background task  → return 202 with status=pending.

    Pass ``force_new=true`` to skip steps 1–2.
    """
    cache = search_service.cache
    query_hash = CacheService.query_hash(
        generation_request.subject,
        generation_request.topic,
        generation_request.grade,
        generation_request.rounds,
    )

    log.info("generation_request", user_id=current_user.id, subject=generation_request.subject, topic=generation_request.topic, grade=generation_request.grade, force_new=generation_request.force_new)
    # ── 1. Redis unit cache hit ───────────────────────────────────────────────
    if not generation_request.force_new:
        cached_ids = cache.get_unit_ids(
            generation_request.subject,
            generation_request.topic,
            generation_request.grade,
        )
        if cached_ids:
            # Best approved material is first in list
            material = db.query(Material).filter(Material.id == cached_ids[0]).first()
            if material:
                # Log the query as a cache-hit record
                db_query = Query(
                    id=str(uuid.uuid4()),
                    user_id=current_user.id,
                    subject=generation_request.subject,
                    topic=generation_request.topic,
                    grade=generation_request.grade,
                    rounds=generation_request.rounds,
                    query_text=build_query_text(
                        generation_request.subject,
                        generation_request.topic,
                        generation_request.grade,
                        generation_request.rounds,
                    ),
                    status="completed",
                    result=material.content_json
                    if isinstance(material.content_json, str)
                    else json.dumps(material.content_json),
                    completed_at=datetime.utcnow(),
                )
                db.add(db_query)
                # Increment times_served
                material.times_served = (material.times_served or 0) + 1
                try:
                    db.commit()
                except OperationalError as exc:
                    db.rollback()
                    log.error("cache_hit_commit_failed", error=str(exc))
                    raise HTTPException(status_code=503, detail="Database temporarily unavailable")
                cache.update_hot_units(
                    generation_request.subject,
                    generation_request.topic,
                    generation_request.grade,
                )
                log.info("generation_cache_hit", query_id=db_query.id, material_id=material.id)
                return GenerationResponse(
                    generation_id=db_query.id,
                    status="completed",
                    message="Returned from cache (unit cache hit). Files are ready.",
                    from_cache=True,
                )

    # ── 2. BM25 tsvector search ───────────────────────────────────────────────
    query_text = build_query_text(
        generation_request.subject,
        generation_request.topic,
        generation_request.grade,
        generation_request.rounds,
    )
    similar = []
    if not generation_request.force_new:
        bm25_hits = search_service.find_exact(
            generation_request.subject,
            generation_request.topic,
            generation_request.grade,
            db,
        )
        if bm25_hits:
            # Return the top BM25 result immediately as a completed response
            top = bm25_hits[0]
            material = db.query(Material).filter(
                Material.id == top["material_id"]
            ).first()
            if material:
                db_query = Query(
                    id=str(uuid.uuid4()),
                    user_id=current_user.id,
                    subject=generation_request.subject,
                    topic=generation_request.topic,
                    grade=generation_request.grade,
                    rounds=generation_request.rounds,
                    query_text=query_text,
                    status="completed",
                    result=material.content_json
                    if isinstance(material.content_json, str)
                    else json.dumps(material.content_json),
                    completed_at=datetime.utcnow(),
                )
                db.add(db_query)
                material.times_served = (material.times_served or 0) + 1
                try:
                    db.commit()
                except OperationalError as exc:
                    db.rollback()
                    log.error("bm25_hit_commit_failed", error=str(exc))
                    raise HTTPException(status_code=503, detail="Database temporarily unavailable")
                # Warm Redis for next request
                cache.set_unit_ids(
                    generation_request.subject,
                    generation_request.topic,
                    generation_request.grade,
                    [material.id],
                )
                cache.update_hot_units(
                    generation_request.subject,
                    generation_request.topic,
                    generation_request.grade,
                )
                log.info("generation_bm25_hit", query_id=db_query.id, material_id=material.id)
                return GenerationResponse(
                    generation_id=db_query.id,
                    status="completed",
                    message="Found via full-text search. Files are ready.",
                    from_cache=True,
                )

        # ── 3. pgvector similarity ─────────────────────────────────────────────
        vec_hits = search_service.find_similar_by_text(
            generation_request.subject,
            generation_request.topic,
            generation_request.grade,
            db,
        )
        if vec_hits:
            top = vec_hits[0]
            material = db.query(Material).filter(
                Material.id == top["material_id"]
            ).first()
            if material:
                db_query = Query(
                    id=str(uuid.uuid4()),
                    user_id=current_user.id,
                    subject=generation_request.subject,
                    topic=generation_request.topic,
                    grade=generation_request.grade,
                    rounds=generation_request.rounds,
                    query_text=query_text,
                    status="completed",
                    result=material.content_json
                    if isinstance(material.content_json, str)
                    else json.dumps(material.content_json),
                    completed_at=datetime.utcnow(),
                )
                db.add(db_query)
                material.times_served = (material.times_served or 0) + 1
                try:
                    db.commit()
                except OperationalError as exc:
                    db.rollback()
                    log.error("vector_hit_commit_failed", error=str(exc))
                    raise HTTPException(status_code=503, detail="Database temporarily unavailable")
                log.info("generation_vector_hit", query_id=db_query.id, material_id=material.id)
                return GenerationResponse(
                    generation_id=db_query.id,
                    status="completed",
                    message="Found via semantic similarity. Files are ready.",
                    from_cache=True,
                )

        # Surface BM25 suggestions to frontend even when we're about to generate
        similar = [
            {
                "generation_id": h["query_id"],
                "subject": h["subject"],
                "topic": h["topic"],
                "grade": h["grade"],
                "rounds": generation_request.rounds,
                "similarity_score": h.get("bm25_rank", 0.0),
                "created_at": None,
                "status": "completed",
            }
            for h in bm25_hits[:3]
        ]

    # ── 3. Queue background generation ───────────────────────────────────────
    db_query = Query(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        subject=generation_request.subject,
        topic=generation_request.topic,
        grade=generation_request.grade,
        rounds=generation_request.rounds,
        query_text=query_text,
        status="pending",
    )
    db.add(db_query)
    try:
        db.commit()
        db.refresh(db_query)
    except OperationalError as exc:
        db.rollback()
        log.error("generation_queue_commit_failed", error=str(exc))
        raise HTTPException(status_code=503, detail="Database temporarily unavailable")

    log.info("generation_queued", query_id=db_query.id, subject=generation_request.subject, topic=generation_request.topic)
    record_audit(
        db,
        action="generate",
        user_id=current_user.id,
        resource_id=db_query.id,
        resource_type="query",
        details={
            "subject": generation_request.subject,
            "topic": generation_request.topic,
            "grade": generation_request.grade,
            "rounds": generation_request.rounds,
            "from_cache": False,
        },
        ip_address=request.client.host if request.client else None,
        request_id=getattr(request.state, "request_id", None),
    )
    background_tasks.add_task(
        process_generation_task,
        db_query.id,
        {
            "subject": generation_request.subject,
            "topic": generation_request.topic,
            "grade": generation_request.grade,
            "rounds": generation_request.rounds,
        },
        generation_service,
        query_hash,
    )

    return GenerationResponse(
        generation_id=db_query.id,
        status="pending",
        message="Generation started. Poll GET /generations/{id} for status.",
        from_cache=False,
        similar_queries=similar,
    )


@router.get("/", response_model=GenerationListResponse)
def list_generations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 10,
    offset: int = 0,
):
    """List the current user's generation history."""
    queries = (
        db.query(Query)
        .filter(Query.user_id == current_user.id)
        .order_by(Query.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return GenerationListResponse(
        generations=[
            {
                "generation_id": q.id,
                "status": q.status,
                "created_at": q.created_at,
                "completed_at": q.completed_at,
                "subject": q.subject,
                "topic": q.topic,
                "grade": q.grade,
                "rounds": q.rounds,
            }
            for q in queries
        ],
        limit=limit,
        offset=offset,
    )


@router.get("/{generation_id}", response_model=GenerationStatusResponse)
def get_generation(
    generation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get generation status and results by ID."""
    query = (
        db.query(Query)
        .filter(Query.id == generation_id, Query.user_id == current_user.id)
        .first()
    )
    if not query:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Generation not found")

    material = (
        db.query(Material).filter(Material.query_id == query.id).first()
        if query.status == "completed"
        else None
    )

    return GenerationStatusResponse(
        generation_id=query.id,
        status=query.status,
        created_at=query.created_at,
        completed_at=query.completed_at,
        subject=query.subject,
        topic=query.topic,
        grade=query.grade,
        rounds=query.rounds,
        result=json.loads(query.result) if query.result else None,
        error=query.error_message,
        material_id=material.id if material else None,
    )


@router.get("/{generation_id}/download/{file_type}")
def download_file(
    generation_id: str,
    file_type: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Download a generated file (student_pdf, teacher_pdf, or round{n}_<type>)."""
    query = (
        db.query(Query)
        .filter(Query.id == generation_id, Query.user_id == current_user.id)
        .first()
    )
    if not query:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Generation not found")

    if query.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Generation is not completed yet (status: {query.status})",
        )

    material = db.query(Material).filter(Material.query_id == query.id).first()
    if not material:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No materials found for this generation",
        )

    try:
        file_paths = json.loads(material.file_paths) if material.file_paths else {}
    except (json.JSONDecodeError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Invalid file paths data in database",
        )

    file_path = None
    if file_type in ("student_pdf", "teacher_pdf"):
        file_path = file_paths.get(file_type)
    elif file_type.startswith("round"):
        parts = file_type.split("_", 1)
        if len(parts) == 2 and parts[0][5:].isdigit():
            round_num = int(parts[0][5:])
            sub_type = parts[1]
            for round_file in file_paths.get("rounds", []):
                if round_file.get("round") == round_num:
                    file_path = round_file.get(sub_type)
                    break

    if not file_path or not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found for type: {file_type}",
        )

    return FileResponse(
        path=file_path,
        filename=os.path.basename(file_path),
        media_type="application/octet-stream",
    )
