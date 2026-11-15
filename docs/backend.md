# Backend — Enterprise AI Document Assistant

Backend engineering documentation (Agent 2). The backend is a FastAPI modular monolith: one Python
package, one app object, business logic in `services/`, thin HTTP handlers in `api/`.

## Status

- **Milestone 1 (Document Management): implemented.** PDF upload, validation, text extraction,
  local persistence, listing, and status retrieval are functional and tested.
- **Milestone 2 (Document Processing, Indexing & Lexical Retrieval): implemented.** Structure-aware
  chunking, BM25 lexical indexing, embedded-ChromaDB vector store (prepared for future embeddings),
  indexing lifecycle, and the `POST /documents/{id}/index`, `GET /index/status`, `POST /search`
  endpoints are functional and tested. The system runs in **lexical-only mode** with no embedding
  provider or API key.
- `GET /health` (Phase 0 contract) remains operational.

## Layout

```
src/enterprise_ai_document_assistant/
├─ api/
│  ├─ main.py          # app object; includes the documents + retrieval routers; GET /health
│  ├─ documents.py     # thin HTTP router for /documents (no business logic)
│  └─ retrieval.py     # thin HTTP router for /index/status, /search, /documents/{id}/index
├─ core/
│  └─ config.py        # Settings (Agent 1-owned; extended with backend-specific settings)
└─ services/
   ├─ documents/       # Milestone 1
   │  ├─ models.py     # Pydantic request/response models + DocumentStatus
   │  ├─ validation.py # upload validation (type, size, magic, safe filename)
   │  ├─ extraction.py # pypdf wrapper + typed exceptions + per-page extraction
   │  ├─ storage.py    # local development persistence (filesystem)
   │  └─ service.py    # DocumentService orchestration
   └─ retrieval/       # Milestone 2
      ├─ models.py     # Chunk, SearchResult, Citation (contract data models)
      ├─ chunking.py   # structure-aware, deterministic chunker (page boundaries)
      ├─ bm25.py       # BM25Index (rank-bm25) + deterministic tokenizer
      ├─ chunk_store.py# persists chunks (single source of truth for the index)
      ├─ vector_store.py# embedded ChromaDB store (zero-vector no-op EF; lexical-only)
      ├─ fusion.py     # Reciprocal Rank Fusion + rerank (identity when disabled)
      ├─ retriever.py  # Retriever (lexical/vector/hybrid, graceful degradation)
      └─ index.py      # IndexService (index/reindex lifecycle + status)
```

## API (Milestone 1)

| Method | Path | Success | Errors |
| --- | --- | --- | --- |
| `POST` | `/documents` | `201` + `DocumentMetadata` | `400` invalid upload (empty / not a PDF / oversized) |
| `GET` | `/documents` | `200` `{"documents": [...]}` | — |
| `GET` | `/documents/{document_id}` | `200` + `DocumentMetadata` | `404` unknown id |

`DocumentMetadata`:

```json
{
  "id": "uuid",
  "filename": "sanitized-name.pdf",
  "status": "processed",
  "page_count": 5,
  "created_at": "2026-11-14T20:12:27Z",
  "error": null
}
```

- `status` is `processed` or `error`. Encrypted or malformed PDFs are **accepted and stored** with
  `status: "error"` and a human-readable `error` reason (so the user sees what happened); invalid
  uploads (empty, non-PDF, oversized) are **rejected** with `400`.
- `page_count` is `null` when extraction did not succeed.

## API (Milestone 2)

| Method | Path | Success | Errors |
| --- | --- | --- | --- |
| `POST` | `/documents/{document_id}/index` | `200` `{"document_id", "chunks_indexed", "vectors_added"}` | `404` unknown doc; `409` doc has no extractable text (status `error`) |
| `GET` | `/index/status` | `200` `IndexStatus` | — |
| `POST` | `/search` | `200` `{"query", "mode", "results", "citations"}` | `422` empty/invalid query or `top_k` |

`IndexStatus`: `documents_indexed`, `chunks_indexed`, `vectors_present` (false in lexical-only mode),
`retrieval_mode` (`lexical`), `collection`.

`SearchResult`: `chunk_id`, `document_id`, `filename`, `page`, `chunk_index`, `text`, `score`
(higher = better), `sources` (e.g. `["bm25"]`). `Citation`: `document_id`, `filename`, `page`,
`chunk_index`, `excerpt`.

- `POST /search` takes `{"query": "<non-empty>", "top_k": <positive int, optional>}`. An empty match
  returns `200` with `results: []` (not a 404). `mode` echoes the effective mode actually used
  (may be `lexical` even if `hybrid` is configured but no vectors are present).
- `POST /documents/{id}/index` is idempotent: reindexing replaces the document's chunks (upsert by
  `chunk_id`) rather than duplicating them. `vectors_added` is `0` in lexical-only mode.

## Behaviour (Milestone 2)

- **Chunking** (`chunking.py`): structure-aware and deterministic. Each chunk is confined to a
  single page (accurate page attribution). Paragraphs are never split mid-paragraph; a paragraph
  larger than the target size is split at word boundaries (never mid-word). Configurable
  `chunk_size_tokens` / `chunk_overlap_tokens` (approximated by whitespace-delimited words — no
  tokenizer dependency). `chunk_id` is `f"{document_id}:{chunk_index}"` — globally unique and stable
  across reindexing. Empty/whitespace-only pages produce no chunks.
