"""Add pgvector, fts_vector, approval fields (Sprint 4.5)

Revision ID: c4d5e6f7a8b9
Revises: 6c639cdb729d
Create Date: 2026-03-26

Changes:
- Enable pgvector extension
- materials: add subject, topic, grade, approval_count, times_served, embedding (vector 768), fts_vector (tsvector)
- materials: add GIN index on fts_vector, HNSW index on embedding
- materials: add trigger to auto-update fts_vector on INSERT/UPDATE
- users: add school column
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c4d5e6f7a8b9"
down_revision: Union[str, Sequence[str], None] = "6c639cdb729d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    dialect = op.get_context().dialect.name

    # ── materials: denormalised search fields (all dialects) ──────────────────
    op.add_column("materials", sa.Column("subject", sa.String(100), nullable=True))
    op.add_column("materials", sa.Column("topic", sa.String(255), nullable=True))
    op.add_column("materials", sa.Column("grade", sa.String(20), nullable=True))

    # ── materials: approval / usage counters (all dialects) ───────────────────
    op.add_column(
        "materials",
        sa.Column("approval_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "materials",
        sa.Column("times_served", sa.Integer(), nullable=False, server_default="0"),
    )

    # ── users: school (all dialects) ──────────────────────────────────────────
    op.add_column("users", sa.Column("school", sa.String(200), nullable=True))

    if dialect == "postgresql":
        # pgvector extension
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")

        # Postgres-native column types
        op.execute("ALTER TABLE materials ADD COLUMN IF NOT EXISTS embedding vector(768)")
        op.execute("ALTER TABLE materials ADD COLUMN IF NOT EXISTS fts_vector tsvector")

        # Indexes
        op.execute(
            "CREATE INDEX IF NOT EXISTS idx_materials_fts "
            "ON materials USING gin(fts_vector)"
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS idx_materials_vec "
            "ON materials USING hnsw(embedding vector_cosine_ops)"
        )

        # Trigger: auto-update fts_vector on insert/update
        op.execute(
            """
            CREATE OR REPLACE FUNCTION update_material_fts_vector()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.fts_vector := to_tsvector(
                    'simple',
                    COALESCE(NEW.subject, '') || ' ' ||
                    COALESCE(NEW.topic,   '') || ' ' ||
                    COALESCE(NEW.grade,   '')
                );
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql
            """
        )
        op.execute(
            """
            CREATE OR REPLACE TRIGGER materials_fts_trigger
                BEFORE INSERT OR UPDATE ON materials
                FOR EACH ROW EXECUTE FUNCTION update_material_fts_vector()
            """
        )
    else:
        # SQLite fallback: TEXT columns (no vector search, no FTS trigger)
        op.add_column("materials", sa.Column("embedding", sa.Text(), nullable=True))
        op.add_column("materials", sa.Column("fts_vector", sa.Text(), nullable=True))


def downgrade() -> None:
    dialect = op.get_context().dialect.name

    if dialect == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS materials_fts_trigger ON materials")
        op.execute("DROP FUNCTION IF EXISTS update_material_fts_vector()")
        op.execute("DROP INDEX IF EXISTS idx_materials_vec")
        op.execute("DROP INDEX IF EXISTS idx_materials_fts")
        op.execute("ALTER TABLE materials DROP COLUMN IF EXISTS fts_vector")
        op.execute("ALTER TABLE materials DROP COLUMN IF EXISTS embedding")
    else:
        op.drop_column("materials", "fts_vector")
        op.drop_column("materials", "embedding")

    op.drop_column("users", "school")
    op.drop_column("materials", "times_served")
    op.drop_column("materials", "approval_count")
    op.drop_column("materials", "grade")
    op.drop_column("materials", "topic")
    op.drop_column("materials", "subject")
