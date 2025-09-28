# api/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from ..models import ChatRoom, Message



class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.chat_room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'chat_{self.chat_room_id}'
        self.user = self.scope['user']
        
        # Check if user is authenticated
        if self.user.is_anonymous:
            await self.close()
            return
        
        # Verify user is participant in this chat room
        chat_room = await self.get_chat_room(self.chat_room_id)
        if not chat_room or not await self.is_participant(chat_room, self.user):
            await self.close()
            return
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send user online status
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_status',
                'user_id': self.user.id,
                'username': self.user.username,
                'status': 'online'
            }
        )

    async def disconnect(self, close_code):
        # Send user offline status
        if hasattr(self, 'room_group_name') and hasattr(self, 'user'):
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'user_status',
                    'user_id': self.user.id,
                    'username': self.user.username,
                    'status': 'offline'
                }
            )
        
        # Leave room group
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get('type', 'message')
            
            if message_type == 'message':
                await self.handle_message(text_data_json)
            elif message_type == 'typing':
                await self.handle_typing(text_data_json)
            elif message_type == 'read_message':
                await self.handle_read_message(text_data_json)
                
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'error': 'Invalid JSON format'
            }))

    async def handle_message(self, data):
        message_content = data.get('message', '').strip()
        if not message_content:
            return
        
        chat_room = await self.get_chat_room(self.chat_room_id)
        if not chat_room:
            return
        
        # Create message in database
        message = await self.create_message(
            chat_room, self.user, message_content
        )
        
        if message:
            # Get message data
            message_data = await self.get_message_data(message)
            
            # Send message to room group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': message_data
                }
            )

    async def handle_typing(self, data):
        is_typing = data.get('is_typing', False)
        
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing_indicator',
                'user_id': self.user.id,
                'username': self.user.username,
                'is_typing': is_typing
            }
        )

    async def handle_read_message(self, data):
        message_id = data.get('message_id')
        if message_id:
            await self.mark_message_read(message_id, self.user)
            
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'message_read',
                    'message_id': message_id,
                    'reader_id': self.user.id
                }
            )

    # Receive message from room group
    async def chat_message(self, event):
        message = event['message']
        
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message': message
        }))

    async def typing_indicator(self, event):
        # Don't send typing indicator to the user who is typing
        if event['user_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'typing',
                'user_id': event['user_id'],
                'username': event['username'],
                'is_typing': event['is_typing']
            }))

    async def user_status(self, event):
        # Don't send status to the user themselves
        if event['user_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'user_status',
                'user_id': event['user_id'],
                'username': event['username'],
                'status': event['status']
            }))

    async def message_read(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message_read',
            'message_id': event['message_id'],
            'reader_id': event['reader_id']
        }))

    # Database operations
    @database_sync_to_async
    def get_chat_room(self, room_id):
        try:
            return ChatRoom.objects.select_related('patient', 'doctor').get(id=room_id)
        except ChatRoom.DoesNotExist:
            return None

    @database_sync_to_async
    def is_participant(self, chat_room, user):
        return user in [chat_room.patient, chat_room.doctor]

    @database_sync_to_async
    def create_message(self, chat_room, user, content):
        try:
            # Check if chat is active and user can send messages
            if chat_room.status != 'active':
                return None
                
            # For patients, check if doctor has accepted
            if user == chat_room.patient and not chat_room.doctor_accepted:
                return None
                
            message = Message.objects.create(
                chat_room=chat_room,
                sender=user,
                content=content,
                message_type='text'
            )
            return message
        except Exception:
            return None

    @database_sync_to_async
    def get_message_data(self, message):
        from django.utils.timesince import timesince
        from django.utils import timezone
        
        return {
            'id': message.id,
            'content': message.content,
            'message_type': message.message_type,
            'sender': {
                'id': message.sender.id,
                'username': message.sender.username,
                'role': message.sender.role
            },
            'created_at': message.created_at.isoformat(),
            'time_since': timesince(message.created_at, timezone.now()),
            'is_read': message.is_read
        }

    @database_sync_to_async
    def mark_message_read(self, message_id, reader):
        try:
            message = Message.objects.get(id=message_id)
            if reader != message.sender:
                message.mark_as_read(reader)
                return True
        except Message.DoesNotExist:
            pass
        return False


