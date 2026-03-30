"""
Materials API — approve / reject / versions (Sprint 4.5).

POST /materials/{id}/approve   — approval_count++ + times_served++
POST /materials/{id}/reject    — times_served++, signals caller to regenerate
GET  /materials/versions       — ?subject=X&topic=Y&grade=Z → all versions sorted by approval_count DESC
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.logging import get_logger
from app.db.session import get_db
from app.models.material import Material
from app.models.user import User
from app.schemas.generation import (
    MaterialApprovalResponse,
    MaterialVersionItem,
    MaterialVersionsResponse,
)
from app.services.audit import record_audit
from app.services.cache import CacheService

router = APIRouter()
log = get_logger("app.api.materials")


def _get_material_or_404(material_id: str, db: Session) -> Material:
    material = db.query(Material).filter(Material.id == material_id).first()
    if not material:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Material {material_id} not found",
        )
    return material


@router.post("/{material_id}/approve", response_model=MaterialApprovalResponse)
def approve_material(
    material_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Teacher approves a material.

    - approval_count += 1
    - times_served   += 1
    - Redis unit cache is refreshed with the updated approval-sorted ID list
      so subsequent requests get the most-approved version first.
    """
    material = _get_material_or_404(material_id, db)

    material.approval_count = (material.approval_count or 0) + 1
    material.times_served = (material.times_served or 0) + 1
    db.commit()
    db.refresh(material)

    # Refresh Redis: re-sort all versions for this subject/topic/grade by approval_count
    if material.subject and material.topic and material.grade:
        _refresh_unit_cache(
            material.subject, material.topic, material.grade, db
        )

    log.info("material_approved", material_id=material_id, user_id=current_user.id, approval_count=material.approval_count)
    record_audit(
        db,
        action="approve",
        user_id=current_user.id,
        resource_id=material_id,
        resource_type="material",
        details={"approval_count": material.approval_count},
        ip_address=request.client.host if request.client else None,
        request_id=getattr(request.state, "request_id", None),
    )
    return MaterialApprovalResponse(
        status="approved",
        material_id=material.id,
        approval_count=material.approval_count,
    )


@router.post("/{material_id}/reject", response_model=MaterialApprovalResponse)
def reject_material(
    material_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Teacher rejects a material (wants a different version).

    - times_served += 1
    - Returns next_action=generate_new so the frontend can call
      POST /generations/ with force_new=true.
    """
    material = _get_material_or_404(material_id, db)

    material.times_served = (material.times_served or 0) + 1
    db.commit()

    log.info("material_rejected", material_id=material_id, user_id=current_user.id)
    record_audit(
        db,
        action="reject",
        user_id=current_user.id,
        resource_id=material_id,
        resource_type="material",
        ip_address=request.client.host if request.client else None,
        request_id=getattr(request.state, "request_id", None),
    )
    return MaterialApprovalResponse(
        status="rejected",
        material_id=material.id,
        approval_count=material.approval_count,
    )


@router.get("/versions", response_model=MaterialVersionsResponse)
def get_material_versions(
    subject: str,
    topic: str,
    grade: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return all known versions for a given subject/topic/grade,
    sorted by approval_count DESC so the best version is first.
    """
    materials = (
        db.query(Material)
        .filter(
            Material.subject == subject,
            Material.topic == topic,
            Material.grade == grade,
        )
        .order_by(Material.approval_count.desc(), Material.version.asc())
        .all()
    )

    return MaterialVersionsResponse(
        subject=subject,
        topic=topic,
        grade=grade,
        versions=[
            MaterialVersionItem(
                material_id=m.id,
                version=m.version or 1,
                approval_count=m.approval_count or 0,
                times_served=m.times_served or 0,
                subject=m.subject or "",
                topic=m.topic or "",
                grade=m.grade or "",
                created_at=m.created_at,
            )
            for m in materials
        ],
    )


# ── helpers ───────────────────────────────────────────────────────────────────

def _refresh_unit_cache(subject: str, topic: str, grade: str, db: Session) -> None:
    """Re-query DB for the approval-sorted ID list and write it to Redis."""
    try:
        materials = (
            db.query(Material)
            .filter(
                Material.subject == subject,
                Material.topic == topic,
                Material.grade == grade,
            )
            .order_by(Material.approval_count.desc())
            .all()
        )
        ids = [m.id for m in materials]
        if ids:
            cache = CacheService()
            cache.set_unit_ids(subject, topic, grade, ids)
    except Exception as exc:
        log.warning("unit_cache_refresh_failed", subject=subject, topic=topic, grade=grade, error=str(exc))
