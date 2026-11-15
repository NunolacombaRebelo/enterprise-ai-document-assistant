# API / Frontend Integration Contract — Phase 0

This contract is the source of truth for how the backend and frontend communicate in Phase 0. It
must be established **before** Agents 2 and 3 begin implementation work. Changes to this contract
are coordinated through Agent 1 (see `ownership.md`).

## Backend (FastAPI)

| Item | Value |
| --- | --- |
| Framework | FastAPI |
| Python module | `enterprise_ai_document_assistant.api.main` |
| Application variable | `app` |
| Internal port | `8000` |
| Health endpoint | `GET /health` |
| Expected health JSON | `{"status": "ok"}` |

The backend must start without an OpenAI API key. The health endpoint is used by infrastructure,
Docker health checks, and the frontend to confirm the backend is reachable.

### Endpoint list

- `GET /health` → `200` `{"status": "ok"}`
- Milestone 1 (Document Management): `POST /documents`, `GET /documents`, `GET /documents/{document_id}` — see below.
- Milestone 2 (Advanced RAG Infrastructure): `POST /documents/{document_id}/index`, `GET /index/status`, `POST /search` — see below.

Additional endpoints (grounded question answering with LLM generation) are defined in later
milestones (Milestone 3+) and added to this contract through Agent 1 coordination.

> **Milestone 2 note:** these endpoints are **implemented** by Agent 2 and tested; Agent 3 builds
> the frontend against them. The data models and retrieval interfaces they rely on are defined in
> [`retrieval.md`](retrieval.md). No real model endpoints or API keys are required; the system runs
> in lexical-only mode by default.

## Milestone 1 — Document Management

Implemented by Agent 2. These endpoints are live and tested; Agent 3 should build the frontend
against exactly this behaviour. The response models below are the single source of truth for the
JSON shapes (defined in `src/enterprise_ai_document_assistant/services/documents/models.py`).

### Models

**`DocumentStatus`** (enum): `"processed"` | `"error"`.

**`DocumentMetadata`**:
| Field | Type | Notes |
| --- | --- | --- |
| `id` | string | Stable unique identifier (UUIDv4). |
| `filename` | string | Original uploaded filename, sanitized. |
| `status` | `"processed"` \| `"error"` | Processing status. |
| `page_count` | int \| null | Page count when extraction succeeded; `null` otherwise. |
| `created_at` | string (ISO-8601 UTC) | Upload timestamp. |
| `error` | string \| null | Human-readable reason when `status` is `"error"`; `null` otherwise. |

**`DocumentListResponse`**:
| Field | Type | Notes |
| --- | --- | --- |
| `documents` | `DocumentMetadata[]` | All stored documents, most recent first. |

### Endpoints

#### `POST /documents` — upload and process one PDF
- **Request:** `multipart/form-data` with a single file field named **`file`**.
- **Success:** `201 Created` → `DocumentMetadata`.
- **Errors:**
  - `400 Bad Request` for invalid uploads: empty file, non-PDF (missing `%PDF` header), or size
    above the limit (`max_upload_bytes`, default 25 MiB). Body: `{"detail": "<reason>"}`.
  - Encrypted or malformed PDFs are **not** rejected: they are accepted and stored as a document
    with `status: "error"` and an `error` reason (returned as `201`).

#### `GET /documents` — list documents
- **Success:** `200 OK` → `DocumentListResponse` (`{"documents": [...]}`, most recent first).

#### `GET /documents/{document_id}` — get one document
- **Success:** `200 OK` → `DocumentMetadata`.
- **Errors:**
  - `404 Not Found` for an unknown id. Body: `{"detail": "<reason>"}`.

### Error format

All error responses use FastAPI's standard shape: `{"detail": "<human-readable message>"}` with the
appropriate HTTP status code. No secrets or file contents are included in errors.

### Frontend notes (Agent 3)
- Send uploads as multipart with the field name `file` (e.g. `requests.post(f"{API_BASE_URL}/documents", files={"file": fh})`).
- Poll/list via `GET /documents`; fetch one via `GET /documents/{id}`.
- A document with `status: "error"` was uploaded successfully but could not be processed — surface
  its `error` reason to the user rather than treating it as a failed request.

## Milestone 2 — Advanced RAG Infrastructure (implemented)

Implemented by Agent 2 against `retrieval.md`; consumed by Agent 3 over HTTP. These endpoints are
**live and tested**. They work in **lexical-only mode** with no embedding provider configured. No
real model endpoints or API keys are required.

### Models

