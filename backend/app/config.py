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

    # VLM settings
    vlm_enabled: bool = False
    vlm_provider: str = "openai"
    vlm_model: str = "gpt-4o"
    vlm_api_key: str = ""
    vlm_api_base: str = ""
    vlm_max_retries: int = 3
    vlm_timeout_seconds: float = 60.0

    # OCR settings
    ocr_enabled: bool = True
    ocr_denoise: bool = True

    # Extraction pipeline settings
    extraction_enabled: bool = True
    table_extraction_enabled: bool = True
    extraction_max_workers: int = 4

    # Embedding settings
    embedding_provider: str = "local"
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_api_key: str = ""
    embedding_dimension: int = 384
    image_embedding_model: str = "clip-ViT-B-32"
    image_embedding_dimension: int = 512

    # Qdrant collection names
    qdrant_text_collection: str = "sheet_text_embeddings"
    qdrant_image_collection: str = "sheet_image_embeddings"

    # Search settings
    search_default_limit: int = 20
    search_max_limit: int = 100
    search_semantic_weight: float = 0.7
    search_keyword_weight: float = 0.3
    search_min_score: float = 0.1
    search_enable_reranking: bool = True


settings = Settings()
