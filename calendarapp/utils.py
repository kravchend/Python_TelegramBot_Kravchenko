from bot.handlers.users import get_bot
from bot.handlers.keyboards import appointment_action_keyboard
import logging

logger = logging.getLogger(__name__)


async def send_invitation_to_user(invitee, event, appointment):
    logger.debug(f"Получатель: {invitee}, Событие: {event}, Встреча: {appointment}")

    if not invitee.telegram_id:
        logger.warning(f"Пользователь {invitee.username} не имеет Telegram ID. Приглашение доступно только на сайте.")
        return "ON_SITE"

    try:
        bot = await get_bot()
        logger.debug(f"Получен объект бота: {bot}")

        await bot.send_message(
            invitee.telegram_id,
            f"Вас пригласили на событие '{event.name}' {event.date} в {event.time}.",
            reply_markup=appointment_action_keyboard(appointment.id),
        )
        logger.info(f"Приглашение отправлено: {invitee.username}")
        return "SENT"
    except Exception as e:
        logger.error(f"Ошибка отправки приглашения пользователю {invitee.username}: {e}")
        if "chat not found" in str(e):
            return "ON_SITE"
        return "ERROR"
