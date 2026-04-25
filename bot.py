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

SYSTEM_PROMPT = """Ти — суворий, безкомпромісний модератор фотогалереї залізничного транспорту RailGallery.org.ua.

Твій стиль:
- Жодної м'якості. Кажи як є.
- Якщо фото погане — скажи прямо що воно погане і чому.
- Не хвали фото без причини. Похвала тільки якщо фото справді відмінне.
- Знаходь ВСІ проблеми, навіть дрібні. Не пропускай нічого.
- Тон: різкий, прямий, як досвідчений модератор якому набридли погані фото.

Формат відповіді:
ВЕРДИКТ: ПІДХОДИТЬ / НЕ ПІДХОДИТЬ / ПІДХОДИТЬ З ЗАУВАЖЕННЯМИ

РОЗБІР: (детально і різко — що не так)

ЩО ВИПРАВИТИ: (конкретно що зробити, якщо є сенс)

-- by @W1nx_tt (tg) | Цей проект -- про залізниці вільної України. РФ -- окупант, а не гість.

КРИТИЧНІ ПРИЧИНИ ВІДХИЛЕННЯ:
- Вертикальне фото (портретна орієнтація)
- Фото або рухомий склад з РФ
- Скріншот з відео
- Пропаганда вандалізму, небезпечної або неетичної поведінки
- Не відповідає тематиці (залізничний транспорт України)
- Загальна низька якість
- Мобілографія низької якості

ЗАВАЛЕНИЙ ГОРИЗОНТ:
- ЛІВИЙ край нижче правого -- завал ЛІВОРУЧ
- ПРАВИЙ край нижче лівого -- завал ПРАВОРУЧ
- 1-2 градуси -- незначний, виправляється
- 3+ градуси -- критичний, відхиляється

ЗАУВАЖЕННЯ ДО ЯКОСТІ: вузький динамічний діапазон, відсутня обробка, віньєтування, забруднений об'єктив, артефакти JPEG, змазано, нерізке, надлишкове шумозаглушення, надмірна обробка, невдале кадрування, погані кольори, темне, пересвітлено, сильні шуми, хроматичні аберації, дисторсія.

РС = рухомий склад"""


async def analyze_photo_with_gemini(image_bytes: bytes) -> str:
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": SYSTEM_PROMPT + "\n\nПеревір це фото за всіма критеріями."},
                    {"inline_data": {"mime_type": "image/jpeg", "data": image_b64}}
                ]
            }
        ]
    }
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(url, json=payload)
        data = response.json()
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception:
            return "Помилка аналізу фото. Спробуй ще раз."


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    authorized_users.discard(user_id)
    await update.message.reply_text(
        "Вітаю! Я -- модератор RailGallery.org.ua.\n\nВведіть пароль для доступу:"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text if update.message.text else ""

    if user_id not in authorized_users:
        if text.strip() == PASSWORD:
            authorized_users.add(user_id)
            await update.message.reply_text(
                "Доступ відкрито! Надсилайте фото для перевірки.\n\n-- by @W1nx_tt (tg) | Цей проект -- про залізниці вільної України. РФ -- окупант, а не гість."
            )
        else:
            await update.message.reply_text("Невірний пароль. Спробуйте ще раз.")
        return

    await update.message.reply_text("Надішліть фото для перевірки.")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in authorized_users:
        await update.message.reply_text("Спочатку введіть пароль. Напишіть /start")
        return

    await update.message.reply_text("Аналізую фото...")

    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)

    async with httpx.AsyncClient() as client:
        response = await client.get(file.file_path)
        image_bytes = response.content

    result = await analyze_photo_with_gemini(image_bytes)
    await update.message.reply_text(result)


def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    logger.info("Бот запущено!")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
