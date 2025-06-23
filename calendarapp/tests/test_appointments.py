import pytest
from calendarapp.models import User, Event, Appointment

@pytest.mark.django_db
def test_appointment_creation():
    org = User.objects.create_user(username="org", telegram_id=101)
    inv = User.objects.create_user(username="inv", telegram_id=102)
    event = Event.objects.create(user=org, name="E1", date="2024-02-01", time="15:00:00")
    appt = Appointment.objects.create(
        organizer=org,
        invitee=inv,
        event=event,
        date="2024-02-01",
        time="15:00:00",
        details="Test",
        status="pending"
    )
    assert appt.status == "pending"
    assert "org" in str(appt)