py
from __future__ import annotations

import asyncio
from aiohttp import web

async def health(request: web.Request) -> web.Response:
    return web.Response(text="ok")

async def start_web_server(host: str, port: int) -> web.AppRunner:
    """
    Мини HTTP сервер для Render (healthcheck).
    """
    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/health", health)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host=host, port=port)
    await site.start()
    return runner

async def stop_web_server(runner: web.AppRunner) -> None:
    await runner.cleanup()