FROM python:3.10-slim

# Install ffmpeg for OpenAI Whisper and clean up apt cache to save space
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy everything into the container
COPY . .

# Install dependencies using --no-cache-dir to prevent RAM exhaustion on Render free tier
RUN pip install --no-cache-dir -r backend/requirements.txt
RUN pip install --no-cache-dir python-telegram-bot

# Ensure start script is executable
RUN chmod +x start.sh

# Expose FastAPI port
EXPOSE 8000

# Run the unified boot script
CMD ["./start.sh"]
