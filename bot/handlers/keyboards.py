from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram import types
from calendarapp.models import User
from asgiref.sync import sync_to_async


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
        [
            types.KeyboardButton(text="🌍 Общие события"),
            types.KeyboardButton(text="⬇️ Выгрузить мои события"),
        ],
    ]
    return types.ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def get_invite_keyboard(event_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="➕ Пригласить", callback_data=f"invite_event_{event_id}")
        ]]
    )


def get_users_invite_keyboard(event_id, users):
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


async def get_invitable_users(exclude_user_id):
    return list(await sync_to_async(
        lambda: list(User.objects.exclude(telegram_id=exclude_user_id))
    )())


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
