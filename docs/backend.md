# Backend — Enterprise AI Document Assistant

Backend engineering documentation (Agent 2). The backend is a FastAPI modular monolith: one Python
package, one app object, business logic in `services/`, thin HTTP handlers in `api/`.

## Status

- **Milestone 1 (Document Management): implemented.** PDF upload, validation, text extraction,
  local persistence, listing, and status retrieval are functional and tested.
- `GET /health` (Phase 0 contract) remains operational.

## Layout

```
src/enterprise_ai_document_assistant/
├─ api/
│  ├─ main.py          # app object; includes the documents router; GET /health
│  └─ documents.py     # thin HTTP router for /documents (no business logic)
├─ core/
│  └─ config.py        # Settings (Agent 1-owned; extended with backend-specific settings)
└─ services/
   └─ documents/
      ├─ models.py     # Pydantic request/response models + DocumentStatus
      ├─ validation.py # upload validation (type, size, magic, safe filename)
      ├─ extraction.py # pypdf wrapper + typed exceptions
      ├─ storage.py    # local development persistence (filesystem)
      └─ service.py    # DocumentService orchestration
```

## API (Milestone 1)

| Method | Path | Success | Errors |
| --- | --- | --- | --- |
| `POST` | `/documents` | `201` + `DocumentMetadata` | `400` invalid upload (empty / not a PDF / oversized) |
| `GET` | `/documents` | `200` `{"documents": [...]}` | — |
| `GET` | `/documents/{document_id}` | `200` + `DocumentMetadata` | `404` unknown id |

`DocumentMetadata`:

```json
{
  "id": "uuid",
  "filename": "sanitized-name.pdf",
  "status": "processed",
  "page_count": 5,
  "created_at": "2026-11-14T20:12:27Z",
  "error": null
}
```

- `status` is `processed` or `error`. Encrypted or malformed PDFs are **accepted and stored** with
  `status: "error"` and a human-readable `error` reason (so the user sees what happened); invalid
  uploads (empty, non-PDF, oversized) are **rejected** with `400`.
- `page_count` is `null` when extraction did not succeed.

## Behaviour

- **Validation** (`validation.py`): requires non-empty bytes, a `%PDF` magic header, and a size at
  or under `max_upload_bytes`. The filename is sanitized (path separators, `..`, unsafe characters
  removed; bounded length; fallback `document.pdf`). The on-disk name is a separate UUID key, so a
  stored file can never escape the documents directory.
- **Extraction** (`extraction.py`): wraps `pypdf`. Returns page count + text. Encrypted PDFs raise
  `EncryptedPdfError`; corrupt PDFs raise `MalformedPdfError`. A scanned/image-only PDF (zero
  extractable text) is returned successfully with empty text and classified `processed` (page count
  still known) — see Limitations.
- **Persistence** (`storage.py`): each document is `<documents_dir>/<id>.pdf` (raw bytes) plus
  `<documents_dir>/<id>.json` (metadata). `documents_dir` defaults to `.data/documents`
  (git-ignored). No external database.
- **Orchestration** (`service.py`): `DocumentService.upload` validates → generates a UUID →
  extracts → persists. `list_documents` returns most-recent-first; `get_document` raises
  `DocumentNotFoundError` for unknown ids.

## Configuration

Backend-specific settings added to `core/config.py` (via the coordinated extension path):

| Setting | Default | Env var |
| --- | --- | --- |
| `documents_dir` | `.data/documents` | `DOCUMENTS_DIR` |
| `max_upload_bytes` | `25 * 1024 * 1024` (25 MiB) | `MAX_UPLOAD_BYTES` |

## Security

- Uploaded files are untrusted input: type/size/magic validated before processing; filenames
  sanitized; storage keyed by UUID (no path traversal).
- Uploaded content is never executed; only the PDF structure is parsed.
- No file contents, sizes, or secrets are logged; only the sanitized filename and a fixed limit.
- Runtime data lives under `.data/` (git-ignored); nothing is committed.

## Testing

`tests/backend/` (Agent 2-owned):

- `test_validation.py` — type, size, empty, filename/path-traversal.
- `test_extraction.py` — page count/text, encrypted, malformed.
- `test_storage.py` — save/get/list/delete, corrupt-metadata resilience (temp dirs).
- `test_documents_api.py` — full API flow via TestClient with a temp documents dir (upload, list,
  get, 404, 400 cases, encrypted→error, filename sanitization, oversized).
- `pdf_factory.py` — synthetic PDF fixtures (no external generator, offline).

All tests run without network, credentials, or paid services.

## Dependencies

- **`pypdf`** (runtime) — required for PDF text extraction. **Requested from Agent 1** (see
  `docs/handoffs/02-backend.md`); not yet in `pyproject.toml`/`uv.lock`.

## Limitations

- Scanned/image-only PDFs are classified `processed` with empty text (page count known). OCR is out
  of scope for Milestone 1; such documents will simply have no searchable text until a later phase.
- Single-user local development storage (filesystem). No multi-tenancy, no background processing,
  no vector store (later milestones).
- `pypdf` is installed in the local venv for validation but is not yet declared in
  `pyproject.toml`/`uv.lock` pending Agent 1 coordination.
