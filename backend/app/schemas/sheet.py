from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models.sheet import Discipline, ExtractionConfidence, SheetType


class SheetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    page_number: int
    sheet_number: Optional[str] = None
    sheet_title: Optional[str] = None
    discipline: Discipline
    sheet_type: SheetType
    image_path: Optional[str] = None
    thumbnail_path: Optional[str] = None
    extraction_confidence: ExtractionConfidence
    needs_human_review: bool
    text_embedding_id: Optional[str] = None
    image_embedding_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class SheetList(BaseModel):
    items: list[SheetRead]
    total: int


class SheetDetail(SheetRead):
    native_text: Optional[str] = None
    ocr_text: Optional[str] = None
    vlm_description: Optional[str] = None
    merged_text: Optional[str] = None
