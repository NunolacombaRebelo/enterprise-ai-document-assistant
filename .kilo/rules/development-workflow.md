# Development workflow

Rules that govern how work is done in this repository. The root `AGENTS.md` is the source of
truth for project purpose, architecture, and the multi-agent protocol; this file holds the
actionable day-to-day workflow guardrails.

## Before you start a task
- Read `AGENTS.md` (root) first. It is always loaded and is authoritative.
- Read the relevant contract: `docs/contracts/api.md` (API) and `docs/contracts/ownership.md`
  (who owns what).
- Inspect existing code before modifying it. Do not assume structure — verify it.
- For non-trivial changes, state a short plan (what changes, which files, why) before editing.

## While working
- Keep changes focused on the task. No drive-by refactors, no broad reformatting, no unrelated
  cleanup while other agents may be working.
- Respect file ownership (`docs/contracts/ownership.md`). Only edit files you own.
- Add new dependencies only when strictly necessary for the task, and only through the
  dependency-change procedure (Agent 1 owns `pyproject.toml` / `uv.lock`).
- Use Python type hints on all new functions and public APIs.
- Handle errors explicitly: no bare `except:` that swallows exceptions silently; log or raise
  with context.
- Prefer the existing patterns in the codebase over introducing new abstractions.

## After working
- Run the relevant validation commands before declaring done:
  - `uv run ruff check .`
  - `uv run ruff format --check .`
  - `uv run pytest`
- Update the appropriate documentation (see `docs/contracts/ownership.md` for which doc each agent
  owns).
- Report any incomplete or untested work explicitly. Never claim tests passed unless they were
  actually executed in this session.

## Definition of Done (per change)
- Owned files only were modified.
- Lint + format + relevant tests pass (and were actually run).
- Documentation updated where required.
- No credentials, machine-specific paths, or runtime data committed.
- Handoff note updated if the change affects another agent's area.
