import os
import sys
import logging
import base64
import asyncio
import httpx
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
PASSWORD = os.environ.get("BOT_PASSWORD", "W1NX88")

if not TELEGRAM_TOKEN:
    logger.error("TELEGRAM_TOKEN is not set!")
    sys.exit(1)

authorized_users = set()

PROMPT = "Ty -- suvoriy moderator RailGallery.org.ua. Format: VERDYKT: PIDHODYT/NE PIDHODYT/Z ZAUVAZHENNIAMY. ROZBIR: detalno. SHCHO VYPRAVYTY: porady. -- by @W1nx_tt (tg) | Cey proekt pro zaliznytsi Ukrainy. RF -- okupant."


async def gemini(image_bytes: bytes) -> str:
    img = base64.b64encode(image_bytes).decode()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    data = {
        "contents": [{
            "parts": [
                {"text": PROMPT},
                {"inline_data": {"mime_type": "image/jpeg", "data": img}}
            ]
        }]
    }
    try:
        async with httpx.AsyncClient(timeout=60) as c:
            r = await c.post(url, json=data)
            j = r.json()
            return j["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        logger.error(f"Gemini error: {e}")
        return "Pomylka analizu. Sprobuy shche raz."


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    authorized_users.discard(update.effective_user.id)
    await update.message.reply_text("Vvedy parol dlya dostupu:")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    txt = update.message.text or ""
    if uid not in authorized_users:
        if txt.strip() == PASSWORD:
            authorized_users.add(uid)
            await update.message.reply_text("Dostup vidkryto! Nadsilay foto.")
        else:
            await update.message.reply_text("Nevirnyy parol.")
    else:
        await update.message.reply_text("Nadishly foto.")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in authorized_users:
        await update.message.reply_text("Spochatku vvedy parol /start")
        return
    await update.message.reply_text("Analizuyu...")
    try:
        f = await context.bot.get_file(update.message.photo[-1].file_id)
        async with httpx.AsyncClient() as c:
            r = await c.get(f.file_path)
        result = await gemini(r.content)
        await update.message.reply_text(result)
    except Exception as e:
        logger.error(f"Photo error: {e}")
        await update.message.reply_text("Pomylka. Sprobuy shche raz.")


async def run():
    logger.info("Starting bot...")
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    logger.info("Bot is running!")
    async with app:
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)
        await asyncio.Event().wait()
        await app.updater.stop()
        await app.stop()


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(run())
    finally:
        loop.close()
