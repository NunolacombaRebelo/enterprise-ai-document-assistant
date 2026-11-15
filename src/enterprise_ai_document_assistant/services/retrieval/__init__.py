"""Retrieval service (Milestone 2).

Owned by Agent 2 (Backend Engineering). Responsibilities:
- Structure-aware, deterministic chunking with page attribution.
- BM25 lexical indexing (rank-bm25).
- Embedded ChromaDB vector store (prepared for future real embeddings; lexical-only in Milestone 2).
- Hybrid fusion (Reciprocal Rank Fusion) and optional reranking.
- Indexing lifecycle and status.

Business logic lives here; the API layer (``api/retrieval.py``) is a thin HTTP wrapper. See
``docs/contracts/retrieval.md`` for the data models and interfaces implemented by this package.
"""

from enterprise_ai_document_assistant.services.retrieval.bm25 import BM25Index, tokenize
from enterprise_ai_document_assistant.services.retrieval.chunking import (
    ChunkingConfig,
    chunk_pages,
    chunk_text,
)
from enterprise_ai_document_assistant.services.retrieval.fusion import (
    reciprocal_rank_fusion,
    rerank,
)
from enterprise_ai_document_assistant.services.retrieval.index import (
    DocumentNotIndexableError,
    IndexResult,
    IndexService,
    IndexStatus,
)
from enterprise_ai_document_assistant.services.retrieval.models import (
    Chunk,
    Citation,
    SearchResult,
    chunk_metadata,
    citation_from_result,
)
from enterprise_ai_document_assistant.services.retrieval.retriever import Retriever
from enterprise_ai_document_assistant.services.retrieval.vector_store import VectorStore

__all__ = [
    "BM25Index",
    "Chunk",
    "ChunkingConfig",
    "Citation",
    "DocumentNotIndexableError",
    "IndexResult",
    "IndexService",
    "IndexStatus",
    "Retriever",
    "SearchResult",
    "VectorStore",
    "chunk_metadata",
    "chunk_pages",
    "chunk_text",
    "citation_from_result",
    "reciprocal_rank_fusion",
    "rerank",
    "tokenize",
]
