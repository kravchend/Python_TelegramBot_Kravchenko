import os
from dotenv import load_dotenv

# Загрузи переменные окружения до импорта Django!
dotenv_path = ".env.local" if os.path.exists(".env.local") else ".env"
load_dotenv(dotenv_path)

import asyncio
import logging
import django

# Теперь переменные, такие как DATABASE_HOST, уже в окружении
print("DATABASE_HOST из окружения:", os.environ.get("DATABASE_HOST"))

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