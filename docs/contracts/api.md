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

Additional endpoints (question, retrieval, citations) are defined in later milestones and added to
this contract through Agent 1 coordination.

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
