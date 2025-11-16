# 1. First, create a management command to test Cloudinary
# api/management/commands/test_cloudinary.py

from django.core.management.base import BaseCommand
from django.conf import settings
import cloudinary
import cloudinary.uploader

class Command(BaseCommand):
    help = 'Test Cloudinary configuration'

    def handle(self, *args, **options):
        self.stdout.write("="*60)
        self.stdout.write("🔍 Testing Cloudinary Configuration")
        self.stdout.write("="*60)
        
        # Check environment variables
        self.stdout.write("\n1. Environment Variables:")
        self.stdout.write(f"   CLOUDINARY_CLOUD_NAME: {settings.CLOUDINARY_CLOUD_NAME or '❌ NOT SET'}")
        self.stdout.write(f"   CLOUDINARY_API_KEY: {'✅ SET' if settings.CLOUDINARY_API_KEY else '❌ NOT SET'}")
        self.stdout.write(f"   CLOUDINARY_API_SECRET: {'✅ SET' if settings.CLOUDINARY_API_SECRET else '❌ NOT SET'}")
        
        # Check cloudinary config
        self.stdout.write("\n2. Cloudinary Config:")
        config = cloudinary.config()
        self.stdout.write(f"   Cloud Name: {config.cloud_name or '❌ NOT CONFIGURED'}")
        self.stdout.write(f"   API Key: {'✅ CONFIGURED' if config.api_key else '❌ NOT CONFIGURED'}")
        self.stdout.write(f"   API Secret: {'✅ CONFIGURED' if config.api_secret else '❌ NOT CONFIGURED'}")
        
        # Check DEFAULT_FILE_STORAGE
        self.stdout.write("\n3. Storage Backend:")
        self.stdout.write(f"   DEFAULT_FILE_STORAGE: {settings.DEFAULT_FILE_STORAGE}")
        expected = 'cloudinary_storage.storage.MediaCloudinaryStorage'
        if settings.DEFAULT_FILE_STORAGE == expected:
            self.stdout.write(self.style.SUCCESS("   ✅ Correctly set to Cloudinary"))
        else:
            self.stdout.write(self.style.ERROR(f"   ❌ Should be: {expected}"))
        
        # Test upload
        self.stdout.write("\n4. Testing Upload:")
        try:
            result = cloudinary.uploader.upload(
                "https://via.placeholder.com/150",
                folder="test",
                public_id="test_upload"
            )
            self.stdout.write(self.style.SUCCESS("   ✅ Upload successful!"))
            self.stdout.write(f"   URL: {result['secure_url']}")
            
            # Clean up test file
            cloudinary.uploader.destroy(result['public_id'])
            self.stdout.write("   🧹 Test file cleaned up")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"   ❌ Upload failed: {str(e)}"))
        
        self.stdout.write("\n" + "="*60)


# 2. Check your model - it should look like this:
# api/models.py

"""
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100)
    
    # THIS SHOULD WORK WITH CLOUDINARY if DEFAULT_FILE_STORAGE is set correctly
    profile_picture = models.ImageField(
        upload_to='profile_pictures/',  # This becomes a folder in Cloudinary
        blank=True,
        null=True
    )
    
    # ... rest of your fields
    
    def __str__(self):
        return f"{self.first_name} {self.last_name}"
"""


# 3. Updated settings.py - CRITICAL FIXES
# settings.py

"""
# ===== CLOUDINARY CONFIGURATION - FIXED =====

import os
import cloudinary

# Get credentials
CLOUDINARY_CLOUD_NAME = os.environ.get('CLOUDINARY_CLOUD_NAME')
CLOUDINARY_API_KEY = os.environ.get('CLOUDINARY_API_KEY')  
CLOUDINARY_API_SECRET = os.environ.get('CLOUDINARY_API_SECRET')

# Validate
if not all([CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET]):
    print("⚠️  WARNING: Cloudinary not configured. Using local storage.")
    print(f"    CLOUDINARY_CLOUD_NAME: {CLOUDINARY_CLOUD_NAME or 'NOT SET'}")
    print(f"    CLOUDINARY_API_KEY: {'SET' if CLOUDINARY_API_KEY else 'NOT SET'}")
    print(f"    CLOUDINARY_API_SECRET: {'SET' if CLOUDINARY_API_SECRET else 'NOT SET'}")

# Configure cloudinary
cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET,
    secure=True
)

# Cloudinary Storage Settings
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': CLOUDINARY_CLOUD_NAME,
    'API_KEY': CLOUDINARY_API_KEY,
    'API_SECRET': CLOUDINARY_API_SECRET,
}

# THIS IS THE MOST IMPORTANT LINE - Set Cloudinary as default storage
DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'

# Media settings (Cloudinary will override these)
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
"""


# 4. Check your installed apps order - THIS IS CRITICAL
"""
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # ⚠️ CLOUDINARY MUST BE BEFORE YOUR APP
    'cloudinary_storage',  # Must be BEFORE cloudinary
    'cloudinary',          # Must be BEFORE your app
    
    # Third party apps
    'corsheaders',
    'rest_framework',
    'channels',
    'channels_redis',
    'rest_framework_simplejwt.token_blacklist',
    
    # Your apps - MUST BE AFTER CLOUDINARY
    'api',
    'django_celery_beat',
]
"""


# 5. Verify requirements.txt
"""
django-cloudinary-storage==0.3.0
cloudinary==1.41.0
"""


# 6. Create a test view to verify (optional)
# api/views.py

"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.conf import settings
import cloudinary

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def test_cloudinary_config(request):
    '''Test endpoint to check Cloudinary configuration'''
    
    config = cloudinary.config()
    
    return Response({
        'storage_backend': settings.DEFAULT_FILE_STORAGE,
        'cloudinary_configured': bool(config.cloud_name and config.api_key),
        'cloud_name': config.cloud_name,
        'secure': config.secure if hasattr(config, 'secure') else None,
    })
"""


# 7. Add to urls.py
"""
from api.views import test_cloudinary_config

urlpatterns = [
    # ... your other urls
    path('api/test-cloudinary/', test_cloudinary_config, name='test-cloudinary'),
]
"""