from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.services.storage import StorageService

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure MinIO buckets exist
    try:
        storage = StorageService()
        storage.ensure_buckets()
        logger.info("MinIO buckets ensured")
    except Exception as exc:
        logger.warning("Could not ensure MinIO buckets on startup: %s", exc)

    # Startup: ensure Qdrant collections exist
    try:
        from app.services.search.vector_store import vector_store
        await vector_store.ensure_collections()
        logger.info("Qdrant collections ensured")
    except Exception as exc:
        logger.warning("Could not ensure Qdrant collections on startup: %s", exc)

    yield


app = FastAPI(
    title="Construction Plan Archive API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development; restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
