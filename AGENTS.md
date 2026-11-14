# Enterprise AI Document Assistant — Agent Instructions

Read this file first. It is the authoritative "README for AI agents" for this repository. It is
loaded automatically by Kilo Code and is write-protected (changes require explicit approval).
The modular rules in `.kilo/rules/` (loaded via `kilo.jsonc`) hold the actionable per-category
guardrails; this file holds the project overview, architecture, and the multi-agent protocol.

## Project purpose

An independent, professional AI-engineering portfolio project. It lets small businesses:

- Upload PDF documents.
- Extract and process document content.
- Generate embeddings and index documents.
- Ask natural-language questions.
- Retrieve relevant document passages.
- Generate grounded answers with source citations.
- Interact through a professional web interface.

It uses only original, public, or synthetic demonstration content. No proprietary company code or
configuration is used.

## Technology stack

| Concern | Choice | Notes |
| --- | --- | --- |
| Language | Python 3.12 | managed by `uv` |
| Backend | FastAPI | `src/enterprise_ai_document_assistant/api/main.py` → `app` |
| Frontend | Streamlit | `frontend/app.py` entrypoint |
| RAG orchestration | LangChain | **future** (Phase 3), not installed in Phase 0 |
| Vector storage | ChromaDB | **future** (Phase 2), not installed in Phase 0 |
| LLM | OpenAI-compatible APIs | **future** (Phase 3), not required to start |
| Dependency management | uv | `uv.lock` is generated; never hand-edit |
| Packaging / orchestration | Docker + Docker Compose | `compose.yaml`, `docker/` |
| Testing | pytest | `tests/` |
| Linting / formatting | Ruff | configured in `pyproject.toml` |
| CI | Git + GitHub Actions | `.github/workflows/ci.yml` |

Prefer a **modular monolith** over microservices. Do not install LangChain, ChromaDB, or
LLM-specific dependencies during Phase 0 unless strictly necessary.

## Architecture boundaries

Modular monolith: one Python package, one FastAPI app, one Streamlit frontend. Frontend talks to
the backend over HTTP only (`API_BASE_URL`). No shared in-process state between the two.

```
src/enterprise_ai_document_assistant/
├─ api/        # FastAPI app + endpoints          (Agent 2)  main.py holds `app`
├─ core/       # shared configuration/utilities   (Agent 1 owns config)
├─ services/   # ingestion, extraction, chunking, embedding, retrieval (Agent 2, future)
├─ rag/        # RAG orchestration                (Agent 2, future)
└─ providers/  # LLM / embedding / vector-store abstractions (Agent 2, future)
frontend/      # Streamlit app                    (Agent 3)
tests/         # backend/ frontend/ integration/  (Agents 2 / 3 / 1 respectively)
```

Rationale and the planned RAG data flow are in `docs/architecture/overview.md`; decisions are in
`docs/decisions/`.

## Repository navigation

- `AGENTS.md` — this file (read first).
- `.kilo/rules/` — modular development rules (loaded via `kilo.jsonc`).
- `.kilo/skills/` — reusable skills (`implement-feature`, `review-change`).
- `docs/contracts/api.md` — the API/frontend integration contract (Phase 0).
- `docs/contracts/ownership.md` — agent responsibilities, file ownership, change procedures.
- `docs/architecture/overview.md` — architecture overview.
- `docs/decisions/` — Architecture Decision Records.
- `docs/development.md` — setup, native/Docker execution, troubleshooting, clean-machine restore.
- `docs/roadmap.md` — phase plan.
- `docs/handoffs/` — per-agent handoff notes.
- `README.md` — human-facing overview.

## Agent responsibilities & file ownership

Three independent Kilo conversations share ONE VS Code window and ONE Git repository (branch
`main`). They do NOT have filesystem isolation. The authoritative ownership table is in
`docs/contracts/ownership.md`; summary:

- **Agent 1 — Platform & Architecture**: repository architecture, dependency management, Docker,
  CI/CD, shared config, security/portability, dev rules, architecture docs, integration/final
  validation. Owns `AGENTS.md`, `.kilo/`, `.github/`, `pyproject.toml`, `uv.lock`,
  `.python-version`, `.env.example`, `.gitignore`, `.dockerignore`, `.editorconfig`,
  `compose.yaml`, `docker/`, `README.md`, `docs/architecture/`, `docs/contracts/`,
  `docs/decisions/`, `docs/development.md`, `docs/roadmap.md`, `tests/integration/`,
  `docs/handoffs/01-platform.md`.
