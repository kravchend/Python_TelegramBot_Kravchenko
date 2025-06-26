import pytest
from calendarapp.models import Event, User

@pytest.mark.django_db
def test_event_str():
    user = User.objects.create_user(username="usr2", telegram_id=777)
    event = Event.objects.create(
        user=user,
        name="EventName",
        date="2024-05-21",
        time="13:00:00"
    )
    assert str(event).startswith("EventName")