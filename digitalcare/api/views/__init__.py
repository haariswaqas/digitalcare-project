from .AuthViews import LoginView, RegisterView, OTPVerificationView, ResendOTPView
from .PasswordResetViews import *
from .ProfileViews import BaseProfileView, StudentProfileView, VisitorProfileView, AdultProfileView, DoctorProfileView, PharmacistProfileView, LabTechProfileView
from .HealthCardViews import *
from .health_card_views import *
from .FacilityViews import *
from .AppointmentViews import *
from .AppointmentReminderViews import *

from .ChatViews import *
from .ConsultationViews import *
from .DrugViews import DrugViewSet, PharmacyInventoryViewSet
from .PrescriptionViews import PrescriptionViewSet, PrescriptionItemViewSet
from .PrescriptionPDFView import *
from .SymptomViews import *
from .ProviderSearch import *
from .VideoConsultationViews import *

from .AdminUserViews import *
from .ShiftViews import *

from .CloudinaryTestView import *
from .TestFileUploadView import *