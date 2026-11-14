# ADR 0006 — AI-agent development rules and multi-agent ownership

## Status
Accepted (Phase 0)

## Context
Three independent Kilo Code conversations will develop this repository in ONE VS Code window and ONE
shared Git repository (branch `main`). Separate conversations do not provide filesystem isolation, so
without explicit rules the agents would collide on shared files, dependencies, and contracts. We need
versioned, machine-readable agent instructions that keep development fast, safe, and consistent.

## Decision
Adopt a documented multi-agent model with:
- A root **`AGENTS.md`** (auto-loaded, write-protected) holding project purpose, architecture,
  conventions, and the coordination protocol.
- **Modular Kilo rules** in `.kilo/rules/` (loaded via `kilo.jsonc`) for workflow, architecture/code
  quality, security/portability, testing, and multi-agent coordination.
- **Reusable skills** in `.kilo/skills/` (`implement-feature`, `review-change`).
- **Exclusive file ownership** per agent (Agent 1 Platform, Agent 2 Backend, Agent 3 Frontend),
  defined authoritatively in `docs/contracts/ownership.md`.
- **Integration contracts** in `docs/contracts/` (API + ownership) established before Agents 2/3
  begin.
- **Per-agent handoff files** in `docs/handoffs/`.

## Consequences
- Positive: agents have unambiguous scope, shared-file changes are coordinated through Agent 1, and
  work is reproducible and reviewable.
- Negative: agents must follow the protocol (inspect git status, stage only owned files, no
  destructive git commands); enforced by rules and review skill rather than tooling.
- Only Agent 1 modifies dependency files and global rules; contract changes go through Agent 1.
