from aiogram import Router, types
from asgiref.sync import sync_to_async
from calendarapp.models import User
from bot.calendar_instance import calendar
from bot.handlers.keyboards import main_keyboard
from aiogram.filters import Command
import logging

import random
import string

router = Router()
logger = logging.getLogger(__name__)


async def get_bot():
    from bot.loader import bot
    return bot


# @router.message(Command("start"))
@router.message(Command("start", "register"))
async def send_welcome(message: types.Message):
    telegram_id = message.from_user.id
    username = message.from_user.username or f"User_{telegram_id}"
    password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))

    try:
        user, created = await sync_to_async(User.objects.get_or_create)(
            telegram_id=telegram_id,
            defaults={
                'username': username,
                'email': f"{username}@telegram.bot",
                'is_active': True
            }
        )

        if created:
            user.set_password(password)
            await sync_to_async(user.save)()
            # Анимация
            await message.answer(
                f"💫"
            )

            await message.answer(
                f"🤝  {username}, вы успешно\n зарегистрированы!\n\n"

                f"🗝️🛡️  Ваши данные для входа на сайт:\n\n"

                f"  👤  Username: `{username}`\n"
                f"  🔐  Password: `{password}`\n\n"

                f"  🔗  http://127.0.0.1:8000/login/\n\n"

                f"💻  Используйте для доступа \nк записям на других устройствах!",

                reply_markup=main_keyboard(),
                parse_mode="Markdown"
            )
        else:
            await message.answer(
                f"👤  {username}, \nдобро пожаловать!",
                reply_markup=main_keyboard()
            )

    except Exception as e:
        logger.error(f"⚠️  Ошибка регистрации пользователя (Telegram ID {telegram_id}): {e}")
        await message.answer("⚠️  Произошла ошибка. Попробуйте позже.")


async def get_user_id(message):
    telegram_id = message.from_user.id
    return await calendar.get_user_db_id(telegram_id)
