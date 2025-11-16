from ..views import cloudinary_diagnostic, test_file_upload

from django.urls import path
urlpatterns = [
   
    path('cloudinary-diagnostic/', cloudinary_diagnostic, name='cloudinary-diagnostic'),
    path('test-file-upload/', test_file_upload, name='test-file-upload')
]