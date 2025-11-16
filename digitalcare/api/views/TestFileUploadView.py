# Add this test endpoint to api/views.py

from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import cloudinary.uploader

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def test_file_upload(request):
    """
    Test endpoint to verify file uploads go to Cloudinary
    
    Send a POST request with a file in the 'file' field
    """
    
    if 'file' not in request.FILES:
        return Response(
            {'error': 'No file provided. Send a file in the "file" field.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    uploaded_file = request.FILES['file']
    
    # Test 1: Check the default storage backend
    storage_info = {
        'storage_backend': str(type(default_storage)),
        'storage_class': default_storage.__class__.__name__,
    }
    
    # Test 2: Try saving with Django's default storage
    try:
        # This should use Cloudinary if configured correctly
        file_path = default_storage.save(
            f'test_uploads/{uploaded_file.name}',
            ContentFile(uploaded_file.read())
        )
        
        # Get the URL
        file_url = default_storage.url(file_path)
        
        django_save_result = {
            'success': True,
            'file_path': file_path,
            'file_url': file_url,
            'uses_cloudinary': 'cloudinary.com' in file_url or 'res.cloudinary.com' in file_url,
        }
        
        # Clean up test file
        try:
            default_storage.delete(file_path)
        except:
            pass
            
    except Exception as e:
        django_save_result = {
            'success': False,
            'error': str(e)
        }
    
    # Test 3: Try direct Cloudinary upload
    uploaded_file.seek(0)  # Reset file pointer
    try:
        result = cloudinary.uploader.upload(
            uploaded_file,
            folder='test_direct_upload',
            resource_type='auto'
        )
        
        cloudinary_direct_result = {
            'success': True,
            'url': result.get('secure_url'),
            'public_id': result.get('public_id'),
            'format': result.get('format'),
            'resource_type': result.get('resource_type'),
        }
        
        # Clean up
        try:
            cloudinary.uploader.destroy(result['public_id'])
        except:
            pass
            
    except Exception as e:
        cloudinary_direct_result = {
            'success': False,
            'error': str(e)
        }
    
    # Diagnosis
    issues = []
    
    if not django_save_result.get('success'):
        issues.append(f"❌ Django default_storage.save() failed: {django_save_result.get('error')}")
    elif not django_save_result.get('uses_cloudinary'):
        issues.append(f"❌ Django is saving to local storage, not Cloudinary. URL: {django_save_result.get('file_url')}")
    
    if not cloudinary_direct_result.get('success'):
        issues.append(f"❌ Direct Cloudinary upload failed: {cloudinary_direct_result.get('error')}")
    
    all_good = (
        django_save_result.get('success') and 
        django_save_result.get('uses_cloudinary') and
        cloudinary_direct_result.get('success')
    )
    
    return Response({
        'status': 'OK' if all_good else 'ISSUES_FOUND',
        'storage_info': storage_info,
        'django_default_storage_test': django_save_result,
        'cloudinary_direct_upload_test': cloudinary_direct_result,
        'issues': issues if issues else ['✅ All tests passed! Files are uploading to Cloudinary.'],
        'recommendation': (
            '✅ Everything works! Your profile picture uploads should now go to Cloudinary.'
            if all_good
            else '⚠️ There are issues with file uploads. Check the details above.'
        )
    })


# Add to api/urls.py:
"""
from .views import test_file_upload

urlpatterns = [
    # ... existing urls
    path('test-file-upload/', test_file_upload, name='test-file-upload'),
]
"""


# ============================================
# ALTERNATIVE: Check if there's a MODEL issue
# ============================================

# Make sure your model looks like this:
"""
# api/models.py

from django.db import models

class StudentProfile(models.Model):
    user = models.OneToOneField('User', on_delete=models.CASCADE)
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100)
    
    # This should automatically use Cloudinary
    profile_picture = models.ImageField(
        upload_to='profile_pictures/',
        blank=True,
        null=True
    )
    
    # NOT THIS - don't specify storage explicitly:
    # profile_picture = models.ImageField(
    #     upload_to='profile_pictures/',
    #     storage=SomeOtherStorage(),  # ← REMOVE THIS if present
    #     blank=True,
    #     null=True
    # )
"""


# ============================================
# CRITICAL: Check if you have migrations issue
# ============================================

"""
After confirming settings are correct, you MUST:

1. Make new migrations:
   python manage.py makemigrations

2. Apply migrations:
   python manage.py migrate

3. Restart server

This ensures the model uses the new storage backend.
"""


# ============================================
# Manual test with curl (if you prefer)
# ============================================

"""
curl -X POST https://digitalcare-project.onrender.com/api/test-file-upload/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@/path/to/your/image.jpg"
"""