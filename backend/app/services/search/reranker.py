from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

_RRF_K = 60


def _rrf_score(rank: int, k: int = _RRF_K) -> float:
    return 1.0 / (k + rank)


def reciprocal_rank_fusion(
    semantic_results: list[dict],
    keyword_results: list[dict],
    semantic_weight: float = 0.7,
    keyword_weight: float = 0.3,
    min_score: float = 0.0,
) -> list[dict]:
    """Fuse semantic and keyword results using Reciprocal Rank Fusion.

    Each dict must have a 'sheet_id' key.  Extra fields from both result sets
    are merged, with semantic result fields taking precedence.
    """
    scores: dict[str, float] = {}
    semantic_scores: dict[str, float] = {}
    keyword_scores: dict[str, float] = {}
    all_data: dict[str, dict] = {}

    for rank, item in enumerate(semantic_results):
        sid = item["sheet_id"]
        rrf = _rrf_score(rank + 1) * semantic_weight
        scores[sid] = scores.get(sid, 0.0) + rrf
        semantic_scores[sid] = item.get("semantic_score", item.get("score", 0.0))
        all_data[sid] = {**item}

    for rank, item in enumerate(keyword_results):
        sid = item["sheet_id"]
        rrf = _rrf_score(rank + 1) * keyword_weight
        scores[sid] = scores.get(sid, 0.0) + rrf
        keyword_scores[sid] = item.get("keyword_score", item.get("score", 0.0))
        if sid not in all_data:
            all_data[sid] = {**item}
        else:
            # Merge fields — prefer semantic data, fill missing from keyword
            for k, v in item.items():
                if k not in all_data[sid] or all_data[sid][k] is None:
                    all_data[sid][k] = v

    fused = []
    for sid, score in scores.items():
        if score < min_score:
            continue
        entry = {**all_data[sid]}
        entry["score"] = score
        entry["semantic_score"] = semantic_scores.get(sid)
        entry["keyword_score"] = keyword_scores.get(sid)
        fused.append(entry)

    fused.sort(key=lambda x: x["score"], reverse=True)
    return fused
