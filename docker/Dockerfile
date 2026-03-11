# Ussop - AI Visual Inspector
# Multi-stage build: keeps the final image lean
FROM python:3.11-slim AS builder

WORKDIR /build

# System deps for OpenCV + PostgreSQL client
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir ".[integrations]" \
    psycopg2-binary alembic redis

# ─────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Runtime system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx libglib2.0-0 libsm6 libxext6 libxrender-dev \
    libgomp1 libpq5 curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11 /usr/local/lib/python3.11
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY . .

# Create runtime directories
RUN mkdir -p data/images data/masks data/models data/db

EXPOSE 8080

# Default: API server with uvicorn
# Worker mode: set WORKER_MODE=1 env var to run background jobs
CMD ["sh", "-c", \
     "if [ \"$WORKER_MODE\" = '1' ]; then \
        python -m ussop.worker; \
      else \
        python -m uvicorn ussop.api.main:app --host 0.0.0.0 --port 8080 --workers ${API_WORKERS:-1}; \
      fi"]
