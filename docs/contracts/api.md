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

### Phase 0 endpoint list

- `GET /health` → `200` `{"status": "ok"}`

Additional endpoints (document upload, question, retrieval) are defined in later phases and added
to this contract through Agent 1 coordination.

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
