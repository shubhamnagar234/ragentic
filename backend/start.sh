#!/bin/bash
set -e

# Run database migrations or startup checks if any
echo "[STARTUP] Starting Celery worker in background..."
celery -A app.workers.celery_app worker --pool=solo --loglevel=info --concurrency=1 &

PORT="${PORT:-7860}"
echo "[STARTUP] Starting FastAPI server on port $PORT..."
exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
