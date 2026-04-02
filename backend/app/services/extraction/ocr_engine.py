"""OCR fallback engine using EasyOCR."""
from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class OCREngine:
    """Lazy-initialized OCR engine using EasyOCR."""

    def __init__(self) -> None:
        self._reader = None

    def _init_engine(self) -> bool:
        """Lazy-initialize the EasyOCR reader. Returns True if successful."""
        if self._reader is not None:
            return True
        try:
            import easyocr  # noqa: F401

            logger.info("Initializing EasyOCR reader...")
            self._reader = easyocr.Reader(["en"], gpu=False, verbose=False)
            logger.info("EasyOCR reader initialized")
            return True
        except ImportError:
            logger.warning("EasyOCR not installed, OCR will be skipped")
            return False
        except Exception as exc:
            logger.warning("Failed to initialize EasyOCR: %s", exc)
            return False

    def extract_text(self, image_bytes: bytes) -> str:
        """Extract text from the image and return as a single string."""
        results = self.extract_text_with_positions(image_bytes)
        lines = [r["text"] for r in results if r.get("text")]
        return "\n".join(lines)

    def extract_text_with_positions(self, image_bytes: bytes) -> list[dict]:
        """Extract text with bounding boxes and confidence scores.

        Returns a list of dicts with keys: text, bbox, confidence.
        """
        if not self._init_engine():
            return []

        try:
            import numpy as np
            import io as _io

            nparr = np.frombuffer(image_bytes, np.uint8)
            try:
                import cv2

                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                if img is None:
                    raise ValueError("cv2 decode returned None")
            except (ImportError, ValueError):
                from PIL import Image

                pil_img = Image.open(_io.BytesIO(image_bytes))
                img = np.array(pil_img)

            results = self._reader.readtext(img)
            output = []
            for bbox, text, confidence in results:
                output.append(
                    {
                        "text": text,
                        "bbox": bbox,
                        "confidence": float(confidence),
                    }
                )
            return output
        except Exception as exc:
            logger.warning("OCR extraction failed: %s", exc)
            return []
