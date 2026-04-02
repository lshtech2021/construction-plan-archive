from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.document import Document, ProcessingStatus
from app.models.sheet import Sheet
from app.services.pdf_processor import PDFProcessor
from app.services.storage import StorageService

logger = logging.getLogger(__name__)


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
                except Exception as exc:
                    logger.error(
                        "Error processing page %d of document %s: %s",
                        page_number,
                        document_id,
                        exc,
                    )

            document.processing_status = ProcessingStatus.completed
            await self.session.commit()
            logger.info("Document %s processing completed (%d pages)", document_id, page_count)

        except Exception as exc:
            logger.error("Document %s processing failed: %s", document_id, exc)
            document.processing_status = ProcessingStatus.failed
            document.processing_error = str(exc)
            await self.session.commit()
