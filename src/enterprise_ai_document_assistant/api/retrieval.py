"""Retrieval endpoints (Milestone 2).

Thin HTTP layer over :class:`IndexService`. Route handlers contain no business logic; they translate
between HTTP and the service and map service exceptions to HTTP status codes.

Endpoints (see ``docs/contracts/api.md`` Milestone 2 addition):
- ``POST /documents/{document_id}/index`` — index one document.
- ``GET /index/status`` — index status.
- ``POST /search`` — search indexed documents.
"""

from __future__ import annotations

import logging
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from enterprise_ai_document_assistant.core.config import get_settings
from enterprise_ai_document_assistant.services.documents.storage import (
    DocumentNotFoundError,
    DocumentStore,
)
from enterprise_ai_document_assistant.services.retrieval.index import (
    DocumentNotIndexableError,
    IndexService,
)
from enterprise_ai_document_assistant.services.retrieval.models import (
    Citation,
    SearchResult,
    citation_from_result,
)
from enterprise_ai_document_assistant.services.retrieval.vector_store import VectorStore

logger = logging.getLogger(__name__)

router = APIRouter(tags=["retrieval"])


# --- Response models (Milestone 2) -------------------------------------------


class IndexResponse(BaseModel):
    """Response for ``POST /documents/{document_id}/index``."""

    document_id: str
    chunks_indexed: int
    vectors_added: int


class IndexStatusResponse(BaseModel):
    """Response for ``GET /index/status``."""

    documents_indexed: int
    chunks_indexed: int
    vectors_present: bool
    retrieval_mode: str
    collection: str


class SearchRequest(BaseModel):
    """Request body for ``POST /search``."""

    query: str = Field(min_length=1, description="Non-empty search query.")
    top_k: int | None = Field(
        default=None, ge=1, description="Max results; defaults to config retrieval_top_k."
    )


class SearchResponse(BaseModel):
    """Response for ``POST /search``."""

    query: str
    mode: str
    results: list[SearchResult]
    citations: list[Citation]


# --- Dependency wiring -------------------------------------------------------


@lru_cache
def _index_service() -> IndexService:
    """Build a cached :class:`IndexService` from application settings.

    The vector store is created lazily so the app starts and serves lexical search even before any
    document is indexed. The Chroma collection is created on first use (no model runs).
    """
    settings = get_settings()
    document_store = DocumentStore(settings.documents_dir)
    vector_store = VectorStore(
        path=settings.vector_store_path,
        collection_name=settings.chroma_collection,
        distance_fn=settings.chroma_distance_fn,
    )
    return IndexService(
        settings=settings,
        document_store=document_store,
        vector_store=vector_store,
    )


def get_index_service(service: IndexService = Depends(_index_service)) -> IndexService:  # noqa: B008
    """FastAPI dependency returning the shared :class:`IndexService`."""
    return service


# --- Endpoints ----------------------------------------------------------------


@router.post(
    "/documents/{document_id}/index",
    response_model=IndexResponse,
    summary="Index one document",
)
def index_document(
    document_id: str,
    service: IndexService = Depends(get_index_service),  # noqa: B008
) -> IndexResponse:
    """Index (or reindex) an uploaded document.

    Returns ``200`` with the count of indexed chunks. ``404`` if the document does not exist;
    ``409`` if the document has no extractable text (status ``error``).
    """
    try:
        result = service.index_document(document_id)
    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DocumentNotIndexableError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return IndexResponse(
        document_id=result.document_id,
        chunks_indexed=result.chunks_indexed,
        vectors_added=result.vectors_added,
    )


@router.get("/index/status", response_model=IndexStatusResponse, summary="Index status")
def index_status(
    service: IndexService = Depends(get_index_service),  # noqa: B008
) -> IndexStatusResponse:
    """Return the current index status (works with an empty index)."""
    s = service.status()
    return IndexStatusResponse(
        documents_indexed=s.documents_indexed,
        chunks_indexed=s.chunks_indexed,
        vectors_present=s.vectors_present,
        retrieval_mode=s.retrieval_mode,
        collection=s.collection,
    )


@router.post("/search", response_model=SearchResponse, summary="Search indexed documents")
def search(
    search_request: SearchRequest,
    service: IndexService = Depends(get_index_service),  # noqa: B008
) -> SearchResponse:
    """Search indexed documents and return ranked results with citations.

    ``422`` for a missing/empty query or invalid ``top_k`` (FastAPI validation). An empty match
    returns ``200`` with ``results: []`` (not a 404).
    """
    results, mode = service.search(search_request.query, top_k=search_request.top_k)
    citations = [citation_from_result(r) for r in results]
    return SearchResponse(
        query=search_request.query,
        mode=mode,
        results=results,
        citations=citations,
    )
