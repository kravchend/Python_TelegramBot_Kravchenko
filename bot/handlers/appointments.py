from aiogram.filters import Command
from aiogram import types, Router
from bot.handlers.keyboards import (
    main_keyboard, appointment_action_keyboard,
    get_users_invite_keyboard, get_invitable_users)
from asgiref.sync import sync_to_async
from bot.calendar_instance import calendar
from calendarapp.models import User, Event, Appointment
from bot.handlers.users import get_bot
from calendarapp.utils import send_invitation_to_user
from aiogram.exceptions import TelegramBadRequest

import logging

logger = logging.getLogger(__name__)

router = Router()


##### СТАТУС ПРИГЛАШЕНИЙ #####
@router.message(lambda message: message.text == "🔍  Статус приглашений")
async def status_button_handler(message: types.Message):
    await display_status(message)


@router.message(Command("status"))
async def display_status(message: types.Message):
    telegram_id = message.from_user.id
    user_id = await calendar.get_user_db_id(telegram_id)

    if not user_id:
        await message.answer("ℹ️ Зарегистрируйтесь:\ncommand: '/register'", reply_markup=main_keyboard())
        return

    invitee_appointments = await sync_to_async(lambda: list(
        Appointment.objects.filter(invitee_id=user_id).select_related('event', 'organizer')
    ))()

    organizer_appointments = await sync_to_async(lambda: list(
        Appointment.objects.filter(organizer_id=user_id).select_related('event', 'invitee')
    ))()

    status_display = {
        "pending": "⏳ Ожидание подтверждения",
        "confirmed": "✅ Подтверждённое",
        "cancelled": "❌ Отклонённое"
    }

    for appt in invitee_appointments:
        event = appt.event
        organizer = appt.organizer
        text = (
            f" 👤 {organizer.username}\n"
            f" 🔹 {event.name}\n"
            f" 🕒 {event.date} {event.time.strftime('%H:%M')}\n"
            f" 👉{status_display.get(appt.status, '❓ Неизвестно')}"
        )
        if appt.status == "pending":
            keyboard = appointment_action_keyboard(appt.id)
            await message.answer(text, reply_markup=keyboard)
        else:
            await message.answer(text)

    if organizer_appointments:
        text = "✨🗽 Вы организатор\n\n"
        for appt in organizer_appointments:
            event = appt.event
            invitee = appt.invitee
            text += (
                f" 🔹 {event.name}"
                f" 🕒 {event.date} {event.time.strftime('%H:%M')}\n"
                f" 🧑‍🤝‍🧑 {invitee.username}\n"
                f" 👉 {status_display.get(appt.status, '🤷 Неизвестно')}\n\n"
            )
        await message.answer(text, reply_markup=main_keyboard())

    if not invitee_appointments and not organizer_appointments:
        await message.answer("🔔 Нет встреч или приглашений.", reply_markup=main_keyboard())


@router.callback_query(lambda cq: cq.data.startswith("invite_"))
async def invite_user_callback(callback_query: types.CallbackQuery):
    data = callback_query.data

    if data == "invite_done":
        # await callback_query.message.edit_text(
        #     "✅ Приглашение завершено!", reply_markup=None
        # )
        await callback_query.message.answer(
            "✅ Приглашение завершено!",
            reply_markup=main_keyboard(),
        )
        return

    parts = data.split("_")
    if len(parts) != 3:
        await callback_query.answer(" ⛔ Некорректный формат кнопки!", show_alert=True)
        return

    _, event_id, invitee_tg_id = parts

    try:
        event_id = int(event_id)
        invitee_tg_id = int(invitee_tg_id)
        organizer_tg_id = callback_query.from_user.id

        event = await sync_to_async(Event.objects.get)(id=event_id)
        organizer = await sync_to_async(User.objects.get)(telegram_id=organizer_tg_id)
        invitee = await sync_to_async(User.objects.get)(telegram_id=invitee_tg_id)

        appointment = await sync_to_async(lambda: Appointment.objects.filter(
            event=event,
            invitee=invitee
        ).first())()

        if appointment and appointment.status in ["pending", "confirmed"]:
            await callback_query.answer(
                f"⚠️ {invitee.username} уже приглашен",
                show_alert=True
            )
            return

        if not appointment or appointment.status == "cancelled":
            appointment = await sync_to_async(Appointment.objects.create)(
                event=event,
                organizer=organizer,
                invitee=invitee,
                date=event.date,
                time=event.time,
                status="pending",
            )

        result = await send_invitation_to_user(invitee, event, appointment)

        if result == "SENT":
            await callback_query.answer(f"{invitee.username} приглашён в Telegram!", show_alert=True)
        else:
            await callback_query.answer(
                f"{invitee.username} получил уведомление через сайт.",
                show_alert=True,
                reply_markup = main_keyboard(),
            )

        users = await get_invitable_users(event_id=event_id, exclude_user_id=organizer_tg_id)
        if not users:
            await callback_query.message.answer(
                "Все пользователи приглашены! Спасибо.",
                reply_markup=main_keyboard(),
            )

        else:
            keyboard = get_users_invite_keyboard(event.id, users)
            await callback_query.message.edit_text(
                "Кого пригласить на это событие? Выберите пользователя:",
                reply_markup=keyboard
            )

    except Exception as e:
        logger.error(f"Ошибка при обработке callback: {e}")
        await callback_query.answer(f"Ошибка: {e}", show_alert=True)


