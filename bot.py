import os
import logging
import base64
import httpx
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
PASSWORD = os.environ.get("BOT_PASSWORD", "W1NX88")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

authorized_users = set()

PROMPT = "Ty -- suvoriy moderator RailGallery.org.ua. Perevirjay foto za pravylamy sajtu. Format vidpovidi: VERDYKT: PIDHODYT / NE PIDHODYT / PIDHODYT Z ZAUVAZHENNIAMY. ROZBIR: (detalno). SHCHO VYPRYVYTY: (porady). -- by @W1nx_tt (tg) | Cey proekt -- pro zaliznytsi vilnoi Ukrainy. RF -- okupant. Krytychni: vertykalne foto, foto z RF, skrinshot z video, vandalizm, ne vidpovidaye tematyci, nyzka yakist mobilografii. Zavalelyy horyzont: LIVYY kray nyzche -- zavál LIVORUCH, PRAVYY nyzche -- zavál PRAVORUCH, 1-2 gr -- vypravljayetsya, 3+ gr -- vidkhylyayetsya. Zauvajennya: vuzkyi dynam. diapazon, vidsutnya obrobka, vinyetuvannya, artefakty JPEG, zmyzano, nerizke, nadmirna obrobka, pohani kolory, temne, peresvitleno, shumы, aberaciyi, dystorsiya."


async def gemini(image_bytes: bytes) -> str:
    img = base64.b64encode(image_bytes).decode()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    data = {
        "contents": [{
            "parts": [
                {"text": PROMPT + " Perevirj ce foto."},
                {"inline_data": {"mime_type": "image/jpeg", "data": img}}
            ]
        }]
    }
    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.post(url, json=data)
        j = r.json()
        try:
            return j["candidates"][0]["content"]["parts"][0]["text"]
        except Exception:
            return "Pomylka analizu. Sprobuy shche raz."


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    authorized_users.discard(update.effective_user.id)
    await update.message.reply_text("Vvedy parol dlya dostupu:")


async def message(update: Update, context: ContextTypes.DEFAULT_TYPE):
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


async def photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in authorized_users:
        await update.message.reply_text("Spochatku vvedy parol /start")
        return
    await update.message.reply_text("Analizuyu...")
    f = await context.bot.get_file(update.message.photo[-1].file_id)
    async with httpx.AsyncClient() as c:
        r = await c.get(f.file_path)
    result = await gemini(r.content)
    await update.message.reply_text(result)


def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message))
    app.add_handler(MessageHandler(filters.PHOTO, photo))
    logger.info("Bot started!")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
