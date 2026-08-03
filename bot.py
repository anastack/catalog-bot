import os
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

import handlers

logger = logging.getLogger(__name__)

bot = Bot(token=os.getenv("TELEGRAM_BOT_TOKEN", ""))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
dp.include_router(handlers.router)

async def start_bot():
    if not bot.token:
        logger.warning("TELEGRAM_BOT_TOKEN is missing. Bot will not start.")
        return
        
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Starting Telegram bot polling...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(start_bot())
