"""Add audit_log table (Sprint 5)

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-03-29

Changes:
- Create audit_log table for tracking user actions
- Indexes on action, user_id, timestamp, and composite (user_id, action)
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d5e6f7a8b9c0"
down_revision: Union[str, Sequence[str], None] = "c4d5e6f7a8b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "audit_log",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("action", sa.String(50), nullable=False, index=True),
        sa.Column("user_id", sa.String(), nullable=True, index=True),
        sa.Column("resource_id", sa.String(), nullable=True),
        sa.Column("resource_type", sa.String(50), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("request_id", sa.String(36), nullable=True),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            index=True,
        ),
    )
    op.create_index("idx_audit_user_action", "audit_log", ["user_id", "action"])


def downgrade() -> None:
    op.drop_index("idx_audit_user_action", table_name="audit_log")
    op.drop_table("audit_log")
