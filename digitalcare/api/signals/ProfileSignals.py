from django.db.models.signals import post_save
from django.dispatch import receiver
from ..models import (
    User, VisitorProfile, StudentProfile, AdultProfile, DoctorProfile,
    PharmacistProfile, LabTechProfile, Facility
)

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        if instance.role == User.STUDENT:
            StudentProfile.objects.create(user=instance)
        elif instance.role == User.VISITOR:
            VisitorProfile.objects.create(user=instance)
        elif instance.role == User.ADULT:
            AdultProfile.objects.create(user=instance)
        elif instance.role == User.DOCTOR:
            DoctorProfile.objects.create(user=instance)
        elif instance.role == User.PHARMACIST:
            PharmacistProfile.objects.create(user=instance)
        elif instance.role == User.LAB_TECH:
            LabTechProfile.objects.create(user=instance)
        elif instance.role == User.FACILITY_ADMIN:
            Facility.objects.create(admin=instance, status='Pending')  # Default fields

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if instance.role == User.STUDENT and hasattr(instance, 'studentprofile'):
        instance.studentprofile.save()
    elif instance.role == User.VISITOR and hasattr(instance, 'visitorprofile'):
        instance.visitorprofile.save()
    elif instance.role == User.ADULT and hasattr(instance, 'adultprofile'):
        instance.adultprofile.save()
    elif instance.role == User.DOCTOR and hasattr(instance, 'doctorprofile'):
        instance.doctorprofile.save()
    elif instance.role == User.PHARMACIST and hasattr(instance, 'pharmacistprofile'):
        instance.pharmacistprofile.save()
    elif instance.role == User.LAB_TECH and hasattr(instance, 'labtechprofile'):
        instance.labtechprofile.save()
    elif instance.role == User.FACILITY_ADMIN and hasattr(instance, 'facility'):
        instance.facility.save()
