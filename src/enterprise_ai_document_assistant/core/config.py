"""Environment-based application configuration.

Configuration is read from environment variables (and an optional ``.env`` file) via
``pydantic-settings``. No real credentials are required for Phase 0: the application must start
without an OpenAI API key.

Owned by Agent 1 (Platform & Architecture). Backend-specific settings that Agent 2 needs should be
added here only through the coordinated dependency/configuration change procedure described in
``docs/contracts/ownership.md``.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, loaded from the environment.

    All values have safe defaults so the app starts on a clean machine with no ``.env`` file and
    no API credentials. Secrets (e.g. ``OPENAI_API_KEY``) are optional and never logged.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Application -------------------------------------------------------
    app_env: str = "development"  # development | staging | production
    log_level: str = "INFO"  # DEBUG | INFO | WARNING | ERROR | CRITICAL

    # --- API (backend) -----------------------------------------------------
    api_host: str = "127.0.0.1"
    api_port: int = 8000

    # --- Frontend / backend communication ---------------------------------
    # Native default; overridden to http://api:8000 inside Docker Compose.
    api_base_url: str = "http://localhost:8000"
    frontend_port: int = 8501

    # --- Future LLM provider (Phase 3+) -----------------------------------
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o-mini"
    openai_api_key: str | None = None  # optional; never logged

    # --- Embedding provider (Milestone 3+; interface only in Milestone 2) --
    # Configured but NOT required to start. A missing/empty provider means the system runs in
    # lexical-only mode; it must never block upload, chunking, lexical indexing, or search.
    # The endpoint/key are optional and are NEVER logged. No model is downloaded or called in
    # Milestone 2 — embeddings are injected externally in a later milestone.
    embedding_provider: str = "openai"
    embedding_model: str = "text-embedding-3-small"
    # Optional OpenAI-compatible base URL + key for embeddings. Empty by default. Never logged.
    embedding_base_url: str | None = None
    embedding_api_key: str | None = None

    # --- Vector storage (Milestone 2): embedded ChromaDB ------------------
    # Persistent local directory for the embedded ChromaDB client. Relative path, runtime data
    # only (git-ignored), volume-backed at /app/.data/vector-store inside Docker. No external
    # service is required. See docs/architecture/overview.md and ADR 0007.
    vector_store_path: str = ".data/vector-store"
    # Name of the Chroma collection that holds document chunks.
    chroma_collection: str = "documents"
    # Distance function for vector similarity. cosine is the default for text embeddings.
    chroma_distance_fn: str = "cosine"

    # --- Retrieval (Milestone 2) ------------------------------------------
    # Retrieval mode: "lexical" (BM25 only — always available, no embeddings needed),
    # "vector" (Chroma similarity only — requires embeddings to be present), or
    # "hybrid" (BM25 + vector fused with Reciprocal Rank Fusion). The app must start and serve
    # lexical search even when no embedding provider is configured.
    retrieval_mode: str = "lexical"  # lexical | vector | hybrid
    # Reciprocal Rank Fusion constant (standard default 60). Only used in hybrid mode.
    rrf_k: int = 60
    # Number of candidates each retriever returns before fusion/reranking.
    retrieval_top_k: int = 10
    # Optional reranking of the fused candidate list. Disabled by default; enabled later when a
    # reranker is configured. Must not require a real model in Milestone 2.
    rerank_enabled: bool = False
    # Chunking parameters for structure-aware chunking (used by Agent 2's chunker).
    chunk_size_tokens: int = 400  # target tokens per chunk (approximate; Agent 2 may refine)
    chunk_overlap_tokens: int = 60  # overlap between consecutive chunks

    # --- Document storage (Milestone 1) -----------------------------------
    # Local development persistence for uploaded documents and their metadata.
    # Relative path, runtime data only (git-ignored). Never committed.
    documents_dir: str = ".data/documents"
    # Maximum accepted upload size in bytes (default 25 MiB). Enforced before processing.
    max_upload_bytes: int = 25 * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    """Return a cached :class:`Settings` instance."""
    return Settings()
