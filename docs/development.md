# Development Guide

Setup, execution, testing, troubleshooting, and clean-machine restoration for both Windows and
Linux. Everything runs through `uv` — no global Python tool installs are required.

## Prerequisites

- **uv** — install from <https://docs.astral.sh/uv/>. (Python 3.12 is managed by uv; no separate
  Python install is needed.)
- **Git** — for version control.
- **Docker + Docker Compose** — only for the containerized workflow.

## Windows setup (PowerShell)

```powershell
# 1. Get the repository (clone or extract a ZIP) and open it in VS Code.
cd enterprise-ai-document-assistant

# 2. Install locked dependencies into the project virtual environment.
uv sync --locked

# 3. (Optional) Create your local environment file from the template.
Copy-Item .env.example .env
#    Edit .env if you need to change ports or add an API key later. Phase 0 needs none.
```

## Linux setup

```bash
cd enterprise-ai-document-assistant
uv sync --locked
cp .env.example .env   # optional; Phase 0 needs no real values
```

## uv dependency management

- `pyproject.toml` declares runtime and dev dependencies.
- `uv.lock` is the generated, reproducible lockfile — **never hand-edit it**.
- `uv sync --locked` installs exactly the locked versions into `.venv/`.
- To change dependencies, only Agent 1 edits `pyproject.toml` and runs `uv lock` (see
  `docs/contracts/ownership.md`).

## Local development (native, no Docker)

Start the backend:

```bash
uv run uvicorn enterprise_ai_document_assistant.api.main:app --host 127.0.0.1 --port 8000
```

In a second terminal, start the frontend. The frontend imports itself as a package (`frontend.*`),
so the **repository root must be on `PYTHONPATH`** — Streamlit only adds the script's own directory
(`frontend/`) to `sys.path`, not the repo root. Run from the repository root with `PYTHONPATH` set:

```bash
# Linux / macOS
PYTHONPATH="$(pwd)" uv run streamlit run frontend/app.py
```

```powershell
# Windows PowerShell
$env:PYTHONPATH = (Get-Location).Path; uv run streamlit run frontend/app.py
```

Open http://localhost:8501. Health check: `curl http://localhost:8000/health` → `{"status":"ok"}`.

For development with auto-reload on the backend:

```bash
uv run uvicorn enterprise_ai_document_assistant.api.main:app --reload --port 8000
```

## Docker workflow

```bash
docker compose up --build
```

- Frontend: http://localhost:8501
- Backend:  http://localhost:8000 (health at `/health`)

Stop and remove containers:

```bash
docker compose down
```

Host ports are configurable via environment variables (`API_PORT`, `FRONTEND_PORT`), e.g.
`API_PORT=9000 FRONTEND_PORT=9501 docker compose up --build`.

The vector store (Milestone 2, embedded ChromaDB) and document storage are persisted on the named
volume `vector-data` (mounted at `/app/.data`), so they survive `docker compose down` (use
`docker compose down -v` to also delete them). Locally this is `.data/` (git-ignored). See ADR 0007.

## Testing and linting

```bash
uv run ruff check .          # lint
uv run ruff format --check . # formatting check
uv run pytest                # tests
```

To apply formatting (only when you own the files being formatted):

```bash
uv run ruff format .
```

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `uv: command not found` | uv not installed / not on PATH | Install uv and restart the terminal. |
| `Failed to build ... Readme file does not exist` | Building before `README.md` exists | Ensure `README.md` is present (it is tracked). |
| Port already in use | Another process on 8000/8501 | Change `API_PORT` / `FRONTEND_PORT`, or stop the other process. |
| Frontend can't reach backend | `API_BASE_URL` wrong | Native: `http://localhost:8000`; Docker: `http://api:8000`. |
| `uv sync --locked` fails on lock mismatch | `pyproject.toml` changed without re-locking | Agent 1 runs `uv lock`; others do not edit deps. |
| `ModuleNotFoundError: No module named 'frontend'` (native) | Repo root not on `PYTHONPATH` when running `streamlit run frontend/app.py` | Set `PYTHONPATH` to the repo root before launching (see "Local development"). |
| `ModuleNotFoundError: No module named 'frontend'` (Docker) | Frontend image missing the launcher / `PYTHONPATH=/app` | Rebuild: `docker compose build frontend`. The image uses `docker/frontend-launch.sh` + `PYTHONPATH=/app`. |
| Starlette TestClient import error mentioning `httpx2` | `chromadb → huggingface-hub 2.x → httpx2` shadowing `httpx` | Resolved by the `[tool.uv] constraint-dependencies = ["huggingface-hub<1"]` in `pyproject.toml`. If it reappears, confirm the constraint is present and re-run `uv lock` + `uv sync --locked`. |
| Search returns no results / only lexical matches | Running in lexical-only mode (no embedding provider configured) | Expected in Milestone 2. Set an embedding endpoint/key and switch `RETRIEVAL_MODE` to `vector`/`hybrid` in Milestone 3. |

## Clean-machine restoration

To restore the project on a fresh machine (Windows or Linux):

1. Install **uv** and **git** (and Docker if using containers).
2. Obtain the repository (git clone or ZIP).
3. Run `uv sync --locked` — uv reads `.python-version` (3.12), installs that interpreter if needed,
   and creates `.venv/` with the exact locked dependencies.
4. (Optional) `cp .env.example .env` and fill in any values you need (none required in Phase 0).
5. Run the app natively or via `docker compose up --build`.
6. Verify with `uv run pytest`.

No global Python packages, no manual venv creation, and no machine-specific paths are required.

## Transfer checklist (moving the repository)

**Files to transfer:** the entire tracked repository (everything `git ls-files` lists), including
`pyproject.toml`, `uv.lock`, `.python-version`, `compose.yaml`, `docker/`, `src/`, `frontend/`,
`tests/`, `docs/`, `AGENTS.md`, `kilo.jsonc`, `.kilo/`, `.github/`, and the dotfiles
(`.env.example`, `.gitignore`, `.dockerignore`, `.editorconfig`).

**Files to exclude:** `.venv/`, `__pycache__/`, caches, `.env` (real credentials), `.data/`,
`uploads/`, vector-store files, editor/OS artifacts. These are git-ignored and must not be copied.

**Dependencies to reinstall:** run `uv sync --locked` on the destination machine. Do not copy
`.venv/` between machines (it is machine-specific).

**Environment variables to configure:** none required to start (Milestone 0–2). The app runs in
lexical-only mode with no credentials. For Milestone 3+, copy `.env.example` to `.env` and set
`OPENAI_API_KEY`, `EMBEDDING_BASE_URL` / `EMBEDDING_API_KEY`, and `RETRIEVAL_MODE` as needed.

**Docker rebuilding:** run `docker compose up --build` on the destination to rebuild images from the
Dockerfiles (do not copy built images or volumes).

**Resuming development with Kilo:** open the repository in VS Code with Kilo Code. Kilo auto-loads
`AGENTS.md` and the `.kilo/rules/` (via `kilo.jsonc`) and discovers the skills in `.kilo/skills/`.
Read `AGENTS.md` and your agent's handoff file before continuing work.
