#!/bin/bash
# Start the FastAPI backend in the background
cd backend
uvicorn main:app --host 0.0.0.0 --port $PORT &

# Start the Telegram Bot in the foreground
cd ../telegram_bot
export BACKEND_URL="http://localhost:$PORT/api"
python bot.py
