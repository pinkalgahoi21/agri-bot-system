# Agri-Bot

For the authenticated website and Telegram deployment, start with [the redeployment guide](REDEPLOY.md).

## Current setup

Copy `.env.example` to `.env` and configure your model and services. Run `docker compose up --build` and open `http://localhost:8000`. Use a separate Telegram token with `TELEGRAM_POLLING=1` locally, or set an HTTPS `WEBHOOK_URL` on the deployed service. For local Python development install `backend/requirements.txt` in a virtual environment (Python 3.12 recommended), then start `uvicorn main:app` from backend.

Drop reference PDFs, TXT, Markdown, CSV or DOCX files in `data/knowledge/`. From the repository root run `python scripts/ingest.py`; use `--reset` only to discard and rebuild the index. Set `RAG_MAX_DISTANCE` for the maximum cosine distance. Under backend run `python -m unittest discover -v`; from the root run `python scripts/eval.py` for the live model routing check (consumes quota). See [architecture](docs/ARCHITECTURE.md), [audit](docs/AUDIT.md) and [changes](docs/CHANGES.md).

## Model configuration

The website and Telegram share the LangGraph backend. Set GOOGLE_API_KEY for Gemini chat, vision, audio transcription and embeddings. The shipped model IDs are in model.defaults.env. LLM_MODEL_ROUTER, LLM_MODEL_VISION and LLM_MODEL_REASONING inherit LLM_MODEL_DEFAULT when unset. A qualified LLM_MODEL_DEFAULT such as provider:model switches the default provider and model together. Install the matching LangChain integration and configure its credentials before switching. A replacement for the vision or speech model must accept the corresponding input type.

The router uses temperature zero. LLM_TEMPERATURE controls other roles. LLM_TIMEOUT is in seconds. LLM_MAX_RETRIES controls the bounded rate-limit retry loop. Set LANGSMITH_TRACING=true and LANGSMITH_API_KEY to opt into hosted tracing of model interactions. Local logs record model timing and token counts when the provider reports them.

Voice uses Gemini audio transcription and gTTS synthesis. Language and voice availability depend on the provider. Whisper is not required.

The Chroma collection records the embedding provider and model. Changing either requires an explicit index rebuild with python scripts/ingest.py --reset. This replaces the collection and consumes embedding quota. Use persistent storage for VECTOR_DB_DIR when available. On ephemeral hosting the startup script can rebuild the index after storage is cleared. Set INGEST_ON_START=0 when supplying a prepared index.
