# ADR 0008 — Hybrid retrieval with BM25 + Reciprocal Rank Fusion, provider-abstracted

## Status
Accepted (Milestone 2)

## Context
Milestone 2 must define retrieval that is robust **before** real embeddings exist. A missing
embedding provider must not block upload, chunking, lexical indexing, or basic search. The system
must also support adding vector similarity and hybrid fusion later without rebuilding the
application, and must avoid unnecessary framework abstractions and speculative code.

## Decision
Adopt a **provider-abstracted, mode-driven retrieval** design:
- **Lexical (BM25)** via `rank-bm25` (`BM25Okapi`) — always available, deterministic, no model.
- **Vector similarity** via the embedded ChromaDB store — used only when vectors are present.
- **Hybrid** via **Reciprocal Rank Fusion** (RRF, constant `k` from config, default 60) to combine
  the BM25 and vector ranked lists without needing calibrated scores from different retrievers.
- **Optional reranking**, disabled by default (identity when off).
- A `Retriever` orchestrates a configurable `retrieval_mode` (`lexical` | `vector` | `hybrid`). In
  `vector`/`hybrid` mode with no vectors present, it degrades gracefully to lexical (logging a
  warning) rather than returning dummy semantic results.
- Embeddings are produced by an `EmbeddingProvider` interface; Milestone 2 has **no concrete
  production implementation wired up** (interface only). A concrete OpenAI-compatible provider is
  added in Milestone 3 against `embedding_base_url` / `embedding_api_key`.
- **No LangChain dependency** is introduced: the retrieval pipeline is thin and hand-rolled, which is
  simpler and more transparent than pulling in a large framework at this stage. LangChain may be
  reconsidered in a later milestone if its value is demonstrated.

## Consequences
- Positive: lexical-only mode works with zero credentials/models; hybrid quality improves as real
  embeddings are added incrementally; RRF needs no score calibration; citations derive from chunk
  metadata (traceable); no speculative framework abstractions.
- Negative: BM25 alone is weaker than semantic search for paraphrased queries — accepted until
  embeddings land in Milestone 3. RRF does not exploit absolute scores — acceptable given it fuses
  heterogeneous retrievers.
- The chunk/metadata schema and interfaces are fixed in `docs/contracts/retrieval.md`; Agent 2
  implements them, Agent 3 consumes the HTTP endpoints in `docs/contracts/api.md`.
