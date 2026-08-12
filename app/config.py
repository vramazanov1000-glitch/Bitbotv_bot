import os

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL", "")

DEFAULT_QUOTE = os.getenv("DEFAULT_QUOTE", "USDT")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
PORT = int(os.getenv("PORT", "10000"))

BITGET_BASE_URL = "https://api.bitget.com"
CANDLE_LIMIT = int(os.getenv("CANDLE_LIMIT", "240"))

SHOW_DISCLAIMER = os.getenv("SHOW_DISCLAIMER", "1") == "1"
