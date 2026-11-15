# ADR 0007 — Use embedded ChromaDB for vector storage

## Status
Accepted (Milestone 2)

## Context
Milestone 2 introduces persistent vector storage for document chunks. The requirements are:
persistence across restarts, a configurable storage location, no dependency on absolute machine
paths, **no external services**, clean integration with the existing Docker Compose setup, no vector
data committed to Git, reproducible installs, and support for externally generated embeddings later.
The vector database is fixed as ChromaDB (not Weaviate/Qdrant/Pinecone).

Two deployment shapes were evaluated:

| | Embedded ChromaDB (in-process) | Dedicated ChromaDB server container |
| --- | --- | --- |
| Complexity | Low — a Python library, no network | High — extra service, client/server, ports, healthchecks |
| Fits modular monolith? | Yes | No — adds an external service |
| "No external services" rule | Satisfied | Violated |
| Persistence | Local dir under `.data/vector-store` (volume-backed in Docker) | Server-managed, harder to reason about |
| Embedding independence | Store raw vectors; embeddings injected later | Same |

## Decision
Use **embedded ChromaDB** (the `chromadb` Python package in persistent local mode). It persists to
`vector_store_path` (default `.data/vector-store`), which is git-ignored and volume-backed at
`/app/.data/vector-store` inside Docker Compose (the existing `vector-data` named volume on the `api`
service). No dedicated ChromaDB container or client/server split is introduced.

## Consequences
- Positive: simplest reliable option; satisfies "no external services"; single source of truth for
  chunks; clean Docker integration via the existing volume; portable (relative path, no machine
  paths); reproducible via `uv.lock`.
- Negative: the embedded client pulls a sizeable transitive tree (onnxruntime, tokenizers, grpcio).
  This is accepted as the cost of the chosen vector DB and is documented. To honor "no automatic
  embedding model downloads," the application uses interface-only embeddings (no default embedding
  function that downloads a model); embeddings are injected externally in Milestone 3.
- A transitive conflict was resolved: `chromadb → huggingface-hub 2.x → httpx2`, which breaks
  Starlette's TestClient (it prefers `httpx2` over `httpx`). We constrain `huggingface-hub<1`
  (via `[tool.uv] constraint-dependencies`) to remove `httpx2` while keeping Chroma fully functional.
