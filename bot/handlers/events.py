from aiogram import F, Router, types
from bot.calendar_instance import calendar
from aiogram.filters import Command
from bot.handlers.keyboards import (
    main_keyboard, get_invite_keyboard, event_public_action_keyboard, get_users_invite_keyboard, get_invitable_users)
from asgiref.sync import sync_to_async
from datetime import datetime
from bot.handlers.types import DummyEvent
from .calendar_states import calendar_creation_state, calendar_edit_state
from calendarapp.models import User, Event
from bot.handlers.users import get_bot

router = Router()


async def get_event_id_by_number(user_id, number):
    events = Event.objects.filter(user_id=user_id).order_by('date', 'time')
    if 1 <= number <= len(events):
        return events[number - 1].id
    return None


async def get_user_events_with_index(user_id):
    events = await calendar.get_all_events(user_id)
    indexed = [
        {**e, 'order': i + 1}
        for i, e in enumerate(events)
    ]
    return indexed


def render_event_message(event):
    text = f"Событие: {event.name} | {event.date} {event.time}\n{event.details}"
    keyboard = event_public_action_keyboard(event.id, getattr(event, 'is_public', False))
    return text, keyboard


@router.callback_query(lambda c: c.data.startswith("event_public_"))
async def make_event_public_callback(callback: types.CallbackQuery):
    event_id = int(callback.data.removeprefix("event_public_"))
    try:
        event = await sync_to_async(Event.objects.get)(id=event_id)
        event.is_public = True
        await sync_to_async(event.save)()
        await callback.answer("Теперь это событие публичное.")
        text, markup = render_event_message(event)
        await callback.message.edit_text(text, reply_markup=markup)
    except Event.DoesNotExist:
        await callback.answer("Событие не найдено.", show_alert=True)


@router.callback_query(lambda c: c.data.startswith("event_private_"))
async def make_event_private_callback(callback: types.CallbackQuery):
    event_id = int(callback.data.removeprefix("event_private_"))
    try:
        event = await sync_to_async(Event.objects.get)(id=event_id)
        event.is_public = False
        await sync_to_async(event.save)()
        await callback.answer("Теперь это событие приватное.")
        text, markup = render_event_message(event)
        await callback.message.edit_text(text, reply_markup=markup)
    except Event.DoesNotExist:
        await callback.answer("Событие не найдено.", show_alert=True)


@router.message(Command("list_public"))
async def list_all_public_events_handler(message: types.Message):
    user_id = message.from_user.id
    events = await sync_to_async(calendar.get_public_events)(exclude_user_id=user_id)
    events = list(events)
    if not events:
        await message.answer("Публичных событий других пользователей пока нет.")
    else:
        text = "Публичные события:\n\n"
        for event in events:
            text += f"{event.name} — {event.date} {event.time}\n"
        await message.answer(text)


@router.message(Command("public_events"))
async def list_user_public_events_handler(message: types.Message):
    args = ""
    if message.text:
        args = message.text.partition(' ')[2].strip()
    if args.startswith('@'):
        try:
            target_user = await sync_to_async(User.objects.get)(username=args[1:])
        except User.DoesNotExist:
            await message.answer("Пользователь не найден.")
            return
    elif args.isdigit():
        try:
            target_user = await sync_to_async(User.objects.get)(id=int(args))
        except User.DoesNotExist:
            await message.answer("Пользователь не найден.")
            return
    else:
        await message.answer("Укажите пользователя: /public_events @username или /public_events user_id")
        return

    events = Event.objects.filter(user=target_user, is_public=True)
    if events.exists():
        text = f"Публичные события пользователя {target_user.username}:\n"
        for event in events:
            text += (
                f"\n— {event.name}, {event.date.strftime('%d.%m.%Y')} в {event.time.strftime('%H:%M')}\n"
                f"{event.details}\n"
            )
        await message.answer(text)
    else:
        await message.answer("Нет общедоступных событий у этого пользователя.")


