# Multi-agent coordination

Three independent Kilo conversations develop this repository in ONE VS Code window and ONE shared
Git repository (branch `main`). Separate conversations do NOT provide filesystem isolation — all
agents share the same working tree. These rules prevent collisions.

## File ownership (authoritative: `docs/contracts/ownership.md`)
- **Agent 1 — Platform & Architecture**: `AGENTS.md`, `.kilo/`, `.github/`, `pyproject.toml`,
  `uv.lock`, `.python-version`, `.env.example`, `.gitignore`, `.dockerignore`, `.editorconfig`,
  `compose.yaml`, `docker/`, `README.md`, `docs/architecture/`, `docs/contracts/`,
  `docs/decisions/`, `docs/development.md`, `docs/roadmap.md`, `tests/integration/`,
  `docs/handoffs/01-platform.md`.
- **Agent 2 — Backend Engineering**: `src/enterprise_ai_document_assistant/`, `tests/backend/`,
  `docs/backend.md`, `docs/handoffs/02-backend.md`.
- **Agent 3 — Frontend Engineering**: `frontend/`, `tests/frontend/`, `docs/frontend.md`,
  `docs/handoffs/03-frontend.md`.

## Concurrency rules (all agents)
1. Respect your assigned file ownership. Only edit files you own.
2. Never simultaneously edit shared configuration files. If you need a shared-file change, stop and
   coordinate through Agent 1.
3. Only Agent 1 modifies dependency files (`pyproject.toml`, `uv.lock`) and global development
   rules (`AGENTS.md`, `.kilo/rules/`).
4. Contract changes are coordinated through Agent 1 (`docs/contracts/`).
5. Agents 2 and 3 must not change shared files.
6. Inspect `git status` before making changes.
7. No agent may discard, reset, or overwrite another agent's work. Never run destructive git
   commands (`reset --hard`, `checkout -- .`, `clean -fd`) that could remove others' changes.
8. Avoid broad repository-wide formatting or refactoring while others may be working. Scope edits
   to your owned files.
9. Coordinate Git commits so you do not accidentally include another agent's uncommitted changes.
   Stage only your own files explicitly; never use `git add -A` / `git add .` blindly.
10. If a conflict or a dependency change is required, stop the affected operation and document the
    request in your handoff file rather than forcing it through.

## Commit hygiene
- Use focused commits with clear messages describing what changed and why.
- Stage only the files you own and changed for this task.
- Do not commit credentials, machine-specific paths, or runtime data.
- Do not push to any remote without explicit approval (Phase 0 has no remote configured).