- **Agent 2 — Backend Engineering**: FastAPI app, endpoints, backend config/logging, services,
  future RAG/providers, backend tests/docs. Owns `src/enterprise_ai_document_assistant/`,
  `tests/backend/`, `docs/backend.md`, `docs/handoffs/02-backend.md`.
- **Agent 3 — Frontend Engineering**: Streamlit app, frontend architecture, HTTP API client, UI
  components, UX, frontend tests/docs. Owns `frontend/`, `tests/frontend/`, `docs/frontend.md`,
  `docs/handoffs/03-frontend.md`.

### Multi-agent coordination protocol (all agents must follow)
1. Read `AGENTS.md` before implementation.
2. Read the relevant architecture docs and API contracts.
3. Inspect existing code before modifying it.
4. Plan non-trivial changes.
5. Keep changes focused.
6. Respect file ownership — only edit files you own.
7. Avoid unnecessary dependencies.
8. Use Python type hints.
9. Handle errors explicitly.
10. Add meaningful tests.
11. Run relevant validation commands.
12. Update appropriate documentation.
13. Report incomplete or untested work.
14. Never claim tests passed unless they were actually executed.
15. Never expose credentials.
16. Never deploy, publish, or push without approval.

Concurrency specifics (inspect `git status` first; never discard/reset/overwrite another agent's
work; no broad repo-wide reformatting while others work; coordinate commits so you don't include
another agent's uncommitted changes; stop and document if a conflict or dependency change is
needed) are in `.kilo/rules/multi-agent-coordination.md`.

## Coding conventions

- Python 3.12, type hints on all new functions/public APIs.
- Consistent logging via the standard `logging` module (module-level `logger =
  logging.getLogger(__name__)`). Never log secrets.
- Configuration from `core/config.py` (`pydantic-settings`), not hard-coded values.
- Follow Ruff lint + format as configured in `pyproject.toml`.
- No dead code, no speculative abstractions for unimplemented phases.
- Prefer existing patterns over new abstractions.

## Dependency management

- Single root-level Python project. Runtime deps vs dev deps are separated in `pyproject.toml`.
- `uv.lock` is generated by the real resolver — never fabricate or hand-edit it.
- Use `uv sync --locked` for reproducible installs. Do not rely on global pip installs.
- Only Agent 1 modifies `pyproject.toml` / `uv.lock`. Others request changes via
  `docs/contracts/ownership.md`.

## Testing requirements

- Add meaningful tests for new logic in the correct owned directory.
- Tests must not require paid APIs, external credentials, or network access.
- No fake passing tests. Never bypass a failing test to go green.
- Phase 0 has only minimal infrastructure/config tests; full suites belong to Agents 2 and 3.

## Security requirements

- Never commit `.env`, credentials, API keys, `.venv`, `__pycache__`, uploaded private documents,
  vector database files, runtime-generated data, or machine-specific paths.
- The app starts without an OpenAI API key in Phase 0.
- Never expose secrets in logs. Keep runtime state separate from source code.

## Portability requirements

- The repository must be transferable via Git or ZIP and work on both Windows and Linux.
- All tracked files use portable, relative paths (no `C:\...`, no user-specific dirs).
- LF line endings (`.editorconfig`). Everything runs through `uv` (no global tool installs).
- Native execution with `uv` must remain possible without Docker.

## Documentation requirements

- Keep documentation concise and accurate. Update the doc you own when your area changes.
- Record significant decisions as ADRs in `docs/decisions/`.
- Update your handoff file (`docs/handoffs/0X-*.md`) after each substantial change.

## Definition of Done (per change)

- Owned files only were modified.
- `uv run ruff check .`, `uv run ruff format --check .`, and `uv run pytest` pass (and were run).
- Documentation updated where required.
- No credentials, machine-specific paths, or runtime data committed.
- Handoff note updated if the change affects another agent's area.
