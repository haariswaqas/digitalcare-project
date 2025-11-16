from .ProfileUrls import urlpatterns as ProfileUrls
from .AuthUrls import urlpatterns as AuthUrls
from .health_card_urls import urlpatterns as HealthCardUrls

from .PasswordResetUrls import urlpatterns as PasswordResetUrls
from .FacilityUrls import urlpatterns as FacilityUrls
from .AppointmentUrls import urlpatterns as AppointmentUrls
from .SchedulerUrls import urlpatterns as SchedulerUrls
from .ChatUrls import urlpatterns as ChatUrls
from .ConsultationUrls import urlpatterns as ConsultationUrls
from .VideoConsultationUrls import urlpatterns as VideoConsultationUrls
from .DrugUrls import urlpatterns as DrugUrls

from .PrescriptionUrls import urlpatterns as PrescriptionUrls
from .SymptomUrls import urlpatterns as SymptomUrls 
from .ProviderSearchUrls import urlpatterns as ProviderSearchUrls
from .AdminUserUrls import urlpatterns as AdminUserUrls
from .ShiftUrls import urlpatterns as ShiftUrls


from .CloudinaryTestUrls import urlpatterns as CloudinaryTestUrls

urlpatterns = (
    ProfileUrls 
    + AuthUrls 
    + PasswordResetUrls 
    + FacilityUrls 
    + AppointmentUrls 
    + ChatUrls
    + ConsultationUrls + VideoConsultationUrls
    + DrugUrls
    + PrescriptionUrls
    + SymptomUrls + ProviderSearchUrls + AdminUserUrls +ShiftUrls + HealthCardUrls + SchedulerUrls + CloudinaryTestUrls
)
