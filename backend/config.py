import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN  = os.getenv("TELEGRAM_TOKEN")
GOOGLE_API_KEY  = os.getenv("GOOGLE_API_KEY")
OPENWEATHER_KEY = os.getenv("OPENWEATHER_API_KEY", os.getenv("OPENWEATHER_KEY"))

# Used by google-generativeai (ai_service, image_service, etc.)
AI_MODEL = "gemini-2.0-flash"

# Used by LangGraph agent via init_chat_model — format: "provider/model-name"
# To switch models, just change this one line, e.g.:
#   "openai/gpt-4o", "anthropic/claude-3-5-sonnet-20241022", "groq/llama-3.3-70b-versatile"
AGENT_MODEL = "google_genai/gemini-2.0-flash"

MAX_HISTORY = 10