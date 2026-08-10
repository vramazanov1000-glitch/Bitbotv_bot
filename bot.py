import os
import io
import requests
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from openai import OpenAI
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# Получаем токены из переменных окружения Render
TOKEN = os.getenv('BOT_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

if not TOKEN:
    raise ValueError("Не задан BOT_TOKEN в переменных окружения!")

bot = telebot.TeleBot(TOKEN)
ai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

def calculate_rsi(prices, period=14):
    """Расчет индикатора RSI"""
    if len(prices) < period + 1:
        return [50.0] * len(prices)
    deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    rsi = [50.0] * len(prices)
    if avg_loss == 0:
        rsi[period] = 100.0
    else:
        rs = avg_gain / avg_loss
        rsi[period] = 100 - (100 / (1 + rs))

    for i in range(period + 1, len(prices)):
        gain = gains[i-1]
        loss = losses[i-1]
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
        if avg_loss == 0:
            rsi[i] = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi[i] = 100 - (100 / (1 + rs))
    return rsi

def analyze_market_overheat(funding_rate, long_short_ratio):
    """
    Оценивает степень перегрева рынка на основе фандинга и лонг/шорт ратио.
    """
    overheat_status = "⚖️ Баланс сил в рынке"
    warning_note = "Явных перекосов и критических зон толпы нет."

    if funding_rate > 0.01 and long_short_ratio > 1.5:
        overheat_status = "🔥 Перегрет в ЛОНГ (Толпа перегружена лонгами)"
        warning_note = "Высок риск длинного сквиза (Long Squeeze) при резком проливе вниз."
    elif funding_rate < -0.01 and long_short_ratio < 0.7:
        overheat_status = "❄️ Перегрет в ШОРТ (Толпа перегружена шортами)"
        warning_note = "Высок риск шорт-сквиза (Short Squeeze) при импульсном выносе вверх."

    return overheat_status, warning_note

def get_market_metrics(symbol, granularity="15m"):
    """Сбор метрик, данных толпы и расчет RSI с Bitget"""
    metrics = {
        "long_ratio": 50.0,
        "short_ratio": 50.0,
        "ratio": 1.0,
        "funding_rate": 0.01,
        "open_interest": "N/A",
        "rsi": 50.0,
        "raw_candles": []
    }
    try:
        # 1. Long/Short Ratio
        url_ls = "https://api.bitget.com/api/v2/mix/market/long-short-account-ratio"
        res_ls = requests.get(url_ls, params={"symbol": symbol, "productType": "usdt-futures", "granularity": "1h"}, timeout=5).json()
        if res_ls.get("code") == "00000" and res_ls.get("data"):
            item = res_ls["data"][0]
            metrics["long_ratio"] = float(item.get("longRatio", 0.5)) * 100
            metrics["short_ratio"] = float(item.get("shortRatio", 0.5)) * 100
            metrics["ratio"] = float(item.get("longShortRatio", 1.0))

        # 2. Funding Rate и Open Interest
        url_ticker = "https://api.bitget.com/api/v2/mix/market/ticker"
        res_t = requests.get(url_ticker, params={"symbol": symbol, "productType": "usdt-futures"}, timeout=5).json()
        if res_t.get("code") == "00000" and res_t.get("data"):
            t_item = res_t["data"][0]
            metrics["funding_rate"] = float(t_item.get("fundingRate", 0)) * 100
            metrics["open_interest"] = t_item.get("holdingAmount", "N/A")

        # 3. Свечи для графика и RSI
        url_candles = "https://api.bitget.com/api/v2/mix/market/candles"
        res_c = requests.get(url_candles, params={"symbol": symbol, "productType": "usdt-futures", "granularity": granularity, "limit": "50"}, timeout=5).json()
        if res_c.get("code") == "00000" and res_c.get("data"):
            raw = res_c["data"]
            raw.reverse()
            metrics["raw_candles"] = raw
            prices = [float(c[4]) for c in raw]
            rsi_values = calculate_rsi(prices, 14)
            metrics["rsi"] = rsi_values[-1]
    except Exception as e:
        print(f"Ошибка сбора метрик для {symbol}: {e}")

    return metrics

def generate_chart(display_name, raw_candles, granularity_label):
    """Генерация комплексного графика: Цена + RSI под выбранный таймфрейм"""
    try:
        if not raw_candles:
            return None

        prices = [float(c[4]) for c in raw_candles]
        times = list(range(len(prices)))
        rsi_values = calculate_rsi(prices, 14)

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), gridspec_kw={'height_ratios': [3, 1]})
        plt.style.use('dark_background')

        # График цены
        ax1.plot(times, prices, color='#00ffcc', linewidth=2, label=f'Цена ({granularity_label})')
        ax1.fill_between(times, prices, min(prices), color='#00ffcc', alpha=0.1)
        ax1.set_title(f"{display_name}/USDT — Анализ терминала ({granularity_label})", fontsize=13, color='white', pad=10)
        ax1.set_ylabel("Цена USDT", color='#aaaaaa')
        ax1.grid(color='#333333', linestyle='--', linewidth=0.5)
        ax1.legend(loc='upper left')

        # График RSI
        ax2.plot(times, rsi_values, color='#ff00ff', linewidth=1.5, label='RSI (14)')
        ax2.axhline(70, color='red', linestyle='--', linewidth=0.8, alpha=0.7, label='Перекупленность (70)')
        ax2.axhline(30, color='green', linestyle='--', linewidth=0.8, alpha=0.7, label='Перепроданность (30)')
        ax2.set_ylim(0, 100)
        ax2.set_ylabel("RSI", color='#aaaaaa')
        ax2.set_xlabel(f"Свечи ({granularity_label})", color='#aaaaaa')
        ax2.grid(color='#333333', linestyle='--', linewidth=0.5)
        ax2.legend(loc='upper left', fontsize=8)

        plt.tight_layout()

        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150)
        buf.seek(0)
        plt.close()
        return buf
    except Exception as e:
        print(f"Ошибка генерации графика с RSI: {e}")
    return None

