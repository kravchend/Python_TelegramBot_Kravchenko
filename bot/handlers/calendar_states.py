from aiogram import types, Router, F
from aiogram.filters import Command
from bot.handlers.keyboards import main_keyboard, get_invite_keyboard
from bot.calendar_instance import calendar
from datetime import datetime
from bot.handlers.types import DummyEvent

router = Router()

calendar_creation_state = {}
calendar_delete_state = {}
calendar_edit_state = {}


def log_func(func):
    async def wrapper(*args, **kwargs):
        print(f"[LOG] Вызов функции: {func.__name__}")
        return await func(*args, **kwargs)

    return wrapper


@router.message(F.text == "✏️  Создать")
@router.message(Command("calendar_create"))
@log_func
async def calendar_create_handler(message: types.Message, **kwargs):
    telegram_id = message.from_user.id
    user_id = await calendar.get_user_db_id(telegram_id)
    if not user_id:
        await message.answer(
            " 🗝️  Зарегистрируйтесь \n\n     🔗     '/register'",
            reply_markup=main_keyboard()
        )
        return
    calendar_creation_state[telegram_id] = {"step": "name"}
    await message.answer(" ✏️  Название события: ")


@router.message(lambda message: calendar_creation_state.get(message.from_user.id) is not None)
@log_func
async def process_calendar_creation(message: types.Message, **kwargs):
    from bot.handlers.events import render_event_message
    telegram_id = message.from_user.id
    state = calendar_creation_state.get(telegram_id)
    if not state:
        return

    user_id = await calendar.get_user_db_id(telegram_id)
    if not user_id:
        await message.answer(
            " 🗝️  Зарегистрируйтесь \n\n     🔗     '/register'",
            reply_markup=main_keyboard()
        )
        return

    try:
        step = state["step"]

        if step == "name":
            state["name"] = message.text.strip()
            state["step"] = "details"
            await message.answer(" 📝  Описание события:")
            return

        if step == "details":
            state["details"] = message.text.strip()
            state["step"] = "date"
            await message.answer(" 🗓️  Дата события (ГГГГ-ММ-ДД):")
            return

        if step == "date":
            datetime.strptime(message.text.strip(), "%Y-%m-%d")  # Валидация
            state["date"] = message.text.strip()
            state["step"] = "time"
            await message.answer(" ⏱️  Время события (ЧЧ:ММ):")
            return

        if step == "time":
            try:
                time_obj = datetime.strptime(message.text.strip(), "%H:%M")
            except ValueError:
                await message.answer(" ⚠️ Неверный формат времени. Используйте ЧЧ:ММ")
                return

            state["time"] = time_obj.strftime("%H:%M:%S")
            event_id = await calendar.create_event(
                user_id, state["name"], state["date"], state["time"], state["details"]
            )

            if not event_id:
                await message.answer(" ⚠️ Ошибка при создании события.", reply_markup=main_keyboard())
                calendar_creation_state.pop(telegram_id, None)
                return

            from bot.handlers.events import get_user_events_with_index
            events = await get_user_events_with_index(user_id)
            my_event = next((e for e in events if str(e.get("id")) == str(event_id)), None)

            if not my_event:
                await message.answer(" ⚠️ Событие создано, но не отображено.", reply_markup=main_keyboard())
            else:
                text, keyboard = render_event_message(DummyEvent(
                    id=str(my_event["id"]),
                    name=my_event["name"],
                    details=my_event["details"],
                    date=datetime.strptime(my_event["date"], "%Y-%m-%d"),
                    time=datetime.strptime(my_event["time"], "%H:%M:%S"),
                    is_public=bool(my_event.get("is_public", False)),
                ))
                await message.answer(text, reply_markup=keyboard)

            calendar_creation_state.pop(telegram_id, None)

    except Exception as e:
        await message.answer(f" ⚠️  Ошибка: {e}", reply_markup=main_keyboard())
        calendar_creation_state.pop(telegram_id, None)


@router.message(lambda message: calendar_edit_state.get(
    message.from_user.id) is not None and message.text and not message.text.startswith('/'))
