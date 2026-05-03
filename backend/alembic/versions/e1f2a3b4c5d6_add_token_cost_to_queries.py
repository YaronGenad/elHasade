"""Add input_tokens, output_tokens, cost_usd to queries (Sprint 1-B)

Revision ID: e1f2a3b4c5d6
Revises: c4d5e6f7a8b9
Create Date: 2026-03-31

Changes:
- queries: add input_tokens (Integer, nullable)
- queries: add output_tokens (Integer, nullable)
- queries: add cost_usd (Float, nullable)
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e1f2a3b4c5d6"
down_revision: Union[str, Sequence[str], None] = "c4d5e6f7a8b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("queries", sa.Column("input_tokens", sa.Integer(), nullable=True))
    op.add_column("queries", sa.Column("output_tokens", sa.Integer(), nullable=True))
    op.add_column("queries", sa.Column("cost_usd", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("queries", "cost_usd")
    op.drop_column("queries", "output_tokens")
    op.drop_column("queries", "input_tokens")
