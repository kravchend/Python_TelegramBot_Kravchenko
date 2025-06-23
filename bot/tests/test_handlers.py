import pytest
from aiogram.types import Message
from bot.handlers import users

@pytest.mark.asyncio
async def test_send_welcome(mocker):
    message = mocker.Mock(spec=Message)
    message.from_user = mocker.Mock()
    message.from_user.full_name = "Иван Тестовый"
    message.answer = mocker.AsyncMock()
    await users.send_welcome(message)
    message.answer.assert_called_once()
    args, kwargs = message.answer.call_args
    assert "Привет, Иван Тестовый" in args[0]

@pytest.mark.asyncio
async def test_register_user_handler_already_registered(mocker):
    message = mocker.Mock(spec=Message)
    message.from_user = mocker.Mock()
    message.from_user.id = 10
    message.from_user.username = "testuser"
    message.answer = mocker.AsyncMock()
    mocker.patch("bot.handlers.users.calendar.get_user_db_id", return_value=1)
    await users.register_user_handler(message)
    message.answer.assert_called_once()
    args, kwargs = message.answer.call_args
    assert "уже зарегистрированы" in args[0].lower()