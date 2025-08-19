from calendarapp.models import User, Event, BotStatistics, Appointment
from asgiref.sync import sync_to_async
from datetime import datetime
import calendar as pycalendar
import logging

logger = logging.getLogger(__name__)


class EventHTMLCalendar(pycalendar.HTMLCalendar):
    def __init__(self, event_days, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.event_days = set(event_days)

    def formatday(self, day, weekday):
        if day == 0:
            return '<td class="noday">&nbsp;</td>'
        elif day in self.event_days:
            return f'<td class="has-event" data-day="{day}">{day}<span class="event-dot">•</span></td>'
        else:
            return f'<td>{day}</td>'


class Calendar:
    def render_for_template(self, year=None, month=None, event_days=None):
        now = datetime.now()
        year = year or now.year
        month = month or now.month
        event_days = event_days or []
        cal = EventHTMLCalendar(event_days, firstweekday=0)
        html_calendar = cal.formatmonth(year, month)
        return html_calendar, year, month

    async def _increment_stat(self, field):
        today = datetime.now().date()
        stats, _ = await sync_to_async(BotStatistics.objects.get_or_create)(
            date=today,
            defaults={
                'user_count': 0,
                'event_count': 0,
                'edited_events': 0,
                'cancelled_events': 0,
            }
        )
        if hasattr(stats, field):
            setattr(stats, field, getattr(stats, field) + 1)
            await sync_to_async(stats.save)()

    async def register_user(self, telegram_id, username=None):
        try:
            if not username:
                username = f"user_{telegram_id}"
            user, created = await sync_to_async(User.objects.get_or_create)(
                telegram_id=telegram_id,
                defaults={'username': username}
            )
            if created:
                logger.info(f"🎉 {telegram_id} зарегистрирован!")
                await self._increment_stat('user_count')
            else:
                logger.info(f"🙂 {telegram_id} уже зарегистрирован!")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка регистрации пользователя {telegram_id}: {e}")
            return False

    async def is_registered(self, telegram_id):
        return await sync_to_async(User.objects.filter(telegram_id=telegram_id).exists)()

    async def get_user_db_id(self, telegram_id):
        try:
            user = await sync_to_async(User.objects.get)(telegram_id=telegram_id)
            logger.info(f"User found: {user}")
            return user.id
        except User.DoesNotExist:
            logger.warning(f"User {telegram_id} не найден")
            return None

    async def create_event(self, user_id, event_name, event_date, event_time, event_details):
        try:
            user = await sync_to_async(User.objects.get)(id=user_id)
            event = await sync_to_async(Event.objects.create)(
                user=user,
                name=event_name,
                date=event_date,
                time=event_time,
                details=event_details
            )
            user.events_created += 1
            await sync_to_async(user.save)()
            await self._increment_stat('event_count')
            return event.id
        except Exception:
            return None

    async def get_event(self, user_id, event_id):
        try:
            event = await sync_to_async(Event.objects.get)(id=event_id, user_id=user_id)
            return {
                "id": event.id,
                "name": event.name,
                "date": str(event.date),
                "time": str(event.time),
                "details": event.details
            }
        except Event.DoesNotExist:
            return None

    async def edit_event(self, user_id, event_id, event_name=None, event_date=None, event_time=None,
                         event_details=None):
        try:
            event = await sync_to_async(Event.objects.get)(id=event_id, user_id=user_id)
            changed = False
            if event_name:
                event.name = event_name
                changed = True
            if event_date:
                event.date = event_date
                changed = True
            if event_time:
                event.time = event_time
                changed = True
            if event_details:
                event.details = event_details
                changed = True
            if changed:
                await sync_to_async(event.save)()
                user_id = event.user_id
                user = await sync_to_async(User.objects.get)(id=user_id)
                user.events_edited += 1
                await sync_to_async(user.save)()
                await self._increment_stat('edited_events')
            return changed
        except Event.DoesNotExist:
            return False

    @staticmethod
    def _delete_event_sync(user_id, event_id):
        try:
            event = Event.objects.get(id=event_id, user_id=user_id)
            user = event.user
            deleted = event.delete()
            if deleted[0] > 0:
                user.events_cancelled += 1
                user.save()
            return deleted[0] > 0
        except Event.DoesNotExist:
            return False
        except Exception as e:
            return False

    async def delete_event(self, user_id, event_id):
        result = await sync_to_async(Calendar._delete_event_sync)(user_id, event_id)
        if result:
            await self._increment_stat('cancelled_events')
        return result

    async def get_all_events(self, user_id):
        events = await sync_to_async(lambda: list(Event.objects.filter(user_id=user_id).order_by('date', 'time')))()
        return [
            {
                "id": e.id,
                "name": e.name,
                "date": str(e.date),
                "time": str(e.time),
                "details": e.details
            }
            for e in events
        ]

    async def invite_user_to_event(self, organizer, invitee, event, date, time, details=""):
        if isinstance(date, str):
            try:
                date = datetime.strptime(date, "%Y-%m-%d").date()
            except Exception as e:
                logger.error(f"Ошибка парсинга даты: {e}")
                return None

        if isinstance(time, str):
            try:
                time = datetime.strptime(time, "%H:%M").time()
            except Exception as e:
                logger.error(f"Ошибка парсинга времени: {e}")
                return None

        logger.debug(
            f"DEBUG-invite: organizer={organizer.id}, invitee={invitee.id}, event={event.id}, date={date}, time={time}, details={details}"
        )

        try:
            def create_or_get_appointment():
                return Appointment.objects.get_or_create(
                    organizer=organizer,
                    invitee=invitee,
                    event=event,
                    date=date,
                    time=time,
                    defaults={"details": details, "status": "pending"},
                )

            appointment, created = await sync_to_async(create_or_get_appointment)()

            if not created:
                if appointment.status in ["pending", "confirmed"]:
                    logger.info(
                        f"Приглашение уже активно: статус '{appointment.status}' для invitee={invitee.id}, event={event.id}"
                    )
                    return None
                else:
                    logger.info(f"Обновление статуса на 'pending' для invitee={invitee.id}, event={event.id}")
                    appointment.status = "pending"
                    await sync_to_async(appointment.save)()

            logger.info(f"Приглашение создано: {appointment}")
            return appointment

        except Exception as e:
            logger.error(f"❌ Ошибка создания приглашения: {e}")
            return None

    async def make_event_public(self, event_id: int, user_id: int) -> bool:
        try:
            event = await sync_to_async(Event.objects.get)(id=event_id, user_id=user_id)
            if event.is_public:
                return False
            event.is_public = True
            await sync_to_async(event.save)()
            return True
        except Event.DoesNotExist:
            return False

    def get_public_events(self, exclude_user_id: int = None):
        qs = Event.objects.filter(is_public=True)
        if exclude_user_id:
            qs = qs.exclude(user_id=exclude_user_id)
        return qs.order_by('date', 'time')