def get_ai_risk_analysis(symbol, m, tf_label):
    """ИИ-аналитик с учетом RSI, сентимента, таймфрейма и оценки перегрева"""
    if not ai_client:
        return "⚠️ Не задан OPENAI_API_KEY в переменных окружения Render."

    status, note = analyze_market_overheat(m['funding_rate'], m['ratio'])

    prompt = (
        f"Ты — профессиональный трейдер, аналитик Smart Money и жесткий риск-менеджер. "
        f"Проанализируй текущие метрики фьючерса {symbol} с биржи Bitget для таймфрейма {tf_label}:\n"
        f"- Long/Short Ratio (настроение толпы): {m['ratio']:.2f} (Лонги: {m['long_ratio']:.1f}%, Шорты: {m['short_ratio']:.1f}%)\n"
        f"- Funding Rate (ставка финансирования): {m['funding_rate']:.4f}%\n"
        f"- Open Interest (открытый интерес): {m['open_interest']}\n"
        f"- RSI (14): {m['rsi']:.1f} (Зоны: >70 перекуплен, <30 перепродан)\n"
        f"- Статус перегрева рынка: {status}\n"
        f"- Примечание по рискам: {note}\n\n"
        f"Дай краткий, холодный вердикт:\n"
        f"1. Прогноз направления цены на дистанции таймфрейма ({tf_label}). Обязательно начни этот пункт с одной из стрелок: 📈 [Вверх / Лонг-сквиз], 📉 [Вниз / Шорт-сквиз] или ⚖️ [Флэт/Ожидание].\n"
        f"2. Учёт RSI, статуса перегрева и риска сквиза толпы.\n"
        f"3. Четкая рекомендация по сделке.\n"
        f"Пиши структурированно, без воды."
    )
    try:
        response = ai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=350,
            temperature=0.3
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"⚠️ Ошибка запроса к ИИ-модели: {e}"

def get_keyboard(display_name, current_gran="15m", current_label="15 минут"):
    """Создание инлайн-кнопок таймфреймов и кнопки обновления"""
    keyboard = InlineKeyboardMarkup(row_width=4)
    keyboard.add(
        InlineKeyboardButton("5m", callback_data=f"tf|{display_name}|5m|5 минут"),
        InlineKeyboardButton("15m", callback_data=f"tf|{display_name}|15m|15 минут"),
        InlineKeyboardButton("1h", callback_data=f"tf|{display_name}|1h|1 час"),
        InlineKeyboardButton("4h", callback_data=f"tf|{display_name}|4h|4 часа")
    )
    keyboard.add(
        InlineKeyboardButton("🔄 Обновить данные", callback_data=f"ref|{display_name}|{current_gran}|{current_label}")
    )
    return keyboard

@bot.message_handler(commands=['start'])
def send_welcome(message):
    text = (
        f"Привет, Васиф! 🚀 Терминал с RSI, анализом перегрева толпы и кнопкой обновления запущен.\n\n"
        "📊 Метрики + График + RSI + Статус перегрева + Кнопка обновления в 1 клик.\n\n"
        "Отправь тикер монеты (например: BTC, TRX, ETH), чтобы начать!"
    )
    bot.send_message(message.chat.id, text, parse_mode="HTML")

