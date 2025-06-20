from aiogram import Dispatcher, F, Router, types
from aiogram.filters import Command
from bot.calendar_instance import calendar
from datetime import datetime

router = Router()


def main_keyboard():
    keyboard = [
        [
            types.KeyboardButton(text="📆 Календарь: создать событие"),
            types.KeyboardButton(text="📅 Календарь: список событий"),
        ],
        [
            types.KeyboardButton(text="📆 Календарь: изменить событие"),
            types.KeyboardButton(text="📆 Календарь: удалить событие"),
        ],
    ]
    return types.ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


calendar_creation_state = {}


async def send_welcome(message: types.Message):
    full_name = message.from_user.full_name
    await message.answer(
        f"Привет, {full_name}! Я бот-календарь.",
        reply_markup=main_keyboard()
    )


async def get_user_id(message):
    telegram_id = message.from_user.id
    return await calendar.get_user_db_id(telegram_id)


async def register_user_handler(message: types.Message):
    telegram_id = message.from_user.id
    username = message.from_user.username

    user_id = await calendar.get_user_db_id(telegram_id)
    if user_id:
        await message.answer("Вы уже зарегистрированы.")
        return

    res = await calendar.register_user(telegram_id, username)
    if res:
        await message.answer("Регистрация успешна! Теперь вы можете пользоваться ботом.")
    else:
        await message.answer("Ошибка регистрации. Попробуйте позже.")


async def button_create_calendar_event(message: types.Message):
    telegram_id = message.from_user.id
    user_id = await calendar.get_user_db_id(telegram_id)
    if not user_id:
        await message.answer("Вы не зарегистрированы. Используйте /register")
        return

    calendar_creation_state[user_id] = {"step": "name"}
    await message.answer(
        "Введите название события:",
        reply_markup=types.ReplyKeyboardRemove()
    )


async def process_calendar_creation(message: types.Message):
    telegram_id = message.from_user.id
    user_id = await calendar.get_user_db_id(telegram_id)
    if not user_id:
        await message.answer("Вы не зарегистрированы. Используйте /register")
        return

    state = calendar_creation_state.get(user_id)
    if not state:
        return

    step = state["step"]

    if step == "name":
        state["name"] = message.text.strip()
        state["step"] = "details"
        await message.answer("Введите описание события:")
    elif step == "details":
        state["details"] = message.text.strip()
        state["step"] = "date"
        await message.answer("Введите дату события (ГГГГ-ММ-ДД):")
    elif step == "date":
        state["date"] = message.text.strip()
        state["step"] = "time"
        await message.answer("Введите время события (ЧЧ:ММ):")
    elif step == "time":
        state["time"] = message.text.strip()
        try:
            datetime.strptime(state["date"], "%Y-%m-%d")
            datetime.strptime(state["time"], "%H:%M")
            event_id = await calendar.create_event(
                user_id, state["name"], state["date"], state["time"], state["details"]
            )
            await message.answer(
                f"Событие '{state['name']}' добавлено в календарь!\nID: {event_id}",
                reply_markup=main_keyboard()
            )
        except Exception:
            await message.answer(
                "Ошибка в данных события. Попробуйте создать событие заново.",
                reply_markup=main_keyboard()
            )
        calendar_creation_state.pop(user_id, None)


async def button_list_calendar_events(message: types.Message):
    telegram_id = message.from_user.id
    user_id = await calendar.get_user_db_id(telegram_id)
    if not user_id:
        await message.answer("Вы не зарегистрированы. Используйте /register")
        return

    events = await calendar.get_all_events(user_id)
    if not events:
        await message.answer("Событий пока нет.", reply_markup=main_keyboard())
        return
    lines = [
        f"{e['id']}: {e['name']} | {e['date']} {e['time']} — {e['details']}"
        for e in events
    ]
    await message.answer("Список событий:\n" + "\n".join(lines), reply_markup=main_keyboard())


