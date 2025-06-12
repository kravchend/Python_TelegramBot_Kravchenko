from django.contrib import admin
from .models import User, Event, BotStatistics, Appointment


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('id', 'telegram_id', 'username', 'registered_at')
    search_fields = ('telegram_id', 'username')
    list_filter = ('registered_at',)


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'name', 'date', 'time')
    search_fields = ('name', 'user__telegram_id', 'user__username')
    list_filter = ('date',)


@admin.register(BotStatistics)
class BotStatisticsAdmin(admin.ModelAdmin):
    list_display = ('date', 'user_count', 'event_count', 'edited_events', 'cancelled_events')
    search_fields = ('date',)
    list_filter = ('date',)


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ['organizer', 'invitee', 'event', 'date', 'time', 'details', 'status']
