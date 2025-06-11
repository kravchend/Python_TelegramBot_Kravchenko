from calendarapp.models import User, Event
from asgiref.sync import sync_to_async


class Calendar:
    async def register_user(self, telegram_id, username=None):
        try:
            await sync_to_async(User.objects.get_or_create)(
                telegram_id=telegram_id,
                defaults={'username': username}
            )
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
            return changed
        except Event.DoesNotExist:
            return False

    async def delete_event(self, user_id, event_id):
        deleted, _ = await sync_to_async(Event.objects.filter(id=event_id, user_id=user_id).delete)()
        return deleted > 0
