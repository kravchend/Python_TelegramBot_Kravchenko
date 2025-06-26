from django.contrib import admin
from .models import User, Event, BotStatistics, Appointment


class EventInline(admin.TabularInline):
    model = Event
    fields = ('name', 'date', 'time', 'details')
    extra = 0
    readonly_fields = ('name', 'date', 'time', 'details')


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('telegram_id', 'username', 'registered_at', 'events_created', 'events_edited', 'events_cancelled')
    search_fields = ('telegram_id', 'username')
    inlines = [EventInline]
    readonly_fields = ('registered_at', 'events_created', 'events_edited', 'events_cancelled')
    ordering = ('-registered_at',)


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'date', 'time', 'is_public')
    search_fields = ('name', 'user__username', 'user__telegram_id')
    list_filter = ('date', 'user', 'is_public')
    list_select_related = ('user',)
    ordering = ('-date', '-time')


@admin.register(BotStatistics)
class BotStatisticsAdmin(admin.ModelAdmin):
    list_display = ('date', 'user_count', 'event_count', 'edited_events', 'cancelled_events')
    list_filter = ('date',)
    readonly_fields = ('date', 'user_count', 'event_count', 'edited_events', 'cancelled_events')
    ordering = ('-date',)


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('organizer', 'invitee', 'event', 'date', 'time', 'status')
    list_filter = ('status', 'date', 'organizer', 'invitee')
    search_fields = ('organizer__username', 'invitee__username', 'event__name')
    autocomplete_fields = ('organizer', 'invitee', 'event')
    ordering = ('-date', '-time')
