# Handoff — Agent 2 (Backend Engineering)

## Current status
**Milestone 2 (Document Processing, Indexing & Lexical Retrieval) is implemented and validated.** On
top of Milestone 1 (document management), the backend now chunks uploaded PDFs, indexes them for
lexical (BM25) search, persists the index across restarts, and serves the three Milestone 2
endpoints. The system runs in **lexical-only mode** with **no embedding provider, no real model
endpoints, and no API keys**. The Phase 0 `GET /health` and all Milestone 1 endpoints remain
operational.

## What changed (Milestone 2)
- `src/enterprise_ai_document_assistant/api/main.py` — included the retrieval router (Milestone 1
  documents router and `GET /health` preserved).
- `src/enterprise_ai_document_assistant/api/retrieval.py` — new thin HTTP router:
  `POST /documents/{id}/index`, `GET /index/status`, `POST /search`.
- `src/enterprise_ai_document_assistant/services/retrieval/` — new service package:
  - `models.py` — `Chunk`, `SearchResult`, `Citation` + `chunk_metadata` / `citation_from_result`.
  - `chunking.py` — structure-aware, deterministic chunker (page boundaries, word-boundary safe,
    configurable size/overlap).
  - `bm25.py` — `BM25Index` (rank-bm25 `BM25Okapi`) + deterministic tokenizer.
  - `chunk_store.py` — persists chunks as the single source of truth for the index.
  - `vector_store.py` — embedded ChromaDB store with a zero-vector no-op embedding function
    (no model runs); `vectors_present` tracking; upsert/delete/count.
  - `fusion.py` — Reciprocal Rank Fusion + `rerank` (identity when disabled).
  - `retriever.py` — `Retriever` (lexical/vector/hybrid, graceful degradation to lexical).
  - `index.py` — `IndexService` (index/reindex lifecycle, status, persistence).
- `src/enterprise_ai_document_assistant/services/documents/extraction.py` — added `PageText` and
  `extract_pdf_pages()` (per-page extraction for accurate page attribution). The existing
  `extract_pdf()` contract is unchanged.
- `tests/backend/` — new: `retrieval_fixtures.py` (eval corpus), `test_chunking.py`, `test_bm25.py`,
  `test_vector_store.py`, `test_fusion.py`, `test_retriever.py`, `test_index_service.py`,
  `test_retrieval_api.py`, `test_retrieval_quality.py`.
- `docs/backend.md` — updated with Milestone 2 architecture, API, behaviour, testing, limitations.

## API behaviour (Milestone 2, per `docs/contracts/api.md`)
- `POST /documents/{document_id}/index` → `200` `{"document_id", "chunks_indexed", "vectors_added"}`;
  `404` unknown doc; `409` doc has no extractable text (status `error`). Idempotent (reindex
  upserts by `chunk_id`). `vectors_added` is `0` in lexical-only mode.
- `GET /index/status` → `200` `{"documents_indexed", "chunks_indexed", "vectors_present",
  "retrieval_mode", "collection"}`. Works with an empty index.
- `POST /search` (body `{"query", "top_k"?}`) → `200` `{"query", "mode", "results", "citations"}`;
  `422` for empty/invalid query or `top_k`. Empty match → `200` with `results: []`. `mode` echoes the
  effective mode (lexical in Milestone 2).

## ChromaDB integration approach (critical requirement)
- **No automatic embedding model execution in production paths.** Verified against `chromadb 1.5.9`:
  `add` without a custom embedding function runs Chroma's default local ONNX model (no download, but
  a real computation). To avoid this, `VectorStore` supplies a **zero-vector no-op embedding
  function** (returns a fixed zero vector, no model). The zero vector is a storage placeholder and is
  **never** used for ranking.
- `vectors_present` is `false` in lexical-only mode; `VectorStore.query` raises if called when no
  real vectors are present, so placeholder vectors are never presented as semantic results.
- Verified: `upsert` with a real vector over the placeholder replaces it without duplicating
  (Milestone 3 activation path). The collection persists to `vector_store_path` (volume-backed in
  Docker).

## ⚠️ Coordination items for Agent 1

