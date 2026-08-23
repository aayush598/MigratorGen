FROM python:3.14-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_LINK_MODE=copy

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml ./
COPY sdk/python/ sdk/python/

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-install-project --no-dev --no-editable

COPY . .

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-install-project --no-dev --no-editable && \
    uv pip install -e sdk/python[all] --no-editable


FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    LOG_LEVEL=INFO \
    UV_LINK_MODE=copy

RUN groupadd -g 1000 appgroup && useradd --uid 1000 --gid 1000 --create-home appuser

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY --from=builder /app ./

RUN uv sync --no-install-project --no-dev --no-editable

USER 1000

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl --fail http://localhost:8001/health || exit 1

CMD ["python", "-m", "uvicorn", "backend.worker.src.main:app", "--host", "0.0.0.0", "--port", "8001"]