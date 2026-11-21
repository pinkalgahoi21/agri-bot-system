# Pre-change audit

The checkout uses FastAPI, SQLAlchemy, Gemini via LangChain, a compiled LangGraph tool loop, Chroma, Vite/React, and python-telegram-bot. It does not currently use Groq Scout. Telegram delegates to the same HTTP routes as the website.

| Area | Decision | Finding |
| --- | --- | --- |
| api/routes, graph | Fix | A classifier outside the graph, weather phrase matching, and a separate tool loop compete for control. A user answering a previous question can land in a generic error branch. |
| services/treatment_flow, vector_rag, table_evidence | Keep/fix | Real PDF retrieval exists. Evidence from a layout-preserved page is preferable to attributing a product to an adjacent row. Current index is English MiniLM over bundled PDFs, not multilingual multi-format ingestion. |
| services/search_service | Replace | Returns fixed URLs; it never performs online scheme discovery. |
| services/weather_service | Keep | Geocodes and retrieves real forecasts. Keep tool failures distinct from diagnosis failures. |
| models, farm_memory | Keep/fix | Crop-scoped bounded summary exists; no complete journal, durable graph checkpoint or served chat transcript. |
| image, voice, language | Keep | Photo mismatch gate and transcription exist; TTS does not cover every registered language. |
| local_login, auth | Keep/fix | Password hashing, OTP and opaque revocable sessions exist. Not JWT refresh or password recovery. |
| frontend, bot_webhook | Keep | Existing chat, signup, photo drafts and voice controls work without replacing either client. Narrow onboarding and limited Telegram commands. |
| legacy medicine helpers | Retire from active routing | Dictionary lookup is not a substitute for reference document evidence. |
| deployment | Keep | Docker and Render configuration exist. Credentials belong in server environment only; no values reproduced here. |

Production logs previously showed a successful model HTTP response followed by JSONDecodeError, not quota exhaustion. Structured classification mitigates this; an HTTP 200 with a fallback message still does not demonstrate successful advice. Other reported failures include provider timeouts and loss of context on short replies. Live provider availability cannot be inferred from offline tests.
