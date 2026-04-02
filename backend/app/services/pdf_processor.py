from __future__ import annotations

import io
import logging
from typing import Optional

import fitz  # PyMuPDF
from PIL import Image

from app.config import settings
from app.services.storage import StorageService

logger = logging.getLogger(__name__)


class PDFProcessor:
    def __init__(self, storage: StorageService) -> None:
        self.storage = storage

    def get_page_count(self, pdf_bytes: bytes) -> int:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        try:
            return doc.page_count
        finally:
            doc.close()

    def render_page_to_image(
        self,
        pdf_bytes: bytes,
        page_number: int,
        dpi: Optional[int] = None,
    ) -> bytes:
        dpi = dpi or settings.pdf_render_dpi
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        try:
            page = doc[page_number]
            zoom = dpi / 72.0
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            return pix.tobytes("png")
        finally:
            doc.close()

    def render_thumbnail(
        self,
        pdf_bytes: bytes,
        page_number: int,
        max_width: int = 400,
        max_height: int = 400,
    ) -> bytes:
        dpi = settings.thumbnail_dpi
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        try:
            page = doc[page_number]
            zoom = dpi / 72.0
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            img.thumbnail((max_width, max_height))
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            return buf.getvalue()
        finally:
            doc.close()

    def extract_native_text(self, pdf_bytes: bytes, page_number: int) -> str:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        try:
            page = doc[page_number]
            return page.get_text("text").strip()
        finally:
            doc.close()

    def process_page(
        self,
        pdf_bytes: bytes,
        page_number: int,
        project_id: str,
        document_id: str,
    ) -> dict:
        logger.debug("Processing page %d for document %s", page_number, document_id)

        # Render full-resolution image
        image_bytes = self.render_page_to_image(pdf_bytes, page_number)
        image_object_name = f"{project_id}/{document_id}/pages/page_{page_number:04d}.png"
        self.storage.upload_file(
            settings.bucket_rendered_pages,
            image_object_name,
            image_bytes,
            content_type="image/png",
        )

        # Render thumbnail
        thumbnail_bytes = self.render_thumbnail(pdf_bytes, page_number)
        thumbnail_object_name = (
            f"{project_id}/{document_id}/thumbnails/thumb_{page_number:04d}.png"
        )
        self.storage.upload_file(
            settings.bucket_thumbnails,
            thumbnail_object_name,
            thumbnail_bytes,
            content_type="image/png",
        )

        # Extract native text
        native_text = self.extract_native_text(pdf_bytes, page_number)

        return {
            "image_path": image_object_name,
            "thumbnail_path": thumbnail_object_name,
            "native_text": native_text,
            "has_native_text": bool(native_text),
            "image_bytes": image_bytes,
        }
