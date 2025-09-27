from django.db import models
from .Message import Message
from ..authentication_models import User

class MessageReadStatus(models.Model):
    """
    Track read status for each message per user (for group chats if needed later)
    """
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='read_statuses')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    read_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('message', 'user')