from aiogram import F, Router, types, Bot
from aiogram.filters import Command
from bot.calendar_instance import calendar
from datetime import datetime

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from calendarapp.models import User, Event, Appointment
from asgiref.sync import sync_to_async

import logging

logger = logging.getLogger(__name__)

router = Router()


def get_bot():
    from bot.loader import bot
    return bot


def get_appointment_model():
    from calendarapp.models import User, Event, Appointment
    return User, Event, Appointment


def main_keyboard():
    keyboard = [
        [
            types.KeyboardButton(text="📆 Календарь")
        ],

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


def get_invite_keyboard(event_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="➕ Пригласить", callback_data=f"invite_event_{event_id}")
        ]]
    )


def get_users_invite_keyboard(event_id, exclude_user_id):
    users = list(User.objects.exclude(telegram_id=exclude_user_id))
    inline_keyboard = []

    for i in range(0, len(users), 2):
        row = [
            InlineKeyboardButton(
                text=users[i].username or f"ID {users[i].telegram_id}",
                callback_data=f"invite_{event_id}_{users[i].telegram_id}",
            )
        ]
        if i + 1 < len(users):
            row.append(
                InlineKeyboardButton(
                    text=users[i + 1].username or f"ID {users[i + 1].telegram_id}",
                    callback_data=f"invite_{event_id}_{users[i + 1].telegram_id}",
                )
            )
        inline_keyboard.append(row)
    inline_keyboard.append([InlineKeyboardButton(text="Готово", callback_data="invite_done")])

    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)


def appointment_action_keyboard(appointment_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Подтвердить", callback_data=f"appt_confirm_{appointment_id}")],
        [InlineKeyboardButton(text="Отклонить", callback_data=f"appt_cancel_{appointment_id}")]
    ])


async def get_user_events_with_index(user_id):
    events = await calendar.get_all_events(user_id)
    indexed = [
        {**e, 'order': i + 1}
        for i, e in enumerate(events)
    ]
    return indexed


@sync_to_async
def get_appointment_by_id(app_id):
    return Appointment.objects.get(pk=app_id)


@sync_to_async
def update_appointment_status(app_id, new_status):
    appointment = Appointment.objects.get(pk=app_id)
    appointment.status = new_status
    appointment.save()
    return appointment


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
    await message.answer("Ваш календарь:\n" + "\n".join(lines), reply_markup=main_keyboard())


@router.message(F.text == "📆 Календарь")
async def show_calendar_month(message: types.Message, bot: Bot):
    html_calendar, year, month = calendar.render_for_template()
    txt = f"Календарь за {month:02}.{year}:\n\n"
    await message.answer(txt + "(Открыть общий календарь на сайте: https://your-domain/calendar/)")


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

    # Получаем пользователей
    organizer = await calendar.get_user_db_id(organizer_telegram_id)
    invitee = await calendar.get_user_db_id(int(invitee_telegram_id))
    event = await sync_to_async(Event.objects.get)(id=int(event_id))

    if not (organizer and invitee and event):
        await message.answer(
            "Проверьте корректность пользователя и события.",
            reply_markup=main_keyboard()
        )
        return

    # Получаем объекты User
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

    # Отправляем сообщения
    bot = get_bot()
    await bot.send_message(
        invitee_telegram_id,
        f"Вас пригласили на событие '{event.name}' {date} в {time}.",
        reply_markup=get_invite_keyboard(appt.id)
    )

    await message.answer(
        f"Приглашение отправлено! Ожидаем ответа.\nID встречи: {appt.id}",
        reply_markup=main_keyboard()
    )


@router.message(Command("myappointments"))
async def list_my_appointments(message: types.Message):
    telegram_id = message.from_user.id
    user_id = await calendar.get_user_db_id(telegram_id)
    if not user_id:
        await message.answer(
            "Вы не зарегистрированы. Используйте /register",
            reply_markup=main_keyboard()
        )
        return
    user = await sync_to_async(User.objects.get)(id=user_id)
    qs = await calendar.get_busy_appointments(user)
    if not qs:
        await message.answer("Встреч не найдено", reply_markup=main_keyboard())
        return
    lines = [
        f"Дата: {a['date']} {a['time']}, статус: {a['status']}, event_id: {a['event_id']}"
        for a in qs
    ]
    await message.answer("Ваши встречи:\n" + "\n".join(lines))


