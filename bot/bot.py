import asyncio
import logging
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "TelegramBot_Calendar.settings")
django.setup()

from bot.loader import bot, dp
from bot.handlers import register_handlers

logging.basicConfig(level=logging.INFO)

register_handlers(dp)


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
