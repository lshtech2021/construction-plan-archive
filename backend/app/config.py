from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = "development"
    secret_key: str = "change-me-in-production"
    api_prefix: str = "/api"

    # Database
    database_url: str = "postgresql+asyncpg://cpa:cpa_secret@localhost:5432/construction_archive"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # MinIO
    minio_host: str = "minio"
    minio_api_port: int = 9000
    minio_root_user: str = "minioadmin"
    minio_root_password: str = "minioadmin"
    minio_secure: bool = False

    # Qdrant
    qdrant_host: str = "qdrant"
    qdrant_http_port: int = 6333

    # PDF processing
    pdf_render_dpi: int = 300
    thumbnail_dpi: int = 72

    # Bucket names
    bucket_original_pdfs: str = "original-pdfs"
    bucket_rendered_pages: str = "rendered-pages"
    bucket_thumbnails: str = "thumbnails"


settings = Settings()
