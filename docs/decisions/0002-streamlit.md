# ADR 0002 — Use Streamlit for the frontend

## Status
Accepted (Phase 0)

## Context
The frontend is a professional web interface for uploading documents and asking questions. For a
portfolio project with a small team (and AI agents), we want rapid iteration, minimal boilerplate,
and easy data/LLM UI patterns.

## Decision
Use **Streamlit** for the frontend. Entrypoint is `frontend/app.py`; internal port is `8501`. The
frontend communicates with the backend over HTTP using `API_BASE_URL`.

## Consequences
- Positive: fast to build, good for interactive/data apps, small surface area for agents to work in.
- Negative: less control over low-level web behavior than a SPA framework — acceptable here.
- Frontend must not import backend internals; HTTP only.
