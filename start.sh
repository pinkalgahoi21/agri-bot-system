#!/bin/bash
# Start the FastAPI backend and Webhook in the foreground
cd backend
set -e
if [ "${INGEST_ON_START:-1}" = "1" ]; then
  python -c 'from services.vector_rag import ensure_index; ensure_index()'
fi
exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}"
