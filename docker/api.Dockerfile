# Backend (FastAPI) service image.
#
# Build context is the repository root (set in compose.yaml). Uses uv for reproducible,
# locked dependency installation. Runs as a non-root user. No credentials are baked in.
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_NO_SYNC=1

WORKDIR /app

# Install uv (pinned) into the image.
COPY --from=ghcr.io/astral-sh/uv:0.13.8 /uv /usr/local/bin/uv

# Copy project metadata and source, then install locked runtime dependencies plus the project.
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN uv sync --frozen --no-dev

# Drop privileges.
RUN useradd --create-home --uid 1000 appuser
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4).status==200 else 1)"]

CMD ["/app/.venv/bin/uvicorn", "enterprise_ai_document_assistant.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
