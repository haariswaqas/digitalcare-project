# api/urls/chat_urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers

from ..views import (
    ChatRoomViewSet, MessageViewSet, AvailableDoctorsView, 
    ChatNotificationViewSet
)

# Main router
router = DefaultRouter()
router.register(r'chat-rooms', ChatRoomViewSet, basename='chatroom')
router.register(r'available-doctors', AvailableDoctorsView, basename='available-doctors')
router.register(r'notifications', ChatNotificationViewSet, basename='chat-notifications')

# Nested router for messages within chat rooms
chat_router = routers.NestedDefaultRouter(router, r'chat-rooms', lookup='chat_room')
chat_router.register(r'messages', MessageViewSet, basename='chatroom-messages')

urlpatterns = [
    path('', include(router.urls)),
    path('', include(chat_router.urls)),
]