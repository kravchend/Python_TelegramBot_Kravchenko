import pytest
from calendarapp.models import User, Event


@pytest.mark.django_db
def test_user_creation():
    user = User.objects.create_user(username="myuser", telegram_id=100)
    assert user.username == "myuser"
    assert user.telegram_id == 100

@pytest.mark.django_db
def test_event_creation():
    user = User.objects.create_user(username="usr1", telegram_id=999)
    event = Event.objects.create(
        user=user,
        name="TestEvent",
        date="2024-01-01",
        time="12:00:00"
    )
    assert event.name == "TestEvent"
    assert event.user == user