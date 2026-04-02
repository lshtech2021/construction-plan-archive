"""Title block metadata extraction from text signals."""
from __future__ import annotations

import logging
import re
from typing import Optional

from app.schemas.extraction import TitleBlockData

logger = logging.getLogger(__name__)

# Sheet number prefix → discipline mapping
_PREFIX_TO_DISCIPLINE: dict[str, str] = {
    "A": "architectural",
    "S": "structural",
    "C": "civil",
    "M": "mechanical",
    "E": "electrical",
    "P": "plumbing",
    "FP": "fire_protection",
    "L": "landscape",
    "ID": "interior_design",
    "G": "general",
    "SP": "specifications",
}

# Regex patterns for sheet numbers (handles multi-char prefixes first)
_SHEET_NUMBER_RE = re.compile(
    r"\b(FP|ID|SP|[ASCMEPLG])-?\d{3,4}[A-Z]?\b",
    re.IGNORECASE,
)


class MetadataExtractor:
    """Extract and cross-validate title block metadata from multiple text sources."""

    def extract_metadata(
        self,
        native_text: str,
        ocr_text: str,
        vlm_result: dict,
    ) -> TitleBlockData:
        """Merge metadata from native text, OCR, and VLM results."""
        # Start from VLM result (most structured)
        vlm_block_raw = vlm_result.get("title_block") or vlm_result
        try:
            vlm_data = TitleBlockData(
                **{k: v for k, v in vlm_block_raw.items() if k in TitleBlockData.model_fields}
            )
        except Exception:
            vlm_data = TitleBlockData()

        combined_text = " ".join(filter(None, [native_text, ocr_text]))
        return self._cross_validate(vlm_data, ocr_text or "", native_text or "")

    def _parse_sheet_number(self, text: str) -> Optional[str]:
        """Extract a sheet number from arbitrary text."""
        match = _SHEET_NUMBER_RE.search(text)
        if match:
            return match.group(0).upper()
        return None

    def _infer_discipline_from_sheet_number(self, sheet_number: str) -> Optional[str]:
        """Infer discipline from sheet number prefix."""
        if not sheet_number:
            return None
        # Try multi-char prefixes first
        for prefix in sorted(_PREFIX_TO_DISCIPLINE.keys(), key=len, reverse=True):
            if sheet_number.upper().startswith(prefix):
                return _PREFIX_TO_DISCIPLINE[prefix]
        return None

    def _cross_validate(
        self,
        vlm_data: TitleBlockData,
        ocr_text: str,
        native_text: str,
    ) -> TitleBlockData:
        """Cross-validate VLM data against OCR and native text, filling gaps."""
        combined = " ".join(filter(None, [native_text, ocr_text]))

        # Fill sheet_number if missing
        sheet_number = vlm_data.sheet_number
        if not sheet_number:
            sheet_number = self._parse_sheet_number(combined)

        # Infer discipline_code from sheet_number if missing
        discipline_code = vlm_data.discipline_code
        if not discipline_code and sheet_number:
            inferred = self._infer_discipline_from_sheet_number(sheet_number)
            if inferred:
                # Store the prefix as discipline_code
                for prefix, disc in _PREFIX_TO_DISCIPLINE.items():
                    if disc == inferred:
                        discipline_code = prefix
                        break

        # Determine confidence
        filled_fields = sum(
            1
            for f in [
                vlm_data.project_name,
                vlm_data.project_number,
                sheet_number,
                vlm_data.sheet_title,
                vlm_data.firm_name,
            ]
            if f
        )
        if filled_fields >= 4:
            confidence = "high"
        elif filled_fields >= 2:
            confidence = "medium"
        else:
            confidence = "low"

        return TitleBlockData(
            project_name=vlm_data.project_name,
            project_number=vlm_data.project_number,
            client_name=vlm_data.client_name,
            sheet_number=sheet_number,
            sheet_title=vlm_data.sheet_title,
            discipline_code=discipline_code,
            revision_number=vlm_data.revision_number,
            revision_date=vlm_data.revision_date,
            issue_date=vlm_data.issue_date,
            drawn_by=vlm_data.drawn_by,
            checked_by=vlm_data.checked_by,
            firm_name=vlm_data.firm_name,
            scale=vlm_data.scale,
            confidence=confidence,
        )
