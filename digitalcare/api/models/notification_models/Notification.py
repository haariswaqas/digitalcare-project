from django.db import models
from ..authentication_models import User

class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('GENERAL', 'General'),
        ('HEALTH_CARD_SCAN', 'Health Card Scan'),
        ('SECURITY_ALERT', 'Security Alert'),
        ('CARD_EXPIRY_REMINDER', 'Card Expiry Reminder'),
        ('APPOINTMENT', 'Appointment'),
    ]
    
    PRIORITY_CHOICES = [
        ('LOW', 'Low'),
        ('NORMAL', 'Normal'),
        ('HIGH', 'High'),
        ('URGENT', 'Urgent'),
    ]
    
    recipient = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES, default='GENERAL')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='NORMAL')
    metadata = models.JSONField(default=dict, blank=True)
    is_read = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)