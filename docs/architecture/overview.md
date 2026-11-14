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
│  frontend/app.py     │   GET /health, (future endpoints)  │   api/main.py -> app      │
│  port 8501           │ ◀───────────────────────────────── │   port 8000               │
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

- **`api/`** — FastAPI application and endpoints. `main.py` holds the `app` object. Phase 0 exposes
  `GET /health`. Agent 2 owns this.
- **`core/`** — shared configuration (`config.py`, pydantic-settings) and cross-cutting utilities.
  Agent 1 owns config; Agent 2 may extend it through coordination.
- **`services/`** — backend business logic: document ingestion, PDF text extraction, chunking,
  embedding generation, retrieval. Agent 2, future phases.
- **`rag/`** — RAG orchestration: assembling grounded answers with citations. Agent 2, future.
- **`providers/`** — abstractions over LLM, embedding, and vector-store implementations so the rest
  of the code does not depend on a specific vendor. Agent 2, future.
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

## Planned RAG data flow (future phases)

1. **Ingest** (Phase 1): upload a PDF → extract text.
2. **Chunk** (Phase 2): split text into passages.
3. **Embed + index** (Phase 2): generate embeddings, store in the vector store (ChromaDB).
4. **Retrieve** (Phase 3): for a question, retrieve the most relevant passages.
5. **Generate** (Phase 3): call the LLM with retrieved context to produce a grounded answer.
6. **Cite** (Phase 4): attach source citations (document + passage) to the answer.

## Future provider abstraction

`providers/` will define thin interfaces for:
- **LLM** — OpenAI-compatible chat completion.
- **Embedding** — text-to-vector.
- **Vector store** — ChromaDB persistence.

This lets the rest of the system swap implementations without changes. It is intentionally not built
in Phase 0 (no speculative code).

## Future ChromaDB persistence

When vector storage lands (Phase 2), ChromaDB will persist to a directory under `.data/vector-store`
(configured by `VECTOR_STORE_PATH`). In Docker Compose this path is backed by the named volume
`vector-data` mounted at `/app/.data` on the `api` service, so embeddings survive container restarts.
The directory is git-ignored; no vector data is ever committed.
