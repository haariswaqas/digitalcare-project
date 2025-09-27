# api/serializers/chat_serializers.py
from rest_framework import serializers
from ..models import User, ChatRoom, Message, ChatNotification

class ChatUserSerializer(serializers.ModelSerializer):
    """Simplified user serializer for chat purposes"""
    full_name = serializers.SerializerMethodField()
    is_online = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'role', 'full_name', 'is_online']
    
    def get_full_name(self, obj):
        # Try to get full name from profile based on role
        try:
            if hasattr(obj, 'doctorprofile'):
                profile = obj.doctorprofile
                return f"Dr. {profile.first_name} {profile.last_name}".strip()
            elif hasattr(obj, 'adultprofile'):
                profile = obj.adultprofile
                return f"{profile.first_name} {profile.last_name}".strip()
            elif hasattr(obj, 'studentprofile'):
                profile = obj.studentprofile
                return f"{profile.first_name} {profile.last_name}".strip()
            elif hasattr(obj, 'visitorprofile'):
                profile = obj.visitorprofile
                return f"{profile.first_name} {profile.last_name}".strip()
            else:
                return obj.username
        except:
            return obj.username
    
    def get_is_online(self, obj):
        # You can implement online status logic here
        # For now, return False - you can enhance this with Redis or similar
        return False


class MessageSerializer(serializers.ModelSerializer):
    sender = ChatUserSerializer(read_only=True)
    time_since = serializers.SerializerMethodField()
    
    class Meta:
        model = Message
        fields = [
            'id', 'content', 'message_type', 'sender', 'attachment', 
            'attachment_name', 'is_read', 'read_at', 'is_edited', 
            'created_at', 'time_since'
        ]
        read_only_fields = ['sender', 'is_read', 'read_at', 'is_edited']
    
    def get_time_since(self, obj):
        from django.utils import timezone
        from django.utils.timesince import timesince
        return timesince(obj.created_at, timezone.now())


class ChatRoomListSerializer(serializers.ModelSerializer):
    other_participant = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatRoom
        fields = [
            'id', 'subject', 'status', 'other_participant', 'last_message',
            'unread_count', 'created_at', 'last_message_at'
        ]
    
    def get_other_participant(self, obj):
        request_user = self.context['request'].user
        other_user = obj.get_other_participant(request_user)
        return ChatUserSerializer(other_user).data
    
    def get_last_message(self, obj):
        last_message = obj.messages.last()
        if last_message:
            return {
                'content': last_message.content,
                'sender_username': last_message.sender.username,
                'created_at': last_message.created_at,
                'message_type': last_message.message_type
            }
        return None
    
    def get_unread_count(self, obj):
        request_user = self.context['request'].user
        return obj.messages.filter(is_read=False).exclude(sender=request_user).count()


class ChatRoomDetailSerializer(serializers.ModelSerializer):
    patient = ChatUserSerializer(read_only=True)
    doctor = ChatUserSerializer(read_only=True)
    messages = MessageSerializer(many=True, read_only=True)
    
    class Meta:
        model = ChatRoom
        fields = [
            'id', 'patient', 'doctor', 'subject', 'status', 'patient_consent',
            'doctor_accepted', 'created_at', 'last_message_at', 'messages'
        ]


class CreateChatRoomSerializer(serializers.ModelSerializer):
    doctor_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = ChatRoom
        fields = ['doctor_id', 'subject', 'patient_consent']
    
    def validate_doctor_id(self, value):
        try:
            doctor = User.objects.get(id=value, role='doctor')
            if not hasattr(doctor, 'doctorprofile') or not doctor.doctorprofile.is_active:
                raise serializers.ValidationError("Doctor is not available for consultations.")
            return value
        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid doctor ID.")
    
    def create(self, validated_data):
        doctor_id = validated_data.pop('doctor_id')
        doctor = User.objects.get(id=doctor_id)
        patient = self.context['request'].user
        
        # Check if chat already exists
        existing_chat = ChatRoom.objects.filter(patient=patient, doctor=doctor).first()
        if existing_chat:
            raise serializers.ValidationError("Chat room already exists with this doctor.")
        
        chat_room = ChatRoom.objects.create(
            patient=patient,
            doctor=doctor,
            **validated_data
        )
        
        return chat_room


class CreateMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ['content', 'message_type', 'attachment']
    
    def create(self, validated_data):
        validated_data['sender'] = self.context['request'].user
        validated_data['chat_room'] = self.context['chat_room']
        
        # Handle file attachment name
        if validated_data.get('attachment'):
            validated_data['attachment_name'] = validated_data['attachment'].name
        
        return super().create(validated_data)


class ChatNotificationSerializer(serializers.ModelSerializer):
    chat_room = ChatRoomListSerializer(read_only=True)
    
    class Meta:
        model = ChatNotification
        fields = [
            'id', 'notification_type', 'title', 'content', 'is_read',
            'created_at', 'chat_room'
        ]