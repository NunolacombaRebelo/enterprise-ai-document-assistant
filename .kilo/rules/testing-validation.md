# Testing and validation

## Commands (run these before declaring work done)
```bash
uv sync --locked            # reproducible install from uv.lock
uv run ruff check .         # lint
uv run ruff format --check .# formatting check
uv run pytest               # tests
```

## Test requirements
- Add meaningful tests for new logic. A test that asserts nothing, or that is hard-wired to pass,
  is a fake passing test — do not write those.
- Tests must NOT require paid APIs, external credentials, or network access. Use fakes / in-memory
  / `TestClient` as appropriate.
- Phase 0 includes only minimal infrastructure/config tests. The full backend suite is Agent 2's
  responsibility (`tests/backend/`); the full frontend suite is Agent 3's (`tests/frontend/`).
  Integration tests are Agent 1's (`tests/integration/`).
- Never bypass a failing test to make CI green. Fix the code or the test honestly; if the test is
  wrong, say so explicitly.

## Validation honesty
- Only report "tests passed" if you actually ran them in this session and saw them pass.
- If a check could not be executed (e.g. Docker build unavailable), document that it was not
  executed rather than claiming it passed.
