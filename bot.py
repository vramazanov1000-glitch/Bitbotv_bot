import os
import telebot
from flask import Flask, request, abort
import requests
from openai import OpenAI

# Получаем переменные окружения
TOKEN = os.getenv('TELEGRAM_TOKEN', '8890656649:AAFKuBm1FwvArvspXdehC_ziUKiSA9kPnzk')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
RENDER_EXTERNAL_URL = os.getenv('RENDER_EXTERNAL_URL') # Например: https://bitbotv-bot.onrender.com

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# Функция для получения RSI по монете (на примере Bitget)
def get_bitget_rsi(symbol="BICOUSDT"):
    try:
        url = f"https://api.bitget.com/api/v2/spot/market/candles?symbol={symbol}&granularity=1H&limit=50"
        response = requests.get(url, timeout=10)
        data = response.json()

        if data.get("code") == "00000" and data.get("data"):
            closes = [float(candle[4]) for candle in data["data"]] # закрытия свечей
            # Простейший расчет RSI (14) для примера
            if len(closes) >= 15:
                gains, losses = [], []
                for i in range(1, 15):
                    change = closes[i] - closes[i-1]
                    if change > 0:
                        gains.append(change)
                    else:
                        losses.append(abs(change))
                avg_gain = sum(gains) / 14 if gains else 0
                avg_loss = sum(losses) / 14 if losses else 0
                if avg_loss == 0:
                    return 100.0
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
                return round(rsi, 2)
        return "Не удалось рассчитать"
    except Exception as e:
        print(f"Ошибка API Bitget: {e}")
        return "Ошибка данных"

@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = telebot.types.InlineKeyboardMarkup()
    btn = telebot.types.InlineKeyboardButton("📊 Анализ BICO/USDT", callback_data="analyze_bico")
    markup.add(btn)
    bot.reply_to(message, "Привет, Васиф! Бот запущен на вебхуках и готов к работе. Нажми кнопку ниже для анализа:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "analyze_bico")
def callback_analyze(call):
    bot.answer_callback_query(call.id, "Считаю RSI...")
    rsi = get_bitget_rsi("BICOUSDT")
    text = f"📊 **Анализ BICO/USDT**\nТекущий RSI (14): `{rsi}`\n\nСистема работает стабильно на вебхуках Render!"
    bot.send_message(call.message.chat.id, text, parse_mode="Markdown")

# Эндпоинт для приема вебхуков от Telegram
@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    else:
        abort(403)

# Проверочный маршрут, чтобы Render понимал, что сервис жив
@app.route('/')
def index():
    return "Bot is running via Webhooks!", 200

if __name__ == "__main__":
    # Устанавливаем вебхук при старте, если задан внешний URL
    if RENDER_EXTERNAL_URL:
        webhook_url = f"{RENDER_EXTERNAL_URL.rstrip('/')}/{TOKEN}"
        bot.remove_webhook()
        bot.set_webhook(url=webhook_url)
        print(f"Вебхук установлен на: {webhook_url}")

    # Запуск Flask-сервера (порт берется из окружения Render или по умолчанию 5000)
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
