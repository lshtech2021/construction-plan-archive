from __future__ import annotations

import io
import logging
from datetime import timedelta
from typing import Optional

from minio import Minio
from minio.error import S3Error

from app.config import settings

logger = logging.getLogger(__name__)


class StorageService:
    def __init__(self) -> None:
        self.client = Minio(
            f"{settings.minio_host}:{settings.minio_api_port}",
            access_key=settings.minio_root_user,
            secret_key=settings.minio_root_password,
            secure=settings.minio_secure,
        )
        self.default_buckets = [
            settings.bucket_original_pdfs,
            settings.bucket_rendered_pages,
            settings.bucket_thumbnails,
        ]

    def ensure_buckets(self) -> None:
        for bucket in self.default_buckets:
            try:
                if not self.client.bucket_exists(bucket):
                    self.client.make_bucket(bucket)
                    logger.info("Created MinIO bucket: %s", bucket)
            except S3Error as exc:
                logger.error("Error ensuring bucket %s: %s", bucket, exc)
                raise

    def upload_file(
        self,
        bucket: str,
        object_name: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> str:
        stream = io.BytesIO(data)
        self.client.put_object(
            bucket,
            object_name,
            stream,
            length=len(data),
            content_type=content_type,
        )
        logger.debug("Uploaded %s/%s (%d bytes)", bucket, object_name, len(data))
        return object_name

    def upload_file_stream(
        self,
        bucket: str,
        object_name: str,
        data: io.BytesIO,
        length: int,
        content_type: str = "application/octet-stream",
    ) -> str:
        self.client.put_object(
            bucket,
            object_name,
            data,
            length=length,
            content_type=content_type,
        )
        logger.debug("Uploaded stream %s/%s (%d bytes)", bucket, object_name, length)
        return object_name

    def download_file(self, bucket: str, object_name: str) -> bytes:
        response = self.client.get_object(bucket, object_name)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def get_presigned_url(
        self,
        bucket: str,
        object_name: str,
        expires_hours: int = 1,
    ) -> str:
        url = self.client.presigned_get_object(
            bucket,
            object_name,
            expires=timedelta(hours=expires_hours),
        )
        return url

    def delete_file(self, bucket: str, object_name: str) -> None:
        self.client.remove_object(bucket, object_name)
        logger.debug("Deleted %s/%s", bucket, object_name)

    def check_connection(self) -> bool:
        try:
            self.client.list_buckets()
            return True
        except Exception as exc:
            logger.warning("MinIO connection check failed: %s", exc)
            return False
