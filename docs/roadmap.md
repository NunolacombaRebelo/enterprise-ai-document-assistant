# Roadmap

The project is delivered in phases. Each phase builds on the previous one. Phase 0 establishes the
engineering foundation; later phases add functionality.

## Phase 0 — Repository foundation *(current)*
- Project structure (src layout), dependency management (uv + lockfile).
- Configuration and security (`.env.example`, `.gitignore`, `.dockerignore`, `.editorconfig`).
- Agent instructions (`AGENTS.md`), Kilo rules and skills, integration contracts.
- Docker Compose infrastructure, CI workflow.
- Documentation (architecture, development, decisions, handoffs).
- Minimal startup stubs (backend `/health`, frontend placeholder) for infrastructure validation.

**Exit criteria:** reproducible `uv sync --locked`; lint/format/tests pass; Docker Compose valid;
agents can begin work without restructuring the repository.

## Phase 1 — PDF upload and text extraction
- Backend endpoint to accept PDF uploads.
- PDF text extraction service.
- Store extracted content in runtime data (not committed).
- Frontend upload UI.
- *(Agent 2: backend; Agent 3: frontend.)*

## Phase 2 — Chunking and vector storage
- Text chunking service.
- Embedding generation (provider abstraction).
- ChromaDB vector storage with persistence (named volume in Docker).
- *(Agent 2. Adds LangChain/ChromaDB dependencies via Agent 1 coordination.)*

## Phase 3 — Retrieval and LLM integration
- Retrieval of relevant passages.
- RAG orchestration with an OpenAI-compatible LLM.
- Grounded answer generation.
- *(Agent 2. Adds LLM provider via Agent 1 coordination.)*

## Phase 4 — Citations and frontend improvements
- Source citations attached to answers.
- Polished professional UI/UX.
- *(Agent 2: citations; Agent 3: UI.)*

## Phase 5 — Evaluation, testing, security hardening, portfolio release
- Evaluation harness for answer quality.
- Comprehensive test coverage across backend and frontend.
- Security hardening (input validation, rate limiting, secret handling review).
- Portfolio release packaging and final documentation.
- *(All agents; Agent 1 leads integration and final validation.)*
