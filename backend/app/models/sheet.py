from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.document import Document


class Discipline(str, enum.Enum):
    architectural = "architectural"
    structural = "structural"
    civil = "civil"
    mechanical = "mechanical"
    electrical = "electrical"
    plumbing = "plumbing"
    fire_protection = "fire_protection"
    landscape = "landscape"
    interior_design = "interior_design"
    specifications = "specifications"
    general = "general"
    other = "other"
    unknown = "unknown"


class SheetType(str, enum.Enum):
    floor_plan = "floor_plan"
    elevation = "elevation"
    section = "section"
    detail = "detail"
    schedule = "schedule"
    diagram = "diagram"
    reflected_ceiling_plan = "reflected_ceiling_plan"
    site_plan = "site_plan"
    one_line_diagram = "one_line_diagram"
    riser_diagram = "riser_diagram"
    cover_sheet = "cover_sheet"
    general_notes = "general_notes"
    other = "other"
    unknown = "unknown"


class ExtractionConfidence(str, enum.Enum):
    high = "high"
    medium = "medium"
    low = "low"
    failed = "failed"
    pending = "pending"


class Sheet(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "sheets"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    sheet_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    sheet_title: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    discipline: Mapped[Discipline] = mapped_column(
        Enum(Discipline, name="discipline"),
        default=Discipline.unknown,
        nullable=False,
    )
    sheet_type: Mapped[SheetType] = mapped_column(
        Enum(SheetType, name="sheettype"),
        default=SheetType.unknown,
        nullable=False,
    )
    image_path: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)
    thumbnail_path: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)
    native_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ocr_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    vlm_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    merged_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extraction_confidence: Mapped[ExtractionConfidence] = mapped_column(
        Enum(ExtractionConfidence, name="extractionconfidence"),
        default=ExtractionConfidence.pending,
        nullable=False,
    )
    needs_human_review: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    text_embedding_id: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    image_embedding_id: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    document: Mapped["Document"] = relationship("Document", back_populates="sheets")

    __table_args__ = (
        Index("ix_sheets_document_id", "document_id"),
    )
