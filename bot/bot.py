import asyncio
import logging
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "TelegramBot_Calendar.settings")
django.setup()

from aiogram import Bot, Dispatcher
from dotenv import load_dotenv

from bot.handlers import register_handlers  # поправить импорт

load_dotenv()
API_TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

register_handlers(dp)


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
