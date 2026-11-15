# Documentation Audit — Enterprise AI Document Assistant

**Audit date:** 2026-11-15
**Auditor:** Senior AI Engineer / Software Architect (Agent 1, Platform & Architecture)
**Scope:** Full repository documentation audit against the current implementation, before the next
development milestone.
**Method:** Evidence-based inspection of source code, configuration, tests, and documentation.
No application code, existing documentation, or configuration was modified. Only this report was
created.

> **Verification baseline (executed on this machine, Windows, this session):**
> `uv sync --locked` clean · `uv run ruff check .` passed · `uv run ruff format --check .` passed ·
> `uv run pytest` → **200 passed** (106 backend, 80 frontend, 14 integration) ·
> `docker compose config` valid.

---

## 1. Executive summary

The documentation is in **good overall health** — the per-agent handoffs (`docs/handoffs/02-backend.md`,
`docs/handoffs/03-frontend.md`) and the backend/frontend engineering docs (`docs/backend.md`,
`docs/frontend.md`) are accurate, current, and evidence-backed. The platform-facing docs
(`AGENTS.md`, `docs/architecture/overview.md`, `docs/contracts/retrieval.md`, `docs/roadmap.md`,
`docs/handoffs/01-platform.md`) contain **stale "future/Phase 0" framing** that predates Milestone 2
completion, and a small number of **factual inaccuracies** where the documented behavior diverges
from the actual implementation.

The most important systemic issue: **Milestone 2 was implemented by Agent 2 (backend) but the
platform docs still describe it as "pending."** The frontend search UI is genuinely still pending
(the "Ask" page is a placeholder and the API client has no `/search` method), so the milestone is
only partially complete — but the backend portion is done and must be reflected.

**No Critical findings** (nothing would cause a user or agent to take a materially wrong action that
breaks the system). There are **4 High** findings (stale milestone-status framing that misleads
agents about what is implemented) and several Medium/Low inaccuracies.

**Capabilities that are NOT implemented (verified, and must not be claimed):** real semantic/vector
search (no real embeddings; `vectors_present` is `false`), hybrid retrieval (degrades to lexical),
LLM-generated answers, agentic functionality, RAG orchestration (`rag/` is empty), and provider
abstractions (`providers/` is empty; no `EmbeddingProvider` interface exists in code).

---

## 2. Complete table of reviewed files

| # | File | Type | Reviewed? | Status |
| --- | --- | --- | --- | --- |
| 1 | `README.md` | Human-facing overview | Yes | Mostly accurate (1 inaccuracy) |
| 2 | `AGENTS.md` | Agent instructions | Yes | Stale (High) |
| 3 | `docs/architecture/overview.md` | Architecture | Yes | Stale (High) |
| 4 | `docs/contracts/api.md` | API contract | Yes | Accurate; "proposed" framing stale |
| 5 | `docs/contracts/retrieval.md` | Retrieval contract | Yes | 4 inaccuracies (Medium) |
| 6 | `docs/contracts/ownership.md` | Ownership contract | Yes | Accurate |
| 7 | `docs/roadmap.md` | Phase plan | Yes | Stale (High) |
| 8 | `docs/development.md` | Dev guide | Yes | Accurate |
| 9 | `docs/backend.md` | Backend doc | Yes | Accurate (best-in-repo) |
| 10 | `docs/frontend.md` | Frontend doc | Yes | Accurate (1 stale note) |
| 11 | `docs/handoffs/01-platform.md` | Agent 1 handoff | Yes | Stale (High) |
| 12 | `docs/handoffs/02-backend.md` | Agent 2 handoff | Yes | Accurate (1 stale coordination item) |
| 13 | `docs/handoffs/03-frontend.md` | Agent 3 handoff | Yes | Accurate (1 stale note) |
| 14 | `.kilo/rules/architecture-code-quality.md` | Dev rule | Yes | Stale (Medium) |
| 15 | `.kilo/rules/development-workflow.md` | Dev rule | Yes | Accurate |
| 16 | `.kilo/rules/multi-agent-coordination.md` | Dev rule | Yes | Accurate |
| 17 | `.kilo/rules/security-portability.md` | Dev rule | Yes | Accurate |
| 18 | `.kilo/rules/testing-validation.md` | Dev rule | Yes | Accurate |
| 19 | `.kilo/skills/implement-feature/SKILL.md` | Skill | Yes | Accurate |
| 20 | `.kilo/skills/review-change/SKILL.md` | Skill | Yes | Accurate |
| 21 | `compose.yaml` | Docker Compose | Yes | 1 stale comment (Low) |
| 22 | `.env.example` | Env template | Yes | Accurate |
| 23 | `pyproject.toml` | Dependencies | Yes | Accurate |
| 24 | `.github/workflows/ci.yml` | CI | Yes | Accurate |
| 25 | `.gitignore` | Ignore rules | Yes | Accurate (bug already fixed) |
| 26 | `docs/decisions/0001–0008` | ADRs | Yes | Accurate (preserved as historical) |

