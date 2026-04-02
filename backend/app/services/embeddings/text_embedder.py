from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="text_embedder")


class TextEmbedder:
    """Lazily-loaded text embedder supporting local sentence-transformers or OpenAI."""

    def __init__(self, provider: str = "local", model: str = "all-MiniLM-L6-v2", api_key: str = "") -> None:
        self.provider = provider
        self.model_name = model
        self.api_key = api_key
        self._model = None
        self._openai_client = None

    def _load_model(self) -> None:
        if self.provider == "local":
            if self._model is None:
                try:
                    from sentence_transformers import SentenceTransformer  # type: ignore
                    self._model = SentenceTransformer(self.model_name)
                    logger.info("Loaded sentence-transformers model: %s", self.model_name)
                except Exception as exc:
                    logger.error("Failed to load sentence-transformers model: %s", exc)
                    raise
        elif self.provider == "openai":
            if self._openai_client is None:
                try:
                    from openai import OpenAI  # type: ignore
                    self._openai_client = OpenAI(api_key=self.api_key)
                    logger.info("Initialized OpenAI client for embeddings")
                except Exception as exc:
                    logger.error("Failed to initialize OpenAI client: %s", exc)
                    raise

    def _embed_sync(self, text: str) -> list[float]:
        self._load_model()
        if self.provider == "local":
            vector = self._model.encode(text, normalize_embeddings=True)
            return vector.tolist()
        elif self.provider == "openai":
            response = self._openai_client.embeddings.create(
                model=self.model_name,
                input=text,
            )
            return response.data[0].embedding
        raise ValueError(f"Unknown embedding provider: {self.provider}")

    def _embed_batch_sync(self, texts: list[str]) -> list[list[float]]:
        self._load_model()
        if self.provider == "local":
            vectors = self._model.encode(texts, normalize_embeddings=True, batch_size=32)
            return [v.tolist() for v in vectors]
        elif self.provider == "openai":
            response = self._openai_client.embeddings.create(
                model=self.model_name,
                input=texts,
            )
            return [item.embedding for item in response.data]
        raise ValueError(f"Unknown embedding provider: {self.provider}")

    async def embed_text(self, text: str) -> list[float]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_executor, self._embed_sync, text)

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_executor, self._embed_batch_sync, texts)


# Module-level singleton; lazily initialized
_text_embedder: Optional[TextEmbedder] = None


def get_text_embedder() -> TextEmbedder:
    global _text_embedder
    if _text_embedder is None:
        from app.config import settings
        _text_embedder = TextEmbedder(
            provider=settings.embedding_provider,
            model=settings.embedding_model,
            api_key=settings.embedding_api_key,
        )
    return _text_embedder
