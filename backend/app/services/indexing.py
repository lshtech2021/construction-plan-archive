from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.document import Document
from app.models.project import Project
from app.models.sheet import Sheet
from app.schemas.search import IndexingStatus

logger = logging.getLogger(__name__)


class IndexingService:
    """Background service to generate embeddings and upsert them to Qdrant."""

    async def index_sheet(self, session: AsyncSession, sheet_id: uuid.UUID) -> bool:
        """Index a single sheet. Returns True on success."""
        try:
            result = await session.execute(
                select(Sheet, Document, Project)
                .join(Document, Sheet.document_id == Document.id)
                .join(Project, Document.project_id == Project.id)
                .where(Sheet.id == sheet_id)
            )
            row = result.first()
            if row is None:
                logger.warning("Sheet %s not found for indexing", sheet_id)
                return False

            sheet: Sheet = row[0]
            document: Document = row[1]
            project: Project = row[2]

            text = sheet.merged_text or sheet.native_text or sheet.ocr_text or ""
            if not text.strip():
                logger.debug("Sheet %s has no text, skipping text embedding", sheet_id)
                return False

            from app.services.embeddings.embedding_service import embedding_service
            embeddings = await embedding_service.generate_sheet_embeddings(
                sheet_id=sheet_id,
                text=text,
            )

            payload = {
                "sheet_id": str(sheet.id),
                "document_id": str(sheet.document_id),
                "project_id": str(document.project_id),
                "page_number": sheet.page_number,
                "sheet_number": sheet.sheet_number,
                "sheet_title": sheet.sheet_title,
                "discipline": sheet.discipline.value if sheet.discipline else None,
                "sheet_type": sheet.sheet_type.value if sheet.sheet_type else None,
                "thumbnail_path": sheet.thumbnail_path,
                "image_path": sheet.image_path,
                "project_name": project.name,
                "document_filename": document.original_filename,
                "extraction_confidence": sheet.extraction_confidence.value if sheet.extraction_confidence else None,
            }

            text_vector = embeddings.get("text_vector")
            if text_vector:
                from app.services.search.vector_store import vector_store
                point_id = vector_store.upsert_text_embedding(
                    sheet_id=sheet_id,
                    vector=text_vector,
                    payload=payload,
                )
                sheet.text_embedding_id = point_id
                await session.commit()
                logger.debug("Indexed sheet %s into Qdrant", sheet_id)

            return True
        except Exception as exc:
            logger.error("Indexing failed for sheet %s: %s", sheet_id, exc)
            return False

    async def index_document(self, session: AsyncSession, document_id: uuid.UUID) -> int:
        """Index all sheets in a document. Returns count of successfully indexed sheets."""
        result = await session.execute(
            select(Sheet.id).where(Sheet.document_id == document_id)
        )
        sheet_ids = [row[0] for row in result.fetchall()]

        count = 0
        for sheet_id in sheet_ids:
            success = await self.index_sheet(session, sheet_id)
            if success:
                count += 1
        return count

    async def reindex_all(self, session: AsyncSession) -> int:
        """Re-index all sheets in the database. Returns count of indexed sheets."""
        result = await session.execute(select(Sheet.id))
        sheet_ids = [row[0] for row in result.fetchall()]

        count = 0
        for sheet_id in sheet_ids:
            success = await self.index_sheet(session, sheet_id)
            if success:
                count += 1
        return count

    async def get_indexing_status(self, session: AsyncSession) -> IndexingStatus:
        """Return indexing statistics."""
        total_result = await session.execute(select(func.count(Sheet.id)))
        total_sheets = total_result.scalar() or 0

        indexed_result = await session.execute(
            select(func.count(Sheet.id)).where(Sheet.text_embedding_id.isnot(None))
        )
        indexed_sheets = indexed_result.scalar() or 0

        text_collection_count = 0
        image_collection_count = 0
        try:
            from app.services.search.vector_store import vector_store
            text_collection_count = vector_store.get_collection_count(settings.qdrant_text_collection)
            image_collection_count = vector_store.get_collection_count(settings.qdrant_image_collection)
        except Exception as exc:
            logger.warning("Could not get Qdrant collection counts: %s", exc)

        return IndexingStatus(
            total_sheets=total_sheets,
            indexed_sheets=indexed_sheets,
            pending_sheets=total_sheets - indexed_sheets,
            text_collection_count=text_collection_count,
            image_collection_count=image_collection_count,
        )


indexing_service = IndexingService()
