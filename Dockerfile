FROM python:3.11-slim AS builder
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# --- Этап 2: Финальный образ ---
FROM python:3.11-slim

# Версия образа — передаётся из CI при сборке (см. .gitlab-ci.yml)
ARG APP_VERSION=dev
ARG GIT_COMMIT=unknown
ARG BUILD_TIME=unknown
ENV APP_VERSION=$APP_VERSION \
    GIT_COMMIT=$GIT_COMMIT \
    BUILD_TIME=$BUILD_TIME

RUN useradd -m -u 1000 appuser
WORKDIR /app
COPY --from=builder /install /usr/local
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 && rm -rf /var/lib/apt/lists/*

COPY app/ ./app/
COPY static/ ./static/
COPY alembic.ini .
COPY alembic/ ./alembic/
COPY scripts/ ./scripts/

RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
