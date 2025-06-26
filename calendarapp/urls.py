from django.urls import path, include
from . import views
from .views import profile

urlpatterns = [
    path('', views.home, name='home'),
    path('home/', views.home, name='home'),
    path('calendar/', views.calendar_view, name='calendar'),
    path('profile/', views.profile, name='profile'),
    path('appointments/', views.user_appointments, name='user_appointments'),
    path('public-events/', views.public_events, name='public_events'),
    path('statistics/', views.statistics_view, name='statistics'),
    path('accounts/profile/', profile),  # исправлено
    path('events/', views.event_list, name='event_list'),
    path('event/create/', views.event_create, name='event_create'),
    path('event/<int:pk>/edit/', views.event_edit, name='event_edit'),
    path('event/<int:pk>/delete/', views.event_delete, name='event_delete'),
    path('export/json/', views.export_events_json, name='export_events_json'),
    path('export/csv/', views.export_events_csv, name='export_events_csv'),
    path('api/', include('calendarapp.api_urls')),

]

