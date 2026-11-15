"""Retrieval quality evaluation (Milestone 2).

A small, deterministic evaluation of BM25 retrieval quality over the synthetic eval corpus, using
Recall@K and Mean Reciprocal Rank (MRR). This is separate from the unit/API tests: it measures
whether relevant passages are actually retrieved and ranked well. No network, no models.
"""

from __future__ import annotations

from enterprise_ai_document_assistant.services.retrieval.bm25 import BM25Index

from .retrieval_fixtures import EVAL_QUERIES, corpus_chunks


def _recall_at_k(retrieved_doc_ids: list[str], relevant: list[str], k: int) -> float:
    """Recall@K: fraction of relevant docs retrieved in the top-K results."""
    if not relevant:
        return 1.0
    top_k = retrieved_doc_ids[:k]
    return len(set(top_k) & set(relevant)) / len(relevant)


def _reciprocal_rank(retrieved_doc_ids: list[str], relevant: list[str]) -> float:
    """Reciprocal rank of the first relevant result (0.0 if none)."""
    for rank, doc_id in enumerate(retrieved_doc_ids, start=1):
        if doc_id in relevant:
            return 1.0 / rank
    return 0.0


def test_bm25_retrieval_quality_meets_thresholds() -> None:
    """BM25 retrieval over the eval corpus achieves high Recall@3 and MRR.

    The corpus is small and the queries use discriminating keywords, so a correct BM25 index should
    retrieve the relevant document in the top results. Thresholds are deliberately lenient to avoid
    brittleness while still catching a broken retriever.
    """
    chunks = corpus_chunks()
    index = BM25Index()
    index.build(chunks)

    recalls: list[float] = []
    rr_scores: list[float] = []
    for query, relevant in EVAL_QUERIES.items():
        results = index.search(query, top_k=5)
        # Map chunk ids to document ids, preserving rank order.
        retrieved_doc_ids = []
        for chunk_id, _ in results:
            doc_id = chunk_id.rsplit(":", 1)[0]
            if doc_id not in retrieved_doc_ids:
                retrieved_doc_ids.append(doc_id)
        recalls.append(_recall_at_k(retrieved_doc_ids, relevant, k=3))
        rr_scores.append(_reciprocal_rank(retrieved_doc_ids, relevant))

    mean_recall = sum(recalls) / len(recalls)
    mrr = sum(rr_scores) / len(rr_scores)

    # A correct retriever retrieves the relevant doc in the top-3 for every query.
    assert mean_recall >= 0.9, f"Recall@3 too low: {mean_recall}"
    # The relevant doc should be ranked first (or near-first) for these discriminating queries.
    assert mrr >= 0.8, f"MRR too low: {mrr}"


def test_relevant_document_ranks_first_for_each_query() -> None:
    """For each eval query, the relevant document's chunk ranks first."""
    chunks = corpus_chunks()
    index = BM25Index()
    index.build(chunks)
    for query, relevant in EVAL_QUERIES.items():
        results = index.search(query, top_k=5)
        assert results, f"no results for query {query!r}"
        top_doc = results[0][0].rsplit(":", 1)[0]
        assert top_doc in relevant, f"top result {top_doc} not relevant for {query!r}"
