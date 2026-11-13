import asyncio
import logging
from os import getenv
from aiohttp import web
from aiogram import Bot, Dispatcher

import config
from database import init_db
from handlers import register_handlers

# Logging sozlamalari
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)

bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()

# Render uchun aiohttp web-server
async def handle_ping(request):
    return web.Response(text="Ultimate Donat Bot serveri ishlamoqda!")

async def web_server():
    app = web.Application()
    app.router.add_get("/", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(getenv("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"Veb-server {port}-portda ishga tushdi.")

async def main():
    # Bazani yaratish
    init_db()
    logger.info("Ma'lumotlar bazasi tayyor.")
    
    # Handlerlarni ulash
    register_handlers(dp, bot)
    
    print("Bot muvaffaqiyatli ishga tushdi...")
    
    # Server va pollingni birga yuritish
    await asyncio.gather(
        web_server(),
        dp.start_polling(bot)
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi!")
