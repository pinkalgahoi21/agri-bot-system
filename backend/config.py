import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN  = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY    = os.getenv("GROQ_API_KEY")
OPENWEATHER_KEY = os.getenv("OPENWEATHER_API_KEY", os.getenv("OPENWEATHER_KEY"))

AI_MODEL    = "meta-llama/llama-4-scout-17b-16e-instruct"
MAX_HISTORY = 10