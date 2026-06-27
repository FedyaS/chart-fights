# Chart-Fights backend Dockerfile (FastAPI/Starlette)
# For Fly.io (or similar) deploy per architecture notes.
#
# IMPORTANT: the build context MUST be the repo root (NOT backend/) so that
# both `backend/` and `data/` are visible to the COPY steps below. fly.toml at
# the repo root references this file via `dockerfile = "backend/Dockerfile"`
# and uses the repo root as the context automatically.
#
# Manual local build/run (from repo root):
#   docker build -t chart-fights-backend -f backend/Dockerfile .
#   docker run -p 8080:8080 chart-fights-backend
#   # then: curl http://localhost:8080/health

FROM python:3.11-slim

WORKDIR /app

# System deps (for pandas/parquet if wheels need)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install python deps
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy backend code + data arenas (needed at runtime for loader)
COPY backend/ /app/backend/
COPY data/ /app/data/

# Python path so `from app...` works
ENV PYTHONPATH=/app/backend

# Bind a fixed internal port (8080) that matches fly.toml's `internal_port`.
# We still honor $PORT if the platform injects one, defaulting to 8080.
ENV PORT=8080
EXPOSE 8080

# Shell form so ${PORT} is expanded at runtime. Production: no --reload.
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}
