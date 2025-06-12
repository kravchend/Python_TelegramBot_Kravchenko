from django.shortcuts import render
from django.http import HttpResponse
from bot.calendar_instance import calendar


def home(request):
    return HttpResponse("Добро пожаловать в calendarapp!")


def show_calendar(request):
    html_calendar, year, month = calendar.render_for_template()
    return render(request, 'calendar.html', {
        'html_calendar': html_calendar,
        'year': year,
        'month': month,
    })
