"""
Audit logging service (Sprint 5).

Provides a single ``record_audit`` function that writes to the audit_log table.
Designed to be best-effort: failures are logged but never raise to the caller.
"""
import json
import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.audit import AuditLog

log = get_logger("app.services.audit")


def record_audit(
    db: Session,
    *,
    action: str,
    user_id: Optional[str] = None,
    resource_id: Optional[str] = None,
    resource_type: Optional[str] = None,
    details: Optional[dict] = None,
    ip_address: Optional[str] = None,
    request_id: Optional[str] = None,
) -> None:
    """
    Write one row to audit_log.

    All keyword arguments are optional except ``action``.
    Failures are swallowed and logged so callers are never affected.
    """
    try:
        entry = AuditLog(
            id=str(uuid.uuid4()),
            action=action,
            user_id=user_id,
            resource_id=resource_id,
            resource_type=resource_type,
            details=json.dumps(details) if details else None,
            ip_address=ip_address,
            request_id=request_id,
        )
        db.add(entry)
        db.flush()  # write immediately but let caller's commit control the tx
    except Exception as exc:
        log.warning(
            "audit_write_failed",
            action=action,
            user_id=user_id,
            error=str(exc),
        )
