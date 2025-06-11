from django.db import models


class User(models.Model):
    telegram_id = models.BigIntegerField(unique=True)
    username = models.TextField(blank=True, null=True)
    registered_at = models.DateTimeField(auto_now_add=True)

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
        db_column='user_id',
        related_name='events'
    )
    name = models.TextField()
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