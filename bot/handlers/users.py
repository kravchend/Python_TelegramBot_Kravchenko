from aiogram import Router, types
from asgiref.sync import sync_to_async
from calendarapp.models import User
from bot.calendar_instance import calendar
from bot.handlers.keyboards import main_keyboard
from aiogram.filters import Command

router = Router()


async def get_bot():
    from bot.loader import bot
    return bot


@router.message(Command("start"))
async def send_welcome(message: types.Message):
    telegram_id = message.from_user.id
    username = message.from_user.username or f"User_{telegram_id}"
    user, created = await sync_to_async(User.objects.get_or_create)(
        telegram_id=telegram_id,
        defaults={'username': username}
    )

    if created:
        await message.answer("Вы успешно зарегистрированы!", reply_markup=main_keyboard())
    else:
        await message.answer("Добро пожаловать! Вы уже зарегистрированы.", reply_markup=main_keyboard())


async def get_user_id(message):
    telegram_id = message.from_user.id
    return await calendar.get_user_db_id(telegram_id)
