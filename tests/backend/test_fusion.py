"""Tests for hybrid fusion (RRF) and reranking (Milestone 2).

RRF math is asserted with exact values; rerank is verified to be the identity when disabled.
No network, no models.
"""

from __future__ import annotations

import pytest

from enterprise_ai_document_assistant.services.retrieval.fusion import (
    reciprocal_rank_fusion,
    rerank,
)
from enterprise_ai_document_assistant.services.retrieval.models import SearchResult


def test_rrf_single_list_exact_values() -> None:
    k = 60
    result = reciprocal_rank_fusion([["x", "y"]], k=k)
    assert result[0][0] == "x"
    assert result[1][0] == "y"
    assert result[0][1] == pytest.approx(1 / 61)
    assert result[1][1] == pytest.approx(1 / 62)


def test_rrf_fused_identical_lists() -> None:
    k = 60
    fused = reciprocal_rank_fusion([["x", "y"], ["x", "y"]], k=k)
    assert fused[0][0] == "x"
    assert fused[0][1] == pytest.approx(2 / 61)
    assert dict(fused)["y"] == pytest.approx(2 / 62)


def test_rrf_cross_list() -> None:
    k = 60
    cross = reciprocal_rank_fusion([["x", "z"], ["z", "x"]], k=k)
    assert dict(cross)["x"] == pytest.approx(1 / 61 + 1 / 62)


def test_rrf_tie_broken_by_chunk_id() -> None:
    result = reciprocal_rank_fusion([["b"], ["a"]], k=60)
    assert [cid for cid, _ in result] == ["a", "b"]
    assert result[0][1] == pytest.approx(result[1][1])


def test_rrf_empty_input() -> None:
    assert reciprocal_rank_fusion([], k=60) == []
    assert reciprocal_rank_fusion([[], []], k=60) == []


def test_rrf_deterministic() -> None:
    lists = [["a", "b", "c"], ["c", "a", "b"]]
    assert reciprocal_rank_fusion(lists, k=60) == reciprocal_rank_fusion(lists, k=60)


def _result(chunk_id: str) -> SearchResult:
    return SearchResult(
        chunk_id=chunk_id,
        document_id="d",
        filename="f.pdf",
        page=1,
        chunk_index=0,
        text="text",
        score=1.0,
        sources=("bm25",),
    )


def test_rerank_is_identity_when_disabled() -> None:
    results = [_result("a"), _result("b")]
    assert rerank("query", results) == results
    # Returns a new list (does not mutate the input).
    out = rerank("query", results)
    out.append(_result("c"))
    assert len(results) == 2
