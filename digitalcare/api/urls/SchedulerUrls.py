# api/urls/appointment_reminder_urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from ..views import AppointmentReminderViewSet

router = DefaultRouter()
router.register(r'reminders', AppointmentReminderViewSet, basename='appointment-reminder')

urlpatterns = [
    path('', include(router.urls)),
]