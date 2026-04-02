from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models.document import ProcessingStatus


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    original_filename: str
    stored_path: str
    file_size_bytes: int
    page_count: Optional[int] = None
    processing_status: ProcessingStatus
    processing_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class DocumentUploadResponse(BaseModel):
    id: uuid.UUID
    original_filename: str
    file_size_bytes: int
    processing_status: ProcessingStatus
    message: str


class DocumentStatusResponse(BaseModel):
    id: uuid.UUID
    processing_status: ProcessingStatus
    page_count: Optional[int] = None
    processing_error: Optional[str] = None
    sheets_processed: int


class DocumentList(BaseModel):
    items: list[DocumentRead]
    total: int
