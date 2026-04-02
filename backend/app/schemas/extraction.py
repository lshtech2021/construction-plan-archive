from __future__ import annotations

import enum
from typing import Optional

from pydantic import BaseModel


class ZoneType(str, enum.Enum):
    title_block = "title_block"
    drawing_area = "drawing_area"
    notes = "notes"
    schedule = "schedule"
    legend = "legend"
    revision_block = "revision_block"
    general = "general"


class BoundingBox(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float


class DetectedZone(BaseModel):
    zone_type: ZoneType
    bbox: BoundingBox
    confidence: float = 0.0


class TitleBlockData(BaseModel):
    project_name: Optional[str] = None
    project_number: Optional[str] = None
    client_name: Optional[str] = None
    sheet_number: Optional[str] = None
    sheet_title: Optional[str] = None
    discipline_code: Optional[str] = None
    revision_number: Optional[str] = None
    revision_date: Optional[str] = None
    issue_date: Optional[str] = None
    drawn_by: Optional[str] = None
    checked_by: Optional[str] = None
    firm_name: Optional[str] = None
    scale: Optional[str] = None
    confidence: str = "medium"


class ScheduleRow(BaseModel):
    cells: list[str]


class ScheduleData(BaseModel):
    title: Optional[str] = None
    headers: list[str] = []
    rows: list[ScheduleRow] = []


class DrawingDescription(BaseModel):
    description: str = ""
    drawing_type: Optional[str] = None
    building_system: Optional[str] = None
    elements_shown: list[str] = []
    floor_or_area: Optional[str] = None
    notable_callouts: list[str] = []
    confidence: str = "medium"


class DisciplineClassification(BaseModel):
    discipline: str = "unknown"
    sheet_type: str = "unknown"
    confidence: str = "medium"
    reasoning: str = ""


class ZoneExtraction(BaseModel):
    zone_type: ZoneType
    bbox: Optional[BoundingBox] = None
    text_content: Optional[str] = None
    structured_data: Optional[dict] = None
    confidence: float = 0.0


class SheetExtractionResult(BaseModel):
    page_number: int
    title_block: TitleBlockData = TitleBlockData()
    discipline_classification: DisciplineClassification = DisciplineClassification()
    drawing_description: DrawingDescription = DrawingDescription()
    native_text: Optional[str] = None
    ocr_text: Optional[str] = None
    vlm_text: Optional[str] = None
    merged_text: Optional[str] = None
    zones: list[ZoneExtraction] = []
    schedules: list[ScheduleData] = []
    overall_confidence: str = "pending"
    extraction_warnings: list[str] = []
    needs_human_review: bool = False
    vlm_used: bool = False
    ocr_used: bool = False
    processing_time_seconds: float = 0.0


class ExtractionSummary(BaseModel):
    total_sheets: int
    by_discipline: dict
    by_confidence: dict
    needs_review_count: int
