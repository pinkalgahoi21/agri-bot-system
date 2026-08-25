#!/bin/bash
# Start the FastAPI backend and Webhook in the foreground
cd backend
uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
