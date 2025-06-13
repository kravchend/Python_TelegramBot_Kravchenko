from django.db import models


class User(models.Model):
    telegram_id = models.BigIntegerField(unique=True)
    username = models.CharField(max_length=150, blank=True, null=True)
    registered_at = models.DateTimeField(auto_now_add=True)
    events_created = models.PositiveIntegerField(default=0)
    events_edited = models.PositiveIntegerField(default=0)
    events_cancelled = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'users'
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return f"{self.telegram_id}"


class Event(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='events'
    )
    name = models.CharField(max_length=255)
    date = models.DateField()
    time = models.TimeField()
    details = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'events'
        verbose_name = 'Событие'
        verbose_name_plural = 'События'
        ordering = ['date', 'time']

    def __str__(self):
        return f"{self.name} - {self.date} {self.time}"


class BotStatistics(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    date = models.DateField()
    user_count = models.PositiveIntegerField()
    event_count = models.PositiveIntegerField()
    edited_events = models.PositiveIntegerField()
    cancelled_events = models.PositiveIntegerField()

    class Meta:
        db_table = 'bot_statistics'
        verbose_name = 'Статистика бота'
        verbose_name_plural = 'Статистика бота'
        unique_together = ('user', 'date')

    def __str__(self):
        return f"Статистика за {self.date}"


class Appointment(models.Model):
    organizer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='organized_appointments')
    invitee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='invited_appointments')
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    date = models.DateField()
    time = models.TimeField()
    details = models.TextField(blank=True)
    status = models.CharField(
        max_length=40,
        choices=[
            ('pending', 'Ожидание'),
            ('confirmed', 'Подтверждено'),
            ('cancelled', 'Отменено')
        ],
        default='pending'
    )

    def __str__(self):
        return f"{self.organizer.username} — {self.invitee.username} — {self.event.name} — {self.date} {self.time}"
