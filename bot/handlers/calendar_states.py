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
        return await func(*args, **kwargs)

    return wrapper


@router.message(F.text == "📆 Календарь: изменить событие")
@log_func
async def handle_edit_event_button(message: types.Message, **kwargs):
    await button_edit_calendar_event(message, **kwargs)


@router.message(F.text == "📆 Календарь: удалить событие")
@log_func
async def handle_delete_event_button(message: types.Message, **kwargs):
    await button_delete_calendar_event(message, **kwargs)


@router.message(lambda message: calendar_creation_state.get(message.from_user.id) is not None)
@log_func
async def process_calendar_creation(message: types.Message, **kwargs):
    from bot.handlers.events import render_event_message
    telegram_id = message.from_user.id
    user_id = await calendar.get_user_db_id(telegram_id)
    if not user_id:
        await message.answer(
            "Вы не зарегистрированы. Используйте /register",
            reply_markup=main_keyboard()
        )
        return

    state = calendar_creation_state.get(telegram_id)
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
        await message.answer("Введите время события (ЧЧ:ММ или ЧЧ:ММ:СС")
    elif step == "time":
        state["time"] = message.text.strip()
        try:
            datetime.strptime(state["date"], "%Y-%m-%d")
            try:
                _time_obj = datetime.strptime(state["time"], "%H:%M")
            except ValueError:
                _time_obj = datetime.strptime(state["time"], "%H:%M:%S")
            state["time"] = _time_obj.strftime("%H:%M:%S")
            event_id = await calendar.create_event(
                user_id, state["name"], state["date"], state["time"], state["details"]
            )
            if not event_id:
                await message.answer("Ошибка: не удалось создать событие!", reply_markup=main_keyboard())
            else:
                events = await calendar.get_all_events(user_id)
                my_idx, my_event = None, None
                for idx, event in enumerate(events, 1):
                    if str(event.get("id", event.get("order"))) == str(event_id):
                        my_idx = idx
                        my_event = event
                        break
                if my_idx is None:
                    await message.answer("Ошибка: не удалось найти только что созданное событие!")
                else:
                    time_str = str(my_event["time"])
                    try:
                        time_val = datetime.strptime(time_str, '%H:%M:%S')
                    except ValueError:
                        time_val = datetime.strptime(time_str, '%H:%M')
                    ev = DummyEvent(
                        id=str(my_event.get("id", my_event.get("order"))),
                        name=str(my_event["name"]),
                        details=str(my_event["details"]),
                        date=datetime.strptime(str(my_event["date"]), '%Y-%m-%d'),
                        time=time_val,
                        is_public=bool(my_event.get("is_public", False))
                    )
                    text, keyboard = render_event_message(ev)
                    await message.answer(text, reply_markup=keyboard)
                    await message.answer(
                        "Вы можете пригласить участников на это событие:",
                        reply_markup=get_invite_keyboard(event_id)
                    )
        except Exception as e:
            await message.answer(
                    f"Ошибка в данных события: {e}",
                    reply_markup=main_keyboard()
                )
            calendar_creation_state.pop(telegram_id, None)


@router.message(F.text == "📆 Календарь: создать событие")
@router.message(Command("calendar_create"))
@log_func
async def calendar_create_handler(message: types.Message, **kwargs):
    telegram_id = message.from_user.id
    user_id = await calendar.get_user_db_id(telegram_id)
    if not user_id:
        await message.answer(
            "Вы не зарегистрированы. Используйте /register",
            reply_markup=main_keyboard()
        )
        return
    calendar_creation_state[telegram_id] = {"step": "name"}
    await message.answer("Введите название события:")


@router.message(lambda message: calendar_delete_state.get(message.from_user.id) is not None)
@log_func
async def process_calendar_deletion(message: types.Message, **kwargs):
    telegram_id = message.from_user.id
    user_id = await calendar.get_user_db_id(telegram_id)
    events = calendar_delete_state.get(telegram_id)
    if not user_id or telegram_id not in calendar_delete_state:
        await message.answer(
            "Вы не зарегистрированы. Используйте /register",
            reply_markup=main_keyboard()
        )
        return
    if not events:
        await message.answer("Нет доступных событий.")
        return
    try:
        num = int(message.text.strip())
        if not (1 <= num <= len(events)):
            raise ValueError
        event_item = events[num - 1]
        event_id = event_item["id"] if isinstance(event_item, dict) else event_item.id
        result = await calendar.delete_event(user_id, event_id)
        if result:
            await message.answer("Событие удалено.", reply_markup=main_keyboard())
        else:
            await message.answer("Событие не найдено.", reply_markup=main_keyboard())
        calendar_delete_state.pop(telegram_id, None)
    except Exception as e:
        await message.answer(f"Некорректный номер.")


