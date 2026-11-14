"""Frontend API client package (Agent 3-owned).

The client is the single place the frontend talks to the FastAPI backend over HTTP. UI components
depend on this client, never on backend internals.
"""

from frontend.api.client import DocumentAPIClient
from frontend.api.models import Document, DocumentStatus

__all__ = ["Document", "DocumentAPIClient", "DocumentStatus"]