@bot.message_handler(func=lambda message: True)
def handle_crypto_text(message):
    query = message.text.strip().upper()
    if not query:
        return
    symbol = query + "USDT" if not query.endswith("USDT") else query
    display_name = symbol.replace("USDT", "")

    status_msg = bot.send_message(message.chat.id, f"🔍 Сканирую рынок, считаю RSI и оцениваю перегрев по {display_name}...", parse_mode="HTML")

    granularity, tf_label = "15m", "15 минут"
    m = get_market_metrics(symbol, granularity)

    if m['open_interest'] == "N/A" and m['ratio'] == 1.0:
        bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=status_msg.message_id,
            text=f"⚠️ Фьючерс {symbol} не найден на бирже Bitget. Проверь правильность тикера.",
            parse_mode="HTML"
        )
        return

    ai_verdict = get_ai_risk_analysis(display_name, m, tf_label)
    chart_buf = generate_chart(display_name, m['raw_candles'], tf_label)

    status, _ = analyze_market_overheat(m['funding_rate'], m['ratio'])

    text = (
        f"📊 Терминал: {display_name}/USDT | ⏱ ТФ: {tf_label}\n\n"
        f"👥 Сентимент (L/S Ratio):\n"
        f"🟢 Лонги: {m['long_ratio']:.1f}% | 🔴 Шорты: {m['short_ratio']:.1f}%\n"
        f"⚖️ Коэффициент: {m['ratio']:.2f}\n\n"
        f"⚡ Метрики & Индикаторы:\n"
        f"• Funding: {m['funding_rate']:.4f}%\n"
        f"• Open Interest: {m['open_interest']}\n"
        f"• RSI (14): {m['rsi']:.1f}\n"
        f"• Статус: {status}\n\n"
        f"🤖 ИИ-прогноз и анализ:\n{ai_verdict}"
    )

    try:
        bot.delete_message(message.chat.id, status_msg.message_id)
    except Exception:
        pass

    markup = get_keyboard(display_name, granularity, tf_label)
    if chart_buf:
        bot.send_photo(message.chat.id, chart_buf, caption=text, parse_mode="HTML", reply_markup=markup)
    else:
        bot.send_message(message.chat.id, text, parse_mode="HTML", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("tf|") or call.data.startswith("ref|"))
def handle_callback(call):
    try:
        parts = call.data.split("|")
        action = parts[0]
        display_name = parts[1]
        granularity = parts[2]
        tf_label = parts[3]
        symbol = display_name + "USDT"

        if action == "ref":
            bot.answer_callback_query(call.id, text=f"🔄 Данные по {display_name} обновлены!")
        else:
            bot.answer_callback_query(call.id, text=f"⏱ Таймфрейм: {tf_label}")

        m = get_market_metrics(symbol, granularity)
        ai_verdict = get_ai_risk_analysis(display_name, m, tf_label)
        chart_buf = generate_chart(display_name, m['raw_candles'], tf_label)

        status, _ = analyze_market_overheat(m['funding_rate'], m['ratio'])

        text = (
            f"📊 Терминал: {display_name}/USDT | ⏱ ТФ: {tf_label}\n\n"
            f"👥 Сентимент (L/S Ratio):\n"
            f"🟢 Лонги: {m['long_ratio']:.1f}% | 🔴 Шорты: {m['short_ratio']:.1f}%\n"
            f"⚖️ Коэффициент: {m['ratio']:.2f}\n\n"
            f"⚡ Метрики & Индикаторы:\n"
            f"• Funding: {m['funding_rate']:.4f}%\n"
            f"• Open Interest: {m['open_interest']}\n"
            f"• RSI (14): {m['rsi']:.1f}\n"
            f"• Статус: {status}\n\n"
            f"🤖 ИИ-прогноз и анализ:\n{ai_verdict}"
        )

        markup = get_keyboard(display_name, granularity, tf_label)

        if call.message.content_type == 'photo':
            if chart_buf:
                bot.edit_message_media(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    media=telebot.types.InputMediaPhoto(chart_buf, caption=text, parse_mode="HTML"),
                    reply_markup=markup
                )
            else:
                bot.edit_message_caption(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    caption=text,
                    parse_mode="HTML",
                    reply_markup=markup
                )
        else:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=text,
                parse_mode="HTML",
                reply_markup=markup
            )
    except Exception as e:
        print(f"Ошибка в callback: {e}")

if __name__ == '__main__':
    print("Бот успешно запущен и готов к работе...")
    bot.infinity_polling()
