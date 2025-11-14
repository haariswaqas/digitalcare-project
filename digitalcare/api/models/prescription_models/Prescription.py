from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from ..profile_models import DoctorProfile
from ..authentication_models import User


class Prescription(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('ACTIVE', 'Active'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
        ('EXPIRED', 'Expired'),
    ]

    doctor = models.ForeignKey(
        DoctorProfile,
        on_delete=models.SET_NULL,
        null=True,
        related_name='prescriptions_given'
    )

    # Point directly to User with role constraint
    patient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="prescriptions",
        limit_choices_to={"role__in": ["student", "adult", "visitor"]}, default=5
    )

    issued_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    valid_from = models.DateField(auto_now_add=True, null=True, blank=True)
    valid_until = models.DateField(null=True, blank=True)

    instructions = models.TextField(blank=True)
    diagnosis = models.TextField(blank=True, help_text="Reason for prescription")
    notes = models.TextField(blank=True, help_text="Internal notes for pharmacist")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='ACTIVE')

    class Meta:
        ordering = ['-issued_at']
        indexes = [
            models.Index(fields=['patient', '-issued_at']),
            models.Index(fields=['status', '-issued_at']),
            models.Index(fields=['valid_until', 'status']),
        ]

    def clean(self):
        """Validate patient role"""
        if self.patient and self.patient.role not in ['student', 'adult', 'visitor']:
            raise ValidationError({
                'patient': f'User must be a patient (student/adult/visitor), not {self.patient.role}'
            })

    def save(self, *args, **kwargs):
        """Validate and auto-expire"""
        self.full_clean()  # Run validation
        
        # Auto-expire if past valid_until date
        if self.valid_until and self.status not in ['EXPIRED', 'CANCELLED', 'COMPLETED']:
            today = timezone.localdate()
            if today > self.valid_until:
                self.status = 'EXPIRED'
        
        super().save(*args, **kwargs)

    def get_patient_profile(self):
        """
        Get the actual patient profile (StudentProfile, AdultProfile, or VisitorProfile)
        with caching to avoid repeated queries
        """
        if not hasattr(self, '_patient_profile_cache'):
            patient = self.patient
            if patient.role == 'student':
                self._patient_profile_cache = patient.studentprofile
            elif patient.role == 'adult':
                self._patient_profile_cache = patient.adultprofile
            elif patient.role == 'visitor':
                self._patient_profile_cache = patient.visitorprofile
            else:
                self._patient_profile_cache = None
        return self._patient_profile_cache

    @property
    def patient_profile(self):
        """Convenience property"""
        return self.get_patient_profile()

    @property
    def patient_name(self):
        """Get patient's full name"""
        return self.patient.get_full_name()
    
    @property
    def patient_type(self):
        """Return patient role"""
        return self.patient.role

    @property
    def is_valid(self):
        """Check if prescription is currently valid"""
        if self.status != 'ACTIVE':
            return False
        if self.valid_until:
            return timezone.localdate() <= self.valid_until
        return True

    def __str__(self):
        doctor_name = f"Dr. {self.doctor.user.get_full_name()}" if self.doctor else "Unknown"
        return f"Rx for {self.patient_name} by {doctor_name} ({self.issued_at.strftime('%Y-%m-%d')})"

