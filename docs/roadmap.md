# Roadmap

The project is delivered in phases. Each phase builds on the previous one. Phase 0 establishes the
engineering foundation; later phases add functionality.

## Phase 0 — Repository foundation *(complete)*
- Project structure (src layout), dependency management (uv + lockfile).
- Configuration and security (`.env.example`, `.gitignore`, `.dockerignore`, `.editorconfig`).
- Agent instructions (`AGENTS.md`), Kilo rules and skills, integration contracts.
- Docker Compose infrastructure, CI workflow.
- Documentation (architecture, development, decisions, handoffs).
- Minimal startup stubs (backend `/health`, frontend placeholder) for infrastructure validation.

**Exit criteria:** reproducible `uv sync --locked`; lint/format/tests pass; Docker Compose valid;
agents can begin work without restructuring the repository.

## Phase 1 / Milestone 1 — PDF upload and text extraction *(complete)*
- Backend `POST /documents` accepts PDF uploads; validates type/size/magic/filename/path-traversal.
- PDF text extraction + page count via `pypdf`; encrypted/malformed PDFs stored as `error`.
- Local persistence under `.data/documents` (`<id>.pdf` + `<id>.json`, git-ignored).
- `GET /documents` (list) and `GET /documents/{id}` (metadata/status).
- Frontend document-management UI: upload, collection table with status badges, and
  loading/empty/success/error states.
- *(Agent 2: backend; Agent 3: frontend; Agent 1: dependencies, contract, integration.)*

**Exit criteria:** upload/processing/listing/inspection operational end-to-end (native + Docker);
contract matches implementation; automated checks pass; runtime documents stay out of version control.

## Phase 2 / Milestone 2 — Advanced RAG infrastructure *(platform + backend complete; frontend search UI pending)*

**Platform & contracts (Agent 1, complete):**
- Dependencies: `chromadb` (embedded) + `rank-bm25`; `huggingface-hub<1` constraint to keep Starlette
  TestClient working (no `httpx2`). See ADR 0007.
- `core/config.py`: Chroma + retrieval settings (`vector_store_path`, `chroma_collection`,
  `retrieval_mode`, `rrf_k`, `retrieval_top_k`, `rerank_enabled`, chunk sizing, embedding endpoint/key).
- Contracts: `docs/contracts/retrieval.md` (chunk/metadata/index/BM25/vector/hybrid-RRF/rerank/
  citation/lifecycle) and Milestone 2 endpoints in `docs/contracts/api.md`.
- ADRs 0007 (embedded ChromaDB) and 0008 (hybrid retrieval / RRF / provider abstraction).
- Deterministic integration tests for Chroma init/persistence/collection lifecycle, metadata
  contract, RRF math, BM25 determinism, and the no-provider lexical-only guarantee.
- **No real model endpoints or API keys.** The system runs in lexical-only mode by default.

**Backend implementation (Agent 2, complete):** structure-aware chunking, BM25 index, embedded-Chroma
vector store (zero-vector placeholder; prepared for real embeddings), chunk persistence, hybrid
retriever with graceful degradation, and the `/documents/{id}/index`, `/index/status`, `/search`
endpoints — all functional and tested. Embeddings are interface-only here; a concrete provider is
added in Milestone 3. See `docs/backend.md`.

**Frontend implementation (Agent 3, pending):** index/status UI and a search panel consuming
`POST /search`, rendering results with filename/page/score and metadata-derived citations. The
"Ask" page is currently a clearly-identified placeholder; the frontend does not yet call the
Milestone 2 endpoints.

**Exit criteria:** lexical-only search works end-to-end (native + Docker) with no credentials;
contract matches implementation; automated checks pass; no vector data committed. Backend exit
criteria are met; the frontend search UI remains the open item.

## Phase 3 / Milestone 3 — Retrieval quality and LLM integration
- Concrete OpenAI-compatible **embedding provider** wired against `embedding_base_url` /
  `embedding_api_key`; real vectors upserted over placeholders (ADR 0008).
- Vector + hybrid retrieval now active; optional reranking.
- RAG orchestration with an OpenAI-compatible LLM; grounded answer generation.
- *(Agent 2. Adds LLM/embedding provider via Agent 1 coordination.)*

## Phase 4 / Milestone 4 — Citations and frontend improvements
- Source citations attached to generated answers (derived from chunk metadata).
- Polished professional UI/UX.
- *(Agent 2: citations; Agent 3: UI.)*

## Phase 5 — Evaluation, testing, security hardening, portfolio release
- Evaluation harness for answer quality.
- Comprehensive test coverage across backend and frontend.
- Security hardening (input validation, rate limiting, secret handling review).
- Portfolio release packaging and final documentation.
- *(All agents; Agent 1 leads integration and final validation.)*
