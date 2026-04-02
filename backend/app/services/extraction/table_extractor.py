"""Table and schedule extraction from construction drawings."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

from app.schemas.extraction import ScheduleData, ScheduleRow

if TYPE_CHECKING:
    from app.services.extraction.vlm_extractor import VLMExtractor

logger = logging.getLogger(__name__)


class TableExtractor:
    """Extract tables and schedules from construction drawing images."""

    def extract_tables(
        self,
        image_bytes: bytes,
        vlm_extractor: Optional["VLMExtractor"] = None,
    ) -> list[ScheduleData]:
        """Extract all tables from the image.

        Tries img2table first, falls back to VLM if available.
        """
        tables = self._extract_with_img2table(image_bytes)
        if tables:
            return tables

        if vlm_extractor is not None:
            import asyncio

            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # We're already in an async context; caller should use async version
                    logger.debug("Event loop running; img2table returned no results")
                    return []
                table = loop.run_until_complete(
                    self._extract_with_vlm(image_bytes, vlm_extractor)
                )
                if table and (table.headers or table.rows):
                    return [table]
            except Exception as exc:
                logger.warning("VLM table extraction failed: %s", exc)

        return []

    async def extract_tables_async(
        self,
        image_bytes: bytes,
        vlm_extractor: Optional["VLMExtractor"] = None,
    ) -> list[ScheduleData]:
        """Async version of extract_tables."""
        tables = self._extract_with_img2table(image_bytes)
        if tables:
            return tables

        if vlm_extractor is not None:
            try:
                table = await self._extract_with_vlm(image_bytes, vlm_extractor)
                if table and (table.headers or table.rows):
                    return [table]
            except Exception as exc:
                logger.warning("VLM table extraction failed: %s", exc)

        return []

    def _extract_with_img2table(self, image_bytes: bytes) -> list[ScheduleData]:
        """Try to extract tables using img2table."""
        try:
            from img2table.document import Image as Img2TableImage  # noqa: F401
            import io

            doc = Img2TableImage(src=io.BytesIO(image_bytes))
            extracted = doc.extract_tables(implicit_rows=False)
            schedules: list[ScheduleData] = []
            for _, table_list in extracted.items():
                for table in table_list:
                    df = table.df
                    if df is None or df.empty:
                        continue
                    headers = [str(c) for c in df.columns.tolist()]
                    rows = [
                        ScheduleRow(cells=[str(v) for v in row])
                        for row in df.values.tolist()
                    ]
                    schedules.append(ScheduleData(headers=headers, rows=rows))
            return schedules
        except ImportError:
            logger.debug("img2table not installed, skipping")
            return []
        except Exception as exc:
            logger.debug("img2table extraction failed: %s", exc)
            return []

    async def _extract_with_vlm(
        self, image_bytes: bytes, vlm_extractor: "VLMExtractor"
    ) -> ScheduleData:
        """VLM-based table extraction fallback."""
        try:
            return await vlm_extractor.extract_table(image_bytes)
        except Exception as exc:
            logger.warning("VLM table extraction error: %s", exc)
            return ScheduleData()