@log_func
async def process_calendar_editing_by_number(message: types.Message, **kwargs):
    telegram_id = message.from_user.id
    state = calendar_edit_state.get(telegram_id)
    if not state:
        return

    user_id = await calendar.get_user_db_id(telegram_id)
    if not user_id:
        await message.answer(" 🗝️  Зарегистрируйтесь \n\n     🔗     '/register'", reply_markup=main_keyboard())
        calendar_edit_state.pop(telegram_id, None)
        return

    step = state["step"]

    if step == "num":
        try:
            num = int(message.text.strip())
            events = state["events"]
            if not (1 <= num <= len(events)):
                raise ValueError
            event = events[num - 1]
            state.update({
                "id": event["id"],
                "step": "name"
            })
            await message.answer(f"  ✏️  {event['name']} \n Введите новое название:")
        except Exception:
            await message.answer("  ❌  \n Некорректный номер. Попробуйте снова.")
            calendar_edit_state.pop(telegram_id, None)
    elif step == "name":
        state["name"] = message.text.strip()
        state["step"] = "date"
        await message.answer("  🗓️  Новая дата (ГГГГ-ММ-ДД): ")
    elif step == "date":
        state["date"] = message.text.strip()
        state["step"] = "time"
        await message.answer(" ⏱️  Новое время (ЧЧ:ММ): ")
    elif step == "time":
        state["time"] = message.text.strip()
        state["step"] = "details"
        await message.answer(" 📝  Новое описание:")
    elif step == "details":
        state["details"] = message.text.strip()
        try:
            datetime.strptime(state["date"], "%Y-%m-%d")
            datetime.strptime(state["time"], "%H:%M")
        except ValueError:
            await message.answer(" ❌  Ошибка в формате даты или времени!", reply_markup=main_keyboard())
            calendar_edit_state.pop(telegram_id, None)
            return

        result = await calendar.edit_event(
            user_id, state["id"], state["name"], state["date"], state["time"], state["details"]
        )
        if result:
            await message.answer(
                " 💫  Событие обновлено!\n\n Пригласить участников?\n",
                reply_markup=get_invite_keyboard(state["id"])
            )
        else:
            await message.answer("Событие не найдено.", reply_markup=main_keyboard())
        calendar_edit_state.pop(telegram_id, None)


@router.message(Command("calendar_edit"))
@router.message(F.text == "🔑  Изменить")
@log_func
async def button_edit_calendar_event(message: types.Message, **kwargs):
    from bot.handlers.events import get_user_events_with_index
    telegram_id = message.from_user.id
    user_id = await calendar.get_user_db_id(telegram_id)
    if not user_id:
        await message.answer(
            " 🗝️  Зарегистрируйтесь \n\n     🔗     '/register'",
            reply_markup=main_keyboard()
        )
        return

    events = await get_user_events_with_index(user_id)
    if not events:
        await message.answer(" 🤷 Нет событий для изменения.", reply_markup=main_keyboard())
        return

    lines = [f"  👉  {e['order']}. {e['name']} | {e['date']} {e['time']} — {e['details']}" for e in events]
    calendar_edit_state[telegram_id] = {
        "events": events,
        "step": "num"
    }

    await message.answer(
        "  🛠️  Введите номер события для редактирования:\n" + "\n".join(lines),
        reply_markup=types.ReplyKeyboardRemove()
    )


@router.message(Command("calendar_delete"))
@router.message(F.text == "🗑️  Удалить")
@log_func
async def button_delete_calendar_event(message: types.Message, **kwargs):
    from bot.handlers.events import get_user_events_with_index
    telegram_id = message.from_user.id
    user_id = await calendar.get_user_db_id(telegram_id)
    events = await get_user_events_with_index(user_id)
    if not user_id:
        await message.answer(
            " 🗝️  Зарегистрируйтесь \n\n     🔗     '/register'",
            reply_markup=main_keyboard()
        )
        return
    if not events:
        await message.answer("Нет событий для удаления.", reply_markup=main_keyboard())
        return
    calendar_delete_state[telegram_id] = events
    text = "\n".join(
        f" 🔹 {i + 1}. {e['name']} {e['date']} ({datetime.strptime(e['time'], '%H:%M:%S').strftime('%H:%M')})" for i, e
        in enumerate(events))
    await message.answer(
        " 📝  Ваши события:\n\n" + text + "\n\n ⚠️ Отправьте номер события для удаления:\n\n 👇     👇     👇     👇     👇     👇     👇")


# Было: @router.message(lambda message: calendar_delete_state.get(message.from_user.id) is not None)
@router.message(lambda message: calendar_delete_state.get(
    message.from_user.id) is not None and message.text and message.text.strip().isdigit())
@log_func
async def process_calendar_deletion(message: types.Message, **kwargs):
    telegram_id = message.from_user.id
    user_id = await calendar.get_user_db_id(telegram_id)
    events = calendar_delete_state.get(telegram_id)
    if not user_id or telegram_id not in calendar_delete_state:
        await message.answer(
            " 🗝️  Зарегистрируйтесь \n\n     🔗     '/register'",
            reply_markup=main_keyboard()
        )
        return
    if not events:
        await message.answer(" 🤷 Нет доступных событий. ")
        return
    try:
        num = int(message.text.strip())
        if not (1 <= num <= len(events)):
            raise ValueError
        event_item = events[num - 1]
        event_id = event_item["id"] if isinstance(event_item, dict) else event_item.id
        result = await calendar.delete_event(user_id, event_id)
        if result:
            await message.answer(" 🗑️ Событие удалено. ", reply_markup=main_keyboard())
        else:
            await message.answer(" 🤷 Событие не найдено. ", reply_markup=main_keyboard())
        calendar_delete_state.pop(telegram_id, None)
    except Exception as e:
        await message.answer(f" ❗ Некорректный номер ")
