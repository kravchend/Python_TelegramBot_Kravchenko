from django.shortcuts import render, get_object_or_404, redirect
from bot.calendar_instance import calendar
from django.contrib.auth.decorators import login_required
from .models import User, Event, Appointment, BotStatistics
from django.db.models import Q
from datetime import datetime
from .forms import EventForm
from django.http import HttpResponseForbidden


def home(request):
    return render(request, 'pages/home.html')


@login_required
def event_list(request):
    events = Event.objects.filter(user=request.user)
    return render(request, 'pages/event_list.html', {'events': events})


@login_required
def event_create(request):
    if request.method == 'POST':
        form = EventForm(request.POST)
        if form.is_valid():
            new_event = form.save(commit=False)
            new_event.user = request.user  # <-- Вот здесь сохраняем пользователя!
            new_event.save()
            return redirect('calendar')
    else:
        form = EventForm()
    return render(request, 'pages/event_create.html', {'form': form})


@login_required
def event_edit(request, pk):
    event = get_object_or_404(Event, pk=pk)
    if event.user != request.user:
        return HttpResponseForbidden("Нельзя редактировать чужое событие!")
    if request.method == 'POST':
        form = EventForm(request.POST, instance=event)
        if form.is_valid():
            form.save()
            return redirect('calendar')
    else:
        form = EventForm(instance=event)
    return render(request, 'pages/event_edit.html', {'form': form})


@login_required
def event_delete(request, pk):
    event = get_object_or_404(Event, pk=pk)
    if event.user != request.user:
        return HttpResponseForbidden("Нельзя удалить чужое событие!")
    if request.method == 'POST':
        event.delete()
        return redirect('calendar')
    return render(request, 'pages/event_confirm_delete.html', {'event': event})


@login_required
def profile(request):
    user = get_object_or_404(User, username=request.user.username)
    stats = {
        'created': user.events_created,
        'edited': user.events_edited,
        'cancelled': user.events_cancelled,
    }
    return render(request, 'pages/profile.html', {'user': user, 'stats': stats})


@login_required
def calendar_view(request):
    user = get_object_or_404(User, username=request.user.username)
    now = datetime.now()
    month = int(request.GET.get("month", now.month))
    year = int(request.GET.get("year", now.year))
    events = Event.objects.filter(user=user, date__year=year, date__month=month).order_by('date', 'time')
    event_days = set(e.date.day for e in events)
    html_calendar, cal_year, cal_month = calendar.render_for_template(year=year, month=month, event_days=event_days)
    return render(request, 'pages/calendar.html', {
        'events': events,
        'html_calendar': html_calendar,
        'year': cal_year,
        'month': cal_month,
    })


@login_required
def user_appointments(request):
    user = request.user
    appointments = Appointment.objects.filter(
        Q(organizer=user) | Q(invitee=user)
    ).select_related('organizer', 'invitee', 'event').order_by('date', 'time')

    return render(request, 'pages/appointments.html', {'appointments': appointments})


def public_events(request):
    events = Event.objects.filter(is_public=True).order_by('date', 'time')
    return render(request, 'pages/public_events.html', {'events': events})


@login_required
def statistics_view(request):
    user = request.user
    bot_stats = BotStatistics.objects.filter(user__username=user.username).order_by('-date')[:30]
    return render(request, 'pages/statistics.html', {'bot_stats': bot_stats})


@login_required
def profile_view(request):
    user = get_object_or_404(User, telegram_id=request.user.telegram_id)

    stats = {
        'created': user.events_created,
        'edited': user.events_edited,
        'cancelled': user.events_cancelled,
    }

    return render(request, 'pages/profile.html', {
        'user': user,
        'stats': stats
    })
