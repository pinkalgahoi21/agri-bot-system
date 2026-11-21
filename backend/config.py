import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN  = os.getenv("TELEGRAM_TOKEN")
GOOGLE_API_KEY  = os.getenv("GOOGLE_API_KEY")
OPENWEATHER_KEY = os.getenv("OPENWEATHER_API_KEY", os.getenv("OPENWEATHER_KEY"))

MAX_HISTORY = 10
