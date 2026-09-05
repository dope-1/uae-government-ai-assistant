"""Enable pgvector extension.

Revision ID: 0001
Revises:
Create Date: 2026-09-02
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")


def downgrade() -> None:
    # Deliberately preserve the extension: later vector columns may depend on it.
    pass
