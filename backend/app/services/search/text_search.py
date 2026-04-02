from __future__ import annotations

import logging
import uuid
from typing import Optional

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.project import Project
from app.models.sheet import Sheet

logger = logging.getLogger(__name__)

_SNIPPET_LENGTH = 300


def _make_snippet(merged_text: Optional[str], query: str) -> Optional[str]:
    """Return a short snippet from merged_text that contains query terms."""
    if not merged_text:
        return None
    lower = merged_text.lower()
    query_words = query.lower().split()
    idx = lower.find(query_words[0]) if query_words else -1
    if idx == -1:
        return merged_text[:_SNIPPET_LENGTH]
    start = max(0, idx - 50)
    return merged_text[start : start + _SNIPPET_LENGTH]


class TextSearchService:
    """PostgreSQL full-text search using tsvector / tsquery."""

    async def search(
        self,
        session: AsyncSession,
        query: str,
        limit: int = 20,
        offset: int = 0,
        project_id: Optional[uuid.UUID] = None,
        discipline: Optional[str] = None,
        sheet_type: Optional[str] = None,
    ) -> list[dict]:
        """Search sheets using PostgreSQL tsvector/tsquery on merged_text.

        Returns a list of dicts with sheet data and ts_rank score.
        """
        try:
            tsquery = func.plainto_tsquery("english", query)
            tsvector = func.to_tsvector("english", func.coalesce(Sheet.merged_text, ""))
            rank = func.ts_rank(tsvector, tsquery).label("rank")

            stmt = (
                select(
                    Sheet,
                    rank,
                    Document.original_filename,
                    Document.project_id.label("doc_project_id"),
                    Project.name.label("project_name"),
                )
                .join(Document, Sheet.document_id == Document.id)
                .join(Project, Document.project_id == Project.id)
                .where(tsvector.op("@@")(tsquery))
            )

            if project_id is not None:
                stmt = stmt.where(Document.project_id == project_id)
            if discipline:
                stmt = stmt.where(Sheet.discipline == discipline)
            if sheet_type:
                stmt = stmt.where(Sheet.sheet_type == sheet_type)

            stmt = stmt.order_by(rank.desc()).limit(limit).offset(offset)

            result = await session.execute(stmt)
            rows = result.fetchall()

            items = []
            for row in rows:
                sheet: Sheet = row[0]
                ts_rank: float = float(row[1]) if row[1] is not None else 0.0
                original_filename: str = row[2]
                doc_project_id: uuid.UUID = row[3]
                project_name: str = row[4]

                items.append({
                    "sheet_id": str(sheet.id),
                    "document_id": str(sheet.document_id),
                    "project_id": str(doc_project_id),
                    "page_number": sheet.page_number,
                    "sheet_number": sheet.sheet_number,
                    "sheet_title": sheet.sheet_title,
                    "discipline": sheet.discipline.value if sheet.discipline else None,
                    "sheet_type": sheet.sheet_type.value if sheet.sheet_type else None,
                    "thumbnail_path": sheet.thumbnail_path,
                    "image_path": sheet.image_path,
                    "keyword_score": ts_rank,
                    "snippet": _make_snippet(sheet.merged_text, query),
                    "project_name": project_name,
                    "document_filename": original_filename,
                    "extraction_confidence": sheet.extraction_confidence.value if sheet.extraction_confidence else None,
                })
            return items
        except Exception as exc:
            logger.error("Text search failed: %s", exc)
            return []


text_search_service = TextSearchService()
