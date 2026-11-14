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

    # --- Future embedding provider (Phase 2+) -----------------------------
    embedding_provider: str = "openai"
    embedding_model: str = "text-embedding-3-small"

    # --- Future vector storage (Phase 2+) ---------------------------------
    vector_store_path: str = ".data/vector-store"

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
