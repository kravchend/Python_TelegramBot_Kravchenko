from django.urls import path, include
from . import views
from .views import profile, custom_logout

urlpatterns = [
    path('', views.home, name='home'),
    path('home/', views.home, name='home'),  # Продублированный, можно удалить
    path('logout/', views.custom_logout, name='logout'),  # Маршрут выхода
    path('calendar/', views.calendar_view, name='calendar'),
    path('register/', views.site_register_view, name='site_register'),
    path('appointments/<int:pk>/update-status/', views.update_appointment_status, name='update_appointment_status'),
    path('profile/', views.profile, name='profile'),
    path('event/<int:pk>/invite/', views.invite_users_to_event, name='invite_users'),
    path('event/<int:pk>/', views.event_detail, name='event_detail'),
    path('appointments/', views.user_appointments, name='user_appointments'),
    path('public-events/', views.public_events, name='public_events'),
    path('statistics/', views.statistics_view, name='statistics'),
    path('accounts/profile/', profile),
    path('events/', views.event_list, name='event_list'),
    path('event/create/', views.event_create, name='event_create'),
    path('event/<int:pk>/edit/', views.event_edit, name='event_edit'),
    path('event/<int:pk>/delete/', views.event_delete, name='event_delete'),
    path('export/json/', views.export_events_json, name='export_events_json'),
    path('export/csv/', views.export_events_csv, name='export_events_csv'),
    path('api/', include('calendarapp.api_urls')),
]


