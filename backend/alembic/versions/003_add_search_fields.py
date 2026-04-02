"""Add GIN index for full-text search on sheets.merged_text

Revision ID: 003
Revises: 002
Create Date: 2024-06-01 00:00:00.000000
"""
from __future__ import annotations

from alembic import op

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_sheets_merged_text_fts
        ON sheets
        USING gin(to_tsvector('english', COALESCE(merged_text, '')))
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_sheets_merged_text_fts")
