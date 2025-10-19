from django.db import models
from ..profile_models import DoctorProfile
from ..facility_models import Facility
from django.core.exceptions import ValidationError


class Shift(models.Model):
    """
    Represents a doctor's working shift at a specific facility.
    """
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6
    
    DAY_CHOICES = [
        (MONDAY, 'Monday'),
        (TUESDAY, 'Tuesday'),
        (WEDNESDAY, 'Wednesday'),
        (THURSDAY, 'Thursday'),
        (FRIDAY, 'Friday'),
        (SATURDAY, 'Saturday'),
        (SUNDAY, 'Sunday'),
    ]
    
    doctor = models.ForeignKey(
        DoctorProfile, 
        on_delete=models.CASCADE, 
        related_name='shifts', null=True, blank=True,
    )
    facility = models.ForeignKey(
        Facility, 
        on_delete=models.CASCADE, 
        related_name='shifts'
    )
    day_of_week = models.IntegerField(choices=DAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['day_of_week', 'start_time']
        unique_together = ['doctor', 'facility', 'day_of_week', 'start_time']
    
    def clean(self):
        """Validate shift times"""
        if self.start_time >= self.end_time:
            raise ValidationError("Start time must be before end time")
        
        # Check for overlapping shifts for the same doctor at the same facility
        overlapping = Shift.objects.filter(
            doctor=self.doctor,
            facility=self.facility,
            day_of_week=self.day_of_week,
            is_active=True
        ).exclude(pk=self.pk)
        
        for shift in overlapping:
            if (self.start_time < shift.end_time and self.end_time > shift.start_time):
                raise ValidationError(
                    f"This shift overlaps with existing shift: {shift.start_time} - {shift.end_time}"
                )
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.doctor.first_name} {self.doctor.last_name} - {self.get_day_of_week_display()} ({self.start_time}-{self.end_time}) @ {self.facility.name}"
