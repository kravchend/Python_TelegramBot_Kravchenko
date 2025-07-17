import os
from aiogram import Bot, Dispatcher
from dotenv import load_dotenv

dotenv_path = ".env.local" if os.path.exists(".env.local") else ".env"
load_dotenv(dotenv_path)

API_TOKEN = os.getenv("BOT_TOKEN")
if not API_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set in environment variables!")

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot=bot)
