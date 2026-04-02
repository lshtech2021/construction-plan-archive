"""Vision Language Model integration via litellm."""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import re
import time
from typing import Optional

from app.schemas.extraction import (
    DisciplineClassification,
    DrawingDescription,
    ScheduleData,
    ScheduleRow,
    TitleBlockData,
)
from app.services.extraction.prompts import (
    DISCIPLINE_CLASSIFICATION_PROMPT,
    DRAWING_DESCRIPTION_PROMPT,
    FULL_PAGE_ANALYSIS_PROMPT,
    TABLE_EXTRACTION_PROMPT,
    TITLE_BLOCK_EXTRACTION_PROMPT,
)

logger = logging.getLogger(__name__)


class VLMExtractor:
    """Vision Language Model extractor using litellm."""

    def __init__(self) -> None:
        from app.config import settings

        self._enabled: bool = getattr(settings, "vlm_enabled", False)
        self._provider: str = getattr(settings, "vlm_provider", "openai")
        self._model: str = getattr(settings, "vlm_model", "gpt-4o")
        self._api_key: str = getattr(settings, "vlm_api_key", "")
        self._api_base: Optional[str] = getattr(settings, "vlm_api_base", None) or None
        self._max_retries: int = getattr(settings, "vlm_max_retries", 3)
        self._timeout_seconds: float = getattr(settings, "vlm_timeout_seconds", 60.0)

        if not self._api_key:
            self._enabled = False
            logger.info("VLM disabled: no API key configured")

    # ------------------------------------------------------------------
    # Public async methods
    # ------------------------------------------------------------------

    async def analyze_full_page(self, image_bytes: bytes) -> dict:
        """Run full page analysis and return raw dict."""
        if not self._enabled:
            return {}
        text = await self._call_vlm(image_bytes, FULL_PAGE_ANALYSIS_PROMPT)
        return self._parse_json_response(text)

    async def extract_title_block(self, image_bytes: bytes) -> TitleBlockData:
        """Extract title block metadata from a page image."""
        if not self._enabled:
            return TitleBlockData()
        text = await self._call_vlm(image_bytes, TITLE_BLOCK_EXTRACTION_PROMPT)
        data = self._parse_json_response(text)
        try:
            return TitleBlockData(**{k: v for k, v in data.items() if k in TitleBlockData.model_fields})
        except Exception as exc:
            logger.warning("Could not parse TitleBlockData: %s", exc)
            return TitleBlockData()

    async def describe_drawing(self, image_bytes: bytes) -> DrawingDescription:
        """Generate a semantic description of the drawing content."""
        if not self._enabled:
            return DrawingDescription()
        text = await self._call_vlm(image_bytes, DRAWING_DESCRIPTION_PROMPT)
        data = self._parse_json_response(text)
        try:
            return DrawingDescription(**{k: v for k, v in data.items() if k in DrawingDescription.model_fields})
        except Exception as exc:
            logger.warning("Could not parse DrawingDescription: %s", exc)
            return DrawingDescription()

    async def classify_discipline(
        self, image_bytes: bytes, metadata_context: str = ""
    ) -> DisciplineClassification:
        """Classify the discipline and sheet type."""
        if not self._enabled:
            return DisciplineClassification()
        prompt = DISCIPLINE_CLASSIFICATION_PROMPT.replace(
            "{metadata_context}", metadata_context or "No additional metadata available."
        )
        text = await self._call_vlm(image_bytes, prompt)
        data = self._parse_json_response(text)
        try:
            return DisciplineClassification(**{k: v for k, v in data.items() if k in DisciplineClassification.model_fields})
        except Exception as exc:
            logger.warning("Could not parse DisciplineClassification: %s", exc)
            return DisciplineClassification()

    async def extract_table(self, image_bytes: bytes) -> ScheduleData:
        """Extract table/schedule data from the image."""
        if not self._enabled:
            return ScheduleData()
        text = await self._call_vlm(image_bytes, TABLE_EXTRACTION_PROMPT)
        data = self._parse_json_response(text)
        try:
            raw_rows = data.get("rows", [])
            rows = []
            for row in raw_rows:
                if isinstance(row, dict) and "cells" in row:
                    rows.append(ScheduleRow(cells=[str(c) for c in row["cells"]]))
                elif isinstance(row, list):
                    rows.append(ScheduleRow(cells=[str(c) for c in row]))
            return ScheduleData(
                title=data.get("title"),
                headers=[str(h) for h in data.get("headers", [])],
                rows=rows,
            )
        except Exception as exc:
            logger.warning("Could not parse ScheduleData: %s", exc)
            return ScheduleData()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _call_vlm(
        self, image_bytes: bytes, prompt: str, max_retries: Optional[int] = None
    ) -> str:
        """Call the VLM with the given image and prompt, with retry logic."""
        if max_retries is None:
            max_retries = self._max_retries

        try:
            import litellm
        except ImportError:
            logger.warning("litellm not installed, VLM calls will be skipped")
            return ""

        image_url = self._image_to_base64_url(image_bytes)
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": image_url}},
                    {"type": "text", "text": prompt},
                ],
            }
        ]

        kwargs: dict = {
            "model": self._model,
            "messages": messages,
            "timeout": self._timeout_seconds,
            "max_tokens": 2048,
        }
        if self._api_key:
            kwargs["api_key"] = self._api_key
        if self._api_base:
            kwargs["api_base"] = self._api_base

        for attempt in range(max_retries):
            try:
                start = time.monotonic()
                response = await litellm.acompletion(**kwargs)
                elapsed = time.monotonic() - start
                logger.debug("VLM call took %.2fs on attempt %d", elapsed, attempt + 1)
                content = response.choices[0].message.content or ""
                return content
            except Exception as exc:
                wait = 2 ** attempt
                logger.warning(
                    "VLM call failed (attempt %d/%d): %s. Retrying in %ds.",
                    attempt + 1, max_retries, exc, wait,
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(wait)

        return ""

    def _parse_json_response(self, text: str) -> dict:
        """Parse JSON from VLM response text, handling markdown code blocks."""
        if not text:
            return {}
        # Strip markdown code block
        text = text.strip()
        match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if match:
            text = match.group(1).strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to find the first JSON object in the text
            match = re.search(r"\{[\s\S]*\}", text)
            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    pass
        logger.debug("Could not parse JSON from VLM response: %s", text[:200])
        return {}

    def _image_to_base64_url(self, image_bytes: bytes) -> str:
        """Convert image bytes to a base64 data URL."""
        encoded = base64.b64encode(image_bytes).decode("utf-8")
        return f"data:image/png;base64,{encoded}"
