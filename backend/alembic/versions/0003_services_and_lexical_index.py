"""Add structured services and lexical retrieval index.

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-02
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "services",
        sa.Column("id", sa.String(length=120), primary_key=True),
        sa.Column("service_name", sa.Text(), nullable=False),
        sa.Column("authority", sa.String(length=255), nullable=False),
        sa.Column("jurisdiction", sa.String(length=80), nullable=False),
        sa.Column("category", sa.String(length=120), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("requirements", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("documents", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("fees", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("official_url", sa.Text(), nullable=False),
        sa.Column("last_verified", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "source_id",
            sa.String(length=120),
            sa.ForeignKey("sources.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_services_service_name", "services", ["service_name"])
    op.create_index("ix_services_jurisdiction", "services", ["jurisdiction"])
    op.create_index("ix_services_source_id", "services", ["source_id"])
    op.execute(
        "CREATE INDEX ix_document_chunks_text_fts ON document_chunks "
        "USING gin (to_tsvector('simple', text))"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_text_fts")
    op.drop_table("services")
