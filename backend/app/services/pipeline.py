"""Main extraction pipeline orchestrator."""
from __future__ import annotations

import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import Optional

from app.config import settings
from app.schemas.extraction import (
    DisciplineClassification,
    DrawingDescription,
    SheetExtractionResult,
    TitleBlockData,
    ZoneExtraction,
)
from app.services.extraction.discipline_classifier import DisciplineClassifier
from app.services.extraction.layout_detector import LayoutDetector
from app.services.extraction.metadata_extractor import MetadataExtractor
from app.services.extraction.ocr_engine import OCREngine
from app.services.extraction.table_extractor import TableExtractor
from app.services.extraction.text_merger import TextMerger
from app.services.extraction.vlm_extractor import VLMExtractor
from app.services.preprocessing import ImagePreprocessor

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=getattr(settings, "extraction_max_workers", 4))


class ExtractionPipeline:
    """Orchestrates the full extraction pipeline for a single sheet."""

    def __init__(self, storage=None) -> None:
        self.storage = storage
        self.preprocessor = ImagePreprocessor()
        self.layout_detector = LayoutDetector()
        self.vlm_extractor = VLMExtractor()
        self.ocr_engine = OCREngine()
        self.table_extractor = TableExtractor()
        self.metadata_extractor = MetadataExtractor()
        self.discipline_classifier = DisciplineClassifier()
        self.text_merger = TextMerger()

    async def process_sheet(
        self,
        image_bytes: bytes,
        native_text: Optional[str],
        page_number: int,
    ) -> SheetExtractionResult:
        """Run the full extraction pipeline for a single sheet image."""
        start_time = time.monotonic()
        warnings: list[str] = []
        loop = asyncio.get_event_loop()

        result = SheetExtractionResult(page_number=page_number)
        result.native_text = native_text

        # Step 1: Preprocess image
        processed_image = image_bytes
        try:
            processed_image = await loop.run_in_executor(
                _executor,
                partial(
                    self.preprocessor.preprocess,
                    image_bytes,
                    True,
                    getattr(settings, "ocr_denoise", True),
                    True,
                ),
            )
            logger.debug("Page %d: preprocessing complete", page_number)
        except Exception as exc:
            warnings.append(f"Preprocessing failed: {exc}")
            logger.warning("Page %d: preprocessing failed: %s", page_number, exc)

        # Step 2: Detect layout zones
        zones: list[ZoneExtraction] = []
        try:
            detected = await loop.run_in_executor(
                _executor,
                self.layout_detector.detect_zones,
                processed_image,
            )
            zones = [
                ZoneExtraction(
                    zone_type=z.zone_type,
                    bbox=z.bbox,
                    confidence=z.confidence,
                )
                for z in detected
            ]
            result.zones = zones
            logger.debug("Page %d: detected %d zones", page_number, len(zones))
        except Exception as exc:
            warnings.append(f"Zone detection failed: {exc}")
            logger.warning("Page %d: zone detection failed: %s", page_number, exc)

        # Step 3: OCR if enabled and native text is short
        ocr_text: Optional[str] = None
        ocr_enabled = getattr(settings, "ocr_enabled", True)
        if ocr_enabled and len(native_text or "") < 50:
            try:
                ocr_text = await loop.run_in_executor(
                    _executor,
                    self.ocr_engine.extract_text,
                    processed_image,
                )
                result.ocr_text = ocr_text
                result.ocr_used = bool(ocr_text)
                logger.debug("Page %d: OCR extracted %d chars", page_number, len(ocr_text or ""))
            except Exception as exc:
                warnings.append(f"OCR failed: {exc}")
                logger.warning("Page %d: OCR failed: %s", page_number, exc)

        # Step 4: VLM full-page analysis if enabled
        vlm_result: dict = {}
        vlm_text: Optional[str] = None
        vlm_enabled = getattr(settings, "vlm_enabled", False)
        if vlm_enabled:
            try:
                vlm_result = await self.vlm_extractor.analyze_full_page(processed_image)
                result.vlm_used = bool(vlm_result)
                # Extract text description from VLM result
                dd = vlm_result.get("drawing_description") or {}
                vlm_text = dd.get("description") or vlm_result.get("notes_summary") or ""
                result.vlm_text = vlm_text or None
                logger.debug("Page %d: VLM analysis complete", page_number)
            except Exception as exc:
                warnings.append(f"VLM analysis failed: {exc}")
                logger.warning("Page %d: VLM analysis failed: %s", page_number, exc)

        # Step 5: Extract title block metadata
        try:
            title_block = self.metadata_extractor.extract_metadata(
                native_text or "",
                ocr_text or "",
                vlm_result,
            )
            result.title_block = title_block
            logger.debug(
                "Page %d: title block extracted, sheet_number=%s",
                page_number,
                title_block.sheet_number,
            )
        except Exception as exc:
            warnings.append(f"Metadata extraction failed: {exc}")
            logger.warning("Page %d: metadata extraction failed: %s", page_number, exc)

        # Step 6: Extract tables if enabled
        table_enabled = getattr(settings, "table_extraction_enabled", True)
        if table_enabled:
            try:
                schedules = await self.table_extractor.extract_tables_async(
                    processed_image, self.vlm_extractor
                )
                result.schedules = schedules
                logger.debug("Page %d: extracted %d schedules", page_number, len(schedules))
            except Exception as exc:
                warnings.append(f"Table extraction failed: {exc}")
                logger.warning("Page %d: table extraction failed: %s", page_number, exc)

        # Step 7: Classify discipline
        try:
            combined_text = " ".join(
                filter(None, [native_text, ocr_text, vlm_text])
            )
            discipline_cls = await self.discipline_classifier.classify(
                result.title_block.sheet_number,
                combined_text,
                processed_image,
                self.vlm_extractor if vlm_enabled else None,
            )
            result.discipline_classification = discipline_cls
            logger.debug(
                "Page %d: discipline=%s confidence=%s",
                page_number,
                discipline_cls.discipline,
                discipline_cls.confidence,
            )
        except Exception as exc:
            warnings.append(f"Discipline classification failed: {exc}")
            logger.warning("Page %d: discipline classification failed: %s", page_number, exc)

        # Parse drawing description from VLM result if available
        if vlm_result:
            try:
                dd_raw = vlm_result.get("drawing_description") or {}
                result.drawing_description = DrawingDescription(
                    **{k: v for k, v in dd_raw.items() if k in DrawingDescription.model_fields}
                )
            except Exception:
                pass

        # Step 8: Merge texts
        try:
            drawing_desc_text = result.drawing_description.description if result.drawing_description else None
            result.merged_text = self.text_merger.merge_texts(
                native_text, ocr_text, vlm_text, drawing_desc_text
            )
            searchable = self.text_merger.build_searchable_text(
                result.merged_text or "",
                result.title_block,
                result.schedules,
            )
            if searchable and not result.merged_text:
                result.merged_text = searchable
            logger.debug("Page %d: text merging complete", page_number)
        except Exception as exc:
            warnings.append(f"Text merging failed: {exc}")
            logger.warning("Page %d: text merging failed: %s", page_number, exc)

        # Step 9: Determine overall confidence
        result.overall_confidence = self._determine_confidence(result)
        result.needs_human_review = result.overall_confidence in ("low", "failed")

        # Step 10: Finalize
        result.extraction_warnings = warnings
        result.processing_time_seconds = time.monotonic() - start_time
        logger.info(
            "Page %d extraction complete: confidence=%s, time=%.2fs",
            page_number,
            result.overall_confidence,
            result.processing_time_seconds,
        )
        return result

    def _determine_confidence(self, result: SheetExtractionResult) -> str:
        """Determine overall extraction confidence from available signals."""
        has_vlm = result.vlm_used
        has_sheet_number = bool(result.title_block and result.title_block.sheet_number)
        has_text = bool(result.merged_text and len(result.merged_text) > 50)
        has_native = bool(result.native_text and len(result.native_text) > 20)

        if has_vlm and has_sheet_number:
            return "high"
        if has_text or (has_native and has_sheet_number):
            return "medium"
        if has_native:
            return "low"
        if not result.merged_text and not result.native_text and not result.ocr_text:
            return "failed"
        return "low"
