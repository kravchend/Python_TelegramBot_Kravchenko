from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram import types
from calendarapp.models import User, Appointment
from asgiref.sync import sync_to_async


def main_keyboard():
    keyboard = [
        [
            types.KeyboardButton(text="📆 Календарь"),
            types.KeyboardButton(text="🔎 Статус приглашений"),
        ],
        [
            types.KeyboardButton(text="📆 Календарь: создать событие"),
            types.KeyboardButton(text="📅 Календарь: список событий"),
        ],
        [
            types.KeyboardButton(text="📆 Календарь: изменить событие"),
            types.KeyboardButton(text="📆 Календарь: удалить событие"),
        ],
        [
            types.KeyboardButton(text="🌍 Общие события"),
            types.KeyboardButton(text="⬇️ Выгрузить мои события"),
        ],
    ]
    # Добавляем параметр is_persistent=True, чтобы клавиатура была закрепленной
    return types.ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True, is_persistent=True)


def get_invite_keyboard(event_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="➕ Пригласить", callback_data=f"invite_event_{event_id}")
        ]]
    )


def get_users_invite_keyboard(event_id, users):
    inline_keyboard = []
    for i in range(0, len(users), 2):
        row = []
        for j in range(2):
            if i + j < len(users):
                user = users[i + j]
                label = user.username if user.username else f"ID {user.telegram_id}"
                row.append(
                    InlineKeyboardButton(
                        text=label,
                        callback_data=f"invite_{event_id}_{user.telegram_id}",
                    )
                )
        inline_keyboard.append(row)
    inline_keyboard.append([InlineKeyboardButton(text="Готово", callback_data="invite_done")])

    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)


async def get_invitable_users(event_id, exclude_user_id):
    def query():
        already_invited = Appointment.objects.filter(
            event_id=event_id,
            status__in=["pending", "confirmed"]
        ).values_list("invitee__telegram_id", flat=True)

        return User.objects.filter(telegram_id__isnull=False).exclude(
            telegram_id=exclude_user_id
        ).exclude(
            telegram_id__in=already_invited
        )

    return list(await sync_to_async(lambda: list(query()))())


def event_public_action_keyboard(event_id, is_public):
    if is_public:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔒 Сделать приватным", callback_data=f"event_private_{event_id}")]
        ])
    else:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🌐 Сделать публичным", callback_data=f"event_public_{event_id}")]
        ])


def appointment_action_keyboard(appointment_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"appt_confirm_{appointment_id}")],
        [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"appt_cancel_{appointment_id}")]
    ])
