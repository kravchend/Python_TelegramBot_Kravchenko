import asyncio
import logging
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "TelegramBot_Calendar.settings")
django.setup()

from aiogram import Bot, Dispatcher
from dotenv import load_dotenv

from bot.handlers import router, register_handlers

load_dotenv()
API_TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
dp.include_router(router)  # Подключаем router

register_handlers(dp)  # Регистрируем дополнительные хендлеры


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
