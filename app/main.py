py
from __future__ import annotations

import asyncio
import logging
import os
import signal

from .bot import run_bot
from .server import start_web_server, stop_web_server

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

async def main() -> None:
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("ENV BOT_TOKEN is required")

    host = "0.0.0.0"
    port = int(os.getenv("PORT", "10000"))  # Render передаст PORT сам

    runner = await start_web_server(host=host, port=port)

    bot_task = asyncio.create_task(run_bot(token))

    stop_event = asyncio.Event()

    def _stop(*_):
        stop_event.set()

    loop = asyncio.get_running_loop()
    for s in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(s, _stop)
        except NotImplementedError:
            # на Windows может не работать add_signal_handler
            pass

    await stop_event.wait()

    bot_task.cancel()
    await stop_web_server(runner)

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 8.2 Файл `C:\Bitbotv_bot\requirements.txt`

Открой `requirements.txt` и сделай так:

```txt
requests==2.32.3
matplotlib==3.9.0
aiohttp==3.10.5
python-telegram-bot==21.6