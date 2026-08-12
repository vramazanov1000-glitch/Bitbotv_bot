from __future__ import annotations

import time
import requests

from .config import BITGET_BASE_URL, CANDLE_LIMIT


class BitgetAPIError(RuntimeError):
    pass


def _get(url: str, params: dict | None = None, timeout: int = 20) -> dict:
    r = requests.get(url, params=params or {}, timeout=timeout)
    if r.status_code != 200:
        raise BitgetAPIError(f"HTTP {r.status_code}: {r.text}")
    data = r.json()
    # Bitget usually: {"code":"00000","msg":"success","data":[...]}
    if isinstance(data, dict) and data.get("code") not in (None, "00000"):
        raise BitgetAPIError(f"Bitget error: {data}")
    return data


def spot_candles(symbol: str, granularity: str = "1H", limit: int = CANDLE_LIMIT):
    """
    Returns list of candles in ascending time.
    Bitget v2 spot candles:
    /api/v2/spot/market/candles?symbol=BTCUSDT&granularity=1H&limit=100
    Candle fields (strings):
    [ts, open, high, low, close, baseVol, quoteVol]
    """
    url = f"{BITGET_BASE_URL}/api/v2/spot/market/candles"
    data = _get(url, params={"symbol": symbol, "granularity": granularity, "limit": str(limit)})
    rows = data.get("data", [])
    # API may return newest->oldest; ensure oldest->newest
    try:
        rows = sorted(rows, key=lambda x: int(x[0]))
    except Exception:
        pass
    return rows


def spot_ticker(symbol: str):
    """
    /api/v2/spot/market/tickers?symbol=BTCUSDT
    """
    url = f"{BITGET_BASE_URL}/api/v2/spot/market/tickers"
    data = _get(url, params={"symbol": symbol})
    arr = data.get("data") or []
    return arr[0] if arr else {}


def now_ms() -> int:
    return int(time.time() * 1000)