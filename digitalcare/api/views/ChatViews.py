# api/views/chat_views.py
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend

from ..models import (User, ChatRoom, Message, ChatNotification)
from ..serializers import (
    ChatRoomListSerializer, ChatRoomDetailSerializer, CreateChatRoomSerializer,
    MessageSerializer, CreateMessageSerializer, ChatNotificationSerializer,
    ChatUserSerializer
)


class ChatRoomViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing chat rooms
    """
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status']
    
    def get_queryset(self):
        user = self.request.user
        return ChatRoom.objects.filter(
            Q(patient=user) | Q(doctor=user)
        ).select_related('patient', 'doctor').prefetch_related('messages')
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ChatRoomListSerializer
        elif self.action == 'create':
            return CreateChatRoomSerializer
        return ChatRoomDetailSerializer
    
    def create(self, request, *args, **kwargs):
        """Create a new chat room (patients only)"""
        if request.user.role not in ['student', 'adult', 'visitor']:
            return Response(
                {'error': 'Only patients can initiate chat requests.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            chat_room = serializer.save()
            
            # Create notification for doctor
            ChatNotification.objects.create(
                user=chat_room.doctor,
                chat_room=chat_room,
                notification_type='chat_request',
                title=f'New Chat Request',
                content=f'{chat_room.patient.username} wants to start a consultation.'
            )
            
            return Response(
                ChatRoomDetailSerializer(chat_room, context={'request': request}).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def accept_chat(self, request, pk=None):
        """Doctor accepts a chat request"""
        chat_room = self.get_object()
        
        if request.user != chat_room.doctor:
            return Response(
                {'error': 'Only the assigned doctor can accept this chat.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if chat_room.doctor_accepted:
            return Response(
                {'message': 'Chat already accepted.'},
                status=status.HTTP_200_OK
            )
        
        chat_room.doctor_accepted = True
        chat_room.save()
        
        # Create notification for patient
        ChatNotification.objects.create(
            user=chat_room.patient,
            chat_room=chat_room,
            notification_type='chat_accepted',
            title=f'Chat Accepted',
            content=f'Dr. {chat_room.doctor.username} accepted your consultation request.'
        )
        
        # Send system message
        Message.objects.create(
            chat_room=chat_room,
            sender=chat_room.doctor,
            content="Hello! I'm ready to help you. Please describe your concerns.",
            message_type='system'
        )
        
        return Response({'message': 'Chat accepted successfully.'})
    
    @action(detail=True, methods=['post'])
    def close_chat(self, request, pk=None):
        """Close a chat room"""
        chat_room = self.get_object()
        
        if request.user not in [chat_room.patient, chat_room.doctor]:
            return Response(
                {'error': 'You are not authorized to close this chat.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        chat_room.status = 'closed'
        chat_room.save()
        
        # Create system message
        Message.objects.create(
            chat_room=chat_room,
            sender=request.user,
            content=f"Chat closed by {request.user.username}",
            message_type='system'
        )
        
        # Notify other participant
        other_user = chat_room.get_other_participant(request.user)
        ChatNotification.objects.create(
            user=other_user,
            chat_room=chat_room,
            notification_type='chat_closed',
            title='Chat Closed',
            content=f'{request.user.username} closed the consultation.'
        )
        
        return Response({'message': 'Chat closed successfully.'})
    
    

# Add this to your MessageViewSet in chat_views.py

class MessageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing messages within chat rooms
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = MessageSerializer
    
    def get_queryset(self):
        chat_room_id = self.kwargs.get('chat_room_pk')
        if chat_room_id:
            chat_room = get_object_or_404(ChatRoom, id=chat_room_id)
            # Ensure user is participant in the chat
            if self.request.user not in [chat_room.patient, chat_room.doctor]:
                return Message.objects.none()
            return chat_room.messages.all().order_by('created_at')
        return Message.objects.none()
    
    def get_serializer_class(self):
        if self.action == 'create':
            return CreateMessageSerializer
        return MessageSerializer
    
    def list(self, request, *args, **kwargs):
        """List messages and auto-mark unread messages as read"""
        chat_room_id = self.kwargs.get('chat_room_pk')
        
        if chat_room_id:
            chat_room = get_object_or_404(ChatRoom, id=chat_room_id)
            
            # Verify user is participant in the chat
            if request.user not in [chat_room.patient, chat_room.doctor]:
                return Response(
                    {'error': 'You are not authorized to view messages in this chat.'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Auto-mark unread messages as read (excluding user's own messages)
            unread_messages = chat_room.messages.filter(
                is_read=False
            ).exclude(sender=request.user)
            
            # Mark each unread message as read
            for message in unread_messages:
                message.mark_as_read(request.user)
        
        # Continue with normal list behavior
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    def create(self, request, *args, **kwargs):
        """Send a new message"""
        chat_room_id = self.kwargs.get('chat_room_pk')
        chat_room = get_object_or_404(ChatRoom, id=chat_room_id)
        
        # Verify user is participant
        if request.user not in [chat_room.patient, chat_room.doctor]:
            return Response(
                {'error': 'You are not authorized to send messages in this chat.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if chat is active
        if chat_room.status != 'active':
            return Response(
                {'error': 'Cannot send messages to a closed chat.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # For patients, check if doctor has accepted
        if (request.user == chat_room.patient and 
            not chat_room.doctor_accepted):
            return Response(
                {'error': 'Please wait for the doctor to accept your chat request.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = self.get_serializer(
            data=request.data, 
            context={'request': request, 'chat_room': chat_room}
        )
        
        if serializer.is_valid():
            message = serializer.save()
            
            # Create notification for other participant
            other_user = chat_room.get_other_participant(request.user)
            ChatNotification.objects.create(
                user=other_user,
                chat_room=chat_room,
                message=message,
                notification_type='new_message',
                title=f'New message from {request.user.username}',
                content=message.content[:100]
            )
            
            return Response(
                MessageSerializer(message).data,
                status=status.HTTP_201_CREATED
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class AvailableDoctorsView(viewsets.ReadOnlyModelViewSet):
    """
    List available doctors for chat
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ChatUserSerializer
    
    def get_queryset(self):
        # Only patients can see available doctors
        if self.request.user.role not in ['student', 'adult', 'visitor']:
            return User.objects.none()
        
        return User.objects.filter(
            role='doctor',
            status='active',
            doctorprofile__is_active=True
        ).select_related('doctorprofile')


class ChatNotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for chat notifications
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ChatNotificationSerializer
    
    def get_queryset(self):
        return ChatNotification.objects.filter(
            user=self.request.user
        ).order_by('-created_at')
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark a notification as read"""
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response({'message': 'Notification marked as read.'})
    
    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """Mark all notifications as read"""
        self.get_queryset().filter(is_read=False).update(is_read=True)
        return Response({'message': 'All notifications marked as read.'})