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


@router.message(Command("start"))
async def send_welcome(message: types.Message):
    telegram_id = message.from_user.id  # ID текущего пользователя Telegram
    username = message.from_user.username or f"User_{telegram_id}"

    # Генерация случайного пароля
    password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))  # 12 символов: буквы и цифры

    base_register_url = "http://127.0.0.1:8000/register"  # Базовый URL вашей регистрации на сайте

    try:
        # Создаём пользователя или проверяем наличие
        user, created = await sync_to_async(User.objects.get_or_create)(
            telegram_id=telegram_id,
            defaults={
                'username': username,
                'email': f"{username}@telegram.bot",  # Технический email
                'is_active': True  # Активируем пользователя
            }
        )

        if created:
            # Устанавливаем сгенерированный пароль
            user.set_password(password)
            await sync_to_async(user.save)()  # Сохраняем пользователя с паролем

            # Отправляем пользователю его сгенерированный пароль
            await message.answer(
                f"Здравствуйте, {username}! Вы успешно зарегистрированы.\n\n"
                f"Ваши данные для входа на сайт:\n"
                f"🌐 **Сайт:** http://127.0.0.1:8000\n"
                f"👤 **Имя пользователя (username):** `{username}`\n"
                f"🔑 **Пароль:** `{password}`\n\n"
                f"Вы можете использовать эти данные для входа на сайт.",
                reply_markup=main_keyboard(),
                parse_mode="Markdown"
            )
        else:
            # Если пользователь уже зарегистрирован через бота
            await message.answer(
                "Здравствуйте! Вы уже зарегистрированы. Добро пожаловать!",
                reply_markup=main_keyboard()
            )

    except Exception as e:
        logger.error(f"Ошибка регистрации пользователя (Telegram ID {telegram_id}): {e}")
        await message.answer("Произошла ошибка. Попробуйте позже.")


async def get_user_id(message):
    telegram_id = message.from_user.id
    return await calendar.get_user_db_id(telegram_id)
