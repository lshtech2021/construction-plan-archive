"""Hybrid discipline classification for construction drawings."""
from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Optional

from app.schemas.extraction import DisciplineClassification

if TYPE_CHECKING:
    from app.services.extraction.vlm_extractor import VLMExtractor

logger = logging.getLogger(__name__)

# Keyword lists per discipline
_DISCIPLINE_KEYWORDS: dict[str, list[str]] = {
    "architectural": [
        "floor plan", "elevation", "section", "ceiling", "door schedule",
        "window schedule", "finish schedule", "room", "wall type", "partition",
        "reflected ceiling", "casework", "millwork", "stair", "railing",
        "exterior", "interior", "facade", "louver", "curtain wall",
    ],
    "structural": [
        "beam", "column", "footing", "foundation", "slab", "rebar",
        "structural steel", "concrete", "shear wall", "lateral", "joist",
        "girder", "truss", "moment frame", "brace", "pile", "grade beam",
        "steel connection", "weld", "bolted", "reinforcement",
    ],
    "mechanical": [
        "hvac", "duct", "diffuser", "fan", "ahu", "air handler", "rooftop unit",
        "exhaust", "supply air", "return air", "chiller", "boiler",
        "cooling tower", "vav", "fcu", "mechanical room", "cfm", "equipment schedule",
        "damper", "grille", "register",
    ],
    "electrical": [
        "panel", "circuit", "conduit", "wire", "voltage", "ampere",
        "transformer", "switchgear", "one line", "riser diagram", "fixture",
        "lighting", "emergency", "fire alarm", "low voltage", "generator",
        "disconnect", "breaker", "receptacle", "outlet",
    ],
    "plumbing": [
        "pipe", "drain", "waste", "vent", "sanitary", "water supply",
        "hot water", "cold water", "fixture unit", "floor drain", "cleanout",
        "backflow", "water heater", "pump", "valve", "lavatory", "toilet",
        "urinal", "sink", "hose bib",
    ],
    "civil": [
        "grading", "contour", "survey", "site plan", "topography",
        "storm drain", "utility", "pavement", "curb", "gutter",
        "easement", "property line", "setback", "benchmark", "elevation datum",
        "erosion control", "stormwater", "detention",
    ],
    "fire_protection": [
        "sprinkler", "standpipe", "fire suppression", "halon",
        "fm200", "deluge", "fire pump", "fire riser", "suppression system",
        "wet pipe", "dry pipe", "pre-action", "sprinkler head",
    ],
}

# Sheet number prefix → discipline
_PREFIX_DISCIPLINE: dict[str, str] = {
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

_SHEET_NUMBER_RE = re.compile(
    r"\b(FP|ID|SP|[ASCMEPLG])-?\d{3,4}[A-Z]?\b",
    re.IGNORECASE,
)


class DisciplineClassifier:
    """Hybrid classifier using sheet number, keywords, and VLM."""

    async def classify(
        self,
        sheet_number: Optional[str],
        extracted_text: str,
        image_bytes: bytes,
        vlm_extractor: Optional["VLMExtractor"] = None,
    ) -> DisciplineClassification:
        """Classify discipline using the best available signal."""
        # Priority 1: sheet number prefix (most reliable)
        result = self._classify_by_sheet_number(sheet_number)
        if result and result.confidence == "high":
            return result

        # Priority 2: keyword matching
        kw_result = self._classify_by_keywords(extracted_text)

        # Priority 3: VLM
        if vlm_extractor is not None:
            metadata_context = ""
            if sheet_number:
                metadata_context = f"Sheet number: {sheet_number}."
            if kw_result:
                metadata_context += f" Keyword-based guess: {kw_result.discipline}."
            vlm_result = await self._classify_by_vlm(
                image_bytes, metadata_context, vlm_extractor
            )
            if vlm_result and vlm_result.confidence in ("high", "medium"):
                return vlm_result

        if kw_result:
            return kw_result

        if result:
            return result

        return DisciplineClassification()

    def _classify_by_sheet_number(
        self, sheet_number: Optional[str]
    ) -> Optional[DisciplineClassification]:
        """Map sheet number prefix to discipline with high confidence."""
        if not sheet_number:
            return None
        sn = sheet_number.upper().strip()
        for prefix in sorted(_PREFIX_DISCIPLINE.keys(), key=len, reverse=True):
            if sn.startswith(prefix):
                return DisciplineClassification(
                    discipline=_PREFIX_DISCIPLINE[prefix],
                    sheet_type="unknown",
                    confidence="high",
                    reasoning=f"Sheet number prefix '{prefix}' maps to {_PREFIX_DISCIPLINE[prefix]}",
                )
        return None

    def _classify_by_keywords(
        self, text: str
    ) -> Optional[DisciplineClassification]:
        """Score disciplines by keyword presence in text."""
        if not text:
            return None
        text_lower = text.lower()
        scores: dict[str, int] = {}
        for discipline, keywords in _DISCIPLINE_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > 0:
                scores[discipline] = score

        if not scores:
            return None

        best = max(scores, key=lambda d: scores[d])
        return DisciplineClassification(
            discipline=best,
            sheet_type="unknown",
            confidence="medium",
            reasoning=f"Keyword match score: {scores[best]}",
        )

    async def _classify_by_vlm(
        self,
        image_bytes: bytes,
        metadata_context: str,
        vlm_extractor: "VLMExtractor",
    ) -> Optional[DisciplineClassification]:
        """Use VLM for discipline classification."""
        try:
            return await vlm_extractor.classify_discipline(image_bytes, metadata_context)
        except Exception as exc:
            logger.warning("VLM discipline classification failed: %s", exc)
            return None
