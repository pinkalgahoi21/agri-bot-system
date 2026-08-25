import asyncio
import logging
import os
import requests
import tempfile
from dotenv import load_dotenv

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)
from telegram.constants import ParseMode

load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000/api")
if not BACKEND_URL.endswith("/api"):
    BACKEND_URL = f"{BACKEND_URL.rstrip('/')}/api"

logging.basicConfig(format="%(asctime)s [%(levelname)s] %(name)s: %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# States for Onboarding
ASK_NAME, ASK_CITY, ASK_CROP = range(3)

async def check_profile(user_id: int) -> bool:
    # We can ping a generic chat or profile endpoint to check if user exists.
    # To keep it simple without adding a specific GET /profile, we can just assume 
    # if /chat returns 404, the user doesn't exist.
    pass

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "🌾 Welcome to the Farmer Advisory Bot!\n"
        "Let's get your profile set up so I can give you personalized advice.\n\n"
        "What is your name?"
    )
    return ASK_NAME

async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["name"] = update.message.text
    await update.message.reply_text("Great! Which city do you farm in?")
    return ASK_CITY

async def ask_city(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["city"] = update.message.text
    await update.message.reply_text("And finally, what is your main crop?")
    return ASK_CROP

async def ask_crop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    crop = update.message.text
    user_id = update.effective_user.id
    name = context.user_data["name"]
    city = context.user_data["city"]

    def create_prof():
        return requests.post(
            f"{BACKEND_URL}/profile",
            data={
                "user_id": user_id,
                "name": name,
                "city": city,
                "location": city,  # fallback location to city
                "crop": crop
            }
        )

    try:
        response = await asyncio.to_thread(create_prof)
        if response.status_code == 200:
            await update.message.reply_text("✅ Profile created successfully! You can now send me text, voice, or crop photos.")
        else:
            await update.message.reply_text("⚠️ Something went wrong creating your profile.")
    except Exception as e:
        logger.error(f"Error creating profile: {e}")
        await update.message.reply_text("⚠️ Backend error.")

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Profile setup cancelled. Type /start to try again.")
    return ConversationHandler.END

# ── Message Handlers ──────────────────────────────────────────────────────────

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    text = update.message.text
    
    try:
        def post_chat():
            return requests.post(f"{BACKEND_URL}/chat", json={"user_id": user_id, "message": text})

        response = await asyncio.to_thread(post_chat)
        if response.status_code == 404:
            await update.message.reply_text(
                "🌾 Welcome to the Farmer Advisory Bot!\n"
                "It looks like you are new here. Let's get your profile set up quickly.\n\n"
                "What is your name?"
            )
            return ASK_NAME

        if response.status_code == 200:
            data = response.json()
            try:
                await update.message.reply_text(data["response"], parse_mode=ParseMode.MARKDOWN)
            except Exception:
                await update.message.reply_text(data["response"])
        else:
            await update.message.reply_text("Sorry, the backend service is currently unavailable.")
    except Exception as e:
        logger.error(f"Error calling backend: {e}")
        await update.message.reply_text("Something went wrong while connecting to the backend.")
        
    return ConversationHandler.END

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    photo_file = await update.message.photo[-1].get_file()
    
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
    tmp.close()

    try:
        await photo_file.download_to_drive(custom_path=tmp.name)
        
        def post_vision():
            with open(tmp.name, "rb") as f:
                return requests.post(
                    f"{BACKEND_URL}/vision",
                    data={"user_id": user_id},
                    files={"image": f}
                )
        
        # Don't send "Analyzing..." until we confirm they exist
        response = await asyncio.to_thread(post_vision)
        
        if response.status_code == 404:
            await update.message.reply_text(
                "🌾 Welcome to the Farmer Advisory Bot!\n"
                "Before analyzing photos, we need to set up your profile.\n\n"
                "What is your name?"
            )
            return ASK_NAME
            
        msg = await update.message.reply_text("🔍 Analyzing crop image...")
            
        if response.status_code == 200:
            data = response.json()["response"]
            disease = data.get("disease", "Unknown")
            confidence = data.get("confidence", "Low")
            crop = data.get("identified_crop", "Unknown")
            prevention = "\n".join([f"• {p}" for p in data.get("prevention", [])])
            
            out = (f"🌿 *Identified Crop:* {crop}\n"
                   f"🦠 *Disease:* {disease} ({confidence} confidence)\n\n"
                   f"🛡️ *Prevention:*\n{prevention}")
            await msg.edit_text(out, parse_mode="Markdown")
        else:
            await msg.edit_text("❌ Failed to analyze image.")
    except Exception as e:
        logger.error(f"Error in vision: {e}")
        await update.message.reply_text("⚠️ Backend error.")
    finally:
        if os.path.exists(tmp.name):
            os.remove(tmp.name)
            
    return ConversationHandler.END

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    voice_file = await update.message.voice.get_file()
    
    tmp_ogg = tempfile.NamedTemporaryFile(delete=False, suffix=".ogg")
    tmp_ogg.close()
    
    try:
        await voice_file.download_to_drive(custom_path=tmp_ogg.name)
        
        def post_voice():
            with open(tmp_ogg.name, "rb") as f:
                return requests.post(
                    f"{BACKEND_URL}/voice",
                    data={"user_id": user_id},
                    files={"audio": f}
                )
                
        response = await asyncio.to_thread(post_voice)
        
        if response.status_code == 404:
            await update.message.reply_text(
                "🌾 Welcome to the Farmer Advisory Bot!\n"
                "Before we chat, let's set up your profile.\n\n"
                "What is your name?"
            )
            return ASK_NAME
            
        msg = await update.message.reply_text("🎤 Processing your voice note...")
            
        if response.status_code == 200:
            # Check content type. If audio/mpeg, send voice. If JSON, send text fallback.
            content_type = response.headers.get("content-type", "")
            if "audio" in content_type:
                tmp_mp3 = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
                tmp_mp3.write(response.content)
                tmp_mp3.close()
                await msg.delete()
                await update.message.reply_voice(voice=open(tmp_mp3.name, "rb"))
                os.remove(tmp_mp3.name)
            else:
                data = response.json()
                try:
                    await msg.edit_text(data.get("response", "No response."), parse_mode=ParseMode.MARKDOWN)
                except Exception:
                    await msg.edit_text(data.get("response", "No response."))
        else:
            await msg.edit_text("❌ Failed to process voice.")
            
    except Exception as e:
        logger.error(f"Error in voice: {e}")
        await update.message.reply_text("⚠️ Backend error.")
    finally:
        if os.path.exists(tmp_ogg.name):
            os.remove(tmp_ogg.name)
            
    return ConversationHandler.END

def main() -> None:
    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_TOKEN is missing")
        return

    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # By adding handle_message/photo/voice as entry points,
    # the bot gracefully intercepts a new user's very first message (even if it's not /start),
    # detects the 404 from the backend, and drops them seamlessly into ASK_NAME!
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start_command),
            MessageHandler(filters.PHOTO, handle_photo),
            MessageHandler(filters.VOICE, handle_voice),
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
        ],
        states={
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
            ASK_CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_city)],
            ASK_CROP: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_crop)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    app.add_handler(conv_handler)

    logger.info("Starting proxy Telegram bot with SEAMLESS onboarding...")
    app.run_polling()

if __name__ == "__main__":
    main()
