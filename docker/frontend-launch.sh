#!/bin/sh
# Streamlit launcher for the frontend service.
#
# The frontend is a Python package that imports itself as ``frontend.*`` (e.g.
# ``from frontend.api.client import DocumentAPIClient``). Streamlit adds the *script's* directory
# (/app/frontend) to sys.path, not the repository root, so ``import frontend`` would fail inside the
# image. We therefore launch from a script whose own directory IS the repository root (/app), which
# puts /app on sys.path and makes the ``frontend`` package importable. No source files are modified.
set -e

# Use the absolute venv path: the non-root appuser's PATH does not include /app/.venv/bin.
# The script lives in /usr/local/bin, so its directory is NOT /app; PYTHONPATH=/app (set in the
# image) is what makes the ``frontend`` package importable.
cd /app
exec /app/.venv/bin/streamlit run frontend/app.py
