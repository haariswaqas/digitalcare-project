from django.db import models
from django.utils import timezone
from ..authentication_models import User


class ChatRoom(models.Model):
    """
    Represents a chat room between a patient and a doctor
    """
    patient = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='patient_chats',
        limit_choices_to={'role__in': ['student', 'adult', 'visitor']}
    )
    doctor = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='doctor_chats',
        limit_choices_to={'role': 'doctor'}
    )
    
    # Chat room status
    ACTIVE = 'active'
    CLOSED = 'closed'
    ARCHIVED = 'archived'
    
    STATUS_CHOICES = [
        (ACTIVE, 'Active'),
        (CLOSED, 'Closed'),
        (ARCHIVED, 'Archived'),
    ]
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=ACTIVE)
    subject = models.CharField(max_length=200, blank=True, null=True, help_text="Optional chat subject")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_message_at = models.DateTimeField(null=True, blank=True)
    
    # Privacy and consent
    patient_consent = models.BooleanField(default=False, help_text="Patient consent for chat")
    doctor_accepted = models.BooleanField(default=False, help_text="Doctor accepted chat request")
    
    class Meta:
        unique_together = ('patient', 'doctor')
        ordering = ['-last_message_at', '-created_at']
    
    def __str__(self):
        return f"Chat: {self.patient.username} <-> Dr. {self.doctor.username}"
    
    def get_other_participant(self, current_user):
        """Get the other participant in the chat"""
        return self.doctor if current_user == self.patient else self.patient
    
    def update_last_message_time(self):
        """Update the last message timestamp"""
        self.last_message_at = timezone.now()
        self.save(update_fields=['last_message_at'])