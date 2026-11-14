# ADR 0001 — Use Python 3.12 and FastAPI for the backend

## Status
Accepted (Phase 0)

## Context
The backend must serve HTTP endpoints and later host a RAG pipeline. We need a modern, well-typed
language with a fast, async-capable web framework and strong ecosystem support for the future RAG
stack (LangChain, ChromaDB, OpenAI-compatible APIs).

## Decision
Use **Python 3.12** and **FastAPI** for the backend. The application object is `app` in
`enterprise_ai_document_assistant.api.main`. Internal port is `8000`.

## Consequences
- Positive: type hints, automatic OpenAPI docs, async support, broad library compatibility with the
  planned RAG stack.
- Negative: Python startup is slower than compiled alternatives — acceptable for this scale.
- Pinned to 3.12 via `.python-version` and `requires-python` in `pyproject.toml`.
