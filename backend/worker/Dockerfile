FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml ./
COPY sdk/python/ sdk/python/

RUN uv sync --no-install-project --no-dev --no-editable

COPY . .

RUN uv sync --no-install-project --no-dev --no-editable && \
    uv pip install -e sdk/python[all] --no-editable

ENTRYPOINT ["python", "-m", "backend.worker.src.run"]