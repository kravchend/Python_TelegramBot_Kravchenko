from aiogram.filters import Command
from aiogram import types, Router
from bot.handlers.keyboards import (
    main_keyboard, appointment_action_keyboard,
    get_invite_keyboard, get_users_invite_keyboard, get_invitable_users)
from asgiref.sync import sync_to_async
from bot.calendar_instance import calendar
from calendarapp.models import User, Event, Appointment
from bot.handlers.users import get_bot

router = Router()


def get_appointment_model():
    from calendarapp.models import User, Event, Appointment
    return User, Event, Appointment


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


async def invite_user_handler(message, organizer, invitee, event):
    appointment = await sync_to_async(calendar.invite_user_to_event)(
        organizer, invitee, event, event.date, event.time, event.details
    )
    if not appointment:
        await message.answer("Пользователь уже приглашён или приглашение активно.")
        return

    bot = await get_bot()
    await bot.send_message(
        invitee.telegram_id,
        f"Вас пригласили на событие '{event.name}' {event.date} в {event.time}.",
        reply_markup=get_invite_keyboard(appointment.id)
    )
    await message.answer(
        f"Приглашение отправлено {invitee.username}.",
        reply_markup=main_keyboard()
    )


async def offer_invite_after_event(message, event_id):
    telegram_id = message.from_user.id
    users = await get_invitable_users(event_id=event_id, exclude_user_id=telegram_id)
    keyboard = get_users_invite_keyboard(event_id, users)
    await message.answer(
        "Событие создано! Кого пригласить?\n\nВыберите пользователя:",
        reply_markup=keyboard
    )


@router.callback_query(lambda cq: cq.data.startswith("invite_"))
async def invite_user_callback(callback_query: types.CallbackQuery):
    print("DEBUG: Callback data:", callback_query.data)
    data = callback_query.data
    if data == "invite_done":
        await callback_query.message.edit_text(
            "Приглашение завершено!", reply_markup=None
        )
        await callback_query.message.answer(
            "Вы вернулись в главное меню.",
            reply_markup=main_keyboard()
        )
        return

    parts = data.split("_")

    if len(parts) != 3:
        await callback_query.answer("Некорректный формат кнопки!", show_alert=True)
        return

    _, event_id, invitee_tg_id = parts
    try:
        event_id = int(event_id)
        invitee_tg_id = int(invitee_tg_id)
        organizer_tg_id = callback_query.from_user.id

        event = await sync_to_async(Event.objects.get)(id=event_id)
        organizer = await sync_to_async(User.objects.get)(telegram_id=organizer_tg_id)
        invitee = await sync_to_async(User.objects.get)(telegram_id=invitee_tg_id)
        exist = await sync_to_async(Appointment.objects.filter)(
            event=event,
            invitee=invitee,
            status__in=["pending", "confirmed"]
        )
        exist = await sync_to_async(exist.exists)()
        if exist:
            await callback_query.answer(
                "Пользователь уже приглашён или приглашение активно.",
                show_alert=True
            )
        else:
            appointment = await sync_to_async(Appointment.objects.create)(
                event=event,
                organizer=organizer,
                invitee=invitee,
                date=event.date,
                time=getattr(event, 'time', None),
                status="pending"
            )
            bot = await get_bot()
            await bot.send_message(
                invitee.telegram_id,
                f"Вас пригласили на событие '{event.name}' {event.date} в {event.time}.",
                reply_markup=appointment_action_keyboard(appointment.id)
            )
            await callback_query.answer(f"{invitee.username} приглашён!", show_alert=True)

        users = await get_invitable_users(event_id=event_id, exclude_user_id=organizer_tg_id)
        keyboard = get_users_invite_keyboard(event.id, users)
        await callback_query.message.edit_text(
            "Можно пригласить ещё пользователей:", reply_markup=keyboard
        )
    except Exception as e:
        await callback_query.answer(f"Ошибка: {e}", show_alert=True)


@router.callback_query(lambda cq: cq.data.startswith("appt_confirm_") or cq.data.startswith("appt_cancel_"))
async def appointment_action_callback(callback: types.CallbackQuery):
    bot = await get_bot()
    data = callback.data

    if data.startswith("appt_confirm_"):
        appointment_id = int(data.replace("appt_confirm_", ""))
        action = "confirmed"
        text = "Встреча подтверждена!"
    elif data.startswith("appt_cancel_"):
        appointment_id = int(data.replace("appt_cancel_", ""))
        action = "cancelled"
        text = "Встреча отменена!"
    else:
        await callback.answer("Некорректный формат данных встречи.", show_alert=True)
        return

    @sync_to_async
    def get_appointment(appt_id):
        try:
            return Appointment.objects.get(id=appt_id)
        except Appointment.DoesNotExist:
            return None

    appointment = await get_appointment(appointment_id)

    if not appointment:
        await callback.answer("Встреча не найдена.", show_alert=True)
        return

    # ВАЖНО!!! загружаем связанного пользователя в отдельном потоке
    invitee = await sync_to_async(lambda: appointment.invitee)()
    organizer = await sync_to_async(lambda: appointment.organizer)()
    event = await sync_to_async(lambda: appointment.event)()
    invitee_telegram_id = invitee.telegram_id
    organizer_telegram_id = organizer.telegram_id
    invitee_username = invitee.username

    if callback.from_user.id != invitee_telegram_id:
        await callback.answer(
            "Только приглашённый может подтвердить/отклонить встречу.",
            show_alert=True
        )
        return

    if appointment.status != "pending":
        await callback.answer("Приглашение уже неактуально.", show_alert=True)
        return

    appointment.status = action
    await sync_to_async(appointment.save)()
    await callback.message.edit_text(text)

    try:
        await bot.send_message(
            organizer_telegram_id,
            f"{invitee_username or 'Пользователь'} "
            f"{'подтвердил' if action == 'confirmed' else 'отклонил'} приглашение на \"{event.name}\"."
        )
    except Exception as e:
        print("Не удалось отправить уведомление организатору:", e)

    await callback.answer(text)


@sync_to_async
def update_appointment_status(app_id, new_status):
    appointment = Appointment.objects.get(pk=app_id)
    appointment.status = new_status
    appointment.save()
    return appointment


@sync_to_async
def get_appointment_by_id(app_id):
    return Appointment.objects.get(pk=app_id)


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
