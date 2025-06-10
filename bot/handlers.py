from asgiref.sync import sync_to_async
from calendarapp.models import Note

from aiogram import types, Dispatcher, F
from aiogram.filters import Command


def main_keyboard():
    keyboard = [
        [types.KeyboardButton(text="Создать заметку")],
        [types.KeyboardButton(text="Показать мои заметки")],
        [types.KeyboardButton(text="Показать отсортированные заметки")],
    ]
    return types.ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


@sync_to_async
def db_add_note(user_id, text):
    Note.objects.create(user_id=user_id, text=text)


@sync_to_async
def db_get_notes(user_id):
    return list(Note.objects.filter(user_id=user_id).order_by("created_at"))


@sync_to_async
def db_get_sorted_notes(user_id):
    return list(Note.objects.filter(user_id=user_id).order_by("text"))


@sync_to_async
def db_delete_note(user_id, note_id):
    Note.objects.filter(user_id=user_id, id=note_id).delete()


@sync_to_async
def db_update_note(user_id, note_id, new_text):
    Note.objects.filter(user_id=user_id, id=note_id).update(text=new_text)


async def send_welcome(message: types.Message):
    full_name = message.from_user.full_name
    await message.answer(
        f"Привет, {full_name}! Я твой бот для заметок.",
        reply_markup=main_keyboard()
    )


async def button_create_note(message: types.Message):
    await message.answer("Введите текст новой заметки:", reply_markup=types.ReplyKeyboardRemove())


async def save_new_note(message: types.Message):
    user_id = message.from_user.id
    note_text = message.text.strip()
    if not note_text:
        await message.answer("Заметка не может быть пустой. Попробуйте еще раз.")
        return
    await db_add_note(user_id, note_text)
    await message.answer("Заметка сохранена!", reply_markup=main_keyboard())


async def button_list_notes(message: types.Message):
    user_id = message.from_user.id
    notes = await db_get_notes(user_id)
    if not notes:
        await message.answer("У вас пока нет заметок.", reply_markup=main_keyboard())
        return
    notes_str = '\n'.join([f"{idx + 1}. {note.text}" for idx, note in enumerate(notes)])
    await message.answer(f"Ваши заметки:\n{notes_str}", reply_markup=notes_inline_keyboard(notes))


def notes_inline_keyboard(notes):
    buttons = [
        [
            types.InlineKeyboardButton(text=f"✏️ {idx + 1}", callback_data=f"edit_{note.id}"),
            types.InlineKeyboardButton(text=f"🗑 {idx + 1}", callback_data=f"del_{note.id}")
        ]
        for idx, note in enumerate(notes)
    ]
    return types.InlineKeyboardMarkup(inline_keyboard=buttons)


async def button_list_sorted_notes(message: types.Message):
    user_id = message.from_user.id
    notes = await db_get_sorted_notes(user_id)
    if not notes:
        await message.answer("У вас пока нет заметок.", reply_markup=main_keyboard())
        return
    notes_str = '\n'.join([f"{idx + 1}. {note.text}" for idx, note in enumerate(notes)])
    await message.answer(f"Ваши заметки (отсортированы):\n{notes_str}", reply_markup=notes_inline_keyboard(notes))


async def delete_callback_handler(callback: types.CallbackQuery):
    note_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    await db_delete_note(user_id, note_id)
    await callback.message.edit_text('Заметка удалена.')
    await callback.answer()


edit_states = {}


async def edit_callback_handler(callback: types.CallbackQuery):
    note_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    edit_states[user_id] = note_id
    await callback.message.answer(
        f'Введите новый текст для выбранной заметки:',
        reply_markup=types.ReplyKeyboardRemove()
    )
    await callback.answer()


async def save_edited_note(message: types.Message):
    user_id = message.from_user.id
    if user_id in edit_states:
        note_id = edit_states[user_id]
        new_text = message.text.strip()
        await db_update_note(user_id, note_id, new_text)
        await message.answer("Заметка обновлена.", reply_markup=main_keyboard())
        del edit_states[user_id]
    else:
        await message.answer("Нет редактируемой заметки.", reply_markup=main_keyboard())


def register_handlers(dp: Dispatcher):
    dp.message.register(send_welcome, Command("start"))
    dp.message.register(button_create_note, F.text == "Создать заметку")
    dp.message.register(button_list_notes, F.text == "Показать мои заметки")
    dp.message.register(button_list_sorted_notes, F.text == "Показать отсортированные заметки")
    dp.message.register(save_new_note, F.reply_to_message & F.reply_to_message.text == "Введите текст новой заметки:")
    dp.message.register(save_edited_note, lambda msg: msg.from_user.id in edit_states and not msg.text.startswith('/'))
    dp.callback_query.register(delete_callback_handler, F.data.startswith("del_"))
    dp.callback_query.register(edit_callback_handler, F.data.startswith("edit_"))
