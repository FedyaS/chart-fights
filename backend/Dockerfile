# Chart-Fights backend Dockerfile (FastAPI/Starlette skeleton)
# For Fly.io (or similar) deploy per architecture notes.
# Build context: project root (so data/ and backend/ visible)
#
# Usage:
#   cd backend
#   docker build -t chart-fights-backend -f Dockerfile ..
#   docker run -p 8000:8000 chart-fights-backend

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

# Fly.io / prod: use PORT
ENV PORT=8000
EXPOSE 8000

# Run with uvicorn (production: no --reload)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
