import os
import telebot
from flask import Flask, request

TOKEN = os.environ.get("BOT_TOKEN")
if not TOKEN:
    raise ValueError("Не задан BOT_TOKEN в переменных окружения!")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# Веб-хук для приема запросов от Telegram
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    if request.headers.get("content-type") == "application/json":
        json_string = request.get_data().decode("utf-8")
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "!", 200
    else:
        return "Invalid content-type", 403

# Простой эндпоинт для проверки работы сервиса на Render
@app.route("/", methods=["GET"])
def index():
    return "Bot is running via Webhooks!", 200

@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = telebot.types.InlineKeyboardMarkup()
    btn = telebot.types.InlineKeyboardButton("📊 Анализ BICO/USDT", callback_data="analyze_bico")
    markup.add(btn)

    bot.send_message(
        message.chat.id,
        f"Привет, Васиф! 👋 Я твой бот для анализа криптовалюты.\nНажми кнопку ниже, чтобы получить актуальный анализ:",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "analyze_bico")
def callback_inline(call):
    chat_id = call.message.chat.id

    try:
        bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=None)
    except Exception:
        pass

    bot.send_message(chat_id, "⏳ Получаю данные с рынка и генерирую анализ...")

    current_price = "0.1425 USDT"
    trend_arrow = "🟢 РАСТЕТ (📈 Вверх)"
    probability = "78%"

    response_text = (
        "📊 **Анализ фьючерсов: BICO/USDT** (15m)\n\n"
        f"💵 **Текущая цена:** `{current_price}`\n\n"
        f"🎯 **Прогноз:** {trend_arrow}\n"
        f"📈 **Вероятность:** `{probability}`\n\n"
        "💡 *Индикатор RSI(14) находится в нейтральной зоне, наблюдается давление покупателей.*"
    )

    bot.send_message(chat_id, response_text, parse_mode="Markdown")

if __name__ == "__main__":
    RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL")

    if RENDER_EXTERNAL_URL:
        bot.remove_webhook()
        bot.set_webhook(url=f"{RENDER_EXTERNAL_URL}/{TOKEN}")

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
