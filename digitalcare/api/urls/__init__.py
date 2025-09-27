from .ProfileUrls import urlpatterns as ProfileUrls
from .AuthUrls import urlpatterns as AuthUrls
from .PasswordResetUrls import urlpatterns as PasswordResetUrls
from .FacilityUrls import urlpatterns as FacilityUrls
from .AppointmentUrls import urlpatterns as AppointmentUrls
from .ChatUrls import urlpatterns as ChatUrls
from .ConsultationUrls import urlpatterns as ConsultationUrls
from .VideoConsultationUrls import urlpatterns as VideoConsultationUrls
from .PrescriptionUrls import urlpatterns as PrescriptionUrls
from .SymptomUrls import urlpatterns as SymptomUrls 
from .ProviderSearchUrls import urlpatterns as ProviderSearchUrls
from .AdminUserUrls import urlpatterns as AdminUserUrls

urlpatterns = (
    ProfileUrls 
    + AuthUrls 
    + PasswordResetUrls 
    + FacilityUrls 
    + AppointmentUrls 
    + ChatUrls
    + ConsultationUrls + VideoConsultationUrls
    + PrescriptionUrls
    + SymptomUrls + ProviderSearchUrls + AdminUserUrls
)
