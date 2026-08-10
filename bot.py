import os
import telebot
from flask import Flask, request, abort
import requests
from openai import OpenAI

TOKEN = os.getenv('TELEGRAM_TOKEN', '8890656649:AAFKuBm1FwvArvspXdehC_ziUKiSA9kPnzk')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
RENDER_EXTERNAL_URL = os.getenv('RENDER_EXTERNAL_URL')

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

def get_bitget_rsi(symbol="BICOUSDT"):
    """Получение RSI(14) с биржи Bitget для выбранной монеты"""
    try:
        url = f"https://api.bitget.com/api/v2/spot/market/candles?symbol={symbol.upper()}&granularity=1H&limit=50"
        response = requests.get(url, timeout=5)
        data = response.json()

        if data.get("code") == "00000" and data.get("data"):
            closes = [float(candle[4]) for candle in data["data"]]
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
        return None
    except Exception as e:
        print(f"Ошибка API Bitget для {symbol}: {e}")
        return None

def generate_crypto_analysis(symbol, rsi):
    """Генерация текста анализа"""
    clean_symbol = symbol.upper().replace("USDT", "") + "/USDT"

    if rsi is None:
        return (
            f"📊 **Анализ пары: {clean_symbol} (1h)**\n\n"
            "⚠️ Не удалось получить данные с биржи Bitget. Проверь правильность тикера."
        )

    if rsi > 70:
        trend = "ПЕРЕКУПЛЕННОСТЬ (Возможна коррекция вниз 📉)"
        probability = "64%"
    elif rsi < 30:
        trend = "ПЕРЕПРОДАННОСТЬ (Возможен отскок вверх 📈)"
        probability = "68%"
    else:
        trend = "УМЕРЕННЫЙ ТРЕНД (Боковое движение ⚖️)"
        probability = "55%"

    ai_comment = "Индикатор отражает текущий баланс сил покупателей и продавцов на спотовом рынке."
    if client:
        try:
            prompt = f"Напиши краткий рыночный комментарий для криптопары {clean_symbol}, текущий RSI(14) = {rsi}."
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=100
            )
            ai_comment = response.choices[0].message.content.strip()
        except Exception:
            pass

    text = (
        f"📊 **Анализ рынка: {clean_symbol} (1h)**\n\n"
        f"🟢 **Текущий RSI(14):** `{rsi}`\n"
        f"📈 **Состояние:** {trend}\n"
        f"🎯 **Вероятность:** {probability}\n\n"
        f"💡 *Комментарий:* {ai_comment}"
    )
    return text

@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = telebot.types.InlineKeyboardMarkup()
    btn = telebot.types.InlineKeyboardButton("📊 Анализ BICO/USDT", callback_data="analyze_bico")
    markup.add(btn)
    bot.reply_to(
        message, 
        f"Привет, Васиф! 🤝 Бот готов к работе.\n\n"
        f"• Нажми кнопку для анализа **BICO/USDT**\n"
        f"• Или напиши любой тикер (например: `BTC`, `ETH`, `SOL`), чтобы посчитать его RSI!", 
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "analyze_bico")
def callback_analyze(call):
    try:
        bot.answer_callback_query(call.id, "Считаю RSI для BICO...")
        msg = bot.send_message(call.message.chat.id, "⏳ Получаю данные с рынка для BICO/USDT...")

        rsi = get_bitget_rsi("BICOUSDT")
        text = generate_crypto_analysis("BICOUSDT", rsi)

        bot.edit_message_text(text, chat_id=call.message.chat.id, message_id=msg.message_id, parse_mode="Markdown")
    except Exception as e:
        print(f"Ошибка в callback: {e}")
        bot.send_message(call.message.chat.id, "⚠️ Ошибка при обработке запроса.")

@bot.message_handler(func=lambda message: True)
def handle_text_coin(message):
    text_input = message.text.strip().upper()
    coin_name = text_input.replace("/", "").replace("USDT", "")

    if not coin_name or len(coin_name) > 10:
        bot.reply_to(message, "Пожалуйста, укажи корректный тикер монеты, например: `BTC`, `ETH`, `SOL`", parse_mode="Markdown")
        return

    symbol = coin_name + "USDT"

    try:
        msg = bot.reply_to(message, f"⏳ Запрашиваю свечи и считаю RSI для {symbol}...")
        rsi = get_bitget_rsi(symbol)
        analysis_text = generate_crypto_analysis(symbol, rsi)

        bot.edit_message_text(analysis_text, chat_id=message.chat.id, message_id=msg.message_id, parse_mode="Markdown")
    except Exception as e:
        print(f"Ошибка при обработке монеты {symbol}: {e}")
        bot.reply_to(message, f"⚠️ Не удалось обработать монету {symbol}. Проверь название.")

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    else:
        abort(403)

@app.route('/')
def index():
    return "Bot is running via Webhooks!", 200

if __name__ == "__main__":
    if RENDER_EXTERNAL_URL:
        webhook_url = f"{RENDER_EXTERNAL_URL.rstrip('/')}/{TOKEN}"
        bot.remove_webhook()
        bot.set_webhook(url=webhook_url)
        print(f"Вебхук установлен на: {webhook_url}")

    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
