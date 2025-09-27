import os
import asyncio
from openai import OpenAI
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from telegram.constants import ChatAction

# Ключи берем из переменных окружения (Railway: добавим в Settings → Variables)
TELEGRAM_API_KEY = os.getenv("TELEGRAM_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Инициализируем OpenAI-клиент (ключ читается из OPENAI_API_KEY)
client = OpenAI(api_key=OPENAI_API_KEY)

HELP_TEXT = (
    "Привет! Я перевожу русский ↔ турецкий.\n"
    "Отправь текст на русском — пришлю перевод на турецкий.\n"
    "Отправь текст на турецком — пришлю перевод на русский."
)

async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text(HELP_TEXT)

def translate_bidirectional(text: str) -> str:
    """
    Если вход на русском — перевести на турецкий.
    Если вход на турецком — перевести на русский.
    Возвращает только перевод, без комментариев.
    """
    system = (
        "Ты двунаправленный переводчик RU↔TR. "
        "Определи язык входного текста (русский или турецкий) и переведи на другой язык. "
        "Отвечай только переводом, без пояснений, кавычек и меток."
    )
    user = f"Текст для перевода:\n{text}"

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.2,
            max_tokens=500,
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception as e:
        print(f"[translate_bidirectional] error: {e}")
        return "Извините, не удалось выполнить перевод. Попробуйте ещё раз позже."

async def send_long(update: Update, text: str):
    """Безопасная отправка длинных сообщений (Telegram лимит ~4096 символов)."""
    max_len = 4096
    while len(text) > max_len:
        await update.message.reply_text(text[:max_len])
        text = text[max_len:]
        await asyncio.sleep(0.2)
    if text:
        await update.message.reply_text(text)

async def on_text(update: Update, context: CallbackContext) -> None:
    text = update.message.text or ""
    # Покажем статус "печатает…"
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    translation = translate_bidirectional(text)
    await send_long(update, translation)

def main():
    if not TELEGRAM_API_KEY:
        raise RuntimeError("TELEGRAM_API_KEY не задан. Добавь переменную окружения.")
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY не задан. Добавь переменную окружения.")

    app = Application.builder().token(TELEGRAM_API_KEY).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    app.run_polling(allowed_updates=["message"])

if __name__ == "__main__":
    main()
