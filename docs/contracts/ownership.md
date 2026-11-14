# Ownership & Coordination Contract

This is the authoritative file-ownership and coordination contract for the three agents. It must be
established **before** Agents 2 and 3 begin implementation work. The summary in `AGENTS.md` mirrors
this file; this file is the source of truth for ownership.

## Workspace model

- ONE VS Code window, ONE Git repository, ONE branch (`main`).
- THREE independent Kilo conversations share the same working tree.
- Separate Kilo conversations do **not** provide filesystem isolation. All agents see and can touch
  the same files, so ownership discipline is mandatory.

## Agent responsibilities

### Agent 1 — Platform & Architecture
Repository architecture, Python dependency management, Docker/Compose, CI/CD, shared
configuration, security and portability, development rules, architecture documentation, and final
integration/validation.

### Agent 2 — Backend Engineering
FastAPI application, API endpoints, backend configuration and logging, backend services, future RAG
and provider integrations, backend tests, backend documentation.

### Agent 3 — Frontend Engineering
Streamlit application, frontend architecture, HTTP API client, UI components, user experience,
frontend tests, frontend documentation.

## File ownership (exclusive)

| Path | Owner |
| --- | --- |
| `AGENTS.md` | Agent 1 |
| `.kilo/` (rules + skills) | Agent 1 |
| `.github/` | Agent 1 |
| `pyproject.toml` | Agent 1 |
| `uv.lock` | Agent 1 |
| `.python-version` | Agent 1 |
| `.env.example` | Agent 1 |
| `.gitignore` | Agent 1 |
| `.dockerignore` | Agent 1 |
| `.editorconfig` | Agent 1 |
| `compose.yaml` | Agent 1 |
| `docker/` | Agent 1 |
| `README.md` | Agent 1 |
| `docs/architecture/` | Agent 1 |
| `docs/contracts/` | Agent 1 |
| `docs/decisions/` | Agent 1 |
| `docs/development.md` | Agent 1 |
| `docs/roadmap.md` | Agent 1 |
| `tests/integration/` | Agent 1 |
| `docs/handoffs/01-platform.md` | Agent 1 |
| `src/enterprise_ai_document_assistant/` | Agent 2 |
| `tests/backend/` | Agent 2 |
| `docs/backend.md` | Agent 2 |
| `docs/handoffs/02-backend.md` | Agent 2 |
| `frontend/` | Agent 3 |
| `tests/frontend/` | Agent 3 |
| `docs/frontend.md` | Agent 3 |
| `docs/handoffs/03-frontend.md` | Agent 3 |

**Note:** `src/enterprise_ai_document_assistant/core/config.py` was created by Agent 1 as shared
configuration. Agent 2 may extend it to add backend-specific settings, but any change that affects
shared behavior or adds dependencies must go through the dependency/configuration change procedure
below (Agent 1 review).

## Dependency change procedure

1. Only Agent 1 edits `pyproject.toml` and regenerates `uv.lock`.
2. Agents 2/3 who need a new dependency write a request in their handoff file: package name,
   version constraint, why it is needed, which phase requires it.
3. Agent 1 reviews (checking against "no speculative dependencies"), applies the change, runs
   `uv lock`, and confirms in `docs/handoffs/01-platform.md`.
4. The requesting agent re-syncs with `uv sync --locked`.

Do not add LangChain / ChromaDB / OpenAI SDKs before their phase begins (see `docs/roadmap.md`).

## Contract change procedure

1. Propose the change in your handoff file.
2. Agent 1 reviews and updates the contract in `docs/contracts/` (Agent 1 owns this directory).
3. Affected agents confirm the change before implementing against it.

## Parallel development rules

- Each agent works only within its owned paths.
- Never simultaneously edit a shared configuration file. If one is needed, stop and coordinate
  through Agent 1.
- Inspect `git status` before making changes.
- No agent may discard, reset, or overwrite another agent's work (no destructive git commands).
- Avoid broad repository-wide formatting/refactoring while others may be working; scope edits to
  owned files.
- Stage only your own files when committing; never use `git add -A` / `git add .` blindly.
- If a conflict or dependency change is required, stop the affected operation and document the
  request rather than forcing it through.

## Handoff requirements

Each agent maintains its handoff file:
- `docs/handoffs/01-platform.md` (Agent 1)
- `docs/handoffs/02-backend.md` (Agent 2)
- `docs/handoffs/03-frontend.md` (Agent 3)

After each substantial change, update your handoff with: what changed, what was validated (commands
actually run), known limitations, remaining tasks, and anything another agent must know.

## Integration responsibilities

- **Agent 1** owns integration and final validation: running the full suite (`ruff check`,
  `ruff format --check`, `pytest`), validating Docker Compose, confirming the end-to-end health
  path, and performing the Phase completion check.
- **Agent 2** ensures the backend satisfies `docs/contracts/api.md` and keeps backend tests green.
- **Agent 3** ensures the frontend talks to the backend per the contract and keeps frontend tests
  green.
- Cross-agent integration issues are resolved through Agent 1 coordination, not by one agent editing
  another's files.
