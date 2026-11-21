# Implementation notes

The shared graph now starts with a contextual LLM decision, before tools or a general answer. Weather phrase matching is only an outage fallback. Clarification notes preserve the unanswered question without a second summarization request. The existing Telegram and web clients continue to call the same API.

Government scheme searches use DuckDuckGo, restrict returned links to HTTPS government sites, and fall back to clearly labelled portal pointers. Search snippets do not establish eligibility. The updated brief requests visible citations, superseding the earlier preference to hide PDF names.

Set GROQ_API_KEY to select Scout when AGENT_MODEL is unset, or explicitly select a provider/model. Existing Gemini deployments without Groq credentials retain their configured model. Groq audio uses Whisper rather than sending audio to a vision model. A given provider/model must actually be enabled for your account.

For a local Compose start, copy .env.example to .env and set credentials, then run docker compose up --build. PostgreSQL deployments should set DATABASE_URL on the service rather than using the Compose SQLite volume. See REDEPLOY.md for delivery, webhook and staging checks.
