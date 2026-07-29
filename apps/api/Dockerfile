FROM ghcr.io/astral-sh/uv:0.11.32-python3.12-trixie-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_DEV=1 \
    UV_DEFAULT_INDEX=https://pypi.org/simple \
    PORT=8000 \
    WEB_CONCURRENCY=1 \
    MAX_CONCURRENT_JOBS=1

WORKDIR /app

COPY apps/api/pyproject.toml apps/api/uv.lock apps/api/README.md LICENSE ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project

COPY apps/api/src ./src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-editable && \
    uv pip uninstall \
        pylette opencv-python scikit-learn scipy numpy \
        joblib narwhals threadpoolctl && \
    find /app/.venv -type d -name __pycache__ -prune -exec rm -rf {} + && \
    find /app/.venv -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete

FROM python:3.12-slim-trixie AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/app/.venv/bin:$PATH \
    PORT=8000 \
    WEB_CONCURRENCY=1 \
    MAX_CONCURRENT_JOBS=1

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv

RUN useradd --create-home --uid 10001 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:' + __import__('os').getenv('PORT', '8000') + '/health', timeout=3)"

CMD ["beatprints-api"]
