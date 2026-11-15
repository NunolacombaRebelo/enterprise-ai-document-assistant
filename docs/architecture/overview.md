# Architecture Overview

## Design: modular monolith

The system is a **modular monolith**: one Python package, one FastAPI backend, one Streamlit
frontend. This keeps the project simple to run, test, and reason about — appropriate for a
portfolio project and for AI-assisted development where a small, well-bounded surface area reduces
the chance of agents drifting into inconsistent designs.

Microservices, message brokers, and external databases are deliberately **not** introduced. They
would add operational complexity without benefit at this scale.

## Major components

```
┌──────────────────────┐        HTTP (API_BASE_URL)        ┌───────────────────────────┐
│  Streamlit frontend  │ ─────────────────────────────────▶ │   FastAPI backend         │
│  frontend/app.py     │   /health, /documents, /search,    │   api/main.py -> app      │
│  port 8501           │   /index/status, ...               │   port 8000               │
└──────────────────────┘                                     └─────────────┬─────────────┘
                                                                           │
                                                          ┌────────────────┴────────────────┐
                                                          ▼                                 ▼
                                              ┌─────────────────────┐          ┌──────────────────────┐
                                              │  services/          │          │  providers/          │
                                              │  ingestion, extract,│          │  LLM / embedding /   │
                                              │  chunking, embed,   │          │  vector-store        │
                                              │  retrieval          │          │  abstractions        │
                                              └─────────────────────┘          └──────────────────────┘
                                                                              (future phases)
```

- **`api/`** — FastAPI application and endpoints. `main.py` holds the `app` object and includes the
  documents and retrieval routers (`GET /health`, `POST /documents`, `GET /documents`,
  `GET /documents/{id}`, `POST /documents/{id}/index`, `GET /index/status`, `POST /search`). Agent 2
  owns this.
- **`core/`** — shared configuration (`config.py`, pydantic-settings) and cross-cutting utilities.
  Agent 1 owns config; Agent 2 may extend it through coordination.
- **`services/`** — backend business logic. `services/documents/` (ingestion, validation, PDF text
  extraction, persistence) and `services/retrieval/` (chunking, BM25, embedded-Chroma vector store,
  RRF fusion, retriever, index lifecycle) are implemented. Agent 2.
- **`rag/`** — RAG orchestration: assembling grounded answers with citations. Agent 2, future
  (Milestone 3+). Currently a placeholder.
- **`providers/`** — planned abstractions over LLM, embedding, and vector-store implementations so
  the rest of the code does not depend on a specific vendor. Agent 2, future (Milestone 3+).
  Currently a placeholder; the retriever takes an untyped `embedder` for now.
- **`frontend/`** — Streamlit app. Talks to the backend over HTTP only via `API_BASE_URL`. Agent 3.

## Responsibility boundaries

- The frontend never imports backend internals; it communicates over HTTP.
- `services/` and `rag/` do not depend on specific provider vendors; they depend on the abstractions
  in `providers/`.
- Configuration is centralized in `core/config.py`; components read settings from there, not from
  scattered environment reads.

## API / frontend communication

- Frontend → backend is HTTP only. No shared in-process state.
- The frontend reads `API_BASE_URL` from the environment: `http://localhost:8000` natively,
  `http://api:8000` inside Docker Compose.
- See `docs/contracts/api.md` for the authoritative endpoint contract.

## RAG data flow

1. **Ingest** (Milestone 1, done): upload a PDF → validate → extract text + page count.
2. **Chunk** (Milestone 2, done): structure-aware chunking that preserves page boundaries → `Chunk`
   records with citation metadata (document_id, filename, page, chunk_index, per-page char offsets).
3. **Index** (Milestone 2, done): build a BM25 lexical index and store chunks in embedded ChromaDB.
   Embeddings are an **optional slot** — in Milestone 2 no embeddings are generated, so the index is
   lexical-only. Real embeddings are injected externally in a later milestone without rebuilding.
4. **Retrieve** (Milestone 2, done): BM25 (lexical), vector similarity (when vectors exist), or
   hybrid via Reciprocal Rank Fusion. Optional reranking (off by default). In Milestone 2 the system
   runs lexical-only; vector/hybrid degrade to lexical when no real vectors are present.
5. **Generate** (Milestone 3+): call an OpenAI-compatible LLM with retrieved context. *Not in
   Milestone 2.*
6. **Cite** (Milestone 2, metadata only): citations are derived from chunk metadata (document +
   page), never from model output.

See `docs/contracts/retrieval.md` for the exact data models and interfaces, and ADRs 0007/0008 for
the deployment and retrieval decisions.

## Provider abstraction (planned)

`providers/` is **planned** (Milestone 3+) and is currently a placeholder. The intent is thin
interfaces so the rest of the system does not depend on a specific vendor:
- **Embedding** — text-to-vector. No concrete provider is wired up in Milestone 2; the retriever
  takes an untyped `embedder` and runs lexical-only. A concrete OpenAI-compatible implementation is
  added in Milestone 3. No model is downloaded or called in Milestone 2.
- **Vector store** — embedded ChromaDB persistence (ADR 0007), implemented in
  `services/retrieval/vector_store.py`.
- **LLM** — OpenAI-compatible chat completion (Milestone 3+).

The retrieval layer is designed to depend on these abstractions rather than a specific library's API,
so providers can be swapped without changing the application.

## ChromaDB persistence (embedded)

ChromaDB runs **embedded** (in-process Python client, persistent local mode) — see ADR 0007. It
persists to `vector_store_path` (default `.data/vector-store`, configured by `VECTOR_STORE_PATH`).
In Docker Compose this path is backed by the named volume `vector-data` mounted at `/app/.data` on
the `api` service, so the index survives container restarts. The directory is git-ignored; no vector
data is ever committed. No external ChromaDB server/service is required.
