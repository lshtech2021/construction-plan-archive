"""Page layout zone detection using OpenCV."""
from __future__ import annotations

import logging
from typing import Optional

from app.schemas.extraction import BoundingBox, DetectedZone, ZoneType

logger = logging.getLogger(__name__)


class LayoutDetector:
    """Detect zones on a construction drawing page."""

    def detect_zones(self, image_bytes: bytes) -> list[DetectedZone]:
        """Detect layout zones in the image and return a list of DetectedZone objects."""
        try:
            import cv2
            import numpy as np
        except ImportError:
            logger.warning("OpenCV not available, skipping zone detection")
            return []

        try:
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                return []

            h, w = img.shape[:2]
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            zones: list[DetectedZone] = []

            title_block = self._detect_title_block(gray, h, w)
            if title_block:
                zones.append(title_block)

            text_regions = self._detect_text_regions(gray, h, w)
            zones.extend(text_regions)

            table_regions = self._detect_table_regions(gray, h, w)
            zones.extend(table_regions)

            drawing_area = self._detect_drawing_area(h, w, zones)
            zones.append(drawing_area)

            return zones
        except Exception as exc:
            logger.warning("Zone detection failed: %s", exc)
            return []

    def _detect_title_block(
        self, gray_img: "np.ndarray", h: int, w: int
    ) -> Optional[DetectedZone]:
        """Detect title block in the bottom-right region."""
        try:
            import cv2

            # Look in bottom-right region: last 30% width, last 25% height
            x_start = int(w * 0.70)
            y_start = int(h * 0.75)
            roi = gray_img[y_start:h, x_start:w]

            # Morphological operations to find dense content
            _, thresh = cv2.threshold(roi, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (20, 3))
            dilated = cv2.dilate(thresh, kernel, iterations=1)
            contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            if not contours:
                # Return default title block zone in bottom-right region
                return DetectedZone(
                    zone_type=ZoneType.title_block,
                    bbox=BoundingBox(x1=0.70, y1=0.75, x2=1.0, y2=1.0),
                    confidence=0.5,
                )

            # Use the largest contour area
            largest = max(contours, key=cv2.contourArea)
            rx, ry, rw, rh = cv2.boundingRect(largest)

            # Convert back to full-image normalized coordinates
            nx1 = (x_start + rx) / w
            ny1 = (y_start + ry) / h
            nx2 = (x_start + rx + rw) / w
            ny2 = (y_start + ry + rh) / h

            return DetectedZone(
                zone_type=ZoneType.title_block,
                bbox=BoundingBox(x1=nx1, y1=ny1, x2=nx2, y2=ny2),
                confidence=0.75,
            )
        except Exception as exc:
            logger.debug("Title block detection failed: %s", exc)
            return None

    def _detect_drawing_area(
        self, h: int, w: int, other_zones: list[DetectedZone]
    ) -> DetectedZone:
        """Determine the main drawing area by excluding other detected zones."""
        # Simple approach: use most of the page, excluding bottom-right title block area
        x2 = 1.0
        y2 = 1.0
        for zone in other_zones:
            if zone.zone_type == ZoneType.title_block and zone.bbox:
                x2 = min(x2, zone.bbox.x1) if zone.bbox.x1 > 0.5 else x2
                y2 = min(y2, zone.bbox.y1) if zone.bbox.y1 > 0.5 else y2

        return DetectedZone(
            zone_type=ZoneType.drawing_area,
            bbox=BoundingBox(x1=0.0, y1=0.0, x2=max(x2, 0.7), y2=max(y2, 0.75)),
            confidence=0.8,
        )

    def _detect_text_regions(
        self, gray_img: "np.ndarray", h: int, w: int
    ) -> list[DetectedZone]:
        """Detect text-heavy regions using morphological operations."""
        try:
            import cv2

            _, thresh = cv2.threshold(gray_img, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (30, 5))
            dilated = cv2.dilate(thresh, kernel, iterations=1)
            contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            zones: list[DetectedZone] = []
            for contour in contours:
                area = cv2.contourArea(contour)
                # Filter small regions
                if area < (h * w * 0.005):
                    continue
                rx, ry, rw, rh = cv2.boundingRect(contour)
                aspect = rw / max(rh, 1)
                # Text regions tend to be wide
                if aspect < 2.0:
                    continue
                zones.append(
                    DetectedZone(
                        zone_type=ZoneType.notes,
                        bbox=BoundingBox(
                            x1=rx / w,
                            y1=ry / h,
                            x2=(rx + rw) / w,
                            y2=(ry + rh) / h,
                        ),
                        confidence=0.5,
                    )
                )
            return zones[:5]  # Limit to top 5
        except Exception as exc:
            logger.debug("Text region detection failed: %s", exc)
            return []

    def _detect_table_regions(
        self, gray_img: "np.ndarray", h: int, w: int
    ) -> list[DetectedZone]:
        """Detect table regions by looking for grid-like line patterns."""
        try:
            import cv2

            edges = cv2.Canny(gray_img, 50, 150)
            horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
            vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
            h_lines = cv2.morphologyEx(edges, cv2.MORPH_OPEN, horizontal_kernel)
            v_lines = cv2.morphologyEx(edges, cv2.MORPH_OPEN, vertical_kernel)
            grid = cv2.add(h_lines, v_lines)
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (20, 20))
            grid_dilated = cv2.dilate(grid, kernel, iterations=2)
            contours, _ = cv2.findContours(grid_dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            zones: list[DetectedZone] = []
            for contour in contours:
                area = cv2.contourArea(contour)
                if area < (h * w * 0.01):
                    continue
                rx, ry, rw, rh = cv2.boundingRect(contour)
                zones.append(
                    DetectedZone(
                        zone_type=ZoneType.schedule,
                        bbox=BoundingBox(
                            x1=rx / w,
                            y1=ry / h,
                            x2=(rx + rw) / w,
                            y2=(ry + rh) / h,
                        ),
                        confidence=0.6,
                    )
                )
            return zones[:3]  # Limit to top 3
        except Exception as exc:
            logger.debug("Table region detection failed: %s", exc)
            return []
