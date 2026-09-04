# ── Stage 1: Builder ─────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# System dependencies needed for compilation (psycopg, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements/ /build/requirements/
RUN pip install --no-cache-dir --prefix=/install -r requirements/base.txt

# ── Stage 2: Runtime (smaller, no build tools) ───────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Only the runtime C library for Postgres
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy pre-built Python packages from builder stage
COPY --from=builder /install /usr/local

# Copy source code
COPY . /app/

# Non-root user for security
RUN useradd --create-home appuser
USER appuser

# Health check for the API container
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# The commands for running Celery or the API are in docker-compose.yml
