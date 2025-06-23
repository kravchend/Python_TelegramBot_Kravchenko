import pytest
from calendarapp.models import User, BotStatistics

@pytest.mark.django_db
def test_stats_unique():
    user = User.objects.create_user(username="statuser", telegram_id=555)
    BotStatistics.objects.create(
        user=user, date="2024-01-01",
        user_count=1, event_count=1, edited_events=0, cancelled_events=0
    )
    with pytest.raises(Exception):
        BotStatistics.objects.create(
            user=user, date="2024-01-01",
            user_count=2, event_count=3, edited_events=0, cancelled_events=0
        )