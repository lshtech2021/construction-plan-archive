from __future__ import annotations

import logging
import uuid
from typing import Any, Optional

logger = logging.getLogger(__name__)


class VectorStore:
    """Qdrant vector database operations."""

    def __init__(self) -> None:
        self._client = None

    def _get_client(self):
        if self._client is None:
            from qdrant_client import QdrantClient  # type: ignore
            from app.config import settings
            self._client = QdrantClient(
                host=settings.qdrant_host,
                port=settings.qdrant_http_port,
                timeout=10.0,
            )
        return self._client

    async def ensure_collections(self) -> None:
        """Create Qdrant collections with appropriate indexes if they don't exist."""
        from qdrant_client.models import (  # type: ignore
            Distance,
            FieldCondition,
            PayloadSchemaType,
            VectorParams,
        )
        from app.config import settings

        client = self._get_client()

        text_exists = False
        image_exists = False
        try:
            collections = client.get_collections().collections
            names = {c.name for c in collections}
            text_exists = settings.qdrant_text_collection in names
            image_exists = settings.qdrant_image_collection in names
        except Exception as exc:
            logger.warning("Could not list Qdrant collections: %s", exc)
            return

        if not text_exists:
            try:
                client.create_collection(
                    collection_name=settings.qdrant_text_collection,
                    vectors_config=VectorParams(
                        size=settings.embedding_dimension,
                        distance=Distance.COSINE,
                    ),
                )
                # Create payload indexes for filtering
                for field in ("project_id", "discipline", "sheet_type", "document_id"):
                    client.create_payload_index(
                        collection_name=settings.qdrant_text_collection,
                        field_name=field,
                        field_schema=PayloadSchemaType.KEYWORD,
                    )
                logger.info("Created Qdrant text collection: %s", settings.qdrant_text_collection)
            except Exception as exc:
                logger.warning("Could not create text collection: %s", exc)

        if not image_exists:
            try:
                client.create_collection(
                    collection_name=settings.qdrant_image_collection,
                    vectors_config=VectorParams(
                        size=settings.image_embedding_dimension,
                        distance=Distance.COSINE,
                    ),
                )
                for field in ("project_id", "discipline", "sheet_type", "document_id"):
                    client.create_payload_index(
                        collection_name=settings.qdrant_image_collection,
                        field_name=field,
                        field_schema=PayloadSchemaType.KEYWORD,
                    )
                logger.info("Created Qdrant image collection: %s", settings.qdrant_image_collection)
            except Exception as exc:
                logger.warning("Could not create image collection: %s", exc)

    def _build_filter(
        self,
        project_id: Optional[uuid.UUID] = None,
        discipline: Optional[str] = None,
        sheet_type: Optional[str] = None,
    ) -> Optional[Any]:
        """Build a Qdrant filter from optional facets."""
        from qdrant_client.models import Filter, FieldCondition, MatchValue  # type: ignore

        conditions = []
        if project_id is not None:
            conditions.append(FieldCondition(key="project_id", match=MatchValue(value=str(project_id))))
        if discipline:
            conditions.append(FieldCondition(key="discipline", match=MatchValue(value=discipline)))
        if sheet_type:
            conditions.append(FieldCondition(key="sheet_type", match=MatchValue(value=sheet_type)))

        if not conditions:
            return None
        return Filter(must=conditions)

    def upsert_text_embedding(
        self,
        sheet_id: uuid.UUID,
        vector: list[float],
        payload: dict,
    ) -> str:
        """Upsert a text embedding to the text collection. Returns the point ID."""
        from qdrant_client.models import PointStruct  # type: ignore
        from app.config import settings

        point_id = str(sheet_id)
        client = self._get_client()
        client.upsert(
            collection_name=settings.qdrant_text_collection,
            points=[PointStruct(id=point_id, vector=vector, payload=payload)],
        )
        return point_id

    def upsert_image_embedding(
        self,
        sheet_id: uuid.UUID,
        vector: list[float],
        payload: dict,
    ) -> str:
        """Upsert an image embedding to the image collection. Returns the point ID."""
        from qdrant_client.models import PointStruct  # type: ignore
        from app.config import settings

        point_id = str(sheet_id)
        client = self._get_client()
        client.upsert(
            collection_name=settings.qdrant_image_collection,
            points=[PointStruct(id=point_id, vector=vector, payload=payload)],
        )
        return point_id

    def search_text(
        self,
        query_vector: list[float],
        limit: int = 20,
        project_id: Optional[uuid.UUID] = None,
        discipline: Optional[str] = None,
        sheet_type: Optional[str] = None,
        score_threshold: float = 0.0,
    ) -> list[dict]:
        """Search the text collection by vector similarity."""
        from app.config import settings

        client = self._get_client()
        query_filter = self._build_filter(project_id, discipline, sheet_type)

        results = client.search(
            collection_name=settings.qdrant_text_collection,
            query_vector=query_vector,
            limit=limit,
            query_filter=query_filter,
            score_threshold=score_threshold,
            with_payload=True,
        )
        return [{"id": str(r.id), "score": r.score, "payload": r.payload} for r in results]

    def search_image(
        self,
        query_vector: list[float],
        limit: int = 20,
        project_id: Optional[uuid.UUID] = None,
        discipline: Optional[str] = None,
        sheet_type: Optional[str] = None,
        score_threshold: float = 0.0,
    ) -> list[dict]:
        """Search the image collection by vector similarity."""
        from app.config import settings

        client = self._get_client()
        query_filter = self._build_filter(project_id, discipline, sheet_type)

        results = client.search(
            collection_name=settings.qdrant_image_collection,
            query_vector=query_vector,
            limit=limit,
            query_filter=query_filter,
            score_threshold=score_threshold,
            with_payload=True,
        )
        return [{"id": str(r.id), "score": r.score, "payload": r.payload} for r in results]

    def search_similar(
        self,
        sheet_id: uuid.UUID,
        limit: int = 10,
        project_id: Optional[uuid.UUID] = None,
        use_text: bool = True,
    ) -> list[dict]:
        """Find similar sheets using the Qdrant recommend API."""
        from app.config import settings

        client = self._get_client()
        collection = settings.qdrant_text_collection if use_text else settings.qdrant_image_collection
        query_filter = self._build_filter(project_id)
        point_id = str(sheet_id)

        results = client.recommend(
            collection_name=collection,
            positive=[point_id],
            limit=limit,
            query_filter=query_filter,
            with_payload=True,
        )
        return [{"id": str(r.id), "score": r.score, "payload": r.payload} for r in results]

    def get_collection_count(self, collection_name: str) -> int:
        """Return the number of vectors in a collection."""
        try:
            client = self._get_client()
            info = client.get_collection(collection_name=collection_name)
            return info.points_count or 0
        except Exception:
            return 0

    def check_connection(self) -> bool:
        """Return True if Qdrant is reachable."""
        try:
            client = self._get_client()
            client.get_collections()
            return True
        except Exception:
            return False

    def delete_embedding(self, sheet_id: uuid.UUID, collection: str) -> None:
        """Delete a point from a collection."""
        try:
            from qdrant_client.models import PointIdsList  # type: ignore
            client = self._get_client()
            client.delete(
                collection_name=collection,
                points_selector=PointIdsList(points=[str(sheet_id)]),
            )
        except Exception as exc:
            logger.warning("Could not delete embedding for sheet %s: %s", sheet_id, exc)


vector_store = VectorStore()
