# Redeploy the website and Telegram bot

Use the repository directory containing Dockerfile as the Render service root. Startup verifies the document fingerprint, embedding configuration and indexed passage count. A matching bundled reference index restores without embedding API calls. Otherwise startup builds from the PDFs and consumes embedding quota. Monitor RAM and request latency on staging. Local polling is opt-in: only use TELEGRAM_POLLING=1 with a separate test bot token.

Build the root Dockerfile; it bundles the React site and serves it at / on the same origin as /api. For local frontend development run Vite with FastAPI on port 8000. No VITE_API_URL is necessary.

1. Back up the existing farmers database before replacing the service. Point DATABASE_URL at persistent PostgreSQL (or SQLite on a mounted persistent disk). Changing the URL does not migrate data. Existing anonymous browser IDs cannot safely be claimed. Telegram IDs stay separate from new website accounts.
2. Create Render Postgres in the same region as the web service and set DATABASE_URL to its internal connection URL. Set RESEND_API_KEY and AUTH_EMAIL_FROM (a verified sender) for signup codes. Verified users log in with email and password only. Prior Supabase accounts are not automatically linked; plan a verified migration if needed.
3. Keep GOOGLE_API_KEY and OPENWEATHER_API_KEY. For Telegram set TELEGRAM_TOKEN and WEBHOOK_URL to the public HTTPS origin. Restart to register the protected webhook.
4. Before switching traffic, check /health, create a website account, verify its email code, save a farm profile, refresh, sign out and sign in again. Test with a second account and confirm separate profiles. Test Telegram /start and both channels' chat, photo and voice flows. Reauthentication is required when the tab session or access token expires.
