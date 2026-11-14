#!/bin/sh
# Entrypoint for the api service (runs as root, then drops to the app user).
#
# A named volume mounted at /app/.data is initialised by Docker with root ownership, but the app
# runs as the non-root `appuser` (uid 1000) and must create `.data/documents` inside it. We chown
# the volume's top-level directory to the app user, then drop privileges with gosu before starting
# uvicorn. This is a one-time fix per fresh volume; once owned by appuser it is a no-op.
set -e

DATA_DIR="${DATA_DIR:-/app/.data}"
APP_USER="${APP_USER:-appuser}"

mkdir -p "$DATA_DIR"
chown -R "$APP_USER" "$DATA_DIR" 2>/dev/null || true

exec gosu "$APP_USER" /app/.venv/bin/uvicorn enterprise_ai_document_assistant.api.main:app --host 0.0.0.0 --port 8000
