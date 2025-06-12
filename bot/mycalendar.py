from calendarapp.models import User, Event, BotStatistics, Appointment
from asgiref.sync import sync_to_async
from datetime import datetime
from django.db import models
import calendar as pycalendar


class Calendar:
    def render_for_template(self, year=None, month=None):
        now = datetime.now()
        year = year or now.year
        month = month or now.month
        cal = pycalendar.HTMLCalendar(firstweekday=0)
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
            user, created = await sync_to_async(User.objects.get_or_create)(
                telegram_id=telegram_id,
                defaults={'username': username}
            )
            if created:
                await self._increment_stat('user_count')
            return True
        except Exception:
            return False

    async def is_registered(self, telegram_id):
        return await sync_to_async(User.objects.filter(telegram_id=telegram_id).exists)()

    async def get_user_db_id(self, telegram_id):
        try:
            user = await sync_to_async(User.objects.get)(telegram_id=telegram_id)
            return user.id
        except User.DoesNotExist:
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

    async def get_all_events(self, user_id):
        events = []
        async for event in Event.objects.filter(user_id=user_id).order_by('date', 'time'):
            events.append(event)

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
                user = event.user
                user.events_edited += 1
                await sync_to_async(user.save)()
                await self._increment_stat('edited_events')
            return changed
        except Event.DoesNotExist:
            return False

    async def delete_event(self, user_id, event_id):
        try:
            event = await sync_to_async(Event.objects.get)(id=event_id, user_id=user_id)
            user = event.user
            deleted_count, _ = await sync_to_async(Event.objects.filter(id=event_id, user_id=user_id).delete)()
            if deleted_count > 0:
                user.events_cancelled += 1
                await sync_to_async(user.save)()
                await self._increment_stat('cancelled_events')
            return deleted_count > 0
        except Event.DoesNotExist:
            return False

    async def get_busy_appointments(self, user, date=None):
        q = Appointment.objects.filter(
            models.Q(organizer=user) | models.Q(invitee=user),
            status__in=['pending', 'confirmed']
        )
        if date:
            q = q.filter(date=date)
        return await sync_to_async(lambda: list(q.values('date', 'time', 'status', 'event_id')))()

    async def invite_user_to_event(self, organizer, invitee, event, date, time, details=""):
        conflict = await sync_to_async(
            Appointment.objects.filter(
                invitee=invitee,
                date=date,
                time=time,
                status__in=['pending', 'confirmed']
            ).exists
        )()
        if conflict:
            return None  # Пользователь занят

        appt = await sync_to_async(Appointment.objects.create)(
            organizer=organizer,
            invitee=invitee,
            event=event,
            date=date,
            time=time,
            details=details,
            status='pending'
        )
        return appt
