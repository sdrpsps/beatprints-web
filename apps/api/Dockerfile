FROM node:24-alpine AS web-builder

ARG BUILD_VERSION
ARG BUILD_GIT_SHA

ENV PNPM_HOME=/pnpm \
    PATH=/pnpm:$PATH \
    VITE_APP_VERSION=$BUILD_VERSION \
    VITE_GIT_SHA=$BUILD_GIT_SHA

WORKDIR /app

RUN corepack enable

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml VERSION ./
COPY apps/web/package.json ./apps/web/

RUN --mount=type=cache,id=pnpm,target=/pnpm/store \
    pnpm install --frozen-lockfile --filter @beatprints/web...

COPY apps/web ./apps/web
RUN pnpm --filter @beatprints/web build

FROM ghcr.io/astral-sh/uv:0.11.32-python3.14-trixie-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_DEV=1 \
    PORT=8000 \
    WEB_CONCURRENCY=1 \
    MAX_CONCURRENT_JOBS=1

WORKDIR /app

COPY pyproject.toml uv.lock LICENSE ./
COPY apps/api/README.md ./apps/api/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project

COPY apps/api/src ./apps/api/src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-editable --reinstall-package beatprints-api && \
    uv pip uninstall \
        pylette opencv-python scikit-learn scipy numpy \
        joblib narwhals threadpoolctl \
        black mypy-extensions pathspec platformdirs pytokens \
        questionary prompt-toolkit wcwidth \
        rich markdown-it-py mdurl pygments \
        toml typer shellingham \
        python-dotenv pyyaml watchfiles websockets && \
    find /app/.venv -type d -name __pycache__ -prune -exec rm -rf {} + && \
    find /app/.venv -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete

FROM python:3.14-slim-trixie AS runtime

ARG BUILD_VERSION
ARG BUILD_GIT_SHA

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/app/.venv/bin:$PATH \
    WEB_DIST_DIR=/app/web \
    BEATPRINTS_VERSION=$BUILD_VERSION \
    BEATPRINTS_GIT_SHA=$BUILD_GIT_SHA \
    PORT=8000 \
    WEB_CONCURRENCY=1 \
    MAX_CONCURRENT_JOBS=1

WORKDIR /app

RUN useradd --create-home --uid 10001 appuser

COPY --chown=appuser:appuser --from=builder /app/.venv /app/.venv
COPY --chown=appuser:appuser --from=web-builder /app/apps/web/dist /app/web
COPY --chown=appuser:appuser VERSION /app/VERSION

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:' + __import__('os').getenv('PORT', '8000') + '/health', timeout=3)"

CMD ["beatprints-api"]
