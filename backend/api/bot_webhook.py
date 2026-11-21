import asyncio
import logging
import os
import requests
import tempfile
import hashlib
import hmac
from fastapi import APIRouter, Request, HTTPException

def webhook_secret():
    return hmac.new(os.environ["TELEGRAM_TOKEN"].encode(), b"agribot-webhook-v1", hashlib.sha256).hexdigest()

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)
import base64

async def send_report(message, text):
    for start in range(0, len(text), 2000):
        await message.reply_text(text[start:start + 2000])

logger = logging.getLogger(__name__)

router = APIRouter()
bot_app = None

# We use the internal localhost URL for the bot to communicate with the FastAPI endpoints
BACKEND_URL = f"http://127.0.0.1:{os.getenv('PORT', '8000')}/api"

from api.auth import bot_signature
import time

def bot_post(user_id, url, **kwargs):
    timestamp = int(time.time())
    headers = {'X-Bot-User': str(user_id), 'X-Bot-Time': str(timestamp), 'X-Bot-Signature': bot_signature(user_id, timestamp)}
    return requests.post(url, headers=headers, timeout=120, **kwargs)

# States for Onboarding
ASK_NAME, ASK_CITY, ASK_CROP, ASK_DETAILS = range(4)

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
    context.user_data["crop"] = update.message.text
    await update.message.reply_text("Send state, current crop stage, preferred language, and optional land size separated by commas. Example: Bihar, flowering, Hindi, 2 acres")
    return ASK_DETAILS


async def ask_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    fields = [field.strip() for field in update.message.text.split(",", 3)]
    if len(fields) < 3:
        await update.message.reply_text("Please include state, stage and language, separated by commas.")
        return ASK_DETAILS
    crop = context.user_data["crop"]
    user_id = update.effective_user.id
    name = context.user_data["name"]
    city = context.user_data["city"]

    def create_prof():
        return bot_post(user_id,
            f"{BACKEND_URL}/profile",
            data={
                "user_id": user_id,
                "name": name,
                "city": city,
                "location": city,
                "crop": crop, "state": fields[0], "stage": fields[1], "language": fields[2],
                "land_size": fields[3] if len(fields) > 3 else "",
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

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    text = {"/weather": "Weather for my farm", "/schemes": "Find agricultural schemes for my farm"}.get(update.message.text, update.message.text)
    
    try:
        def post_chat():
            return bot_post(user_id,f"{BACKEND_URL}/chat", json={"user_id": user_id, "message": text})

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
            await send_report(update.message, data['response'])
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
                return bot_post(user_id,
                    f"{BACKEND_URL}/vision",
                    data={'language': (update.effective_user.language_code or 'en').split('-')[0], 'caption': update.message.caption or ''},
                    files={"image": f}
                )
        
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
            if data.get("kind") == "crop_notice":
                await msg.edit_text(data["message"])
                return ConversationHandler.END
            fields = [('identified_crop', 'Crop'), ('disease', 'Likely issue'), ('confidence', 'Confidence'), ('severity', 'Severity'), ('cause', 'Cause'), ('prevention', 'Prevention'), ('urgency', 'Urgency')]
            parts = []
            for key, label in fields:
                value = data.get(key, 'Unknown')
                if isinstance(value, list):
                    value = '\n'.join('• ' + item for item in value)
                parts.append(f'{label}: {value}')
            await msg.delete()
            if data.get('treatment'):
                parts.append(data['treatment'])
            await send_report(update.message, '\n\n'.join(parts))
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
                return bot_post(user_id,
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
            data = response.json()
            await msg.delete()
            await send_report(update.message, 'Heard: ' + data['transcribed'] + '\n\n' + data['response'])
            if data.get('audio_base64'):
                await update.message.reply_audio(audio=base64.b64decode(data['audio_base64']), filename='advice.mp3')
        else:
            await msg.edit_text("❌ Failed to process voice.")
            
    except Exception as e:
        logger.error(f"Error in voice: {e}")
        await update.message.reply_text("⚠️ Backend error.")
    finally:
        if os.path.exists(tmp_ogg.name):
            os.remove(tmp_ogg.name)
            
    return ConversationHandler.END


def setup_bot_application(token: str) -> Application:
    app = Application.builder().token(token).build()
    
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start_command),
            CommandHandler(["profile", "crop"], start_command),
            CommandHandler(["weather", "schemes"], handle_message),
            MessageHandler(filters.PHOTO, handle_photo),
            MessageHandler(filters.VOICE, handle_voice),
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
        ],
        states={
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
            ASK_CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_city)],
            ASK_CROP: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_crop)],
            ASK_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_details)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    app.add_handler(conv_handler)
    return app


async def startup_bot():
    """Initialize the Telegram bot. Called from main.py lifespan."""
    global bot_app
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
    WEBHOOK_URL = os.getenv("WEBHOOK_URL", "") 
    
    if not TELEGRAM_TOKEN:
        logger.warning("No TELEGRAM_TOKEN set — Telegram bot disabled.")
        return
    if not WEBHOOK_URL and os.getenv("TELEGRAM_POLLING") != "1":
        logger.info("No webhook configured; polling disabled to preserve any deployed webhook.")
        return

    try:
        logger.info("Initializing Telegram bot...")
        bot_app = setup_bot_application(TELEGRAM_TOKEN)
        await bot_app.initialize()
        await bot_app.start()
        
        if WEBHOOK_URL:
            webhook_endpoint = f"{WEBHOOK_URL.rstrip('/')}/api/telegram/webhook"
            try:
                await bot_app.bot.set_webhook(url=webhook_endpoint, secret_token=webhook_secret())
                logger.info(f"Webhook set to {webhook_endpoint}")
            except Exception as e:
                logger.warning(f"Failed to set webhook (might be rate limited). Error: {e}")
        else:
            try:
                await bot_app.bot.delete_webhook()
            except Exception:
                pass
            logger.info("No WEBHOOK_URL found. Running locally using long-polling instead.")
            if bot_app.updater:
                await bot_app.updater.start_polling()
    except Exception as e:
        logger.error(f"Error during Telegram bot startup: {e}")


async def shutdown_bot():
    """Shut down the Telegram bot gracefully. Called from main.py lifespan."""
    global bot_app
    if bot_app:
        try:
            if bot_app.updater and bot_app.updater.running:
                await bot_app.updater.stop()
            await bot_app.stop()
            await bot_app.shutdown()
        except Exception as e:
            logger.error(f"Error during Telegram bot shutdown: {e}")


@router.post("/telegram/webhook")
async def telegram_webhook(request: Request):
    if not os.getenv("TELEGRAM_TOKEN") or not os.getenv("WEBHOOK_URL") or not hmac.compare_digest(request.headers.get("X-Telegram-Bot-Api-Secret-Token", "").encode(), webhook_secret().encode()):
        raise HTTPException(403, "Forbidden")
    if bot_app:
        update_data = await request.json()
        update = Update.de_json(update_data, bot_app.bot)
        # Use a background task or process directly.
        await bot_app.process_update(update)
    return {"status": "ok"}