**`IndexStatus`**:
| Field | Type | Notes |
| --- | --- | --- |
| `documents_indexed` | int | Number of documents with at least one indexed chunk. |
| `chunks_indexed` | int | Total chunks across all documents. |
| `vectors_present` | bool | Whether any chunk currently has an embedding (false in lexical-only mode). |
| `retrieval_mode` | string | Current configured mode: `"lexical"` \| `"vector"` \| `"hybrid"`. |
| `collection` | string | The Chroma collection name in use. |

**`SearchResult`** (per `retrieval.md`):
| Field | Type | Notes |
| --- | --- | --- |
| `chunk_id` | string | Stable chunk id (`{document_id}:{chunk_index}`). |
| `document_id` | string | Source document id. |
| `filename` | string | Source filename. |
| `page` | int | 1-based page number. |
| `chunk_index` | int | 0-based index within the document. |
| `text` | string | The passage text. |
| `score` | number | Fused/reranked score (higher = better). |
| `sources` | string[] | Which retrievers contributed, e.g. `["bm25"]` or `["bm25","vector"]`. |

**`Citation`** (per `retrieval.md`):
| Field | Type | Notes |
| --- | --- | --- |
| `document_id` | string | Source document id. |
| `filename` | string | Source filename. |
| `page` | int | 1-based page number. |
| `chunk_index` | int | 0-based index within the document. |
| `excerpt` | string | Short quote from the chunk (first ~200 chars, trimmed). |

### Endpoints

#### `POST /documents/{document_id}/index` — index one document
- **Request:** no body. The document must already exist (Milestone 1) and have extractable text.
- **Success:** `200 OK` →
  ```json
  {"document_id": "<id>", "chunks_indexed": 12, "vectors_added": 0}
  ```
  `vectors_added` is `0` in lexical-only mode (no embeddings generated here).
- **Errors:**
  - `404 Not Found` if the document does not exist. Body: `{"detail": "<reason>"}`.
  - `409 Conflict` if the document's status is `"error"` (no extractable text to index). Body:
    `{"detail": "<reason>"}`.

#### `GET /index/status` — index status
- **Success:** `200 OK` → `IndexStatus`.
- Works with an empty index (all counts `0`, `vectors_present` false).

#### `POST /search` — search indexed documents
- **Request body (JSON):**
  ```json
  {"query": "what is the refund policy?", "top_k": 10}
  ```
  - `query`: non-empty string (required).
  - `top_k`: positive int, optional, default from config (`retrieval_top_k`).
- **Success:** `200 OK` →
  ```json
  {
    "query": "what is the refund policy?",
    "mode": "lexical",
    "results": [ <SearchResult>, ... ],
    "citations": [ <Citation>, ... ]
  }
  ```
  - `mode` echoes the effective mode actually used (may be `lexical` even if `hybrid` is
    configured but no vectors are present).
  - `results` is best-first by `score`; empty array when nothing matches.
  - `citations` mirrors `results` (one citation per result), derived from chunk metadata only.
- **Errors:**
  - `422 Unprocessable Entity` for a missing/empty `query` or invalid `top_k` (FastAPI validation).
  - `404 Not Found` is NOT used for "no results" — an empty match returns `200` with `results: []`.

### Error format
Same as Milestone 1: FastAPI standard `{"detail": "<message>"}` with the appropriate status code. No
secrets or file contents in errors.

### Frontend notes (Agent 3)
- After uploading a document, call `POST /documents/{id}/index` to index it, then `GET /index/status`
  to show progress. A `409` means the document had no extractable text — surface that clearly.
- Search box → `POST /search`. Render each result with its `filename`, `page`, and `score`; show the
  `citations` as source references. An empty `results` array is a valid "no matches" state, not an error.
- Do not assume vector results in lexical-only mode; `sources` will be `["bm25"]` and `mode` will be
  `"lexical"`.

## Frontend (Streamlit)

| Item | Value |
| --- | --- |
| Framework | Streamlit |
| Entrypoint | `frontend/app.py` |
| Internal port | `8501` |
| Backend communication | HTTP |
| Environment variable | `API_BASE_URL` |
| Native default | `http://localhost:8000` |
| Docker internal URL | `http://api:8000` |

The frontend reads `API_BASE_URL` from the environment. It defaults to `http://localhost:8000` for
native execution and is set to `http://api:8000` inside Docker Compose (the internal service name).
The frontend must never hardcode the backend address or import backend internals directly.

## Communication rules

- Frontend → backend is **HTTP only**. No shared in-process state.
- All configuration (ports, URLs) comes from environment variables via `core/config.py`; never
  hardcode.
- The app starts and runs without any LLM credentials in Phase 0.

## Contract change procedure

1. Propose the change in your handoff file (`docs/handoffs/0X-*.md`).
2. Agent 1 reviews and updates this file (Agent 1 owns `docs/contracts/`).
3. Both affected agents confirm the change before implementing against it.