@router.message(Command("pendingappointments"))
async def list_pending_appointments(message: types.Message):
    telegram_id = message.from_user.id
    invitee = await calendar.get_user_db_id(telegram_id)
    if not invitee:
        await message.answer("Вы не зарегистрированы.", reply_markup=main_keyboard())
        return
    pending = await sync_to_async(lambda: list(Appointment.objects.filter(invitee=invitee, status='pending').all()))()
    if not pending:
        await message.answer("Нет ожидающих встреч.", reply_markup=main_keyboard())
        return
    for appt in pending:
        event = appt.event
        await message.answer(
            f"Встреча от {appt.organizer.username or appt.organizer.telegram_id}\n"
            f"Событие: {event.name}\n"
            f"Дата: {appt.date} {appt.time}\n"
            f"Описание: {appt.details}",
            reply_markup=appointment_action_keyboard(appt.id)
        )


@router.callback_query()
async def appointment_action_callback(callback: types.CallbackQuery):
    data = callback.data
    bot = get_bot()

    if data.startswith("appointment_accept:"):
        appointment_id = int(data.split(":")[1])
        appointment = await sync_to_async(Appointment.objects.filter(id=appointment_id).first)()
        if not appointment or appointment.status != "pending":
            await callback.answer("Приглашение уже неактуально.", show_alert=True)
            return
        appointment.status = "confirmed"
        await sync_to_async(appointment.save)()
        await callback.message.edit_text("Вы приняли приглашение.")
        await bot.send_message(
            appointment.organizer.telegram_id,
            f"{appointment.invitee.username} принял приглашение на \"{appointment.event.name}\"."
        )
        await callback.answer("Вы приняли приглашение.")
        return

    if data.startswith("appointment_decline:"):
        appointment_id = int(data.split(":")[1])
        appointment = await sync_to_async(Appointment.objects.filter(id=appointment_id).first)()
        if not appointment or appointment.status != "pending":
            await callback.answer("Приглашение уже неактуально.", show_alert=True)
            return
        appointment.status = "cancelled"
        await sync_to_async(appointment.save)()
        await callback.message.edit_text("Вы отклонили приглашение.")
        await bot.send_message(
            appointment.organizer.telegram_id,
            f"{appointment.invitee.username} отклонил приглашение на \"{appointment.event.name}\"."
        )
        await callback.answer("Вы отклонили приглашение.")
        return

    appt_id = int(data.split("_")[-1])
    try:
        appt = await sync_to_async(Appointment.objects.get)(id=appt_id)
    except Appointment.DoesNotExist:
        appt = None

    if not appt:
        await callback.answer("Встреча не найдена.", show_alert=True)
        return

    if callback.from_user.id != appt.invitee.telegram_id:
        await callback.answer(
            "Только приглашённый может подтвердить/отклонить встречу.",
            reply_markup=main_keyboard(),
            show_alert=True
        )
        return

    if "confirm" in data:
        appt.status = "confirmed"
        await sync_to_async(appt.save)()
        await callback.message.edit_text("Встреча подтверждена!")
    elif "cancel" in data:
        appt.status = "cancelled"
        await sync_to_async(appt.save)()
        await callback.message.edit_text("Встреча отменена!")


async def invite_user_handler(message, organizer, invitee, event):
    appointment = await sync_to_async(calendar.invite_user_to_event)(organizer, invitee, event)

    if not appointment:
        await message.answer("Пользователь уже приглашён или приглашение активно.")
        return

    bot = get_bot()
    await bot.send_message(
        invitee.telegram_id,
        f"Вас пригласили на событие '{event.name}' {event.date} в {event.time}.",
        reply_markup=get_invite_keyboard(appointment.id)
    )
    await message.answer(
        f"Приглашение отправлено {invitee.username}.",
        reply_markup=main_keyboard()
    )


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


async def offer_invite_after_event(message, event_id):
    telegram_id = message.from_user.id
    keyboard = get_users_invite_keyboard(event_id, exclude_user_id=telegram_id)
    await message.answer(
        "Событие создано! Кого пригласить?\n\nВыберите пользователя:",
        reply_markup=keyboard
    )


