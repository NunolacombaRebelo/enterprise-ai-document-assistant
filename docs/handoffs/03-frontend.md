# Handoff — Agent 3 (Frontend Engineering)

## Current status
**Not started.** Phase 0 provides the foundation; Agent 3 begins frontend work from here.

## Starting points
- Read `AGENTS.md`, `docs/contracts/api.md`, and `docs/contracts/ownership.md` first.
- The Streamlit entrypoint is `frontend/app.py` (currently a Phase 0 placeholder — replace it).
- Talk to the backend over HTTP using `API_BASE_URL` (native `http://localhost:8000`, Docker
  `http://api:8000`). Never import backend internals.
- Frontend tests live in `tests/frontend/`.

## Owned paths
- `frontend/`
- `tests/frontend/`
- `docs/frontend.md`
- `docs/handoffs/03-frontend.md` (this file)

## Conventions
- Frontend → backend is HTTP only; no shared in-process state.
- Read backend URLs from the environment, never hardcode them.
- Keep the UI professional and accessible.

## Update this file after each substantial change: what changed, what was validated, limitations,
remaining tasks, and anything Agent 1/2 must know.