@router.message(Command("make_public"))
async def make_public_handler(message: types.Message):
    args = ""
    if message.text:
        args = message.text.partition(' ')[2].strip()
    try:
        event_number = int(message.get_args())
        if event_number < 1:
            raise ValueError
    except (ValueError, AttributeError):
        await message.answer("Укажите корректный номер события из списка: /make_public 1")
        return

    user_id = message.from_user.id

    user_events = await sync_to_async(calendar.get_all_events)(user_id)
    user_events = list(user_events)

    if event_number > len(user_events):
        await message.answer("Событие с таким номером не найдено.")
        return

    event = user_events[event_number - 1]
    event_id = event.id

    success = await sync_to_async(calendar.make_event_public)(event_id, user_id)
    if success:
        await message.answer("Событие сделано публичным!")
    else:
        await message.answer(
            "Не удалось сделать событие публичным. Возможно, оно уже публичное или вы не являетесь его создателем.")


@router.message(F.text == "🌍 Общие события")
async def show_public_events_for_user(message: types.Message):
    await list_user_public_events_handler(message)


@router.message(F.text == "📆 Календарь: создать событие")
async def button_create_calendar_event(message: types.Message):
    telegram_id = message.from_user.id
    user_id = await calendar.get_user_db_id(telegram_id)
    if not user_id:
        await message.answer(
            "Вы не зарегистрированы. Используйте /register",
            reply_markup=main_keyboard()
        )
        return

    calendar_creation_state[telegram_id] = {"step": "name"}
    await message.answer(
        "Введите название события:",
        reply_markup=types.ReplyKeyboardRemove()
    )


@router.callback_query(lambda cq: cq.data.startswith("invite_event_"))
async def invite_event_start_callback(callback: types.CallbackQuery):
    event_id = int(callback.data.rsplit("_", 1)[-1])
    users = await get_invitable_users(event_id=event_id, exclude_user_id=callback.from_user.id)
    keyboard = get_users_invite_keyboard(event_id, users)
    await callback.message.edit_text(
        "Кого пригласить на это событие?\nВыберите пользователя:",
        reply_markup=keyboard
    )


@router.message(F.text == "📅 Календарь: список событий")
async def button_list_calendar_events(message: types.Message):
    telegram_id = message.from_user.id
    user_id = await calendar.get_user_db_id(telegram_id)
    if not user_id:
        await message.answer(
            "Вы не зарегистрированы. Используйте: /register",
            reply_markup=main_keyboard()
        )
        return

    events = await get_user_events_with_index(user_id)
    if not events:
        await message.answer("Событий пока нет.", reply_markup=main_keyboard())
        return
    lines = [
        f"{e['order']}: {e['name']} | {e['date']} {e['time']} — {e['details']}"
        for e in events
    ]
    await message.answer("Список событий:\n" + "\n".join(lines), reply_markup=main_keyboard())


@router.message(Command("calendar_list"))
async def calendar_list_handler(message: types.Message):
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
        await message.answer("Событий пока нет.", reply_markup=main_keyboard())
        return
    for e in events:
        ev = DummyEvent(
            id=str(e.get("id", e.get("order"))),
            name=str(e["name"]),
            details=str(e["details"]),
            date=datetime.strptime(str(e["date"]), '%Y-%m-%d'),
            time=datetime.strptime(str(e["time"]), '%H:%M:%S') \
                if len(str(e["time"]).split(':')) == 3 \
                else datetime.strptime(str(e["time"]), '%H:%M'),
            is_public=bool(e.get("is_public", False))
        )
        text, buttons = render_event_message(ev)
        await message.answer(text, reply_markup=buttons)


@router.message(Command("calendar_show"))
async def calendar_show_handler(message: types.Message):
    args = message.text.strip().split()
    if len(args) != 2:
        await message.answer("Используй: /calendar_show <id>", reply_markup=main_keyboard())
        return
    try:
        event_id = int(args[1])
        telegram_id = message.from_user.id
        user_id = await calendar.get_user_db_id(telegram_id)
        if not user_id:
            await message.answer(
                "Вы не зарегистрированы. Используйте /register",
                reply_markup=main_keyboard()
            )
            return

        e = await calendar.get_event(user_id, event_id)
        if not e:
            await message.answer("Событие не найдено.", reply_markup=main_keyboard())
            return
        await message.answer(
            f"Событие:\nID: {e['id']}\n"
            f"Название: {e['name']}\n"
            f"Дата: {e['date']} {e['time']}\n"
            f"Описание: {e['details']}"
        )
    except Exception:
        await message.answer("Ошибка. Проверь ID.", reply_markup=main_keyboard())


