"""Extraction API endpoints."""
from __future__ import annotations

import logging
import uuid
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_storage
from app.models.document import Document
from app.models.sheet import (
    Discipline,
    ExtractionConfidence,
    Sheet,
    SheetType,
)
from app.schemas.extraction import ExtractionSummary, SheetExtractionResult
from app.services.pipeline import ExtractionPipeline
from app.services.storage import StorageService
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Extraction"])


def _map_discipline(value: str) -> Discipline:
    try:
        return Discipline(value)
    except ValueError:
        return Discipline.unknown


def _map_sheet_type(value: str) -> SheetType:
    try:
        return SheetType(value)
    except ValueError:
        return SheetType.unknown


def _map_confidence(value: str) -> ExtractionConfidence:
    try:
        return ExtractionConfidence(value)
    except ValueError:
        return ExtractionConfidence.pending


async def _reprocess_sheet(
    sheet: Sheet,
    session: AsyncSession,
    storage: StorageService,
) -> SheetExtractionResult:
    """Download sheet image, run extraction pipeline, update sheet record."""
    if not sheet.image_path:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Sheet has no rendered image to process",
        )

    image_bytes = storage.download_file(settings.bucket_rendered_pages, sheet.image_path)
    pipeline = ExtractionPipeline(storage)
    extraction_result = await pipeline.process_sheet(
        image_bytes, sheet.native_text, sheet.page_number
    )

    # Update sheet fields from extraction result
    tb = extraction_result.title_block
    sheet.sheet_number = tb.sheet_number or sheet.sheet_number
    sheet.sheet_title = tb.sheet_title or sheet.sheet_title
    sheet.discipline = _map_discipline(extraction_result.discipline_classification.discipline)
    sheet.sheet_type = _map_sheet_type(extraction_result.discipline_classification.sheet_type)
    sheet.ocr_text = extraction_result.ocr_text
    sheet.vlm_description = extraction_result.vlm_text
    sheet.merged_text = extraction_result.merged_text
    sheet.extraction_confidence = _map_confidence(extraction_result.overall_confidence)
    sheet.needs_human_review = extraction_result.needs_human_review
    sheet.extraction_metadata = extraction_result.model_dump(
        include={
            "title_block",
            "discipline_classification",
            "drawing_description",
            "zones",
            "schedules",
            "extraction_warnings",
            "vlm_used",
            "ocr_used",
        }
    )
    sheet.processing_time_seconds = extraction_result.processing_time_seconds
    await session.commit()
    return extraction_result


@router.post("/sheets/{sheet_id}/reprocess", response_model=SheetExtractionResult)
async def reprocess_sheet(
    sheet_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    storage: StorageService = Depends(get_storage),
) -> SheetExtractionResult:
    """Reprocess a single sheet through the extraction pipeline."""
    result = await session.execute(select(Sheet).where(Sheet.id == sheet_id))
    sheet = result.scalar_one_or_none()
    if sheet is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sheet not found")

    return await _reprocess_sheet(sheet, session, storage)


@router.post("/documents/{document_id}/reprocess", status_code=status.HTTP_202_ACCEPTED)
async def reprocess_document(
    document_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db),
    storage: StorageService = Depends(get_storage),
) -> dict:
    """Reprocess all sheets in a document (background task)."""
    doc_result = await session.execute(select(Document).where(Document.id == document_id))
    document = doc_result.scalar_one_or_none()
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    background_tasks.add_task(_reprocess_document_bg, document_id, storage)
    return {"message": "Reprocessing started", "document_id": str(document_id)}


