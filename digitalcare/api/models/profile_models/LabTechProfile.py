# api/models/profile_models/LabTechProfile.py
from django.db import models
from ..authentication_models import User
from ..facility_models import Facility

class LabTechProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=100, null=True, blank=True)
    middle_name = models.CharField(max_length=100, null=True, blank=True)
    last_name = models.CharField(max_length=100, null=True, blank=True)
    
    specialty = models.CharField(max_length=150, blank=True)  # e.g., "Hematology", "Microbiology"
    
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    
    laboratories = models.ManyToManyField(
        Facility, 
        related_name='lab_techs', 
        blank=True,
        limit_choices_to={'facility_type': 'laboratory'}
    )
    is_active = models.BooleanField(default=True)
    license_number = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.id}--- Lab Tech {self.first_name} {self.last_name}"