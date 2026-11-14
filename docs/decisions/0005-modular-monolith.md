# ADR 0005 — Use a modular monolith architecture

## Status
Accepted (Phase 0)

## Context
The system has a backend and a frontend and will later host a RAG pipeline. We must choose between
a modular monolith and microservices. For a portfolio project developed by three AI agents in one
repository, simplicity, testability, and a small bounded surface area are prioritized over
independent deployability.

## Decision
Use a **modular monolith**: one Python package (`src/enterprise_ai_document_assistant/`) with clear
internal modules (`api`, `core`, `services`, `rag`, `providers`), one FastAPI app, one Streamlit
frontend. Frontend talks to backend over HTTP only. No microservices, brokers, or external databases
in the early phases.

## Consequences
- Positive: simple to run/test, easy for agents to reason about, low operational overhead.
- Negative: less isolation than microservices — acceptable at this scale; modules keep boundaries
  clean so a later split is possible if ever needed.
- Future RAG components live in `services/`, `rag/`, and `providers/` within the same package.
