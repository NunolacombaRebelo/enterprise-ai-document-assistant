"""Hybrid fusion and optional reranking (Milestone 2).

Implements :func:`reciprocal_rank_fusion` (the standard hybrid combiner, no model, fully
deterministic) and :func:`rerank` (identity when disabled) per ``docs/contracts/retrieval.md``.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence

from enterprise_ai_document_assistant.services.retrieval.models import SearchResult

logger = logging.getLogger(__name__)


def reciprocal_rank_fusion(
    ranked_lists: Sequence[Sequence[str]], k: int = 60
) -> list[tuple[str, float]]:
    """Fuse multiple ranked lists of chunk ids via Reciprocal Rank Fusion.

    ``score(c) = sum over each list L containing c of 1 / (k + rank_L(c))`` (rank is 1-based).
    Returns ``[(chunk_id, fused_score)]`` sorted by fused score descending, ties broken by chunk id
    ascending for determinism. An empty input returns ``[]``.
    """
    scores: dict[str, float] = {}
    for ranked in ranked_lists:
        for rank, chunk_id in enumerate(ranked, start=1):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))


def rerank(query: str, results: Sequence[SearchResult]) -> list[SearchResult]:
    """Reorder results for the query.

    In Milestone 2 this is the **identity function** (no reranker is configured; ``rerank_enabled``
    defaults to ``False``). A real reranker is a later-milestone concern and must not require a
    model here. The ``query`` argument is accepted for interface stability.
    """
    del query  # unused in Milestone 2; kept for the contract signature
    return list(results)
