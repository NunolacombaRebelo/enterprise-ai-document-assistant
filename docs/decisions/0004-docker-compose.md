# ADR 0004 — Use Docker Compose for packaging and orchestration

## Status
Accepted (Phase 0)

## Context
The project must be runnable in containers for a consistent, portable environment, while still
supporting native execution with uv. We need to run the FastAPI backend and Streamlit frontend
together with correct internal networking.

## Decision
Use **Docker + Docker Compose** with two services (`api`, `frontend`). Build contexts are relative
(the repository root). Host ports are configurable via environment variables. The frontend reaches
the backend over the internal service name `http://api:8000`. Images use `uv` for reproducible,
locked installs and run as a non-root user. No privileged containers, no hardcoded credentials,
local-only exposure by default.

## Consequences
- Positive: consistent environment, easy two-service orchestration, reproducible builds.
- Negative: adds a build step; mitigated by keeping native uv execution fully supported.
- Future ChromaDB persistence will use the named volume `vector-data` mounted at `/app/.data`.
