from __future__ import annotations

import asyncio
import logging
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.schemas.search import (
    IndexingStatus,
    SearchRequest,
    SearchResponse,
    SimilarSheetsRequest,
    SearchResultItem,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/search", tags=["search"])


@router.post("", response_model=SearchResponse, summary="Hybrid / semantic / keyword search")
async def search(
    request: SearchRequest,
    session: AsyncSession = Depends(get_db),
) -> SearchResponse:
    """Search construction plan sheets using hybrid (semantic + keyword), pure semantic,
    or pure keyword search with optional facet filters."""
    from app.services.search.hybrid_search import hybrid_search_service
    return await hybrid_search_service.search(request, session)


@router.post("/similar", response_model=list[SearchResultItem], summary="Find similar sheets")
async def find_similar(
    request: SimilarSheetsRequest,
    session: AsyncSession = Depends(get_db),
) -> list[SearchResultItem]:
    """Return sheets visually or textually similar to the given sheet."""
    from app.services.search.hybrid_search import hybrid_search_service

    project_id = None
    if request.same_project_only:
        # Resolve project_id from the sheet
        from sqlalchemy import select
        from app.models.sheet import Sheet
        from app.models.document import Document
        result = await session.execute(
            select(Document.project_id)
            .join(Sheet, Sheet.document_id == Document.id)
            .where(Sheet.id == request.sheet_id)
        )
        row = result.first()
        if row:
            project_id = row[0]

    return await hybrid_search_service.find_similar(
        sheet_id=request.sheet_id,
        limit=request.limit,
        project_id=project_id,
    )


@router.get("/status", response_model=IndexingStatus, summary="Indexing statistics")
async def indexing_status(
    session: AsyncSession = Depends(get_db),
) -> IndexingStatus:
    """Return statistics about how many sheets have been indexed."""
    from app.services.indexing import indexing_service
    return await indexing_service.get_indexing_status(session)


@router.post(
    "/index/document/{document_id}",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Index a document's sheets",
)
async def index_document(
    document_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db),
):
    """Trigger background indexing for all sheets in the specified document."""
    from app.services.indexing import indexing_service

    background_tasks.add_task(_run_index_document, document_id)
    return {"message": f"Indexing started for document {document_id}"}


@router.post(
    "/index/all",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Full reindex of all sheets",
)
async def index_all(background_tasks: BackgroundTasks):
    """Trigger a full re-index of every sheet in the system."""
    background_tasks.add_task(_run_reindex_all)
    return {"message": "Full reindex started"}


# ---------------------------------------------------------------------------
# Background helpers (create their own DB sessions)
# ---------------------------------------------------------------------------

async def _run_index_document(document_id: uuid.UUID) -> None:
    try:
        from app.database import AsyncSessionLocal
        from app.services.indexing import indexing_service
        async with AsyncSessionLocal() as session:
            count = await indexing_service.index_document(session, document_id)
            logger.info("Indexed %d sheets for document %s", count, document_id)
    except Exception as exc:
        logger.error("Background index_document failed: %s", exc)


async def _run_reindex_all() -> None:
    try:
        from app.database import AsyncSessionLocal
        from app.services.indexing import indexing_service
        async with AsyncSessionLocal() as session:
            count = await indexing_service.reindex_all(session)
            logger.info("Full reindex completed: %d sheets indexed", count)
    except Exception as exc:
        logger.error("Background reindex_all failed: %s", exc)
