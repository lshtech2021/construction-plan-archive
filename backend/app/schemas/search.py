from __future__ import annotations

import enum
import uuid
from typing import Any, Optional

from pydantic import BaseModel, Field


class SearchMode(str, enum.Enum):
    semantic = "semantic"
    keyword = "keyword"
    hybrid = "hybrid"


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    mode: SearchMode = SearchMode.hybrid
    project_id: Optional[uuid.UUID] = None
    discipline: Optional[str] = None
    sheet_type: Optional[str] = None
    min_confidence: Optional[str] = None
    limit: int = Field(20, ge=1, le=100)
    offset: int = Field(0, ge=0)
    semantic_weight: Optional[float] = Field(None, ge=0.0, le=1.0)
    keyword_weight: Optional[float] = Field(None, ge=0.0, le=1.0)
    min_score: Optional[float] = Field(None, ge=0.0, le=1.0)


class SearchResultItem(BaseModel):
    sheet_id: uuid.UUID
    document_id: uuid.UUID
    project_id: uuid.UUID
    page_number: int
    sheet_number: Optional[str] = None
    sheet_title: Optional[str] = None
    discipline: Optional[str] = None
    sheet_type: Optional[str] = None
    thumbnail_path: Optional[str] = None
    image_path: Optional[str] = None
    score: float
    semantic_score: Optional[float] = None
    keyword_score: Optional[float] = None
    snippet: Optional[str] = None
    highlight: Optional[str] = None
    project_name: Optional[str] = None
    document_filename: Optional[str] = None
    extraction_confidence: Optional[str] = None


class SearchResponse(BaseModel):
    query: str
    mode: SearchMode
    total: int
    limit: int
    offset: int
    results: list[SearchResultItem]
    search_time_ms: float
    semantic_results_count: int = 0
    keyword_results_count: int = 0
    filters_applied: dict[str, Any] = Field(default_factory=dict)


class IndexingStatus(BaseModel):
    total_sheets: int
    indexed_sheets: int
    pending_sheets: int
    text_collection_count: int
    image_collection_count: int


class SimilarSheetsRequest(BaseModel):
    sheet_id: uuid.UUID
    limit: int = Field(10, ge=1, le=50)
    same_project_only: bool = False
