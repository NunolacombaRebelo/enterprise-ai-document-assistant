"""Frontend configuration.

Reads the backend base URL from the environment (``API_BASE_URL``) and exposes application
constants. The frontend never hardcodes the backend address and never imports backend internals;
it communicates over HTTP only (see ``docs/contracts/api.md``).

Owned by Agent 3 (Frontend Engineering).
"""

from __future__ import annotations

import os

# Native default; overridden to http://api:8000 inside Docker Compose (see compose.yaml).
DEFAULT_API_BASE_URL = "http://localhost:8000"

# Application identity.
APP_TITLE = "Enterprise AI Document Assistant"
APP_SHORT_NAME = "Aurora"
APP_ICON = ":file_cabinet:"
APP_TAGLINE = "Document intelligence for small businesses"
APP_DESCRIPTION = "Upload PDF documents, manage your collection, and ask grounded questions."

# Upload limits. The backend is the source of truth for what it accepts; these values are used for
# client-side pre-validation so the user gets fast, clear feedback before a request is sent.
MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # 25 MB
ALLOWED_UPLOAD_EXTENSIONS = (".pdf",)

# HTTP behaviour.
REQUEST_TIMEOUT_SECONDS = 30.0
HEALTH_TIMEOUT_SECONDS = 5.0


def get_api_base_url() -> str:
    """Return the configured backend base URL.

    Reads ``API_BASE_URL`` from the environment, falling back to the native default. The value is
    normalised (trailing slash removed) so endpoint paths can be joined safely.
    """
    raw = os.environ.get("API_BASE_URL", DEFAULT_API_BASE_URL).strip()
    if not raw:
        raw = DEFAULT_API_BASE_URL
    return raw.rstrip("/")


def is_pdf_filename(filename: str) -> bool:
    """Return ``True`` if ``filename`` has an allowed PDF extension (case-insensitive)."""
    return filename.lower().endswith(ALLOWED_UPLOAD_EXTENSIONS)
