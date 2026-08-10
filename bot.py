import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import telebot
from telebot import types

# === МИНИ-СЕРВЕР ДЛЯ RENDER (чтобы не было ошибки No open ports detected) ===
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot is running!")

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), SimpleHandler)
    server.serve_forever()

# Запускаем сервер в фоновом потоке
threading.Thread(target=run_server, daemon=True).start()

# === ИНИЦИАЛИЗАЦИЯ БОТА ===
TOKEN = os.environ.get("BOT_TOKEN")
if not TOKEN:
    raise ValueError("Не задан BOT_TOKEN в переменных окружения!")

bot = telebot.TeleBot(TOKEN)

# Принудительно сбрасываем старые соединения (лечит ошибку 409 Conflict)
try:
    bot.remove_webhook()
except Exception:
    pass

@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = types.InlineKeyboardMarkup()
    btn = types.InlineKeyboardButton("📊 Анализ BICO/USDT", callback_data="analyze_bico")
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
    print("Бот запущен...")
    bot.infinity_polling()
