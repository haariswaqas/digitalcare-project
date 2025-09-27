from django.db import models
from ..authentication_models import User
from .ChatRoom import ChatRoom
from .Message import Message

class ChatNotification(models.Model):
    """
    Notifications for chat events
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_notifications')
    chat_room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='notifications')
    message = models.ForeignKey(Message, on_delete=models.CASCADE, null=True, blank=True)
    
    NOTIFICATION_TYPES = [
        ('new_message', 'New Message'),
        ('chat_request', 'Chat Request'),
        ('chat_accepted', 'Chat Accepted'),
        ('chat_closed', 'Chat Closed'),
    ]
    
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=100)
    content = models.TextField()
    
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Notification for {self.user.username}: {self.title}"