@router.callback_query(lambda cq: cq.data.startswith("appt_confirm_") or cq.data.startswith("appt_cancel_"))
async def appointment_action_callback(callback: types.CallbackQuery):
    bot = await get_bot()
    data = callback.data

    logger.debug(f"Получен callback: {data}")

    try:
        if data.startswith("appt_confirm_"):
            appointment_id = int(data.replace("appt_confirm_", ""))
            action = "confirmed"
            participant_action_text = "Вы подтвердили участие в событии!"
            organizer_action_text = "подтвердил"
        elif data.startswith("appt_cancel_"):
            appointment_id = int(data.replace("appt_cancel_", ""))
            action = "cancelled"
            participant_action_text = "Вы отклонили приглашение на событие!"
            organizer_action_text = "отклонил"
        else:
            raise ValueError("Некорректный формат данных.")

        appointment = await sync_to_async(Appointment.objects.get)(id=appointment_id)
        invitee_telegram_id = await sync_to_async(lambda: appointment.invitee.telegram_id)()

        if callback.from_user.id != invitee_telegram_id:
            await callback.answer("Только приглашённый может выполнить это действие.", show_alert=True)
            return

        def update_status():
            appointment.status = action
            appointment.save()

        await sync_to_async(update_status)()

        organizer_telegram_id = await sync_to_async(lambda: appointment.organizer.telegram_id)()
        invitee_username = await sync_to_async(lambda: appointment.invitee.username)()
        event_name = await sync_to_async(lambda: appointment.event.name)()

        if organizer_telegram_id:
            organizer_message = (
                f"⏳ Пользователь {invitee_username} {organizer_action_text} "
                f"приглашение на событие \"{event_name}\"."
            )
            try:
                await bot.send_message(organizer_telegram_id, organizer_message)
            except TelegramBadRequest as e:
                logger.error(
                    f"Ошибка отправки уведомления организатору (Telegram ID {organizer_telegram_id}): {e}"
                )

        await callback.message.edit_text(participant_action_text)
        await callback.answer(participant_action_text)

    except Appointment.DoesNotExist:
        await callback.answer("❓Встреча не найдена.", show_alert=True)
    except ValueError as e:
        await callback.answer("⛔Некорректные данные.", show_alert=True)
    except TelegramBadRequest as e:
        logger.error(f"Ошибка отправки сообщения: {e}")
        await callback.answer("⚠️ Ошибка отправки сообщения.\n\nВозможно, пользователь заблокировал бота.", show_alert=True)
    except Exception as e:
        logger.error(f"Ошибка обработки callback: {e}")
        await callback.answer("❗\nПроизошла ошибка.\nПопробуйте позже.", show_alert=True)


@sync_to_async
def update_appointment_status(app_id, new_status):
    appointment = Appointment.objects.get(pk=app_id)
    appointment.status = new_status
    appointment.save()
    return appointment


@sync_to_async
def get_appointment_by_id(app_id):
    return Appointment.objects.get(pk=app_id)
