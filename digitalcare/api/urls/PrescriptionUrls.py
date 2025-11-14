from django.urls import path, include
from rest_framework.routers import DefaultRouter
from ..views import PrescriptionViewSet, PrescriptionItemViewSet

router = DefaultRouter()
router.register(r'prescriptions', PrescriptionViewSet, basename='prescription')
router.register(r'prescription-items', PrescriptionItemViewSet, basename='prescription-item')

urlpatterns = [
    path('', include(router.urls)),
]
