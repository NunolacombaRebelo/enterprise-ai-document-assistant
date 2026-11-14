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

# Non-root user + gosu (used by the entrypoint to fix volume ownership then drop privileges).
RUN useradd --create-home --uid 1000 appuser \
    && apt-get update \
    && apt-get install -y --no-install-recommends gosu \
    && rm -rf /var/lib/apt/lists/*

COPY docker/api-entrypoint.sh /usr/local/bin/api-entrypoint.sh
RUN chmod +x /usr/local/bin/api-entrypoint.sh

# The entrypoint runs as root to chown the mounted data volume, then drops to appuser via gosu.
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4).status==200 else 1)"]

ENTRYPOINT ["/usr/local/bin/api-entrypoint.sh"]
