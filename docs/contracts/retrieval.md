# Retrieval Contract — Milestone 2 (Advanced RAG Infrastructure)

This contract defines the **data models and interfaces** for document processing, chunking,
indexing, and retrieval. It is the source of truth that Backend Agent 2 implements against and
Frontend Agent 3 consumes (via the HTTP endpoints in `api.md`). It is owned by Agent 1
(`docs/contracts/`). Changes go through the contract change procedure in `ownership.md`.

**Milestone 2 scope:** infrastructure + contracts + deterministic test doubles. **No real model
endpoints or API keys are configured or used.** The system must run in **lexical-only mode** with no
embedding provider present. Embeddings are injected externally in a later milestone (Milestone 3).

## Guiding invariants

1. **Lexical-only mode is first-class.** A missing embedding provider must NOT prevent document
   upload, chunking, lexical (BM25) indexing, or basic search. `retrieval_mode` defaults to
   `"lexical"`.
2. **No dummy semantic results.** The application must never fabricate vector/semantic search
   results. If vectors are not present, vector/hybrid modes degrade gracefully to lexical (or
   report "no vectors available") rather than returning fake matches.
3. **Embeddings are injected, not generated here.** Milestone 2 stores raw text + metadata and a
   zero-vector placeholder slot. A later milestone supplies real embeddings (through the planned
   `EmbeddingProvider` interface) without rebuilding the application.
4. **Document-level traceability.** Every chunk carries enough metadata to cite its source document
   and page. Citations are derived from chunk metadata, not from model output.
5. **No speculative abstractions.** Only the interfaces named below are defined; implementations are
   Agent 2's. No LangChain dependency is introduced unless its value is demonstrated.

## Configuration (from `core/config.py`)

| Setting | Default | Meaning |
| --- | --- | --- |
| `vector_store_path` | `.data/vector-store` | Persistent dir for embedded ChromaDB (git-ignored, volume-backed in Docker). |
| `chroma_collection` | `documents` | Chroma collection name for chunks. |
| `chroma_distance_fn` | `cosine` | Distance function for vector similarity. |
| `retrieval_mode` | `lexical` | `lexical` \| `vector` \| `hybrid`. |
| `rrf_k` | `60` | Reciprocal Rank Fusion constant (hybrid mode only). |
| `retrieval_top_k` | `10` | Candidates per retriever before fusion/rerank. |
| `rerank_enabled` | `false` | Whether to rerank the fused list (off by default). |
| `chunk_size_tokens` | `400` | Target tokens per chunk (approximate). |
| `chunk_overlap_tokens` | `60` | Overlap between consecutive chunks. |
| `embedding_provider` / `embedding_model` | `openai` / `text-embedding-3-small` | Configured but **not required**; empty key = lexical-only. |
| `embedding_base_url` / `embedding_api_key` | `None` | Optional OpenAI-compatible endpoint/key. Never logged. |

## Data models

### Chunk (the indexed unit)

A chunk is a contiguous passage of a document's extracted text. Agent 2 implements
`services/retrieval/models.py` (or equivalent) exposing at least:

```python
@dataclass(frozen=True)
class Chunk:
    id: str  # stable unique id: f"{document_id}:{chunk_index}" (UUID-safe, no path chars)
    document_id: str  # references DocumentMetadata.id (Milestone 1)
    filename: str  # original uploaded filename (sanitized), for display/citation
    page: int  # 1-based page number the chunk starts on (structure-aware)
    chunk_index: int  # 0-based position of this chunk within the document
    text: str  # the passage text (non-empty after trimming)
    char_start: int  # offset of the chunk within its page text (chunks never cross page boundaries)
    char_end: int  # exclusive end offset (within the same page text)
    created_at: str  # ISO-8601 UTC timestamp of indexing
    # Optional, populated only when embeddings exist (Milestone 3+):
    embedding: list[float] | None = None
```

Rules:
- `id` is globally unique across the collection and stable across reindexing of the same document
  version (so reindex can upsert rather than duplicate).
- `page` and `char_start`/`char_end` are required for citations and filtering. `char_start`/`char_end`
  are offsets within the chunk's **page** text (chunks are confined to a single page), not the whole
  document.
- Empty/whitespace-only passages are dropped (do not index empty chunks).

