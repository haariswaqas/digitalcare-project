# api/models/profile_models/PharmacistProfile.py
from django.db import models
from ..authentication_models import User
from ..facility_models import Facility

class PharmacistProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=100, null=True, blank=True)
    middle_name = models.CharField(max_length=100, null=True, blank=True)
    last_name = models.CharField(max_length=100, null=True, blank=True)
    
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    
    pharmacies = models.ManyToManyField(
        Facility, 
        related_name='pharmacists', 
        blank=True,
        limit_choices_to={'facility_type': 'pharmacy'}
    )
    is_active = models.BooleanField(default=True)
    license_number = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.id}--- Pharmacist {self.first_name} {self.last_name}"
