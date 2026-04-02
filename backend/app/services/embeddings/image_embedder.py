from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="image_embedder")


class ImageEmbedder:
    """Lazily-loaded CLIP image embedder via sentence-transformers."""

    def __init__(self, model: str = "clip-ViT-B-32") -> None:
        self.model_name = model
        self._model = None

    def _load_model(self) -> None:
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer  # type: ignore
                self._model = SentenceTransformer(self.model_name)
                logger.info("Loaded CLIP model: %s", self.model_name)
            except Exception as exc:
                logger.error("Failed to load CLIP model: %s", exc)
                raise

    def _embed_image_sync(self, image_bytes: bytes) -> list[float]:
        from io import BytesIO
        from PIL import Image  # type: ignore
        self._load_model()
        image = Image.open(BytesIO(image_bytes)).convert("RGB")
        vector = self._model.encode(image, normalize_embeddings=True)
        return vector.tolist()

    def _embed_images_sync(self, images_bytes: list[bytes]) -> list[list[float]]:
        from io import BytesIO
        from PIL import Image  # type: ignore
        self._load_model()
        images = [Image.open(BytesIO(b)).convert("RGB") for b in images_bytes]
        vectors = self._model.encode(images, normalize_embeddings=True, batch_size=8)
        return [v.tolist() for v in vectors]

    async def embed_image(self, image_bytes: bytes) -> list[float]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_executor, self._embed_image_sync, image_bytes)

    async def embed_images(self, images_bytes: list[bytes]) -> list[list[float]]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_executor, self._embed_images_sync, images_bytes)


# Module-level singleton
_image_embedder: Optional[ImageEmbedder] = None


def get_image_embedder() -> ImageEmbedder:
    global _image_embedder
    if _image_embedder is None:
        from app.config import settings
        _image_embedder = ImageEmbedder(model=settings.image_embedding_model)
    return _image_embedder
