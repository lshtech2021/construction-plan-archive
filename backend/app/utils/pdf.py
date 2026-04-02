from __future__ import annotations

import logging

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)

PDF_MAGIC = b"%PDF-"


def is_valid_pdf(data: bytes) -> bool:
    return data[:5] == PDF_MAGIC


def get_pdf_metadata(data: bytes) -> dict:
    try:
        doc = fitz.open(stream=data, filetype="pdf")
        try:
            meta = doc.metadata or {}
            return {
                "page_count": doc.page_count,
                "title": meta.get("title", ""),
                "author": meta.get("author", ""),
                "subject": meta.get("subject", ""),
                "creator": meta.get("creator", ""),
                "producer": meta.get("producer", ""),
                "creation_date": meta.get("creationDate", ""),
                "mod_date": meta.get("modDate", ""),
            }
        finally:
            doc.close()
    except Exception as exc:
        logger.warning("Failed to read PDF metadata: %s", exc)
        return {"page_count": 0}