### Chunk metadata (stored in Chroma)

Each chunk stored in Chroma carries a **metadata dict** with exactly these keys (string values where
shown; numeric values may be stored as numbers but must round-trip):

| Key | Type | Notes |
| --- | --- | --- |
| `document_id` | string | Links back to the Milestone 1 document. |
| `filename` | string | Original sanitized filename. |
| `page` | int | 1-based page number. |
| `chunk_index` | int | 0-based index within the document. |
| `created_at` | string | ISO-8601 UTC. |

Chroma `id` = `Chunk.id`. Chroma `documents` field = `Chunk.text`. Chroma `embeddings` =
`Chunk.embedding` when a real embedding is present. In lexical-only mode (Milestone 2) the store
holds a **zero placeholder vector** to satisfy Chroma's add-time requirement; it is never used for
ranking and is replaced by a real vector on upsert in Milestone 3 (see the note below and
`docs/backend.md`).

### Search result

```python
@dataclass(frozen=True)
class SearchResult:
    chunk_id: str
    document_id: str
    filename: str
    page: int
    chunk_index: int
    text: str
    score: float  # fused/reranked score (higher = better); see scoring below
    sources: tuple[
        str, ...
    ]  # which retrievers contributed: e.g. ("bm25",), ("vector",), ("bm25","vector")
```

### Citation

A citation is derived from a `SearchResult`'s chunk metadata (never from model output):

```python
@dataclass(frozen=True)
class Citation:
    document_id: str
    filename: str
    page: int
    chunk_index: int
    excerpt: str  # short quote from the chunk (first ~200 chars, trimmed)
```

## Retrieval interfaces

Agent 2 implements these behind `providers/` + `services/retrieval/`. The signatures below are the
contract; internal implementation is free.

### Lexical (BM25)

```python
class BM25Index:
    def build(self, chunks: Sequence[Chunk]) -> None: ...
    def search(self, query: str, top_k: int) -> list[tuple[str, float]]:
        """Return [(chunk_id, bm25_score)] best-first. Deterministic. No network."""
```

- Uses `rank-bm25` (`BM25Okapi`). Tokenization must be simple and deterministic (lowercase,
  whitespace/punctuation split). An empty corpus returns `[]`.
- BM25 scores are non-negative; higher = more relevant.

### Vector similarity

```python
class VectorStore:
    def add(self, chunks: Sequence[Chunk]) -> None:
        """Upsert chunks into Chroma. Chunks with embedding=None are stored WITHOUT a vector."""

    def query(self, embedding: list[float], top_k: int) -> list[tuple[str, float]]:
        """Return [(chunk_id, similarity_score)] best-first using the configured distance fn."""
```

- Backed by embedded ChromaDB (persistent, `vector_store_path`). Collection = `chroma_collection`.
- Must be safe to call when the collection is empty (returns `[]`).
- **Must not** call any embedding model for *query* vectors; it receives already-computed query
  vectors. See the note below on Chroma's default embedding function at `add` time.

> **Chroma `add` and the embedding function.** ChromaDB requires a `documents` field on `add` and
> runs an embedding function over them. To guarantee **no embedding model runs at all** in
> Milestone 2, the `VectorStore` supplies a custom **zero-vector no-op embedding function**
> (`_ZeroEmbeddingFunction` in `services/retrieval/vector_store.py`) that returns a fixed zero
> vector — not Chroma's default local ONNX model. The zero vector is a storage placeholder and is
> **never** used for ranking: `vectors_present` stays `false` until a real vector is upserted, and
> `VectorStore.query` raises if called when no real vectors are present. When real embeddings land in
> Milestone 3, `VectorStore.add`/`upsert` writes the provider's vectors over the placeholder (upsert
> by `Chunk.id`). The application must never treat the placeholder vector as a semantic result. This
> keeps a single storage path (Chroma) for both text/metadata and vectors without running any model.

### Embedding provider (planned; not yet defined in code)

The intended interface for Milestone 3 is:

```python
class EmbeddingProvider(Protocol):
    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """Map texts to vectors."""
```

