"""Initial schema

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enums
    processingstatus = postgresql.ENUM(
        "pending", "processing", "completed", "failed",
        name="processingstatus",
    )
    processingstatus.create(op.get_bind(), checkfirst=True)

    discipline_enum = postgresql.ENUM(
        "architectural", "structural", "civil", "mechanical", "electrical",
        "plumbing", "fire_protection", "landscape", "interior_design",
        "specifications", "general", "other", "unknown",
        name="discipline",
    )
    discipline_enum.create(op.get_bind(), checkfirst=True)

    sheettype_enum = postgresql.ENUM(
        "floor_plan", "elevation", "section", "detail", "schedule", "diagram",
        "reflected_ceiling_plan", "site_plan", "one_line_diagram", "riser_diagram",
        "cover_sheet", "general_notes", "other", "unknown",
        name="sheettype",
    )
    sheettype_enum.create(op.get_bind(), checkfirst=True)

    extractionconfidence_enum = postgresql.ENUM(
        "high", "medium", "low", "failed", "pending",
        name="extractionconfidence",
    )
    extractionconfidence_enum.create(op.get_bind(), checkfirst=True)

    # projects table
    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("client", sa.String(500), nullable=True),
        sa.Column("location", sa.String(500), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_projects_name", "projects", ["name"])

    # documents table
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("original_filename", sa.String(1000), nullable=False),
        sa.Column("stored_path", sa.String(2000), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger, nullable=False),
        sa.Column("page_count", sa.Integer, nullable=True),
        sa.Column(
            "processing_status",
            sa.Enum(
                "pending", "processing", "completed", "failed",
                name="processingstatus",
                create_type=False,
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("processing_error", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_documents_project_id", "documents", ["project_id"])
    op.create_index("ix_documents_processing_status", "documents", ["processing_status"])

    # sheets table
    op.create_table(
        "sheets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("page_number", sa.Integer, nullable=False),
        sa.Column("sheet_number", sa.String(100), nullable=True),
        sa.Column("sheet_title", sa.String(1000), nullable=True),
        sa.Column(
            "discipline",
            sa.Enum(
                "architectural", "structural", "civil", "mechanical", "electrical",
                "plumbing", "fire_protection", "landscape", "interior_design",
                "specifications", "general", "other", "unknown",
                name="discipline",
                create_type=False,
            ),
            nullable=False,
            server_default="unknown",
        ),
        sa.Column(
            "sheet_type",
            sa.Enum(
                "floor_plan", "elevation", "section", "detail", "schedule", "diagram",
                "reflected_ceiling_plan", "site_plan", "one_line_diagram", "riser_diagram",
                "cover_sheet", "general_notes", "other", "unknown",
                name="sheettype",
                create_type=False,
            ),
            nullable=False,
            server_default="unknown",
        ),
        sa.Column("image_path", sa.String(2000), nullable=True),
        sa.Column("thumbnail_path", sa.String(2000), nullable=True),
        sa.Column("native_text", sa.Text, nullable=True),
        sa.Column("ocr_text", sa.Text, nullable=True),
        sa.Column("vlm_description", sa.Text, nullable=True),
        sa.Column("merged_text", sa.Text, nullable=True),
        sa.Column(
            "extraction_confidence",
            sa.Enum(
                "high", "medium", "low", "failed", "pending",
                name="extractionconfidence",
                create_type=False,
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("needs_human_review", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("text_embedding_id", sa.String(500), nullable=True),
        sa.Column("image_embedding_id", sa.String(500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_sheets_document_id", "sheets", ["document_id"])


def downgrade() -> None:
    op.drop_table("sheets")
    op.drop_table("documents")
    op.drop_table("projects")

    op.execute("DROP TYPE IF EXISTS extractionconfidence")
    op.execute("DROP TYPE IF EXISTS sheettype")
    op.execute("DROP TYPE IF EXISTS discipline")
    op.execute("DROP TYPE IF EXISTS processingstatus")