async def calendar_create_handler(message: types.Message):
    await send_welcome(message)


async def calendar_list_handler(message: types.Message):
    telegram_id = message.from_user.id
    user_id = await calendar.get_user_db_id(telegram_id)
    if not user_id:
        await message.answer("Вы не зарегистрированы. Используйте /register")
        return

    events = await calendar.get_all_events(user_id)
    if not events:
        await message.answer("Событий пока нет.")
        return
    lines = []
    for e in events:
        lines.append(f"{e['id']}: {e['name']} | {e['date']} {e['time']} — {e['details']}")
    await message.answer("Список событий:\n" + "\n".join(lines))


async def calendar_show_handler(message: types.Message):
    args = message.text.strip().split()
    if len(args) != 2:
        await message.answer("Используй: /calendar_show <id>")
        return
    try:
        event_id = int(args[1])
        telegram_id = message.from_user.id
        user_id = await calendar.get_user_db_id(telegram_id)
        if not user_id:
            await message.answer("Вы не зарегистрированы. Используйте /register")
            return

        e = await calendar.get_event(user_id, event_id)
        if not e:
            await message.answer("Событие не найдено.")
            return
        await message.answer(
            f"Событие:\nID: {e['id']}\n"
            f"Название: {e['name']}\n"
            f"Дата: {e['date']} {e['time']}\n"
            f"Описание: {e['details']}"
        )
    except Exception:
        await message.answer("Ошибка. Проверь ID.")


async def calendar_edit_handler(message: types.Message):
    telegram_id = message.from_user.id
    user_id = await calendar.get_user_db_id(telegram_id)
    if not user_id:
        await message.answer("Вы не зарегистрированы. Используйте /register")
        return

    args = message.text.strip().split(maxsplit=5)
    if len(args) < 6:
        await message.answer(
            "Используй: /calendar_edit <id> <название> <дата> <время> <описание>"
        )
        return
    try:
        _, event_id, name, date, time, details = args
        event_id = int(event_id)
        result = await calendar.edit_event(user_id, event_id, name, date, time, details)
        if result:
            await message.answer("Событие обновлено.")
        else:
            await message.answer("Событие не найдено.")
    except Exception:
        await message.answer("Ошибка. Проверь параметры.")


async def calendar_delete_handler(message: types.Message):
    telegram_id = message.from_user.id
    user_id = await calendar.get_user_db_id(telegram_id)
    if not user_id:
        await message.answer("Вы не зарегистрированы. Используйте /register")
        return

    args = message.text.strip().split()
    if len(args) != 2:
        await message.answer("Используй: /calendar_delete <id>")
        return
    try:
        event_id = int(args[1])
        result = await calendar.delete_event(user_id, event_id)
        if result:
            await message.answer("Событие удалено.")
        else:
            await message.answer("Событие не найдено.")
    except Exception:
        await message.answer("Ошибка. Проверь ID.")


calendar_delete_state = {}


async def button_delete_calendar_event(message: types.Message):
    telegram_id = message.from_user.id
    user_id = await calendar.get_user_db_id(telegram_id)
    if not user_id:
        await message.answer("Вы не зарегистрированы. Используйте /register")
        return

    calendar_delete_state[user_id] = True
    await message.answer(
        "Введите ID события, которое нужно удалить:",
        reply_markup=types.ReplyKeyboardRemove()
    )


async def process_calendar_deletion(message: types.Message):
    telegram_id = message.from_user.id
    user_id = await calendar.get_user_db_id(telegram_id)
    if not user_id:
        await message.answer("Вы не зарегистрированы. Используйте /register")
        return

    if not calendar_delete_state.get(user_id):
        return
    try:
        event_id = int(message.text.strip())
        result = await calendar.delete_event(user_id, event_id)
        if result:
            await message.answer("Событие удалено.", reply_markup=main_keyboard())
        else:
            await message.answer("Событие с таким ID не найдено.", reply_markup=main_keyboard())
    except Exception:
        await message.answer("Некорректный ID. Пожалуйста, попробуйте снова.", reply_markup=main_keyboard())
    calendar_delete_state.pop(user_id, None)