### 1. `.gitignore` bug (RESOLVED)
- **Issue (original):** `.gitignore` line 29 `documents/` (intended to ignore runtime uploaded
  documents under `.data/`) also matched the **source** package
  `src/enterprise_ai_document_assistant/services/documents/`, which would have kept the Milestone 1
  `services/documents/` package out of version control.
- **Resolution:** the rule is now `/documents/` (anchored to the repo root), so it no longer matches
  the source package. Verified: `git check-ignore` on
  `src/enterprise_ai_document_assistant/services/documents/extraction.py` reports it is **not**
  ignored. The source package is now trackable; it simply has not been committed yet (Milestone 2
  work is pending commit).
- **Action requested:** none — resolved. (Committing the Milestone 1/2 source remains a coordination
  task for the next integration pass.)

### 2. No new dependencies required
- Milestone 2 uses `chromadb` and `rank-bm25`, both already added to `pyproject.toml`/`uv.lock` by
  Agent 1. No further dependency or config changes are needed from me.

## Validation results (executed on this machine, Windows)
- `uv run ruff check src tests/backend` — **passed** (all checks).
- `uv run ruff format --check src tests/backend` — **passed** (36 files).
- `uv run pytest tests/backend tests/integration` — **120 passed** (106 backend + 14 integration,
  including Agent 1's 13 retrieval-infrastructure tests).
- `uv run pytest` (full suite) — **200 passed** (backend + frontend + integration).
- End-to-end smoke test (TestClient, temp dirs): upload 4-page PDF → `201`; index → `200` with
  `chunks_indexed`; `GET /index/status` → correct counts, `vectors_present: false`,
  `retrieval_mode: lexical`; `POST /search` → ranked results with citations; empty query → `422`;
  no-match → `200` `results: []`; unknown doc index → `404`; encrypted doc index → `409`;
  `GET /health` → `ok`.
- OpenAPI path check: all six endpoints registered (`/health`, `/documents`, `/documents/{id}`,
  `/documents/{id}/index`, `/index/status`, `/search`).
- App starts with default settings (`retrieval_mode=lexical`, `embedding_api_key=None`).
- Retrieval quality eval: Recall@3 and MRR over the synthetic eval corpus meet thresholds
  (relevant document ranks first for each query).
- No runtime data committed (`.data/` is git-ignored; tests use temp dirs).

## Known limitations
- **Lexical-only retrieval.** No real embeddings; `vectors_present` is `false`, `mode` is `lexical`.
  Vector/hybrid is prepared but inactive until Milestone 3. The Chroma collection stores a zero
  placeholder vector (never used for ranking).
- **Scanned/image-only PDFs** produce no chunks (no searchable text); OCR is out of scope.
- **BM25 on very small corpora:** a query term present in every chunk has IDF ≤ 0 and is not
  discriminating (clamped to 0). Inherent to BM25; does not affect real documents.
- **Chunk `char_start`/`char_end`** are offsets within the chunk's page text (chunks never cross
  page boundaries), not the whole document.
- Single-user local development storage (filesystem + embedded Chroma); no multi-tenancy, no
  reranker, no LLM generation (later milestones).
- Cross-platform (Linux) validation was not executed here; the code is portable (pure-Python deps,
  relative paths, no machine-specific values) but Linux runs are documented, not tested, on this
  machine.

## Remaining tasks (for later milestones — NOT started)
- **Milestone 3:** concrete OpenAI-compatible embedding provider (real vectors upserted over the
  placeholder), vector/hybrid retrieval active, optional reranking, RAG orchestration + grounded
  answer generation with an LLM.
- **Milestone 4:** source citations attached to generated answers.
- Document deletion endpoint (not in the contract yet).

## Instructions / notes for Agents 1 and 3
- **Agent 1:** the `.gitignore` `documents/` rule is now anchored (`/documents/`) and no longer
  ignores the source package (see item 1, resolved). No new dependencies are needed from me for
  Milestone 2.
- **Agent 3:** the Milestone 2 API is ready to build against. After uploading a document, call
  `POST /documents/{id}/index`, then `GET /index/status` to show progress (`409` = no extractable
  text). Search box → `POST /search` with `{"query", "top_k"}`; render each result with `filename`,
  `page`, `score`, and show `citations` as source references. An empty `results` array is a valid
  "no matches" state. In lexical-only mode `sources` is `["bm25"]` and `mode` is `"lexical"`.
