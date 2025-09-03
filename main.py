import asyncio
import logging
from contextlib import suppress

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from app.config import get_settings
from app.db.session import AsyncSessionLocal
from app.handlers import (
    add_payment,
    add_time,
    edit,
    help,
    objects,
    report,
    start,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def set_commands(bot: Bot):
    """Set bot commands"""
    commands = [
        BotCommand(command="start", description="🚀 Запустить бота"),
        BotCommand(command="add", description="⏰ Добавить часы работы"),
        BotCommand(command="payment", description="💰 Добавить оплату"),
        BotCommand(command="objects", description="🏗️ Список объектов"),
        BotCommand(command="report", description="📊 Отчёты"),
        BotCommand(command="help", description="❓ Справка"),
    ]
    await bot.set_my_commands(commands)


async def main():
    """Main function"""
    settings = get_settings()
    
    # Initialize bot and dispatcher
    bot = Bot(token=settings.bot_token)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Register routers
    dp.include_router(start.router)
    dp.include_router(help.router)
    dp.include_router(objects.router)
    dp.include_router(add_time.router)
    dp.include_router(add_payment.router)
    dp.include_router(edit.router)
    dp.include_router(report.router)
    
    # Set commands
    await set_commands(bot)
    
    logger.info("Bot started")
    
    try:
        # Start polling
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
