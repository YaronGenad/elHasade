"""
Audit log model (Sprint 5).

Records significant user actions for compliance and debugging:
login, generate, approve, reject, download.
"""
from sqlalchemy import Column, String, DateTime, Text, Index
from sqlalchemy.sql import func

from app.db.base import Base


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(String, primary_key=True, index=True)  # UUID as string
    action = Column(String(50), nullable=False, index=True)  # login, generate, approve, reject, download
    user_id = Column(String, nullable=True, index=True)  # FK-like but not enforced (user may be deleted)
    resource_id = Column(String, nullable=True)  # query_id, material_id, etc.
    resource_type = Column(String(50), nullable=True)  # query, material, user
    details = Column(Text, nullable=True)  # JSON string with extra context
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    request_id = Column(String(36), nullable=True)  # X-Request-ID for correlation
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    __table_args__ = (
        Index("idx_audit_user_action", "user_id", "action"),
    )
