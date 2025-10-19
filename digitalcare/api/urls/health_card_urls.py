# api/urls.py (add these to your existing urls)
from django.urls import path
from ..views import (scan_health_card, my_health_card, download_health_card_data, regenerate_qr_code, set_card_pin, scan_history)

urlpatterns = [
    
    # Public QR scan endpoint (no auth required)
    path('health-card/scan/<str:access_token>/', 
         scan_health_card, 
         name='scan_health_card'),
    
    # Authenticated endpoints
    path('health-card/me/', 
         my_health_card, 
         name='my_health_card'),
    
    path('health-card/download/', 
         download_health_card_data, 
         name='download_health_card_data'),
    
    path('health-card/regenerate-qr/', 
         regenerate_qr_code, 
         name='regenerate_qr_code'),
    
    path('health-card/set-pin/', 
         set_card_pin, 
         name='set_card_pin'),
    
    path('health-card/scan-history/', 
         scan_history, 
         name='scan_history'),
]