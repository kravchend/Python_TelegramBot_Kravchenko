from rest_framework import serializers
from .models import User, Event, Appointment


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'telegram_id', 'registered_at']


class EventSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = Event
        fields = ['id', 'name', 'date', 'time', 'is_public', 'user', 'user_username', 'details']


class AppointmentSerializer(serializers.ModelSerializer):
    organizer_username = serializers.CharField(source='organizer.username', read_only=True)
    invitee_username = serializers.CharField(source='invitee.username', read_only=True)
    event_name = serializers.CharField(source='event.name', read_only=True)

    class Meta:
        model = Appointment
        fields = [
            'id', 'organizer', 'organizer_username',
            'invitee', 'invitee_username',
            'event', 'event_name',
            'date', 'time', 'details', 'status'
        ]
