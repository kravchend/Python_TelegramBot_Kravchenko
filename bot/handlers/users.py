from aiogram import Router, types
from bot.calendar_instance import calendar
from bot.handlers.keyboards import main_keyboard
from aiogram.filters import Command

router = Router()


async def get_bot():
    from bot.loader import bot
    return bot


@router.message(Command("start"))
async def send_welcome(message: types.Message):
    full_name = message.from_user.full_name
    await message.answer(
        f"Привет, {full_name}! Я бот-календарь.",
        reply_markup=main_keyboard()
    )


async def get_user_id(message):
    telegram_id = message.from_user.id
    return await calendar.get_user_db_id(telegram_id)


@router.message(Command("register"))
async def register_user_handler(message: types.Message):
    telegram_id = message.from_user.id
    username = message.from_user.username

    user_id = await calendar.get_user_db_id(telegram_id)
    if user_id:
        await message.answer(
            "Вы уже зарегистрированы.",
            reply_markup=main_keyboard()
        )
        return

    res = await calendar.register_user(telegram_id, username)
    if res:
        await message.answer("Регистрация успешна! Теперь вы можете пользоваться ботом.",
                             reply_markup=main_keyboard()
                             )
    else:
        await message.answer(
            "Ошибка регистрации. Попробуйте позже.",
            reply_markup=main_keyboard()
        )
