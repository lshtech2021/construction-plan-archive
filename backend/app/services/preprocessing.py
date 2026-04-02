"""Image preprocessing using OpenCV."""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class ImagePreprocessor:
    """Preprocess images for better OCR and VLM analysis."""

    def preprocess(
        self,
        image_bytes: bytes,
        deskew: bool = True,
        denoise: bool = True,
        enhance_contrast: bool = True,
    ) -> bytes:
        """Preprocess an image and return the processed bytes."""
        try:
            import cv2
            import numpy as np
        except ImportError:
            logger.warning("OpenCV not available, skipping preprocessing")
            return image_bytes

        try:
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                logger.warning("Could not decode image, returning original")
                return image_bytes

            if deskew:
                img = self._deskew(img)
            if denoise:
                img = self._denoise(img)
            if enhance_contrast:
                img = self._enhance_contrast(img)

            success, encoded = cv2.imencode(".png", img)
            if not success:
                logger.warning("Could not encode processed image, returning original")
                return image_bytes
            return encoded.tobytes()
        except Exception as exc:
            logger.warning("Preprocessing failed: %s, returning original", exc)
            return image_bytes

    def _deskew(self, img: "np.ndarray") -> "np.ndarray":
        """Detect and correct image skew."""
        try:
            import cv2
            import numpy as np

            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            coords = np.column_stack(np.where(thresh > 0))
            if len(coords) < 10:
                return img
            rect = cv2.minAreaRect(coords)
            angle = rect[-1]
            # minAreaRect returns angles in [-90, 0), convert to [-45, 45)
            if angle < -45:
                angle = -(90 + angle)
            else:
                angle = -angle
            if abs(angle) < 0.5 or abs(angle) > 15:
                return img
            h, w = img.shape[:2]
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            rotated = cv2.warpAffine(
                img, M, (w, h),
                flags=cv2.INTER_CUBIC,
                borderMode=cv2.BORDER_REPLICATE,
            )
            return rotated
        except Exception as exc:
            logger.debug("Deskew failed: %s", exc)
            return img

    def _denoise(self, img: "np.ndarray") -> "np.ndarray":
        """Apply denoising to the image."""
        try:
            import cv2

            return cv2.fastNlMeansDenoisingColored(img, None, 10, 10, 7, 21)
        except Exception as exc:
            logger.debug("Denoise failed: %s", exc)
            return img

    def _enhance_contrast(self, img: "np.ndarray") -> "np.ndarray":
        """Enhance contrast using CLAHE on the L channel of LAB color space."""
        try:
            import cv2

            lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
            l_channel, a_channel, b_channel = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            l_enhanced = clahe.apply(l_channel)
            lab_enhanced = cv2.merge([l_enhanced, a_channel, b_channel])
            enhanced = cv2.cvtColor(lab_enhanced, cv2.COLOR_LAB2BGR)
            return enhanced
        except Exception as exc:
            logger.debug("Contrast enhancement failed: %s", exc)
            return img

    def crop_zone(self, image_bytes: bytes, bbox_dict: dict) -> bytes:
        """Crop a zone from an image using a bounding box dict with x1, y1, x2, y2."""
        try:
            import cv2
            import numpy as np

            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                return image_bytes

            h, w = img.shape[:2]
            x1 = bbox_dict.get("x1", 0.0)
            y1 = bbox_dict.get("y1", 0.0)
            x2 = bbox_dict.get("x2", 1.0)
            y2 = bbox_dict.get("y2", 1.0)

            # Support normalized (0-1) or pixel coordinates
            if all(0.0 <= v <= 1.0 for v in (x1, y1, x2, y2)):
                px1 = int(x1 * w)
                py1 = int(y1 * h)
                px2 = int(x2 * w)
                py2 = int(y2 * h)
            else:
                px1, py1, px2, py2 = int(x1), int(y1), int(x2), int(y2)

            # Clamp to image bounds
            px1 = max(0, min(px1, w - 1))
            py1 = max(0, min(py1, h - 1))
            px2 = max(px1 + 1, min(px2, w))
            py2 = max(py1 + 1, min(py2, h))

            cropped = img[py1:py2, px1:px2]
            success, encoded = cv2.imencode(".png", cropped)
            if not success:
                return image_bytes
            return encoded.tobytes()
        except Exception as exc:
            logger.warning("Crop zone failed: %s", exc)
            return image_bytes
