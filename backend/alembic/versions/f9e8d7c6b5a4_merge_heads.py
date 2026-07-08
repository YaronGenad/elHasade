"""Merge heads: is_active_to_users, audit_log, token_cost_to_queries

Revision ID: f9e8d7c6b5a4
Revises: a1b2c3d4e5f6, d5e6f7a8b9c0, e1f2a3b4c5d6
Create Date: 2026-05-25
"""
from typing import Sequence, Union

revision: str = "f9e8d7c6b5a4"
down_revision: Union[str, Sequence[str], None] = (
    "a1b2c3d4e5f6",
    "d5e6f7a8b9c0",
    "e1f2a3b4c5d6",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