async def process_calendar_creation(message: types.Message):
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
                reply_markup=get_invite_keyboard(event_id)
            )
            await offer_invite_after_event(message, event_id)
        except Exception:
            await message.answer(
                "Ошибка в данных события. Попробуйте создать событие заново.",
                reply_markup=main_keyboard()
            )
        calendar_creation_state.pop(telegram_id, None)


@router.callback_query(lambda cq: cq.data.startswith("invite_event_"))
async def invite_event_start_callback(callback_query: types.CallbackQuery):
    # Открываем выбор пользователей по событию
    _, _, event_id = callback_query.data.split("_")
    telegram_id = callback_query.from_user.id
    keyboard = get_users_invite_keyboard(event_id, exclude_user_id=telegram_id)
    await callback_query.message.edit_text(
        "Выберите, кого пригласить:", reply_markup=keyboard
    )


@router.callback_query(lambda cq: cq.data.startswith("invite_"))
async def invite_user_callback(callback_query: types.CallbackQuery):
    data = callback_query.data
    if data == "invite_done":
        await callback_query.message.edit_text(
            "Приглашение завершено!", reply_markup=None
        )
        # Если нужно вернуть обычную клавиатуру, отправляй новое сообщение:
        await callback_query.message.answer(
            "Вы вернулись в главное меню.",
            reply_markup=main_keyboard()
        )
        return

    _, event_id, invitee_tg_id = data.split("_")
    organizer_tg_id = callback_query.from_user.id
    event = await sync_to_async(Event.objects.get)(id=event_id)
    organizer = await sync_to_async(User.objects.get)(telegram_id=organizer_tg_id)
    invitee = await sync_to_async(User.objects.get)(telegram_id=invitee_tg_id)

    appointment = await sync_to_async(calendar.invite_user_to_event)(
        organizer, invitee, event
    )

    if not appointment:
        await callback_query.answer("Пользователь уже приглашён или приглашение активно.", show_alert=True)
    else:
        # Оповещение приглашённого
        bot = get_bot()
        await bot.send_message(
            invitee.telegram_id,
            f"Вас пригласили на событие '{event.name}' {event.date} в {event.time}.",
            reply_markup=get_invite_keyboard(appointment.id)
        )
        await callback_query.answer(f"{invitee.username} приглашён!", show_alert=True)

    # Повторное отображение клавиатуры для выбора других
    keyboard = get_users_invite_keyboard(event.id, exclude_user_id=organizer_tg_id)
    await callback_query.message.edit_text(
        "Можно пригласить ещё пользователей:", reply_markup=keyboard
    )


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


async def calendar_create_handler(message: types.Message):
    await send_welcome(message)


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
    lines = [f"{e['order']}: {e['name']} | {e['date']} {e['time']} — {e['details']}" for e in events]
    await message.answer("Список событий:\n" + "\n".join(lines))


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


async def calendar_edit_handler(message: types.Message):
    telegram_id = message.from_user.id
    user_id = await calendar.get_user_db_id(telegram_id)
    if not user_id:
        await message.answer(
            "Вы не зарегистрированы. Используйте /register",
            reply_markup=main_keyboard()
        )
        return

    args = message.text.strip().split(maxsplit=5)
    if len(args) < 6:
        await message.answer(
            "Используй: /calendar_edit <id> <название> <дата> <время> <описание>",
            reply_markup=main_keyboard()
        )
        return
    try:
        _, event_id, name, date, time, details = args
        event_id = int(event_id)
        result = await calendar.edit_event(user_id, event_id, name, date, time, details)
        if result:
            await message.answer("Событие обновлено.", reply_markup=main_keyboard())
        else:
            await message.answer("Событие не найдено.", reply_markup=main_keyboard())
    except Exception:
        await message.answer("Ошибка. Проверь параметры.", reply_markup=main_keyboard())


async def calendar_delete_handler(message: types.Message):
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
        # Получаем все события пользователя с их номерами
        events = await get_user_events_with_index(user_id)
        num = int(args[1])
        if not (1 <= num <= len(events)):
            await message.answer("Некорректный номер. Попробуйте снова.", reply_markup=main_keyboard())
            return
        event_id = events[num - 1]["id"]
        result = await calendar.delete_event(user_id, event_id)
        if result:
            await message.answer("Событие удалено.", reply_markup=main_keyboard())
        else:
            await message.answer("Событие не найдено.", reply_markup=main_keyboard())
    except Exception:
        await message.answer("Ошибка. Проверьте номер.", reply_markup=main_keyboard())


