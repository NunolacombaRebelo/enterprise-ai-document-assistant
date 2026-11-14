---
name: implement-feature
description: Implement a feature or change in this repository following the project's multi-agent ownership, coding, testing, and documentation rules. Use when asked to add a feature, fix a bug, or make a focused change to owned files.
---

# Implement a feature (this project)

A repeatable workflow for making a focused, safe change in this multi-agent repository. Follow the
root `AGENTS.md` and `.kilo/rules/` — this skill operationalizes them; it does not replace them.

## 1. Read relevant context
- Read `AGENTS.md` (root) — always authoritative.
- Read `docs/contracts/api.md` and `docs/contracts/ownership.md`.
- Identify which agent owns the files you need to touch. **If the change requires editing files
  you do not own, stop and note that it needs coordination through Agent 1** — do not edit them.
- Inspect the existing code in the target area before modifying it. Do not assume structure.

## 2. Identify acceptance criteria
- State, in a few bullets, what "done" means for this change (behavior, endpoints, files touched).
- If the request is ambiguous, state your interpretation explicitly before proceeding.

## 3. Plan implementation
- For non-trivial changes, write a short plan: which files change, what each change does, why.
- Keep the plan scoped to owned files only. No drive-by refactors or broad reformatting.

## 4. Modify owned files
- Make focused edits. Use Python type hints on all new functions/public APIs.
- Handle errors explicitly (no silent bare `except`).
- Add new dependencies only if strictly necessary, and only via the dependency-change procedure
  (Agent 1 owns `pyproject.toml` / `uv.lock`).
- Never expose credentials or machine-specific paths.

## 5. Add tests
- Add meaningful tests for the new logic in the correct owned test directory
  (`tests/backend/`, `tests/frontend/`, or `tests/integration/`).
- Tests must not require paid APIs, external credentials, or network access.
- Do not write fake passing tests.

## 6. Validate changes
Run and confirm these actually pass (do not claim otherwise):
```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest
```
Fix scaffold/code errors you introduced. If a check cannot be executed, say so.

## 7. Update handoff
- Update your agent's handoff file (`docs/handoffs/0X-*.md`) with what changed, what was validated,
  known limitations, and anything another agent must know.
- If the change affects a contract or shared config, document the coordination request instead of
  forcing it.