> **Status:** this interface is **planned** and is not yet defined in `providers/` (which is a
> placeholder). In Milestone 2 the `Retriever` takes an untyped `embedder: object | None` and runs
> lexical-only; no concrete provider is wired up. A concrete OpenAI-compatible provider (and the
> formal interface) are added in Milestone 3 against `embedding_base_url` / `embedding_api_key`.
> Tests use a deterministic test double (e.g. hash-based fixed-dimension vectors) — see testing
> section.

### Hybrid fusion (Reciprocal Rank Fusion)

```python
def reciprocal_rank_fusion(
    ranked_lists: Sequence[Sequence[str]], k: int = 60
) -> list[tuple[str, float]]:
    """Fuse multiple ranked lists of chunk_ids.

    score(c) = sum over each list L containing c of 1 / (k + rank_L(c))   (rank is 1-based).
    Returns [(chunk_id, fused_score)] sorted by fused_score descending, ties broken by chunk_id
    ascending for determinism.
    """
```

- RRF is the standard hybrid combiner. It requires no model and is fully deterministic.
- `k` comes from `rrf_k`. Each retriever contributes one ranked list (truncated to `retrieval_top_k`).

### Optional reranking

```python
def rerank(query: str, results: Sequence[SearchResult]) -> list[SearchResult]:
    """Reorder results for the query. Disabled by default (rerank_enabled=False)."""
```

- When disabled, `rerank` is the identity function. A real reranker is a later-milestone concern;
  it must not require a model in Milestone 2.

### Retrieval service (orchestration)

```python
class Retriever:
    def __init__(
        self,
        settings,
        bm25: BM25Index,
        vector: VectorStore | None,
        embedder: object | None,  # EmbeddingProvider (planned); untyped in Milestone 2
    ): ...
    def search(self, query: str, top_k: int | None = None) -> list[SearchResult]:
        """Run the configured mode and return fused, optionally-reranked results.

        - lexical: BM25 only.
        - vector:  requires vectors present; if none, degrade to lexical (log a warning).
        - hybrid:  BM25 + vector (if vectors present), fused via RRF. If no vectors, lexical only.
        """
```

- The retriever **must** return results in lexical-only mode with `vector=None` and
  `embedder=None`. This is the no-provider guarantee.

## Index lifecycle & reindexing

- **Index a document:** after upload + extraction (Milestone 1), chunk the text (structure-aware,
  page boundaries preserved), then `BM25Index.build` (or incremental add) and `VectorStore.add`
  (vectors only if available). Indexing a document is idempotent: reindexing the same document
  version replaces its chunks (upsert by `Chunk.id`) rather than duplicating them.
- **Remove a document:** deleting a document (Milestone 1 storage) removes its chunks from both the
  BM25 corpus and the Chroma collection.
- **Rebuild:** a full rebuild re-chunks all documents and rebuilds both indexes. Supported for
  recovery; not required to run on every start.
- **Persistence:** Chroma persists to `vector_store_path` (volume-backed in Docker). The BM25 index
  is rebuilt from stored chunks on startup (it is not separately persisted) — this keeps a single
  source of truth (the chunks) and avoids two divergent stores.
- **Status:** the index exposes counts (documents indexed, chunks indexed, vectors present) for the
  `GET /index/status` endpoint.

## Citation & filtering guarantees

- Every `SearchResult` resolves to exactly one source document + page via its chunk metadata.
- Filtering by `document_id`, `filename`, or `page` is supported via Chroma metadata where useful,
  and always possible post-hoc from `SearchResult` fields.
- Citations are computed from chunk metadata only; the system never invents a source.

## Testing requirements (deterministic, no network/models)

- **ChromaDB initialization & persistence:** create a client against a temp dir, create/get the
  collection, persist, reopen, and confirm data survives (no external service).
- **Collection lifecycle:** create, upsert, delete-by-document, count.
- **Metadata contract validation:** a stored chunk's metadata dict contains exactly the documented
  keys with correct types; round-trips through Chroma.
- **BM25 determinism:** same corpus + query → same ranked ids/scores; empty corpus → `[]`.
- **RRF math:** known small example produces the expected fused scores (assert exact values).
- **No-provider operation:** `Retriever(vector=None, embedder=None)` in `lexical` mode returns
  correct BM25 results; `hybrid` mode with no vectors degrades to lexical (no crash, no dummy
  results).
- **Deterministic embedding double:** a fixed hash-based embedder yields stable vectors so vector
  path tests are reproducible without a model.
