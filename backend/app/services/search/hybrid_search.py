from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.schemas.search import SearchMode, SearchRequest, SearchResponse, SearchResultItem

logger = logging.getLogger(__name__)


class HybridSearchService:
    """Orchestrates semantic (Qdrant) + keyword (PostgreSQL FTS) search with RRF fusion."""

    async def search(
        self,
        request: SearchRequest,
        session: AsyncSession,
    ) -> SearchResponse:
        start_time = time.monotonic()

        semantic_weight = request.semantic_weight if request.semantic_weight is not None else settings.search_semantic_weight
        keyword_weight = request.keyword_weight if request.keyword_weight is not None else settings.search_keyword_weight
        min_score = request.min_score if request.min_score is not None else settings.search_min_score

        semantic_raw: list[dict] = []
        keyword_raw: list[dict] = []

        # Run semantic and keyword search in parallel where possible
        if request.mode in (SearchMode.semantic, SearchMode.hybrid):
            # Over-fetch to have more candidates for fusion
            _prefetch_factor = 5
            semantic_raw = await self._semantic_search(
                query=request.query,
                project_id=request.project_id,
                discipline=request.discipline,
                sheet_type=request.sheet_type,
                limit=min(request.limit * _prefetch_factor, settings.search_max_limit),
            )

        if request.mode in (SearchMode.keyword, SearchMode.hybrid):
            _prefetch_factor = 5
            from app.services.search.text_search import text_search_service
            keyword_raw = await text_search_service.search(
                session=session,
                query=request.query,
                limit=min(request.limit * _prefetch_factor, settings.search_max_limit),
                offset=0,
                project_id=request.project_id,
                discipline=request.discipline,
                sheet_type=request.sheet_type,
            )

        # Fuse results
        if request.mode == SearchMode.semantic:
            fused = semantic_raw
            for item in fused:
                item["score"] = item.get("semantic_score", item.get("score", 0.0))
        elif request.mode == SearchMode.keyword:
            fused = keyword_raw
            for item in fused:
                item["score"] = item.get("keyword_score", item.get("score", 0.0))
        else:
            # Hybrid — RRF fusion
            if settings.search_enable_reranking:
                from app.services.search.reranker import reciprocal_rank_fusion
                fused = reciprocal_rank_fusion(
                    semantic_results=semantic_raw,
                    keyword_results=keyword_raw,
                    semantic_weight=semantic_weight,
                    keyword_weight=keyword_weight,
                    min_score=min_score,
                )
            else:
                # Simple merge by score
                merged: dict[str, dict] = {}
                for item in semantic_raw:
                    merged[item["sheet_id"]] = item
                for item in keyword_raw:
                    sid = item["sheet_id"]
                    if sid not in merged:
                        merged[sid] = item
                fused = sorted(merged.values(), key=lambda x: x.get("score", 0.0), reverse=True)

        # Filter by min_score
        if min_score > 0:
            fused = [f for f in fused if f.get("score", 0.0) >= min_score]

        total = len(fused)
        page = fused[request.offset : request.offset + request.limit]

        results = [_to_result_item(item) for item in page]
        elapsed_ms = (time.monotonic() - start_time) * 1000

        filters_applied = {}
        if request.project_id:
            filters_applied["project_id"] = str(request.project_id)
        if request.discipline:
            filters_applied["discipline"] = request.discipline
        if request.sheet_type:
            filters_applied["sheet_type"] = request.sheet_type

        return SearchResponse(
            query=request.query,
            mode=request.mode,
            total=total,
            limit=request.limit,
            offset=request.offset,
            results=results,
            search_time_ms=round(elapsed_ms, 2),
            semantic_results_count=len(semantic_raw),
            keyword_results_count=len(keyword_raw),
            filters_applied=filters_applied,
        )

    async def _semantic_search(
        self,
        query: str,
        project_id: Optional[uuid.UUID],
        discipline: Optional[str],
        sheet_type: Optional[str],
        limit: int,
    ) -> list[dict]:
        """Embed query and search Qdrant. Degrades gracefully on failure."""
        try:
            from app.services.embeddings.embedding_service import embedding_service
            query_vector = await embedding_service.embed_query(query)
            if query_vector is None:
                return []

            from app.services.search.vector_store import vector_store
            raw = vector_store.search_text(
                query_vector=query_vector,
                limit=limit,
                project_id=project_id,
                discipline=discipline,
                sheet_type=sheet_type,
                score_threshold=0.0,
            )
            return [_qdrant_to_dict(r) for r in raw]
        except Exception as exc:
            logger.warning("Semantic search failed, falling back to keyword-only: %s", exc)
            return []

    async def find_similar(
        self,
        sheet_id: uuid.UUID,
        limit: int,
        project_id: Optional[uuid.UUID],
    ) -> list[SearchResultItem]:
        """Find sheets similar to the given sheet using Qdrant recommend."""
        try:
            from app.services.search.vector_store import vector_store
            raw = vector_store.search_similar(
                sheet_id=sheet_id,
                limit=limit,
                project_id=project_id,
                use_text=True,
            )
            return [_to_result_item(_qdrant_to_dict(r)) for r in raw]
        except Exception as exc:
            logger.warning("Similar search failed: %s", exc)
            return []


def _qdrant_to_dict(r: dict) -> dict:
    payload = r.get("payload") or {}
    return {
        "sheet_id": r["id"],
        "document_id": payload.get("document_id"),
        "project_id": payload.get("project_id"),
        "page_number": payload.get("page_number", 0),
        "sheet_number": payload.get("sheet_number"),
        "sheet_title": payload.get("sheet_title"),
        "discipline": payload.get("discipline"),
        "sheet_type": payload.get("sheet_type"),
        "thumbnail_path": payload.get("thumbnail_path"),
        "image_path": payload.get("image_path"),
        "semantic_score": r.get("score", 0.0),
        "score": r.get("score", 0.0),
        "project_name": payload.get("project_name"),
        "document_filename": payload.get("document_filename"),
        "extraction_confidence": payload.get("extraction_confidence"),
    }


def _to_result_item(item: dict) -> SearchResultItem:
    return SearchResultItem(
        sheet_id=uuid.UUID(item["sheet_id"]) if isinstance(item.get("sheet_id"), str) else item["sheet_id"],
        document_id=uuid.UUID(item["document_id"]) if isinstance(item.get("document_id"), str) else item["document_id"],
        project_id=uuid.UUID(item["project_id"]) if isinstance(item.get("project_id"), str) else item["project_id"],
        page_number=item.get("page_number", 0),
        sheet_number=item.get("sheet_number"),
        sheet_title=item.get("sheet_title"),
        discipline=item.get("discipline"),
        sheet_type=item.get("sheet_type"),
        thumbnail_path=item.get("thumbnail_path"),
        image_path=item.get("image_path"),
        score=item.get("score", 0.0),
        semantic_score=item.get("semantic_score"),
        keyword_score=item.get("keyword_score"),
        snippet=item.get("snippet"),
        highlight=item.get("highlight"),
        project_name=item.get("project_name"),
        document_filename=item.get("document_filename"),
        extraction_confidence=item.get("extraction_confidence"),
    )


hybrid_search_service = HybridSearchService()
