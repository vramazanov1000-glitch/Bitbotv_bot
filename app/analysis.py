py
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

@dataclass
class Signal:
    symbol: str
    timeframe: str
    direction: str  # "LONG" | "SHORT"
    entry: float
    stop: float
    take_profits: List[float]
    confidence: int  # 1..5
    reason: str

def _sma(values: List[float], period: int) -> List[float]:
    out = []
    s = 0.0
    for i, v in enumerate(values):
        s += v
        if i >= period:
            s -= values[i - period]
        if i >= period - 1:
            out.append(s / period)
        else:
            out.append(float("nan"))
    return out

def _rsi(closes: List[float], period: int = 14) -> List[float]:
    if len(closes) < period + 1:
        return [float("nan")] * len(closes)

    gains = [0.0]
    losses = [0.0]
    for i in range(1, len(closes)):
        ch = closes[i] - closes[i - 1]
        gains.append(max(ch, 0.0))
        losses.append(max(-ch, 0.0))

    # Wilder smoothing
    avg_gain = sum(gains[1 : period + 1]) / period
    avg_loss = sum(losses[1 : period + 1]) / period

    rsi = [float("nan")] * (period)
    for i in range(period, len(closes)):
        if i > period:
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss == 0:
            rsi.append(100.0)
        else:
            rs = avg_gain / avg_loss
            rsi.append(100.0 - (100.0 / (1.0 + rs)))
    return rsi

def _atr(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> List[float]:
    trs = [0.0]
    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        trs.append(tr)

    if len(trs) < period:
        return [float("nan")] * len(trs)

    out = [float("nan")] * (period - 1)
    atr = sum(trs[:period]) / period
    out.append(atr)
    for i in range(period, len(trs)):
        atr = (atr * (period - 1) + trs[i]) / period
        out.append(atr)
    return out

def _to_ohlc(candles: List[list]) -> Tuple[List[int], List[float], List[float], List[float], List[float]]:
    ts, o, h, l, c = [], [], [], [], []
    for row in candles:
        ts.append(int(row[0]))
        o.append(float(row[1]))
        h.append(float(row[2]))
        l.append(float(row[3]))
        c.append(float(row[4]))
    return ts, o, h, l, c

def build_signal(symbol: str, timeframe: str, candles: List[list]) -> Signal | None:
    """
    Простая логика:
    - тренд: SMA20 vs SMA50
    - подтверждение импульса: RSI(14)
    - риск: стоп через ATR
    """
    if len(candles) < 60:
        return None

    ts, o, h, l, c = _to_ohlc(candles)
    sma20 = _sma(c, 20)
    sma50 = _sma(c, 50)
    rsi14 = _rsi(c, 14)
    atr14 = _atr(h, l, c, 14)

    last = len(c) - 1
    price = c[last]

    if any(map(lambda x: x != x, [sma20[last], sma50[last], rsi14[last], atr14[last]])):  # NaN check
        return None

    uptrend = sma20[last] > sma50[last]
    downtrend = sma20[last] < sma50[last]
    rsi = rsi14[last]
    atr = atr14[last]

    # базовые условия
    direction = None
    confidence = 2
    reason_parts = []

    if uptrend and rsi >= 52:
        direction = "LONG"
        confidence += 1
        reason_parts.append("SMA20 > SMA50 (восходящий тренд)")
        reason_parts.append(f"RSI={rsi:.1f} (бычий импульс)")
    elif downtrend and rsi <= 48:
        direction = "SHORT"
        confidence += 1
        reason_parts.append("SMA20 < SMA50 (нисходящий тренд)")
        reason_parts.append(f"RSI={rsi:.1f} (медвежий импульс)")
    else:
        return None

    entry = price

    # стоп и тейки через ATR (простая модель)
    if direction == "LONG":
        stop = entry - 1.5 * atr
        tp1 = entry + 1.0 * atr
        tp2 = entry + 2.0 * atr
        tp3 = entry + 3.0 * atr
    else:
        stop = entry + 1.5 * atr
        tp1 = entry - 1.0 * atr
        tp2 = entry - 2.0 * atr
        tp3 = entry - 3.0 * atr

    # слегка усилим уверенность, если дистанция между средними заметная
    spread = abs(sma20[last] - sma50[last]) / entry
    if spread > 0.002:
        confidence += 1
        reason_parts.append("расхождение SMA20/SMA50 усиливается")
    if spread > 0.004:
        confidence += 1

    confidence = max(1, min(5, confidence))
    reason = "; ".join(reason_parts)

    return Signal(
        symbol=symbol,
        timeframe=timeframe,
        direction=direction,
        entry=float(entry),
        stop=float(stop),
        take_profits=[float(tp1), float(tp2), float(tp3)],
        confidence=confidence,
        reason=reason,
    )