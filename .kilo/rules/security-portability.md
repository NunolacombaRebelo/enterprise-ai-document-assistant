# Security and portability

## Secrets and credentials
- NEVER commit `.env`, API keys, tokens, or any credential. Only `.env.example` (with empty /
  placeholder values) is tracked.
- The application must start **without** an OpenAI API key in Phase 0. Credentials are optional at
  runtime, never required to boot.
- Never print secrets to logs. Mask or omit `OPENAI_API_KEY` and any token in log output.
- Keep runtime state separate from source code: uploads, extracted text, vector stores, and
  generated data live under ignored paths (`.data/`, `uploads/`, etc.), never in the repo.

## Portability (Windows <-> Linux)
- All tracked files must use portable, relative paths. No absolute machine paths, no drive letters
  (`C:\...`), no user-specific directories.
- Use POSIX-style paths in code and config where possible; let Python/uv handle OS differences.
- Line endings: LF (enforced by `.editorconfig`). Do not commit CRLF-only files.
- Do not rely on global tool installs. Everything runs through `uv` (project venv) so the repo is
  reproducible on a clean machine.
- Docker Compose uses relative build contexts and configurable host ports; no hardcoded
  credentials, no privileged containers, local-only exposure by default.

## What must never be committed
- `.env` and any real credential file.
- `.venv/`, `__pycache__/`, caches.
- Uploaded private documents, extracted content, vector database files, or any runtime-generated
  data.
- Machine-specific paths or editor/OS artifacts.