async def _reprocess_document_bg(document_id: uuid.UUID, storage: StorageService) -> None:
    """Background task to reprocess all sheets in a document."""
    from app.database import get_session

    async for session in get_session():
        try:
            sheets_result = await session.execute(
                select(Sheet).where(Sheet.document_id == document_id).order_by(Sheet.page_number)
            )
            sheets = sheets_result.scalars().all()
            pipeline = ExtractionPipeline(storage)
            for sheet in sheets:
                if not sheet.image_path:
                    continue
                try:
                    image_bytes = storage.download_file(
                        settings.bucket_rendered_pages, sheet.image_path
                    )
                    extraction_result = await pipeline.process_sheet(
                        image_bytes, sheet.native_text, sheet.page_number
                    )
                    tb = extraction_result.title_block
                    sheet.sheet_number = tb.sheet_number or sheet.sheet_number
                    sheet.sheet_title = tb.sheet_title or sheet.sheet_title
                    sheet.discipline = _map_discipline(
                        extraction_result.discipline_classification.discipline
                    )
                    sheet.sheet_type = _map_sheet_type(
                        extraction_result.discipline_classification.sheet_type
                    )
                    sheet.ocr_text = extraction_result.ocr_text
                    sheet.vlm_description = extraction_result.vlm_text
                    sheet.merged_text = extraction_result.merged_text
                    sheet.extraction_confidence = _map_confidence(
                        extraction_result.overall_confidence
                    )
                    sheet.needs_human_review = extraction_result.needs_human_review
                    sheet.extraction_metadata = extraction_result.model_dump(
                        include={
                            "title_block",
                            "discipline_classification",
                            "drawing_description",
                            "zones",
                            "schedules",
                            "extraction_warnings",
                            "vlm_used",
                            "ocr_used",
                        }
                    )
                    sheet.processing_time_seconds = extraction_result.processing_time_seconds
                    await session.commit()
                except Exception as exc:
                    logger.error(
                        "Error reprocessing sheet %s: %s", sheet.id, exc
                    )
        except Exception as exc:
            logger.error(
                "Error in background reprocessing for document %s: %s", document_id, exc
            )
        break  # get_session is an async generator; break after first session


@router.get("/sheets/{sheet_id}/extraction", response_model=SheetExtractionResult)
async def get_sheet_extraction(
    sheet_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> SheetExtractionResult:
    """Get extraction data for a sheet."""
    result = await session.execute(select(Sheet).where(Sheet.id == sheet_id))
    sheet = result.scalar_one_or_none()
    if sheet is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sheet not found")

    meta = sheet.extraction_metadata or {}
    try:
        tb = meta.get("title_block") or {}
        from app.schemas.extraction import TitleBlockData, DisciplineClassification, DrawingDescription, ZoneExtraction, ScheduleData
        return SheetExtractionResult(
            page_number=sheet.page_number,
            title_block=TitleBlockData(**{k: v for k, v in tb.items() if k in TitleBlockData.model_fields}) if tb else TitleBlockData(),
            discipline_classification=DisciplineClassification(
                **{k: v for k, v in (meta.get("discipline_classification") or {}).items() if k in DisciplineClassification.model_fields}
            ),
            drawing_description=DrawingDescription(
                **{k: v for k, v in (meta.get("drawing_description") or {}).items() if k in DrawingDescription.model_fields}
            ),
            native_text=sheet.native_text,
            ocr_text=sheet.ocr_text,
            vlm_text=sheet.vlm_description,
            merged_text=sheet.merged_text,
            zones=[ZoneExtraction(**z) for z in (meta.get("zones") or [])],
            schedules=[ScheduleData(**s) for s in (meta.get("schedules") or [])],
            overall_confidence=sheet.extraction_confidence.value if sheet.extraction_confidence else "pending",
            extraction_warnings=meta.get("extraction_warnings") or [],
            needs_human_review=sheet.needs_human_review,
            vlm_used=meta.get("vlm_used", False),
            ocr_used=meta.get("ocr_used", False),
            processing_time_seconds=sheet.processing_time_seconds or 0.0,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to build extraction result: {exc}",
        )


@router.get("/documents/{document_id}/extraction/summary", response_model=ExtractionSummary)
async def get_document_extraction_summary(
    document_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> ExtractionSummary:
    """Get extraction summary statistics for a document."""
    doc_result = await session.execute(select(Document).where(Document.id == document_id))
    if doc_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    sheets_result = await session.execute(
        select(Sheet).where(Sheet.document_id == document_id)
    )
    sheets = sheets_result.scalars().all()

    by_discipline: dict[str, int] = {}
    by_confidence: dict[str, int] = {}
    needs_review = 0

    for sheet in sheets:
        disc = sheet.discipline.value if sheet.discipline else "unknown"
        by_discipline[disc] = by_discipline.get(disc, 0) + 1
        conf = sheet.extraction_confidence.value if sheet.extraction_confidence else "pending"
        by_confidence[conf] = by_confidence.get(conf, 0) + 1
        if sheet.needs_human_review:
            needs_review += 1

    return ExtractionSummary(
        total_sheets=len(sheets),
        by_discipline=by_discipline,
        by_confidence=by_confidence,
        needs_review_count=needs_review,
    )
