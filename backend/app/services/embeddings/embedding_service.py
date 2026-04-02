from __future__ import annotations

import logging
import uuid
from typing import Optional

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Coordinates text and image embedding generation for sheets."""

    async def generate_sheet_embeddings(
        self,
        sheet_id: uuid.UUID,
        text: Optional[str],
        image_bytes: Optional[bytes] = None,
    ) -> dict:
        """Generate text and optionally image embeddings for a sheet.

        Returns a dict with 'text_vector' and 'image_vector' keys.
        Each value is a list[float] or None if generation failed/skipped.
        """
        result: dict = {"text_vector": None, "image_vector": None}

        if text:
            try:
                from app.services.embeddings.text_embedder import get_text_embedder
                embedder = get_text_embedder()
                result["text_vector"] = await embedder.embed_text(text)
            except Exception as exc:
                logger.warning("Text embedding failed for sheet %s: %s", sheet_id, exc)

        if image_bytes:
            try:
                from app.services.embeddings.image_embedder import get_image_embedder
                embedder = get_image_embedder()
                result["image_vector"] = await embedder.embed_image(image_bytes)
            except Exception as exc:
                logger.warning("Image embedding failed for sheet %s: %s", sheet_id, exc)

        return result

    async def embed_query(self, query: str) -> Optional[list[float]]:
        """Embed a search query for semantic search."""
        try:
            from app.services.embeddings.text_embedder import get_text_embedder
            embedder = get_text_embedder()
            return await embedder.embed_text(query)
        except Exception as exc:
            logger.warning("Query embedding failed: %s", exc)
            return None


embedding_service = EmbeddingService()
