from __future__ import annotations

import logging

import redis.asyncio as aioredis
from fastapi import APIRouter
from qdrant_client import AsyncQdrantClient

from app.config import settings
from app.database import engine
from app.services.storage import StorageService
from sqlalchemy import text

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health")
async def health_check() -> dict:
    services: dict[str, str] = {}

    # PostgreSQL
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        services["postgres"] = "healthy"
    except Exception as exc:
        logger.warning("PostgreSQL health check failed: %s", exc)
        services["postgres"] = "unhealthy"

    # Redis
    try:
        r = aioredis.from_url(settings.redis_url)
        await r.ping()
        await r.aclose()
        services["redis"] = "healthy"
    except Exception as exc:
        logger.warning("Redis health check failed: %s", exc)
        services["redis"] = "unhealthy"

    # MinIO
    try:
        storage = StorageService()
        storage.client.list_buckets()
        services["minio"] = "healthy"
    except Exception as exc:
        logger.warning("MinIO health check failed: %s", exc)
        services["minio"] = "unhealthy"

    # Qdrant
    try:
        qclient = AsyncQdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_http_port,
        )
        await qclient.get_collections()
        await qclient.close()
        services["qdrant"] = "healthy"
    except Exception as exc:
        logger.warning("Qdrant health check failed: %s", exc)
        services["qdrant"] = "unhealthy"

    overall = "healthy" if all(v == "healthy" for v in services.values()) else "degraded"
    return {"status": overall, "services": services}