@router.message(F.text == "📆 Календарь: удалить событие")
@router.message(Command("calendar_delete"))
@log_func
async def calendar_delete_handler(message: types.Message, **kwargs):
    from bot.handlers.events import get_user_events_with_index
    telegram_id = message.from_user.id
    user_id = await calendar.get_user_db_id(telegram_id)
    if not user_id:
        await message.answer(
            "Вы не зарегистрированы. Используйте /register",
            reply_markup=main_keyboard()
        )
        return

    args = message.text.strip().split()
    if len(args) != 2:
        await message.answer("Используй: /calendar_delete <номер>", reply_markup=main_keyboard())
        return
    try:
        # Получаем список событий с нужной сортировкой и индексами
        events = await get_user_events_with_index(user_id)
        num = int(args[1])
        if not (1 <= num <= len(events)):
            await message.answer("Некорректный номер. Попробуйте снова.", reply_markup=main_keyboard())
            return
        event_id = str(events[num - 1]["id"])  # <-- вот тут как нужно!
        result = await calendar.delete_event(user_id, event_id)
        if result:
            await message.answer("Событие удалено.", reply_markup=main_keyboard())
        else:
            await message.answer("Событие не найдено.", reply_markup=main_keyboard())
    except Exception:
        await message.answer("Ошибка. Проверьте номер.", reply_markup=main_keyboard())


@router.message(lambda message: calendar_edit_state.get(message.from_user.id) is not None)
@log_func
async def process_calendar_editing_by_number(message: types.Message, **kwargs):
    telegram_id = message.from_user.id
    state = calendar_edit_state.get(telegram_id)
    if not state:
        return

    user_id = await calendar.get_user_db_id(telegram_id)
    if not user_id:
        await message.answer("Вы не зарегистрированы. Используйте /register", reply_markup=main_keyboard())
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
            await message.answer(f"Текущее название: {event['name']}\nВведите новое название:")
        except Exception:
            await message.answer("Некорректный номер. Попробуйте снова.")
            calendar_edit_state.pop(telegram_id, None)
    elif step == "name":
        state["name"] = message.text.strip()
        state["step"] = "date"
        await message.answer("Введите новую дату (ГГГГ-ММ-ДД):")
    elif step == "date":
        state["date"] = message.text.strip()
        state["step"] = "time"
        await message.answer("Введите новое время (ЧЧ:ММ):")
    elif step == "time":
        state["time"] = message.text.strip()
        state["step"] = "details"
        await message.answer("Введите новое описание:")
    elif step == "details":
        state["details"] = message.text.strip()
        try:
            datetime.strptime(state["date"], "%Y-%m-%d")
            datetime.strptime(state["time"], "%H:%M")
        except ValueError:
            await message.answer("Ошибка в формате даты или времени!", reply_markup=main_keyboard())
            calendar_edit_state.pop(telegram_id, None)
            return

        result = await calendar.edit_event(
            user_id, state["id"], state["name"], state["date"], state["time"], state["details"]
        )
        if result:
            await message.answer(
                "Событие обновлено!\nХотите сразу пригласить участников?",
                reply_markup=get_invite_keyboard(state["id"])
            )
        else:
            await message.answer("Событие не найдено.", reply_markup=main_keyboard())
        calendar_edit_state.pop(telegram_id, None)


@router.message(F.text == "📆 Календарь: удалить событие")
@log_func
async def button_delete_calendar_event(message: types.Message, **kwargs):
    from bot.handlers.events import get_user_events_with_index
    telegram_id = message.from_user.id
    user_id = await calendar.get_user_db_id(telegram_id)
    events = await get_user_events_with_index(user_id)
    if not user_id:
        await message.answer(
            "Вы не зарегистрированы. Используйте /register",
            reply_markup=main_keyboard()
        )
        return
    if not events:
        await message.answer("У вас нет событий для удаления.", reply_markup=main_keyboard())
        return
    calendar_delete_state[telegram_id] = events
    text = "\n".join(f"{i + 1}. {e['name']} {e['date']} {e['time']}" for i, e in enumerate(events))
    await message.answer("Ваши события:\n" + text + "\n\nОтправьте номер события для удаления.")


@router.message(F.text == "📆 Календарь: изменить событие")
@log_func
async def button_edit_calendar_event(message: types.Message, **kwargs):
    from bot.handlers.events import get_user_events_with_index
    telegram_id = message.from_user.id
    user_id = await calendar.get_user_db_id(telegram_id)
    if not user_id:
        await message.answer(
            "Вы не зарегистрированы. Используйте /register",
            reply_markup=main_keyboard()
        )
        return

    events = await get_user_events_with_index(user_id)
    if not events:
        await message.answer("У вас нет событий для изменения.", reply_markup=main_keyboard())
        return

    lines = [f"{e['order']}. {e['name']} | {e['date']} {e['time']} — {e['details']}" for e in events]
    calendar_edit_state[telegram_id] = {
        "events": events,
        "step": "num"
    }
    await message.answer(
        "Введите номер события для редактирования:\n" + "\n".join(lines),
        reply_markup=types.ReplyKeyboardRemove()
    )
