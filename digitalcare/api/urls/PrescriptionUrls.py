# api/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from ..views import PrescriptionViewSet, PrescriptionPDF

router = DefaultRouter()
router.register(r'prescriptions', PrescriptionViewSet, basename='prescription')

urlpatterns = [
    path('', include(router.urls)),
    path('prescriptions/<int:pk>/pdf/', PrescriptionPDF, name='prescription-pdf'),
]