calendar_delete_state = {}


async def button_delete_calendar_event(message: types.Message):
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
        await message.answer("У вас нет событий для удаления.", reply_markup=main_keyboard())
        return

    lines = [f"{e['order']}: {e['name']} | {e['date']} {e['time']} — {e['details']}" for e in events]
    calendar_delete_state[telegram_id] = events  # сохраняем события пользователя
    await message.answer(
        "Введите номер события, которое хотите удалить:\n" + "\n".join(lines),
        reply_markup=types.ReplyKeyboardRemove()
    )


async def process_calendar_deletion(message: types.Message):
    telegram_id = message.from_user.id
    user_id = await calendar.get_user_db_id(telegram_id)
    if not user_id or telegram_id not in calendar_delete_state:
        await message.answer(
            "Вы не зарегистрированы. Используйте /register",
            reply_markup=main_keyboard()
        )
        return

    events = calendar_delete_state.get(telegram_id)
    try:
        num = int(message.text.strip())
        await message.answer(f"DEBUG: num={num}, len={len(events)}; events orders: {[e['order'] for e in events]}")
        if not (1 <= num <= len(events)):
            raise ValueError
        event_id = events[num - 1]["id"]
        await message.answer(
            f"DEBUG: Telegram ID: {telegram_id}, User DB ID: {user_id}, "
            f"Удаляем event_id={event_id}, num={num}, всего событий={len(events)}"
        )
        result = await calendar.delete_event(user_id, event_id)
        if result:
            await message.answer("Событие удалено.", reply_markup=main_keyboard())
            calendar_delete_state.pop(telegram_id, None)
        else:
            await message.answer("Событие не найдено.", reply_markup=main_keyboard())
            calendar_delete_state.pop(telegram_id, None)
    except Exception:
        lines = [
            f"{e['order']}: {e['name']} | {e['date']} {e['time']} — {e['details']}" for e in events
        ]
        await message.answer(
            "Некорректный номер. Попробуйте снова.\n\n"
            + "\n".join(lines)
        )


calendar_edit_state = {}


async def button_edit_calendar_event(message: types.Message):
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


async def process_calendar_editing_by_number(message: types.Message):
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
            await message.answer("Событие изменено!", reply_markup=main_keyboard())
        else:
            await message.answer("Событие не найдено.", reply_markup=main_keyboard())
        calendar_edit_state.pop(telegram_id, None)


def register_handlers(router: Router):
    router.message.register(send_welcome, Command("start"))
    router.message.register(register_user_handler, Command("register"))
    router.message.register(user_calendar_handler, Command("calendar"))
    router.message.register(button_create_calendar_event, F.text == "📆 Календарь: создать событие")
    router.message.register(button_list_calendar_events, F.text == "📅 Календарь: список событий")
    router.message.register(process_calendar_creation,
                            lambda msg: calendar_creation_state.get(msg.from_user.id) is not None)
    router.message.register(button_edit_calendar_event, F.text == "📆 Календарь: изменить событие")
    router.message.register(process_calendar_editing_by_number,
                            lambda msg: calendar_edit_state.get(msg.from_user.id) is not None)

    router.message.register(calendar_create_handler, Command("calendar_create"))
    router.message.register(calendar_list_handler, Command("calendar_list"))
    router.message.register(calendar_show_handler, Command("calendar_show"))
    router.message.register(calendar_edit_handler, Command("calendar_edit"))
    router.message.register(calendar_delete_handler, Command("calendar_delete"))
    router.message.register(button_delete_calendar_event, F.text == "📆 Календарь: удалить событие")
    router.message.register(process_calendar_deletion,
                            lambda msg: calendar_delete_state.get(msg.from_user.id) is not None)
    router.message.register(command_invite_user, Command("invite"))
    router.message.register(list_my_appointments, Command("myappointments"))
    router.message.register(list_pending_appointments, Command("pendingappointments"))
    router.callback_query.register(appointment_action_callback,
                                   lambda c: c.data.startswith("appt_confirm_") or c.data.startswith("appt_cancel_"))
