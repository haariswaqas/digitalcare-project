from django.urls import path, include
from rest_framework.routers import DefaultRouter
from ..views import DrugViewSet, PharmacyInventoryViewSet

router = DefaultRouter()
router.register(r'drugs', DrugViewSet, basename='drug')
router.register(r'pharmacy-inventory', PharmacyInventoryViewSet, basename='pharmacy-inventory')

urlpatterns = [
    path('', include(router.urls)),
]
