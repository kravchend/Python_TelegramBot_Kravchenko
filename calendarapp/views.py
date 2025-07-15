from django.shortcuts import render, get_object_or_404, redirect
from bot.calendar_instance import calendar
from django.contrib.auth.decorators import login_required
from bot.handlers.keyboards import appointment_action_keyboard
from .models import User, Event, Appointment, BotStatistics
from django.db.models import Q
from datetime import datetime
from .forms import EventForm, SiteRegistrationForm
from django.http import HttpResponseForbidden, JsonResponse, HttpResponse, HttpResponseServerError
import csv
from django.contrib.auth import login, logout
from django.views.decorators.http import require_POST
from asgiref.sync import async_to_sync, sync_to_async
from bot.handlers.users import get_bot
from django.contrib import messages


def home(request):
    return render(request, 'pages/home.html')


def custom_logout(request):
    logout(request)
    messages.info(request, "Вы успешно вышли из системы. Пожалуйста, войдите или зарегистрируйтесь.")
    return redirect('home')


def site_register_view(request):
    if request.method == 'POST':
        form = SiteRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            login(request, user)
            return redirect('home')
    else:
        form = SiteRegistrationForm()
    return render(request, 'registration/register.html', {'form': form})


@login_required
@require_POST
async def update_appointment_status(request, pk):
    try:
        appointment = await sync_to_async(get_object_or_404)(Appointment, pk=pk, invitee=request.user)
        action = request.POST.get('action')

        if action == 'confirm':
            await sync_to_async(setattr)(appointment, 'status', 'confirmed')
            message_to_invitee = "Вы подтвердили встречу."
            message_to_organizer = (
                f"{await sync_to_async(lambda: appointment.invitee.username)()} подтвердил участие "
                f"в событии '{await sync_to_async(lambda: appointment.event.name)()}'."
            )
        elif action == 'cancel':
            await sync_to_async(setattr)(appointment, 'status', 'cancelled')
            message_to_invitee = "Вы отклонили встречу."
            message_to_organizer = (
                f"{await sync_to_async(lambda: appointment.invitee.username)()} отклонил приглашение "
                f"на событие '{await sync_to_async(lambda: appointment.event.name)()}'."
            )
        else:
            return HttpResponseForbidden("Некорректное действие.")

        await sync_to_async(appointment.save)()

        organizer_telegram_id = await sync_to_async(lambda: appointment.organizer.telegram_id)()
        if organizer_telegram_id:
            try:
                bot = await get_bot()
                await bot.send_message(chat_id=organizer_telegram_id, text=message_to_organizer)
            except Exception as e:
                print(f"Ошибка отправки уведомления организатору: {e}")

        messages.success(request, message_to_invitee)
        return redirect('user_appointments')

    except Exception as e:
        print(f"Ошибка в обработке запроса: {e}")
        return HttpResponseServerError("Произошла ошибка при обработке вашего запроса.")


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
            new_event.user = request.user

            if not new_event.time:
                new_event.time = "12:00"

            new_event.save()
            print(
                f"Event '{new_event.name}' создан для пользователя '{new_event.user.username}' на {new_event.date} в {new_event.time}."
            )
            # После создания события перенаправляем на страницу приглашений
            return redirect('invite_users', pk=new_event.pk)
        else:
            print("Ошибки формы (event_create):", form.errors)
            print("Данные POST (event_create):", request.POST)
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
def calendar_view(request):
    user = get_object_or_404(User, username=request.user.username)
    now = datetime.now()
    month = int(request.GET.get("month", now.month))
    year = int(request.GET.get("year", now.year))
    events = Event.objects.filter(user=user, date__year=year, date__month=month).order_by('date', 'time')

    print(f"Found {events.count()} events for user '{user.username}' in {year}-{month}.")
    for event in events:
        print(f"Event: {event.name} on {event.date}")

    event_days = set(e.date.day for e in events)
    html_calendar, cal_year, cal_month = calendar.render_for_template(year=year, month=month, event_days=event_days)
    print(f"HTML Calendar: {html_calendar[:500]}")

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
def profile(request):
    user = request.user

    created_events = Event.objects.filter(user=user).order_by('date', 'time')

    incoming_appointments = Appointment.objects.filter(
        invitee=user,
        status__in=['pending', 'confirmed']
    ).select_related('organizer', 'event')

    outgoing_appointments = Appointment.objects.filter(
        organizer=user,
        status='pending'
    ).select_related('invitee', 'event')

    stats = {
        'created': user.events_created,
        'edited': user.events_edited,
        'cancelled': user.events_cancelled,
    }
    return render(request, 'pages/profile.html', {
        'user': user,
        'stats': stats,
        'created_events': created_events,
        'incoming_appointments': incoming_appointments,
        'outgoing_appointments': outgoing_appointments,
    })


@login_required
def export_events_json(request):
    user = request.user
    events = Event.objects.filter(user=user)
    data = [
        {
            'name': event.name,
            'date': event.date,
            'time': str(event.time),
            'details': event.details,
            'is_public': event.is_public
        }
        for event in events
    ]
    return JsonResponse({'events': data})


@login_required
def export_events_csv(request):
    user = request.user
    events = Event.objects.filter(user=user)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="events_{user.username or user.id}.csv"'
    writer = csv.writer(response)
    writer.writerow(['name', 'date', 'time', 'details', 'is_public'])
    for event in events:
        writer.writerow([event.name, event.date, event.time, event.details, event.is_public])
    return response


@login_required
def event_detail(request, pk):
    event = get_object_or_404(Event, pk=pk, user=request.user)

    # Пользователи, которых можно пригласить
    invitable_users = User.objects.exclude(id=request.user.id).exclude(
        id__in=Appointment.objects.filter(event=event).values_list('invitee_id', flat=True)
    )

    # Уже приглашённые пользователи
    invited_users = Appointment.objects.filter(event=event).select_related('invitee')

    return render(request, 'pages/event_detail.html', {
        'event': event,
        'invitable_users': invitable_users,
        'invited_users': invited_users,
    })


@login_required
def invite_users_to_event(request, pk):
    event = get_object_or_404(Event, pk=pk, user=request.user)

    users = User.objects.exclude(id=request.user.id).exclude(
        id__in=Appointment.objects.filter(event=event).values_list('invitee_id', flat=True)
    )

    if request.method == "POST":
        selected_user_ids = request.POST.getlist("user_ids")

        for user_id in selected_user_ids:
            try:
                invitee = User.objects.get(id=user_id)
                appointment, created = Appointment.objects.get_or_create(
                    organizer=request.user,
                    invitee=invitee,
                    event=event,
                    date=event.date,
                    time=event.time,
                    defaults={'status': 'pending'}
                )
                if created:
                    async_to_sync(send_invitation_to_telegram)(invitee, event, appointment)
            except User.DoesNotExist:
                continue

        return redirect('event_detail', pk=pk)

    return render(request, "pages/invite_users.html", {
        "event": event,
        "users": users,
    })


async def send_invitation_to_telegram(invitee, event, appointment):
    if invitee.telegram_id:
        try:
            bot = await get_bot()
            await bot.send_message(
                invitee.telegram_id,
                f"Вас пригласили на событие '{event.name}' {event.date} в {event.time}.",
                reply_markup=appointment_action_keyboard(appointment.id)
            )
            print(f"Приглашение отправлено пользователю: {invitee.telegram_id}")
        except Exception as e:
            # Подробное логирование ошибки
            print(f"Ошибка при отправке уведомления пользователю {invitee.telegram_id}: {e}")
    else:
        print(f"Ошибка: пользователь {invitee.username} не привязал Telegram ID")
