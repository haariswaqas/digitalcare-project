from django.db import models
from ..authentication_models import User

class VideoConsultation(models.Model):
    STATUS_CHOICES = [
        ("requested", "Requested"),
        ("accepted", "Accepted"),
        ("started", "Started"),
        ("finished", "Finished"),
        ("cancelled", "Cancelled"),
    ]

    patient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="patient_consultations",
        limit_choices_to={"role__in": ["student", "adult", "visitor"]},  # only valid patient roles
    )
    doctor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="doctor_consultations",
        limit_choices_to={"role": "doctor"},
    )
    created_at = models.DateTimeField(auto_now_add=True)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="requested")
    provider_room = models.CharField(max_length=255, null=True, blank=True)
    provider_kind = models.CharField(max_length=50, default="twilio")
    metadata = models.JSONField(default=dict, blank=True)  # to store token metadata
    recording_url = models.URLField(null=True, blank=True)

    def __str__(self):
        return f"Consult {self.id} ({self.patient} → {self.doctor})"
