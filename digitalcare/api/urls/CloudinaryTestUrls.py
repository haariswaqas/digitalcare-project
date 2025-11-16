from ..views import cloudinary_diagnostic

from django.urls import path
urlpatterns = [
   
    path('cloudinary-diagnostic/', cloudinary_diagnostic, name='cloudinary-diagnostic'),
]