# api/urls.py
from django.urls import path
from ..views import ProviderSearch as provider_search

urlpatterns = [
    path('providers/nearby/', provider_search.nearby_providers, name='nearby-providers'),
    path('patients/update-location/', provider_search.update_user_location, name='update-patient-location'),
]