- **BM25** (`bm25.py`): `rank-bm25` `BM25Okapi` with a deterministic tokenizer (lowercase, split on
  non-alphanumerics). Scores are clamped to be non-negative; chunks with a zero score (no matching
  term) are omitted, so a no-match query returns `[]`. The index is rebuilt from the chunk store on
  startup (not separately persisted).
- **Vector store** (`vector_store.py`): embedded ChromaDB (ADR 0007) persisting to
  `vector_store_path`. A **zero-vector no-op embedding function** satisfies Chroma's add-time
  requirement without running any embedding model. `vectors_present` tracks whether any chunk carries
  a real embedding; `query` raises if called when no real vectors are present, so placeholder vectors
  are never presented as semantic results. In Milestone 2 retrieval is lexical-only; the Chroma
  collection stores chunk text + metadata and is prepared for future real-embedding upserts.
- **Retriever** (`retriever.py`): mode-driven. `lexical` = BM25 only. `vector`/`hybrid` degrade
  gracefully to lexical when no vectors are present (logging a warning) rather than returning dummy
  semantic results. Hybrid fuses BM25 + vector via Reciprocal Rank Fusion (`rrf_k`).
- **Indexing** (`index.py`): `IndexService.index_document` re-extracts from the stored PDF
  (per-page), chunks it, persists the chunks (single source of truth), rebuilds BM25, and upserts
  into Chroma. The original uploaded document is always preserved; indexing never deletes user data.
  `status()` reports counts and `vectors_present`.

## Configuration (Milestone 2)

Milestone 2 settings are already present in `core/config.py` (added by Agent 1): `vector_store_path`,
`chroma_collection`, `chroma_distance_fn`, `retrieval_mode` (default `lexical`), `rrf_k`,
`retrieval_top_k`, `rerank_enabled`, `chunk_size_tokens`, `chunk_overlap_tokens`, and optional
`embedding_base_url` / `embedding_api_key` (default `None`). No model key is required to start.

## Security

- Uploaded files are untrusted input: type/size/magic validated before processing; filenames
  sanitized; storage keyed by UUID (no path traversal).
- Uploaded content is never executed; only the PDF structure is parsed.
- No file contents, sizes, or secrets are logged; only the sanitized filename and a fixed limit.
- Runtime data lives under `.data/` (git-ignored); nothing is committed.
- No embedding model is downloaded or executed in production paths (zero-vector no-op EF).

## Testing

`tests/backend/` (Agent 2-owned):

- **Milestone 1:** `test_validation.py`, `test_extraction.py`, `test_storage.py`,
  `test_documents_api.py`, `pdf_factory.py` (synthetic PDF fixtures).
- **Milestone 2:**
  - `test_chunking.py` — single/multi-page, empty content, paragraph boundaries, word-boundary
    safety, overlap, deterministic ids, page attribution.
  - `test_bm25.py` — determinism, ranking, non-negative scores, empty corpus, no-match, top_k.
  - `test_vector_store.py` — Chroma safety (no implicit model, no placeholder-as-semantic),
    persistence, metadata contract, upsert idempotency, real-embedding upsert path.
  - `test_fusion.py` — RRF exact-value math, tie-breaking, rerank identity.
  - `test_retriever.py` — lexical/vector/hybrid modes, degradation, no-provider guarantee.
  - `test_index_service.py` — index/reindex idempotency, status, persistence across restart,
    not-indexable (409) case.
  - `test_retrieval_api.py` — the three Milestone 2 endpoints + Milestone 1 regression.
  - `test_retrieval_quality.py` — Recall@K / MRR evaluation over a synthetic eval corpus
    (`retrieval_fixtures.py`).

All tests run without network, credentials, or paid services.

## Dependencies

- **`pypdf`** (runtime) — PDF text extraction (Milestone 1).
- **`chromadb`** (runtime) — embedded vector store (Milestone 2).
- **`rank-bm25`** (runtime) — BM25 lexical retrieval (Milestone 2).

All three are declared in `pyproject.toml`/`uv.lock` (coordinated by Agent 1).

## Limitations

- **Lexical-only retrieval.** No real embeddings are configured; `vectors_present` is `false` and
  `mode` is `lexical`. Vector/hybrid retrieval is prepared but inactive until real embeddings land
  (Milestone 3). The Chroma collection stores a zero placeholder vector (never used for ranking).
- **Scanned/image-only PDFs** are classified `processed` with empty text (page count known); OCR is
  out of scope. Such documents produce no chunks and contribute nothing to search.
- **BM25 on very small corpora:** when a query term appears in every indexed chunk, its IDF is ≤ 0
  and it is not discriminating (clamped to 0). This is inherent to BM25 and does not affect real
  documents with varied content.
- **Chunk `char_start`/`char_end`** are offsets within the chunk's *page* text (chunks never cross
  page boundaries), not the whole document.
- Single-user local development storage (filesystem + embedded Chroma). No multi-tenancy, no
  background processing, no reranker, no LLM generation (later milestones).
