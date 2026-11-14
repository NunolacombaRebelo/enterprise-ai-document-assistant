---
name: review-change
description: Review a change in this repository for architecture compliance, code quality, security, and portability, and run the applicable tests. Use when asked to review a diff, a set of files, or a proposed change before it is committed.
---

# Review a change (this project)

A repeatable review workflow. The review checks the change against this repository's rules
(`AGENTS.md`, `.kilo/rules/`, `docs/contracts/`). Report findings; do not silently fix them unless
asked.

## 1. Scope the change
- Identify which files changed (`git status` / the provided diff).
- Map each file to its owning agent via `docs/contracts/ownership.md`. **Flag any edit to a file
  outside the reviewer's or author's ownership** — that is a coordination violation.

## 2. Architecture compliance
- Does the change respect the modular-monolith boundaries (`docs/architecture/overview.md`)?
- Is frontend→backend communication HTTP-only? Any direct import of backend internals from
  `frontend/` is a finding.
- Are new settings added in `core/config.py` (not scattered `os.environ` reads)?
- Were dependencies added without going through Agent 1? Flag it.

## 3. Code quality
- Type hints present on new functions/public APIs?
- Errors handled explicitly (no silent bare `except`)?
- Logging consistent (module-level logger), no secrets logged?
- No dead code, no speculative abstractions for unimplemented phases?
- Follows Ruff lint + format?

## 4. Security
- No credentials, API keys, or secrets introduced or logged?
- No `.env` / real credential files staged?
- Runtime data (uploads, vector stores) kept out of source and out of git?

## 5. Portability
- All paths relative/portable (no `C:\...`, no user-specific dirs)?
- Line endings LF? No CRLF-only files?
- Docker Compose: relative build contexts, configurable ports, no privileged containers, no baked
  credentials?

## 6. Run applicable tests
```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest
```
Report pass/fail honestly. Do not claim a check passed if it was not executed.

## 7. Report findings
Produce a concise report grouped by severity (blocker / should-fix / nit), each with file:line and
a concrete suggestion. End with an overall verdict (approve / request changes) and any coordination
requests needed through Agent 1.
