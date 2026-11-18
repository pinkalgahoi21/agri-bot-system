FROM node:22-alpine AS website
WORKDIR /site
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim

# Install ffmpeg for OpenAI Whisper and clean up apt cache to save space
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy everything into the container
COPY . .
COPY --from=website /site/dist /app/frontend/dist

# Install dependencies using --no-cache-dir to prevent RAM exhaustion on Render free tier
RUN pip install --no-cache-dir -r backend/requirements.txt
RUN cd backend && python -m services.vector_rag

# Ensure start script is executable
RUN sed -i 's/\r$//' start.sh && chmod +x start.sh

# Expose FastAPI port
EXPOSE 8000

# Run the unified boot script
CMD ["./start.sh"]