**Implementation files inspected for evidence** (not documentation, but the source of truth):
`api/main.py`, `api/documents.py`, `api/retrieval.py`, `core/config.py`,
`services/documents/{extraction,storage,validation,models,service}.py`,
`services/retrieval/{models,chunking,bm25,chunk_store,vector_store,fusion,retriever,index}.py`,
`rag/__init__.py`, `providers/__init__.py`, `frontend/{app,config,state,theme}.py`,
`frontend/api/{client,models}.py`, `frontend/components/{documents,chat,cards,layout}.py`,
`tests/backend/*`, `tests/frontend/*`, `tests/integration/*`.

---

## 3. Findings by file (severity-classified)

### 3.1 Critical
**None.** No finding would cause a user or agent to take a materially wrong action that breaks the
system or exposes data. The most severe issues are stale milestone-status framing (High).

### 3.2 High

#### H1 — `AGENTS.md` overstates implemented capabilities and marks ChromaDB as future
- **Location:** `AGENTS.md:14-17` (project purpose lists "Generate embeddings and index documents",
  "Ask natural-language questions", "Generate grounded answers with source citations" as things the
  app lets small businesses do); `AGENTS.md:30-31` (tech stack: "Vector storage | ChromaDB | **future**
  (Phase 2), not installed in Phase 0"); `AGENTS.md:39-40` ("Do not install LangChain, ChromaDB...
  during Phase 0"); `AGENTS.md:51` ("services/ ... (Agent 2, future)"); `AGENTS.md:66` ("api.md — the
  API/frontend integration contract (Phase 0)"); `AGENTS.md:141` ("Phase 0 has only minimal
  infrastructure/config tests").
- **Evidence:** `services/retrieval/` and `services/documents/` are fully implemented and tested
  (200 tests pass). `chromadb>=1.0` and `rank-bm25>=0.2` are runtime deps in `pyproject.toml:17-19`.
  No LLM, no real embeddings, no grounded answers exist (verified: `rag/` and `providers/` are
  placeholder-only; `vectors_present` is `false`).
- **Impact:** An agent reading AGENTS.md would conclude embeddings/LLM/grounded answers are working
  (they are not) and that ChromaDB is not yet installed (it is). This is the most misleading doc for
  agent onboarding.
- **Recommended correction:** Rewrite the "Project purpose" bullet list to distinguish *implemented*
  (upload, extract, chunk, index, lexical retrieval) from *planned* (embeddings, LLM, grounded
  answers, citations). Update the tech-stack table: ChromaDB → "implemented (Milestone 2, embedded)",
  RAG orchestration → "planned (Milestone 3+, not started)", LLM → "planned (Milestone 3+)". Update
  `services/` line to "implemented (documents + retrieval)". Update the testing note.

#### H2 — `docs/architecture/overview.md` describes Milestone 2 endpoints/services as future
- **Location:** `overview.md:18` ("GET /health, (future endpoints)"); `overview.md:33` ("Phase 0
  exposes `GET /health`"); `overview.md:38` ("services/ ... Agent 2, future phases"); `overview.md:77-87`
  (provider abstraction described as if it exists).
- **Evidence:** `api/main.py` includes the documents and retrieval routers (verified via OpenAPI path
  check: `/health`, `/documents`, `/documents/{id}`, `/documents/{id}/index`, `/index/status`,
  `/search`). `services/` contains implemented `documents/` and `retrieval/` packages. `providers/`
  contains only a placeholder `__init__.py` (no `EmbeddingProvider` interface).
- **Impact:** Understates what is implemented; the "provider abstraction" section describes an
  abstraction that does not exist in code.
- **Recommended correction:** Update the component diagram and bullets to reflect the implemented
  endpoints and `services/` packages. Reframe the "Provider abstraction" section as *planned* (not
  implemented), noting that the retriever currently takes an untyped `embedder: object | None`.

#### H3 — `docs/roadmap.md` marks Milestone 2 backend implementation as "pending"
- **Location:** `roadmap.md:29` ("platform foundation complete; backend/frontend implementation
  pending"); `roadmap.md:43-45` ("Backend implementation (Agent 2, pending): chunking service, BM25
  index, embedded-Chroma vector store, hybrid retriever, and the ... endpoints"); `roadmap.md:47-48`
  ("Frontend implementation (Agent 3, pending)").
- **Evidence:** The backend is fully implemented and tested (see `docs/backend.md:10-14` and the 106
  backend tests). The frontend search UI is genuinely still pending (verified: `frontend/api/client.py`
  has no `/search`/`/index`/`/index/status` methods; `frontend/components/chat.py` is a placeholder).
- **Impact:** Misleads agents about the milestone's true state; the backend portion is done.
- **Recommended correction:** Mark Milestone 2 as "backend implemented; frontend search UI pending."
  Keep the frontend item as pending (it is).

#### H4 — `docs/handoffs/01-platform.md` describes Milestone 2 as pending and cites a stale test count
- **Location:** `01-platform.md:13-20` ("platform foundation complete; backend/frontend implementation
  pending"); `01-platform.md:56` ("`uv run pytest` **114 passed**"); `01-platform.md:141` ("**114
  passed**"); `01-platform.md:188-196` (remaining tasks list backend/frontend Milestone 2 as pending).
- **Evidence:** 200 tests pass now (106 backend + 80 frontend + 14 integration). Agent 2 has
  implemented the backend (see `02-backend.md`).
- **Impact:** Stale status and stale validation numbers.
- **Recommended correction:** Update the status to reflect backend completion; update the test count
  to 200; move the backend implementation item to "done" and keep only the frontend search UI pending.

### 3.3 Medium

#### M1 — `docs/contracts/retrieval.md` documents the wrong Chroma embedding mechanism
- **Location:** `retrieval.md:154-161` (note claiming Chroma applies its "default local embedding
  function (no model is downloaded)"); `retrieval.md:87` ("Chroma embeddings = Chunk.embedding only
  when present (omit when None; do not store zero/dummy vectors)").
- **Evidence:** `services/retrieval/vector_store.py` supplies a custom **zero-vector no-op embedding
  function** (`_ZeroEmbeddingFunction`) so that **no** embedding model runs at all (better than the
  documented default-ONNX behavior). It does store a zero placeholder vector. `docs/backend.md:105-109`
  and `02-backend.md:45-55` correctly document this; `retrieval.md` does not.
- **Impact:** The contract describes a mechanism that does not match the implementation, and its
  "do not store zero/dummy vectors" rule contradicts what the code actually does.
- **Recommended correction:** Update the note to describe the zero-vector no-op embedding function
  (no model runs), and reconcile the "do not store zero/dummy vectors" rule with the placeholder
  vector that is stored but never used for ranking.

#### M2 — `docs/contracts/retrieval.md` documents `char_start`/`char_end` as whole-document offsets
- **Location:** `retrieval.md:60-61` ("offset of the chunk within the full document text").
- **Evidence:** `services/retrieval/chunking.py` computes `char_start`/`char_end` as offsets within
  the chunk's **page** text (chunks never cross page boundaries). `docs/backend.md:174-175` and
  `02-backend.md:100-101` correctly note this deviation.
- **Impact:** The contract's field semantics are inaccurate; a consumer could miscompute global
  offsets.
- **Recommended correction:** Change the contract to state these are per-page offsets (chunks are
  page-confined).

#### M3 — `docs/contracts/retrieval.md` and `overview.md` describe an `EmbeddingProvider` interface that does not exist
- **Location:** `retrieval.md:163-173` (the `EmbeddingProvider(Protocol)` interface);
  `retrieval.md:205-212` (`Retriever.__init__(..., embedder: EmbeddingProvider | None)`);
  `overview.md:77-87` (provider abstraction).
- **Evidence:** `grep` for `EmbeddingProvider`/`Protocol`/`class.*Provider` across `src/` returns
  nothing. `services/retrieval/retriever.py` uses `embedder: object | None`. `providers/__init__.py`
  is a placeholder.
- **Impact:** The contract references an interface that is not implemented, so Agent 2 could not have
  implemented against it literally.
- **Recommended correction:** Either (a) mark the `EmbeddingProvider` interface as *planned* and note
  the retriever currently uses an untyped `embedder`, or (b) have Agent 2 introduce the interface in a
  later milestone. Do not present it as an existing contract.

#### M4 — `docs/contracts/api.md` labels the Milestone 2 endpoints as "proposed"
- **Location:** `api.md:30-33` ("these endpoints are **proposed contracts**"); `api.md:90-94`
  ("**proposed** for this milestone").
- **Evidence:** The three Milestone 2 endpoints are implemented and tested (`api/retrieval.py`,
  `tests/backend/test_retrieval_api.py`). The contract content itself is accurate.
- **Impact:** Understates that the endpoints are live; could cause an agent to re-implement them.
- **Recommended correction:** Change "proposed" to "implemented" for the Milestone 2 endpoints (the
  request/response schemas are accurate as-is).

#### M5 — `.kilo/rules/architecture-code-quality.md` says ChromaDB must not be added yet
- **Location:** `architecture-code-quality.md:8` ("No microservices... in Phase 0–2");
  `architecture-code-quality.md:33-34` ("Do not add LangChain / ChromaDB / OpenAI SDKs until their
  phase begins").
- **Evidence:** ChromaDB is installed and used (Milestone 2). The rule predates Milestone 2.
- **Impact:** A rule that contradicts the current dependency state.
- **Recommended correction:** Update the dependency-discipline rule to note ChromaDB/rank-bm25 are
  now in use (Milestone 2) and only LangChain/OpenAI SDKs remain future.

### 3.4 Low

#### L1 — `README.md` search example includes a non-existent `mode` request field
- **Location:** `README.md:379` (the `POST /search` example body includes `"mode": "lexical"`).
- **Evidence:** `api/retrieval.py:62-68` — `SearchRequest` has only `query` and `top_k`; `mode` is a
  response field (`SearchResponse`, line 75). Tests send `{"query": ..., "top_k": ...}` only
  (`tests/backend/test_retrieval_api.py:140`). FastAPI ignores unknown request fields, so the example
  works but is misleading.
- **Impact:** Low — the example still works, but documents a field the API does not accept.
- **Recommended correction:** Remove `"mode"` from the request-body example.

#### L2 — `docs/frontend.md` and `docs/handoffs/03-frontend.md` claim integration tests have pre-existing failures
- **Location:** `frontend.md:210-212`; `03-frontend.md:84-86` ("Agent 1's in-progress RAG integration
  tests ... have pre-existing failures unrelated to the frontend").
- **Evidence:** All 14 integration tests pass now (verified this session). The note is stale.
- **Impact:** Low — could cause a reader to distrust a green suite.
- **Recommended correction:** Remove or update the note to state the integration tests pass.

#### L3 — `docs/handoffs/02-backend.md` reports a `.gitignore` bug that is already fixed
- **Location:** `02-backend.md:59-69` (coordination item #1: "`.gitignore` line 29 `documents/` ...
  also matches the source package ... never been committed"); `02-backend.md:116-118`.
- **Evidence:** `.gitignore:29` is now `/documents/` (anchored to repo root). `git check-ignore` on
  `src/.../services/documents/extraction.py` returns exit 1 (not ignored). The source package is
  untracked (`??`) but **not** ignored.
- **Impact:** Low — the coordination request is resolved; the note is stale. (The source package is
  still uncommitted, which is a separate, real state — see L4.)
- **Recommended correction:** Mark the `.gitignore` item as resolved; note the source package is
  tracked-able but not yet committed.

#### L4 — Milestone 2 work is entirely uncommitted (repo state, not a doc inaccuracy)
- **Location:** `git log` shows only 3 commits (Phase 0, Milestone 1, frontend import fix); 44 files
  are modified/untracked, including all of Milestone 2 (`services/retrieval/`, `api/retrieval.py`,
  `tests/backend/*`, `docs/backend.md`, `docs/contracts/retrieval.md`, ADRs 0007/0008, etc.).
- **Evidence:** `git log --oneline -12` and `git status --short`.
- **Impact:** Milestone 2 is not yet committed to `main`; the repo does not reflect the implemented
  state in version control.
- **Recommended correction:** This is a coordination/commit task, not a doc fix. Flag it for the
  next integration pass so Milestone 2 is committed once the working tree is clear.

#### L5 — `compose.yaml` comment says vector-store persistence is "future"
- **Location:** `compose.yaml:36` ("Named volume for future vector-store persistence (Phase 2)").
- **Evidence:** The embedded ChromaDB store persists to `.data/vector-store` (volume-backed) in
  Milestone 2.
- **Impact:** Low — cosmetic stale comment.
- **Recommended correction:** Update the comment to reflect that the volume now backs the live
  ChromaDB store and document storage.

---

## 4. Exact outdated/incorrect statements (with references)

| # | File:line | Statement | Verified reality |
| --- | --- | --- | --- |
| 1 | `AGENTS.md:14-17` | App "lets small businesses ... Generate embeddings ... Ask natural-language questions ... Generate grounded answers with source citations" | Embeddings/LLM/grounded answers are **not** implemented (lexical-only; `rag/`/`providers/` empty). |
| 2 | `AGENTS.md:30-31` | "Vector storage \| ChromaDB \| **future** (Phase 2), not installed in Phase 0" | ChromaDB is installed and used (Milestone 2). |
| 3 | `AGENTS.md:51` | "services/ ... (Agent 2, future)" | `services/documents/` and `services/retrieval/` are implemented. |
| 4 | `AGENTS.md:141` | "Phase 0 has only minimal infrastructure/config tests" | 200 tests exist across backend/frontend/integration. |
| 5 | `overview.md:18,33` | "GET /health, (future endpoints)" / "Phase 0 exposes `GET /health`" | Documents + retrieval endpoints are implemented. |
| 6 | `overview.md:38` | "services/ ... Agent 2, future phases" | Implemented. |
| 7 | `overview.md:77-87` | Provider abstraction described as existing | `providers/` is a placeholder; no `EmbeddingProvider` interface. |
| 8 | `roadmap.md:29,43-45` | Milestone 2 "backend/frontend implementation pending" | Backend implemented; only frontend search UI pending. |
| 9 | `01-platform.md:13-20,188-196` | Milestone 2 backend/frontend "pending" | Backend done. |
| 10 | `01-platform.md:56,141` | "114 passed" | 200 passed. |
| 11 | `retrieval.md:87` | "do not store zero/dummy vectors" | Code stores a zero placeholder vector (never used for ranking). |
| 12 | `retrieval.md:154-161` | Chroma applies "default local embedding function (no model downloaded)" | Code uses a custom zero-vector no-op EF (no model runs at all). |
| 13 | `retrieval.md:60-61` | `char_start`/`char_end` are "offset of the chunk within the full document text" | They are per-page offsets (chunks are page-confined). |
| 14 | `retrieval.md:163-173,205-212` | `EmbeddingProvider(Protocol)` interface | Does not exist in code; retriever uses `embedder: object | None`. |
| 15 | `api.md:30-33,90-94` | Milestone 2 endpoints "proposed" | Implemented and tested. |
| 16 | `architecture-code-quality.md:8,33-34` | "No microservices... in Phase 0–2" / "Do not add ... ChromaDB ... until their phase begins" | ChromaDB is in use (Milestone 2). |
| 17 | `README.md:379` | Search request body includes `"mode": "lexical"` | `SearchRequest` has only `query`/`top_k`; `mode` is a response field. |
| 18 | `frontend.md:210-212`, `03-frontend.md:84-86` | Integration tests "have pre-existing failures" | All 14 integration tests pass. |
| 19 | `02-backend.md:59-69,116-118` | `.gitignore` `documents/` rule ignores the source package | Rule is now `/documents/` (anchored); source package is not ignored. |
| 20 | `compose.yaml:36` | Vector-store persistence "future (Phase 2)" | Live in Milestone 2. |

---

## 5. Evidence from code / configuration / tests

- **Backend Milestone 2 implemented:** `api/retrieval.py` defines `POST /documents/{id}/index`,
  `GET /index/status`, `POST /search`; `services/retrieval/` contains `models.py`, `chunking.py`,
  `bm25.py`, `chunk_store.py`, `vector_store.py`, `fusion.py`, `retriever.py`, `index.py`.
- **No real embeddings / vector search:** `vector_store.py` uses a zero-vector no-op embedding
  function; `vectors_present` is `false` in lexical-only mode; `retriever.py` degrades vector/hybrid
  to lexical when no vectors are present.
- **No RAG / providers:** `rag/__init__.py` and `providers/__init__.py` are placeholder-only; no
  `EmbeddingProvider`/`Protocol` symbol exists in `src/`.
- **Frontend does not use Milestone 2 endpoints:** `frontend/api/client.py` exposes only
  `health`, `upload_document`, `list_documents`, `get_document`. `frontend/components/chat.py` is a
  "Coming soon" placeholder. `frontend/components/documents.py` search is a client-side filename
  filter (`search in d.filename.lower()`), not `POST /search`.
- **Tests:** `uv run pytest` → **200 passed** (106 backend, 80 frontend, 14 integration). Includes
  `tests/backend/test_retrieval_quality.py` (a genuine Recall@K/MRR eval over a synthetic corpus,
  not a fake passing test).
- **`.gitignore` bug already fixed:** `.gitignore:29` is `/documents/` (anchored); `git check-ignore`
  confirms the source package is not ignored.
- **Commit state:** `git log` shows only 3 commits; 44 files modified/untracked (Milestone 2
  uncommitted).
- **Config:** `core/config.py` has all Milestone 2 settings; `pyproject.toml:17-19` declares
  `chromadb>=1.0` and `rank-bm25>=0.2`; `[tool.uv] constraint-dependencies = ["huggingface-hub<1"]`
  at `pyproject.toml:43-46`.

---

## 6. Recommended corrections

1. **`AGENTS.md` (H1):** Rewrite the project-purpose bullets and tech-stack table to distinguish
   implemented (upload, extract, chunk, index, lexical retrieval) from planned (embeddings, LLM,
   grounded answers, citations). Update `services/` and testing notes.
2. **`docs/architecture/overview.md` (H2):** Update the component diagram/bullets for the implemented
   endpoints and `services/` packages; reframe the provider-abstraction section as planned.
3. **`docs/roadmap.md` (H3):** Mark Milestone 2 backend as implemented; keep frontend search UI pending.
4. **`docs/handoffs/01-platform.md` (H4):** Update status to backend-complete; correct test count to
   200; move backend implementation to done.
5. **`docs/contracts/retrieval.md` (M1–M3):** Describe the zero-vector no-op embedding function;
   correct `char_start`/`char_end` to per-page offsets; mark the `EmbeddingProvider` interface as
   planned (or have Agent 2 introduce it) rather than present.
6. **`docs/contracts/api.md` (M4):** Change the Milestone 2 endpoints from "proposed" to "implemented."
7. **`.kilo/rules/architecture-code-quality.md` (M5):** Note ChromaDB/rank-bm25 are now in use; only
   LangChain/OpenAI SDKs remain future.
8. **`README.md` (L1):** Remove `"mode"` from the `POST /search` request-body example.
9. **`docs/frontend.md` / `03-frontend.md` (L2):** Remove the stale "integration tests have failures" note.
10. **`docs/handoffs/02-backend.md` (L3):** Mark the `.gitignore` coordination item as resolved.
11. **`compose.yaml` (L5):** Update the "future vector-store persistence" comment.
12. **Repo state (L4):** Commit Milestone 2 once the working tree is clear (coordination task).

---

## 7. Prioritized documentation update plan

| Priority | Action | Owner | Effort |
| --- | --- | --- | --- |
| P0 (do first) | Fix `AGENTS.md` capability overstatement + tech-stack table (H1) | Agent 1 | Small |
| P0 | Update `docs/roadmap.md` Milestone 2 status (H3) | Agent 1 | Small |
| P0 | Update `docs/handoffs/01-platform.md` status + test count (H4) | Agent 1 | Small |
| P1 | Update `docs/architecture/overview.md` component diagram + provider section (H2) | Agent 1 | Medium |
| P1 | Correct `docs/contracts/retrieval.md` (embedding mechanism, char offsets, EmbeddingProvider) (M1–M3) | Agent 1 | Medium |
| P1 | Change `docs/contracts/api.md` Milestone 2 "proposed" → "implemented" (M4) | Agent 1 | Small |
| P2 | Update `.kilo/rules/architecture-code-quality.md` dependency note (M5) | Agent 1 | Small |
| P2 | Fix `README.md` search example (L1) | Agent 1 | Small |
| P2 | Remove stale "integration tests fail" notes in `frontend.md`/`03-frontend.md` (L2) | Agent 1 | Small |
| P2 | Mark `.gitignore` item resolved in `02-backend.md` (L3) | Agent 2 | Small |
| P3 | Update `compose.yaml` comment (L5) | Agent 1 | Trivial |
| P3 | Commit Milestone 2 once the tree is clear (L4) | Agent 1 (coordination) | Medium |

**Suggested sequencing:** P0 items first (they most mislead agents), then P1 contract corrections,
then P2/P3 cosmetic fixes. The contract corrections (P1) should be coordinated with Agent 2 since
they touch the retrieval contract that Agent 2 implemented against.

---

## 8. Implementation-status matrix

Legend: **✅ Implemented & tested** · **◐ Partial** · **❌ Not implemented** · **⬜ Planned**

| Capability | Status | Evidence |
| --- | --- | --- |
| PDF upload + validation | ✅ | `api/documents.py`, `services/documents/validation.py` |
| PDF text extraction (per-page) | ✅ | `services/documents/extraction.py` (`extract_pdf_pages`) |
| Local persistence (`.data/documents`) | ✅ | `services/documents/storage.py` |
| Document listing / status retrieval | ✅ | `api/documents.py` (`GET /documents`, `GET /documents/{id}`) |
| Structure-aware chunking (page-confined) | ✅ | `services/retrieval/chunking.py` |
| Chunk metadata + citation metadata | ✅ | `services/retrieval/models.py` |
| BM25 lexical retrieval | ✅ | `services/retrieval/bm25.py` |
| Chunk persistence (single source of truth) | ✅ | `services/retrieval/chunk_store.py` |
| Embedded ChromaDB vector store | ◐ | `services/retrieval/vector_store.py` — stores text/metadata + zero placeholder vector; **no real vectors** |
| Reciprocal Rank Fusion | ✅ | `services/retrieval/fusion.py` |
| Hybrid retrieval (BM25 + vector) | ◐ | `services/retrieval/retriever.py` — implemented but **degrades to lexical** (no real vectors) |
| Reranking | ◐ | `services/retrieval/fusion.py` — identity when `rerank_enabled=False` (default) |
| Indexing workflow (`/index`, `/index/status`) | ✅ | `api/retrieval.py`, `services/retrieval/index.py` |
| `POST /search` endpoint | ✅ | `api/retrieval.py` |
| Real embeddings / semantic search | ❌ | No embedding provider; `vectors_present` is `false` |
| `EmbeddingProvider` interface | ❌ | Does not exist in code (`providers/` is a placeholder) |
| RAG orchestration / grounded answers | ❌ | `rag/` is a placeholder |
| LLM integration | ❌ | No LLM provider; `OPENAI_API_KEY` unused |
| Agentic functionality | ❌ | None present |
| Source citations on generated answers | ❌ | Only metadata-derived citations from retrieval (no generated answers) |
| Frontend document-management UI | ✅ | `frontend/components/documents.py` |
| Frontend search / index UI (consuming `/search`) | ❌ | `frontend/api/client.py` has no `/search` method; `chat.py` is a placeholder |
| Frontend "Ask" page | ❌ | `frontend/components/chat.py` — "Coming soon" placeholder |
| Docker Compose (api + frontend, healthchecks, volume) | ✅ | `compose.yaml` |
| CI (lint + format + test) | ✅ | `.github/workflows/ci.yml` |
| Automated tests | ✅ | 200 passed (106 backend, 80 frontend, 14 integration) |

---

## 9. Conclusion

The documentation is largely accurate and well-maintained, with the per-agent handoffs and the
backend/frontend engineering docs being the strongest. The primary gap is **stale milestone-status
framing** in the platform-facing docs (`AGENTS.md`, `overview.md`, `roadmap.md`, `01-platform.md`),
which still describe Milestone 2 as pending even though the backend is implemented and tested. A
smaller set of **contract inaccuracies** in `docs/contracts/retrieval.md` describe a Chroma
embedding mechanism and an `EmbeddingProvider` interface that do not match the code.

No Critical findings. The recommended corrections are prioritized in Section 7, with the P0 items
(AGENTS.md, roadmap, platform handoff) being the highest-value fixes for agent onboarding. The
implementation-status matrix (Section 8) is the verified baseline to use before starting the next
milestone.
