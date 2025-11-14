from django.urls import path
from api.views import (
    StudentProfileView,
    VisitorProfileView,
    AdultProfileView,
    DoctorProfileView,
    PharmacistProfileView,
    LabTechProfileView
)

urlpatterns = [
    path("student/profile/", StudentProfileView.as_view(), name="student-profile"),
    path("visitor/profile/", VisitorProfileView.as_view(), name="visitor-profile"),
    path("adult/profile/", AdultProfileView.as_view(), name="adult-profile"),
    path("doctor/profile/", DoctorProfileView.as_view(), name="doctor-profile"),
    path("pharmacist/profile/", PharmacistProfileView.as_view(), name="pharmacist-profile"),
    path("lab-tech/profile/", LabTechProfileView.as_view(), name="lab-tech-profile"),
]