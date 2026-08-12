py
from __future__ import annotations

import io
from typing import List, Optional

import matplotlib
matplotlib.use("Agg")  # важно для Render/серверов без дисплея

import matplotlib.pyplot as plt

def plot_close_chart(
    symbol: str,
    timeframe: str,
    candles: List[list],
    entry: Optional[float] = None,
    stop: Optional[float] = None,
    tps: Optional[List[float]] = None,
) -> bytes:
    """
    Рисуем простой график CLOSE + линии entry/stop/tp.
    Возвращаем PNG bytes.
    """
    xs = [int(row[0]) for row in candles]
    closes = [float(row[4]) for row in candles]

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(closes, linewidth=1.5)

    ax.set_title(f"{symbol} | {timeframe}")
    ax.set_xlabel("bars")
    ax.set_ylabel("price")

    if entry is not None:
        ax.axhline(entry, linestyle="--", linewidth=1.2, label=f"Entry {entry:.6g}")
    if stop is not None:
        ax.axhline(stop, linestyle="--", linewidth=1.2, label=f"Stop {stop:.6g}")
    if tps:
        for i, tp in enumerate(tps, start=1):
            ax.axhline(tp, linestyle=":", linewidth=1.0, label=f"TP{i} {tp:.6g}")

    ax.grid(True, alpha=0.25)
    ax.legend(loc="best", fontsize=8)

    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png", dpi=160)
    plt.close(fig)
    buf.seek(0)
    return buf.read()