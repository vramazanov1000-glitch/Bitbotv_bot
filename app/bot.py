py
from __future__ import annotations

import logging
from typing import Optional

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes

from .analysis import build_signal
from .bitget import spot_candles
from .chart import plot_close_chart
from .config import DEFAULT_SYMBOL, DEFAULT_TIMEFRAME, CANDLE_LIMIT

log = logging.getLogger("bot")

def _fmt_signal_text(sig) -> str:
    tps = "\n".join([f"TP{i}: <b>{tp:.6g}</b>" for i, tp in enumerate(sig.take_profits, start=1)])
    txt = (
        f"<b>Signal</b>\n"
        f"Symbol: <b>{sig.symbol}</b>\n"
        f"TF: <b>{sig.timeframe}</b>\n"
        f"Direction: <b>{sig.direction}</b>\n\n"
        f"Entry: <b>{sig.entry:.6g}</b>\n"
        f"Stop: <b>{sig.stop:.6g}</b>\n"
        f"{tps}\n\n"
        f"Confidence: <b>{sig.confidence}/5</b>\n"
        f"Reason: {sig.reason}"
    )
    return txt

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Бот запущен.\n"
        "Команды:\n"
        "/signal [SYMBOL] [TF] — пример: /signal BTCUSDT 1H\n"
        "/help"
    )

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Команды:\n"
        "/signal [SYMBOL] [TF]\n\n"
        "TF для Bitget spot candles обычно: 1m, 5m, 15m, 30m, 1H, 4H, 1D и т.п.\n"
        "Пример: /signal BTCUSDT 1H"
    )

async def cmd_signal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.message
    if not msg:
        return

    args = context.args or []
    symbol = (args[0].upper() if len(args) >= 1 else DEFAULT_SYMBOL)
    timeframe = (args[1] if len(args) >= 2 else DEFAULT_TIMEFRAME)

    await msg.reply_text(f"Запрашиваю данные: {symbol} {timeframe} ...")

    try:
        candles = spot_candles(symbol=symbol, granularity=timeframe, limit=CANDLE_LIMIT)
    except Exception as e:
        log.exception("spot_candles failed")
        await msg.reply_text(f"Ошибка запроса к Bitget: {e}")
        return

    sig = build_signal(symbol=symbol, timeframe=timeframe, candles=candles)
    if not sig:
        await msg.reply_text("Сигнал не найден по текущей стратегии. Попробуй другой TF/монету.")
        return

    # картинка
    try:
        png = plot_close_chart(
            symbol=sig.symbol,
            timeframe=sig.timeframe,
            candles=candles,
            entry=sig.entry,
            stop=sig.stop,
            tps=sig.take_profits,
        )
        await msg.reply_photo(photo=png, caption=_fmt_signal_text(sig), parse_mode=ParseMode.HTML)
    except Exception:
        log.exception("chart failed")
        await msg.reply_text(_fmt_signal_text(sig), parse_mode=ParseMode.HTML)

def build_app(token: str) -> Application:
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("signal", cmd_signal))
    return app

async def run_bot(token: str) -> None:
    """
    Long polling (подходит для Render Web Service).
    """
    app = build_app(token)
    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
    log.info("Bot polling started")