"""HTTP API client for the FastAPI backend.

This is the only module in the frontend that performs HTTP calls. It is built on ``httpx`` (already
a project dependency) and is fully injectable: tests supply a fake transport so no real backend,
network, or credentials are required.

The client never raises raw ``httpx`` exceptions to the UI. It raises a small set of typed
exceptions (see below) that the presentation layer maps to concise, user-facing messages.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx
from frontend.api.models import (
    Document,
    IndexResult,
    IndexStatus,
    SearchResponse,
    parse_document,
    parse_document_list,
    parse_index_result,
    parse_index_status,
    parse_search_response,
)

from frontend import config

logger = logging.getLogger(__name__)


class APIError(Exception):
    """Base class for all frontend API errors."""


class BackendUnavailableError(APIError):
    """The backend could not be reached (offline, DNS, connection refused, timeout)."""


class RequestTimeoutError(APIError):
    """The request exceeded the configured timeout."""


class HTTPStatusError(APIError):
    """The backend returned a non-2xx HTTP status.

    ``status_code`` is the HTTP status; ``detail`` is a short, safe message extracted from the
    response body (never a raw stack trace).
    """

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(f"HTTP {status_code}: {detail}")
        self.status_code = status_code
        self.detail = detail


class UnexpectedResponseError(APIError):
    """The backend returned a 2xx response whose body did not match the expected shape."""


def _extract_detail(response: httpx.Response) -> str:
    """Best-effort extraction of a short, safe error detail from a response body."""
    try:
        data = response.json()
    except ValueError:
        return _status_phrase(response.status_code)
    if isinstance(data, dict):
        detail = data.get("detail")
        if isinstance(detail, str) and detail:
            return detail
        if isinstance(detail, dict):
            # FastAPI validation errors come as {"detail": [{"msg": ...}, ...]}.
            msgs = [d.get("msg") for d in detail if isinstance(d, dict) and d.get("msg")]
            if msgs:
                return "; ".join(str(m) for m in msgs)
    return _status_phrase(response.status_code)


def _status_phrase(status_code: int) -> str:
    return {
        400: "The request was invalid.",
        404: "The requested resource was not found.",
        413: "The file is too large.",
        415: "The file type is not supported.",
        422: "The request could not be processed.",
        500: "The server encountered an error.",
        502: "The server encountered an error.",
        503: "The service is temporarily unavailable.",
    }.get(status_code, "The request failed.")


class DocumentAPIClient:
    """A thin, typed client for the document management endpoints.

    Parameters
    ----------
    base_url:
        Backend base URL (no trailing slash). Defaults to the configured ``API_BASE_URL``.
    timeout:
        Per-request timeout in seconds.
    transport:
        Optional ``httpx`` transport, used to inject a fake transport in tests.
    """

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._base_url = (base_url or config.get_api_base_url()).rstrip("/")
        self._timeout = timeout if timeout is not None else config.REQUEST_TIMEOUT_SECONDS
        self._transport = transport

    @property
    def base_url(self) -> str:
        return self._base_url

    def _client(self) -> httpx.Client:
        kwargs: dict[str, Any] = {"base_url": self._base_url, "timeout": self._timeout}
        if self._transport is not None:
            kwargs["transport"] = self._transport
        return httpx.Client(**kwargs)

    def health(self) -> bool:
        """Return ``True`` when the backend health endpoint reports ok.

        Raises :class:`BackendUnavailableError` / :class:`RequestTimeoutError` when the backend
        cannot be reached, so the caller can distinguish "offline" from "unhealthy".
        """
        try:
            with self._client() as client:
                response = client.get("/health", timeout=config.HEALTH_TIMEOUT_SECONDS)
        except httpx.TimeoutException as exc:
            raise RequestTimeoutError("The backend did not respond in time.") from exc
        except httpx.HTTPError as exc:
            raise BackendUnavailableError("The backend is not reachable.") from exc

        if response.status_code == 200:
            try:
                return response.json().get("status") == "ok"
            except ValueError:
                return False
        return False

    def upload_document(self, filename: str, content: bytes) -> Document:
        """Upload a PDF (multipart field ``file``) and return the created document.

        Raises :class:`HTTPStatusError` for non-2xx, :class:`UnexpectedResponseError` for a 2xx with
        an invalid body, and the availability/timeout errors for transport failures.
        """
        files = {"file": (filename, content, "application/pdf")}
        try:
            with self._client() as client:
                response = client.post("/documents", files=files)
        except httpx.TimeoutException as exc:
            raise RequestTimeoutError("The upload did not complete in time.") from exc
        except httpx.HTTPError as exc:
            raise BackendUnavailableError("The backend is not reachable.") from exc

        if response.status_code not in (200, 201):
            raise HTTPStatusError(response.status_code, _extract_detail(response))
        try:
            return parse_document(response.json())
        except (ValueError, TypeError) as exc:
            raise UnexpectedResponseError(
                "The upload response was not in the expected format."
            ) from exc

    def list_documents(self) -> list[Document]:
        """Return the document collection.

        Raises :class:`HTTPStatusError` for non-2xx and :class:`UnexpectedResponseError` for a 2xx
        with an invalid body.
        """
        try:
            with self._client() as client:
                response = client.get("/documents")
        except httpx.TimeoutException as exc:
            raise RequestTimeoutError("The request did not complete in time.") from exc
        except httpx.HTTPError as exc:
            raise BackendUnavailableError("The backend is not reachable.") from exc

        if response.status_code != 200:
            raise HTTPStatusError(response.status_code, _extract_detail(response))
        try:
            return parse_document_list(response.json())
        except (ValueError, TypeError) as exc:
            raise UnexpectedResponseError(
                "The document list was not in the expected format."
            ) from exc

    def get_document(self, document_id: str) -> Document:
        """Return a single document's metadata and status."""
        try:
            with self._client() as client:
                response = client.get(f"/documents/{document_id}")
        except httpx.TimeoutException as exc:
            raise RequestTimeoutError("The request did not complete in time.") from exc
        except httpx.HTTPError as exc:
            raise BackendUnavailableError("The backend is not reachable.") from exc

        if response.status_code != 200:
            raise HTTPStatusError(response.status_code, _extract_detail(response))
        try:
            return parse_document(response.json())
        except (ValueError, TypeError) as exc:
            raise UnexpectedResponseError(
                "The document response was not in the expected format."
            ) from exc

    # ------------------------------------------------------------------
    # Milestone 2 — retrieval (index + search)
    # ------------------------------------------------------------------
    def index_document(self, document_id: str) -> IndexResult:
        """Index (or reindex) one document.

        Returns the count of indexed chunks. Raises :class:`HTTPStatusError` with status ``404``
        (unknown document) or ``409`` (document has no extractable text) for the documented
        failure cases, and the availability/timeout errors for transport failures.
        """
        try:
            with self._client() as client:
                response = client.post(f"/documents/{document_id}/index")
        except httpx.TimeoutException as exc:
            raise RequestTimeoutError("The indexing request did not complete in time.") from exc
        except httpx.HTTPError as exc:
            raise BackendUnavailableError("The backend is not reachable.") from exc

        if response.status_code != 200:
            raise HTTPStatusError(response.status_code, _extract_detail(response))
        try:
            return parse_index_result(response.json())
        except (ValueError, TypeError) as exc:
            raise UnexpectedResponseError(
                "The index response was not in the expected format."
            ) from exc

    def index_status(self) -> IndexStatus:
        """Return the current index status (works with an empty index)."""
        try:
            with self._client() as client:
                response = client.get("/index/status")
        except httpx.TimeoutException as exc:
            raise RequestTimeoutError("The request did not complete in time.") from exc
        except httpx.HTTPError as exc:
            raise BackendUnavailableError("The backend is not reachable.") from exc

        if response.status_code != 200:
            raise HTTPStatusError(response.status_code, _extract_detail(response))
        try:
            return parse_index_status(response.json())
        except (ValueError, TypeError) as exc:
            raise UnexpectedResponseError(
                "The index status response was not in the expected format."
            ) from exc

    def search(self, query: str, top_k: int | None = None) -> SearchResponse:
        """Search indexed documents and return ranked results with citations.

        ``query`` must be non-empty (the backend rejects empty queries with ``422``). An empty
        match is a valid result (``results`` empty), not an error. Raises :class:`HTTPStatusError`
        with status ``422`` for an empty/invalid query and the availability/timeout errors for
        transport failures.
        """
        body: dict[str, object] = {"query": query}
        if top_k is not None:
            body["top_k"] = top_k
        try:
            with self._client() as client:
                response = client.post("/search", json=body)
        except httpx.TimeoutException as exc:
            raise RequestTimeoutError("The search did not complete in time.") from exc
        except httpx.HTTPError as exc:
            raise BackendUnavailableError("The backend is not reachable.") from exc

        if response.status_code != 200:
            raise HTTPStatusError(response.status_code, _extract_detail(response))
        try:
            return parse_search_response(response.json())
        except (ValueError, TypeError) as exc:
            raise UnexpectedResponseError(
                "The search response was not in the expected format."
            ) from exc