@router.message(F.text == "⬇️ Выгрузить мои события")
async def send_export_links(message: types.Message):
    base_url = "http://127.0.0.1:8000/"
    text = (
        "Выгрузить ваши события:\n"
        f"- <a href='{base_url}export/json/'>JSON</a>\n"
        f"- <a href='{base_url}export/csv/'>CSV</a>"
    )
    await message.answer(text, parse_mode='HTML')


@router.message(F.text.in_(['/выгрузить', '/export']))
async def export_events_command(message: types.Message):
    await send_export_links(message)


@router.callback_query(lambda c: c.data.startswith("edit_event_"))
async def start_edit_event_callback(callback: types.CallbackQuery):
    telegram_id = callback.from_user.id
    user_id = await calendar.get_user_db_id(telegram_id)
    if not user_id:
        await callback.message.answer("Вы не зарегистрированы. Используйте /register", reply_markup=main_keyboard())
        await callback.answer()
        return

    event_id = int(callback.data.split("_")[-1])
    event = await calendar.get_event(user_id, event_id)
    if not event:
        await callback.message.answer("Событие не найдено.", reply_markup=main_keyboard())
        await callback.answer()
        return

    calendar_edit_state[user_id] = {
        "step": "name",
        "id": event_id
    }
    await callback.message.answer(
        f"Текущее название: {event['name']}\nВведите новое название:",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await callback.answer()


@router.message(Command("calendar"))
async def user_calendar_handler(message: types.Message):
    telegram_id = message.from_user.id
    user_id = await calendar.get_user_db_id(telegram_id)
    if not user_id:
        await message.answer(
            "Вы не зарегистрированы. Используйте /register.",
            reply_markup=main_keyboard()
        )
        return
    events = await calendar.get_all_events(user_id)
    if not events:
        await message.answer("У вас нет событий.", reply_markup=main_keyboard())
        return
    lines = [
        f"{e['id']}: {e['name']} | {e['date']} {e['time']} — {e['details']}"
        for e in events
    ]
    await message.answer("Ваш календарь: \n" + "\n".join(lines), reply_markup=main_keyboard())


@router.message(F.text == "📆 Календарь")
async def show_calendar_month(message: types.Message):
    html_calendar, year, month = calendar.render_for_template()
    txt = f"Календарь за {month:02}.{year}:\n\n"
    await message.answer(txt + "(Открыть календарь на сайте: http://127.0.0.1:8000/calendar/)")


@router.message(Command("invite"))
async def command_invite_user(message: types.Message):
    args = message.text.strip().split()
    if len(args) != 5:
        await message.answer(
            "Используйте: /invite <telegram_id> <event_id> <date> <time>",
            reply_markup=main_keyboard()
        )
        return

    _, invitee_telegram_id, event_id, date, time = args
    organizer_telegram_id = message.from_user.id

    organizer = await calendar.get_user_db_id(organizer_telegram_id)
    invitee = await calendar.get_user_db_id(int(invitee_telegram_id))
    event = await sync_to_async(Event.objects.get)(id=int(event_id))

    if not (organizer and invitee and event):
        await message.answer(
            "Проверьте корректность пользователя и события.",
            reply_markup=main_keyboard()
        )
        return

    organizer_obj = await sync_to_async(User.objects.get)(id=organizer)
    invitee_obj = await sync_to_async(User.objects.get)(id=invitee)
    appt = await sync_to_async(calendar.invite_user_to_event)(
        organizer=organizer_obj,
        invitee=invitee_obj,
        event=event,
        date=date,
        time=time,
        details=f"Организатор {message.from_user.full_name}"
    )

    if not appt:
        await message.answer(
            "Этот пользователь занят в эти дату и время.",
            reply_markup=main_keyboard()
        )
        return

    bot = await get_bot()
    await bot.send_message(
        invitee_telegram_id,
        f"Вас пригласили на событие '{event.name}' {date} в {time}.",
        reply_markup=get_invite_keyboard(appt.id)
    )

    await message.answer(
        f"Приглашение отправлено! Ожидаем ответа.\nID встречи: {appt.id}",
        reply_markup=main_keyboard()
    )