calendar_edit_state = {}


async def button_edit_calendar_event(message: types.Message):
    telegram_id = message.from_user.id
    user_id = await calendar.get_user_db_id(telegram_id)
    if not user_id:
        await message.answer("Вы не зарегистрированы. Используйте /register")
        return

    calendar_edit_state[user_id] = {"step": "id"}
    await message.answer(
        "Введите ID изменяемого события:",
        reply_markup=types.ReplyKeyboardRemove()
    )


async def process_calendar_editing(message: types.Message):
    telegram_id = message.from_user.id
    user_id = await calendar.get_user_db_id(telegram_id)
    if not user_id:
        await message.answer("Вы не зарегистрированы. Используйте /register")
        return

    state = calendar_edit_state.get(user_id)
    if not state:
        return

    if state["step"] == "id":
        try:
            event_id = int(message.text.strip())
            event = await calendar.get_event(user_id, event_id)
            if not event:
                await message.answer(
                    "Событие с таким ID не найдено.", reply_markup=main_keyboard()
                )
                calendar_edit_state.pop(user_id, None)
                return
            state["id"] = event_id
            state["step"] = "name"
            await message.answer(f"Текущее название: {event['name']}\nВведите новое название:")
        except Exception:
            await message.answer("Некорректный ID. Попробуйте ещё раз:", reply_markup=main_keyboard())
            calendar_edit_state.pop(user_id, None)
    elif state["step"] == "name":
        state["name"] = message.text.strip()
        state["step"] = "date"
        await message.answer("Введите новую дату (ГГГГ-ММ-ДД):")
    elif state["step"] == "date":
        state["date"] = message.text.strip()
        state["step"] = "time"
        await message.answer("Введите новое время (ЧЧ:ММ):")
    elif state["step"] == "time":
        state["time"] = message.text.strip()
        state["step"] = "details"
        await message.answer("Введите новое описание:")
    elif state["step"] == "details":
        state["details"] = message.text.strip()
        try:
            datetime.strptime(state["date"], "%Y-%m-%d")
            datetime.strptime(state["time"], "%H:%M")
            result = await calendar.edit_event(
                user_id, state["id"], state["name"], state["date"], state["time"], state["details"]
            )
            if result:
                await message.answer(
                    "Событие изменено успешно!", reply_markup=main_keyboard()
                )
            else:
                await message.answer("Событие не найдено.", reply_markup=main_keyboard())
        except Exception:
            await message.answer("Ошибка в формате даты или времени!", reply_markup=main_keyboard())
        calendar_edit_state.pop(user_id, None)


def register_handlers(dp: Dispatcher):
    dp.message.register(register_user_handler, Command("register"))
    dp.message.register(send_welcome, Command("start"))
    dp.message.register(button_create_calendar_event, F.text == "📆 Календарь: создать событие")
    dp.message.register(button_list_calendar_events, F.text == "📅 Календарь: список событий")
    dp.message.register(process_calendar_creation,
                        lambda msg: calendar_creation_state.get(msg.from_user.id) is not None)
    dp.message.register(calendar_create_handler, Command("calendar_create"))
    dp.message.register(calendar_list_handler, Command("calendar_list"))
    dp.message.register(calendar_show_handler, Command("calendar_show"))
    dp.message.register(calendar_edit_handler, Command("calendar_edit"))
    dp.message.register(calendar_delete_handler, Command("calendar_delete"))

    dp.message.register(button_delete_calendar_event, F.text == "📆 Календарь: удалить событие")
    dp.message.register(process_calendar_deletion,
                        lambda msg: calendar_delete_state.get(msg.from_user.id) is not None)
