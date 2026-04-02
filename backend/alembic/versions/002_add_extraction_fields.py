"""Add extraction_metadata and processing_time_seconds to sheets

Revision ID: 002
Revises: 001
Create Date: 2024-06-01 00:00:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sheets",
        sa.Column("extraction_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "sheets",
        sa.Column("processing_time_seconds", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("sheets", "processing_time_seconds")
    op.drop_column("sheets", "extraction_metadata")
