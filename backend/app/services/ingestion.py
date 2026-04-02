from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.document import Document, ProcessingStatus
from app.models.sheet import Discipline, ExtractionConfidence, Sheet, SheetType
from app.services.pdf_processor import PDFProcessor
from app.services.storage import StorageService

logger = logging.getLogger(__name__)


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


class IngestionService:
    def __init__(self, session: AsyncSession, storage: StorageService) -> None:
        self.session = session
        self.storage = storage
        self.pdf_processor = PDFProcessor(storage)

    async def process_document(self, document_id: uuid.UUID) -> None:
        result = await self.session.execute(
            select(Document).where(Document.id == document_id)
        )
        document = result.scalar_one_or_none()
        if document is None:
            logger.error("Document %s not found", document_id)
            return

        try:
            document.processing_status = ProcessingStatus.processing
            await self.session.commit()

            # Download original PDF from MinIO
            pdf_bytes = self.storage.download_file(
                settings.bucket_original_pdfs,
                document.stored_path,
            )

            # Get page count
            page_count = self.pdf_processor.get_page_count(pdf_bytes)
            document.page_count = page_count
            await self.session.commit()

            # Process each page
            project_id = str(document.project_id)
            doc_id = str(document.id)

            sheets: list[Sheet] = []
            page_images: dict[int, bytes] = {}

            for page_number in range(page_count):
                try:
                    page_data = self.pdf_processor.process_page(
                        pdf_bytes,
                        page_number,
                        project_id,
                        doc_id,
                    )
                    sheet = Sheet(
                        document_id=document.id,
                        page_number=page_number,
                        image_path=page_data["image_path"],
                        thumbnail_path=page_data["thumbnail_path"],
                        native_text=page_data["native_text"] or None,
                    )
                    self.session.add(sheet)
                    sheets.append(sheet)
                    if page_data.get("image_bytes"):
                        page_images[page_number] = page_data["image_bytes"]
                except Exception as exc:
                    logger.error(
                        "Error processing page %d of document %s: %s",
                        page_number,
                        document_id,
                        exc,
                    )

            # Commit rendered sheets before extraction so they are persisted
            # even if the extraction pipeline fails.
            await self.session.commit()

            # Run extraction pipeline if enabled
            if settings.extraction_enabled and sheets:
                await self._run_extraction(sheets, page_images, project_id, doc_id)

            document.processing_status = ProcessingStatus.completed
            await self.session.commit()
            logger.info("Document %s processing completed (%d pages)", document_id, page_count)

        except Exception as exc:
            logger.error("Document %s processing failed: %s", document_id, exc)
            document.processing_status = ProcessingStatus.failed
            document.processing_error = str(exc)
            await self.session.commit()

    async def _run_extraction(
        self,
        sheets: list[Sheet],
        page_images: dict[int, bytes],
        project_id: str,
        doc_id: str,
    ) -> None:
        """Run the extraction pipeline on all sheets that have images."""
        from app.services.pipeline import ExtractionPipeline

        pipeline = ExtractionPipeline(self.storage)
        for sheet in sheets:
            try:
                # Get image bytes — either from in-memory cache or MinIO
                image_bytes: bytes | None = page_images.get(sheet.page_number)
                if image_bytes is None and sheet.image_path:
                    try:
                        image_bytes = self.storage.download_file(
                            settings.bucket_rendered_pages, sheet.image_path
                        )
                    except Exception as exc:
                        logger.warning(
                            "Could not download image for sheet page %d: %s",
                            sheet.page_number,
                            exc,
                        )
                if image_bytes is None:
                    continue

                extraction_result = await pipeline.process_sheet(
                    image_bytes, sheet.native_text, sheet.page_number
                )

                tb = extraction_result.title_block
                if tb.sheet_number:
                    sheet.sheet_number = tb.sheet_number
                if tb.sheet_title:
                    sheet.sheet_title = tb.sheet_title
                sheet.discipline = _map_discipline(
                    extraction_result.discipline_classification.discipline
                )
                sheet.sheet_type = _map_sheet_type(
                    extraction_result.discipline_classification.sheet_type
                )
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
                await self.session.commit()
            except Exception as exc:
                logger.error(
                    "Extraction failed for sheet page %d: %s", sheet.page_number, exc
                )

        # Trigger embedding indexing for all sheets after extraction (non-blocking)
        await self._index_sheets(sheets)

    async def _index_sheets(self, sheets: list[Sheet]) -> None:
        """Trigger embedding generation for sheets. Failures do not propagate."""
        try:
            from app.services.indexing import indexing_service
            for sheet in sheets:
                if sheet.id is not None:
                    try:
                        await indexing_service.index_sheet(self.session, sheet.id)
                    except Exception as exc:
                        logger.warning(
                            "Non-fatal: indexing failed for sheet page %d: %s",
                            sheet.page_number,
                            exc,
                        )
        except Exception as exc:
            logger.warning("Non-fatal: sheet indexing step failed: %s", exc)
