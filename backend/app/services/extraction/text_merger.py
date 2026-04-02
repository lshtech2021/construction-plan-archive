"""Multi-signal text merging for construction drawing sheets."""
from __future__ import annotations

import logging
from typing import Optional

from app.schemas.extraction import ScheduleData, TitleBlockData

logger = logging.getLogger(__name__)

# Similarity threshold above which lines are considered duplicates (0-100 scale)
_DEDUP_SIMILARITY_THRESHOLD = 85


class TextMerger:
    """Merge and deduplicate text from multiple extraction signals."""

    def merge_texts(
        self,
        native_text: Optional[str],
        ocr_text: Optional[str],
        vlm_description: Optional[str],
        drawing_description: Optional[str],
    ) -> str:
        """Merge texts from multiple sources, deduplicating similar lines."""
        texts = [t for t in [native_text, ocr_text, vlm_description, drawing_description] if t]
        if not texts:
            return ""
        if len(texts) == 1:
            return texts[0]
        return self._deduplicate_lines(texts)

    def _deduplicate_lines(self, texts: list[str]) -> str:
        """Combine texts, removing lines that are highly similar to already-seen lines."""
        try:
            from rapidfuzz import fuzz
            use_fuzzy = True
        except ImportError:
            logger.debug("rapidfuzz not installed, using exact deduplication")
            use_fuzzy = False

        seen: list[str] = []
        for text in texts:
            for line in text.splitlines():
                line = line.strip()
                if not line:
                    continue
                # Check similarity against already-seen lines
                duplicate = False
                if use_fuzzy:
                    for s in seen:
                        if fuzz.ratio(line.lower(), s.lower()) > _DEDUP_SIMILARITY_THRESHOLD:
                            duplicate = True
                            break
                else:
                    if line.lower() in (s.lower() for s in seen):
                        duplicate = True
                if not duplicate:
                    seen.append(line)

        return "\n".join(seen)

    def build_searchable_text(
        self,
        merged_text: str,
        title_block: TitleBlockData,
        schedules: list[ScheduleData],
    ) -> str:
        """Build a comprehensive searchable text blob from all extracted data."""
        parts: list[str] = []

        if merged_text:
            parts.append(merged_text)

        # Add title block fields
        tb_fields = [
            title_block.project_name,
            title_block.project_number,
            title_block.client_name,
            title_block.sheet_number,
            title_block.sheet_title,
            title_block.firm_name,
            title_block.scale,
        ]
        tb_text = " | ".join(f for f in tb_fields if f)
        if tb_text:
            parts.append(f"Title Block: {tb_text}")

        # Add schedule content
        for schedule in schedules:
            if schedule.title:
                parts.append(f"Schedule: {schedule.title}")
            if schedule.headers:
                parts.append("Headers: " + " | ".join(schedule.headers))
            for row in schedule.rows:
                if row.cells:
                    parts.append(" | ".join(row.cells))

        return "\n".join(parts)
