"""BM25 lexical index (Milestone 2).

Implements the ``BM25Index`` interface from ``docs/contracts/retrieval.md`` using ``rank-bm25``
(``BM25Okapi``). Tokenization is simple and deterministic (lowercase, split on non-alphanumerics)
so indexing and query preprocessing are consistent and reproducible. No network, no model.

The index is rebuilt from the stored chunks (it is not separately persisted), which keeps the chunk
store as the single source of truth and avoids two divergent stores.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Sequence

from rank_bm25 import BM25Okapi

from enterprise_ai_document_assistant.services.retrieval.models import Chunk

logger = logging.getLogger(__name__)

#: Deterministic tokenizer: lowercase, split on runs of non-alphanumerics, drop empties.
_TOKEN_SPLIT = re.compile(r"[^a-z0-9]+")


def tokenize(text: str) -> list[str]:
    """Deterministic tokenization per the contract (lowercase, split on non-alphanumerics)."""
    return [t for t in _TOKEN_SPLIT.split(text.lower()) if t]


class BM25Index:
    """In-memory BM25 index over a set of chunks.

    ``build`` (re)indexes a full set of chunks. ``search`` returns ``[(chunk_id, score)]``
    best-first, deterministic (ties broken by chunk id ascending). An empty corpus returns ``[]``.
    """

    def __init__(self) -> None:
        self._chunks: dict[str, Chunk] = {}
        self._order: list[str] = []
        self._bm25: BM25Okapi | None = None

    def build(self, chunks: Sequence[Chunk]) -> None:
        """(Re)build the index from the given chunks, preserving a deterministic order."""
        # Sort by id so the corpus order (and thus score alignment) is deterministic regardless of
        # insertion order.
        ordered = sorted(chunks, key=lambda c: c.id)
        self._order = [c.id for c in ordered]
        self._chunks = {c.id: c for c in ordered}
        corpus = [tokenize(c.text) for c in ordered]
        self._bm25 = BM25Okapi(corpus) if corpus else None
        logger.debug("Built BM25 index over %d chunk(s)", len(self._order))

    def search(self, query: str, top_k: int) -> list[tuple[str, float]]:
        """Return ``[(chunk_id, bm25_score)]`` best-first, truncated to ``top_k``.

        Scores are clamped to be non-negative (BM25Okapi can yield negative scores when a query
        term is very frequent). Chunks with a zero score (no matching query term) are omitted, so a
        query that matches nothing returns ``[]``. Returns ``[]`` for an empty corpus or a query
        with no tokens.
        """
        if self._bm25 is None or not self._chunks or top_k <= 0:
            return []
        query_tokens = tokenize(query)
        if not query_tokens:
            return []
        scores = self._bm25.get_scores(query_tokens)  # aligned with self._order
        # Clamp to non-negative and drop zero scores (no term match).
        clamped = [max(0.0, float(s)) for s in scores]
        candidates = [
            (self._order[i], clamped[i]) for i in range(len(self._order)) if clamped[i] > 0.0
        ]
        candidates.sort(key=lambda pair: (-pair[1], pair[0]))
        return candidates[:top_k]

    def get(self, chunk_id: str) -> Chunk | None:
        """Return the chunk for an id, or ``None`` if not indexed."""
        return self._chunks.get(chunk_id)

    def __len__(self) -> int:
        return len(self._chunks)
