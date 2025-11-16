# Step 1: Create a simple diagnostic view
# Add this to api/views.py

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.conf import settings
import cloudinary
import sys

@api_view(['GET'])
@permission_classes([AllowAny])  # Public for testing
def cloudinary_diagnostic(request):
    """Diagnose Cloudinary configuration issues"""
    
    # Check Python version
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    
    # Check if cloudinary_storage is installed
    try:
        import cloudinary_storage
        cloudinary_storage_installed = True
        cloudinary_storage_version = getattr(cloudinary_storage, '__version__', 'unknown')
    except ImportError:
        cloudinary_storage_installed = False
        cloudinary_storage_version = None
    
    # Check if cloudinary is installed
    try:
        import cloudinary
        cloudinary_installed = True
        cloudinary_version = getattr(cloudinary, '__version__', 'unknown')
    except ImportError:
        cloudinary_installed = False
        cloudinary_version = None
    
    # Get cloudinary config
    config = cloudinary.config()
    
    # Check environment variables
    import os
    env_vars = {
        'CLOUDINARY_CLOUD_NAME': os.environ.get('CLOUDINARY_CLOUD_NAME', 'NOT SET'),
        'CLOUDINARY_API_KEY': 'SET' if os.environ.get('CLOUDINARY_API_KEY') else 'NOT SET',
        'CLOUDINARY_API_SECRET': 'SET' if os.environ.get('CLOUDINARY_API_SECRET') else 'NOT SET',
    }
    
    # Check settings
    settings_check = {
        'DEFAULT_FILE_STORAGE': settings.DEFAULT_FILE_STORAGE,
        'INSTALLED_APPS_HAS_CLOUDINARY_STORAGE': 'cloudinary_storage' in settings.INSTALLED_APPS,
        'INSTALLED_APPS_HAS_CLOUDINARY': 'cloudinary' in settings.INSTALLED_APPS,
        'MEDIA_URL': settings.MEDIA_URL,
        'MEDIA_ROOT': str(settings.MEDIA_ROOT),
    }
    
    # Check INSTALLED_APPS order
    try:
        cloudinary_storage_index = settings.INSTALLED_APPS.index('cloudinary_storage')
        cloudinary_index = settings.INSTALLED_APPS.index('cloudinary')
        api_index = settings.INSTALLED_APPS.index('api')
        
        apps_order_correct = (
            cloudinary_storage_index < cloudinary_index < api_index
        )
    except ValueError:
        apps_order_correct = False
        cloudinary_storage_index = None
        cloudinary_index = None
        api_index = None
    
    # Test cloudinary connection
    cloudinary_test = {
        'configured': bool(config.cloud_name and config.api_key and config.api_secret),
        'cloud_name': config.cloud_name or 'NOT SET',
        'api_key_present': bool(config.api_key),
        'api_secret_present': bool(config.api_secret),
        'secure': getattr(config, 'secure', None),
    }
    
    # Try a test upload
    upload_test = {
        'attempted': False,
        'success': False,
        'error': None,
        'url': None,
    }
    
    if cloudinary_test['configured']:
        try:
            upload_test['attempted'] = True
            result = cloudinary.uploader.upload(
                "https://via.placeholder.com/150",
                folder="diagnostic_test",
                public_id="test"
            )
            upload_test['success'] = True
            upload_test['url'] = result.get('secure_url')
            
            # Clean up
            try:
                cloudinary.uploader.destroy(result['public_id'])
            except:
                pass
                
        except Exception as e:
            upload_test['error'] = str(e)
    
    # Overall diagnosis
    issues = []
    
    if not cloudinary_storage_installed:
        issues.append("❌ django-cloudinary-storage is not installed")
    
    if not cloudinary_installed:
        issues.append("❌ cloudinary is not installed")
    
    if settings.DEFAULT_FILE_STORAGE != 'cloudinary_storage.storage.MediaCloudinaryStorage':
        issues.append(f"❌ DEFAULT_FILE_STORAGE is set to '{settings.DEFAULT_FILE_STORAGE}' instead of 'cloudinary_storage.storage.MediaCloudinaryStorage'")
    
    if not settings_check['INSTALLED_APPS_HAS_CLOUDINARY_STORAGE']:
        issues.append("❌ 'cloudinary_storage' not in INSTALLED_APPS")
    
    if not settings_check['INSTALLED_APPS_HAS_CLOUDINARY']:
        issues.append("❌ 'cloudinary' not in INSTALLED_APPS")
    
    if not apps_order_correct:
        issues.append("❌ INSTALLED_APPS order is incorrect. cloudinary_storage must be before cloudinary, and both before 'api'")
    
    if env_vars['CLOUDINARY_CLOUD_NAME'] == 'NOT SET':
        issues.append("❌ CLOUDINARY_CLOUD_NAME environment variable not set")
    
    if env_vars['CLOUDINARY_API_KEY'] == 'NOT SET':
        issues.append("❌ CLOUDINARY_API_KEY environment variable not set")
    
    if env_vars['CLOUDINARY_API_SECRET'] == 'NOT SET':
        issues.append("❌ CLOUDINARY_API_SECRET environment variable not set")
    
    if not cloudinary_test['configured']:
        issues.append("❌ Cloudinary config is incomplete")
    
    if upload_test['attempted'] and not upload_test['success']:
        issues.append(f"❌ Test upload failed: {upload_test['error']}")
    
    # Success check
    all_good = len(issues) == 0 and upload_test['success']
    
    return Response({
        'status': 'OK' if all_good else 'ISSUES_FOUND',
        'all_configured': all_good,
        'python_version': python_version,
        'packages': {
            'cloudinary_storage_installed': cloudinary_storage_installed,
            'cloudinary_storage_version': cloudinary_storage_version,
            'cloudinary_installed': cloudinary_installed,
            'cloudinary_version': cloudinary_version,
        },
        'environment_variables': env_vars,
        'django_settings': settings_check,
        'installed_apps_order': {
            'correct': apps_order_correct,
            'cloudinary_storage_index': cloudinary_storage_index,
            'cloudinary_index': cloudinary_index,
            'api_index': api_index,
        },
        'cloudinary_config': cloudinary_test,
        'upload_test': upload_test,
        'issues': issues if issues else ['✅ All checks passed!'],
        'recommendation': (
            "✅ Cloudinary is properly configured! Try uploading a new image."
            if all_good
            else "⚠️ Fix the issues listed above, then restart your server."
        )
    })


# Step 2: Add this to your api/urls.py
"""
from .views import cloudinary_diagnostic

urlpatterns = [
    # ... your existing urls
    path('cloudinary-diagnostic/', cloudinary_diagnostic, name='cloudinary-diagnostic'),
]
"""


# Step 3: Check your requirements.txt - should have these EXACT versions
"""
django-cloudinary-storage==0.3.0
cloudinary==1.41.0
Pillow>=9.0.0
"""


# Step 4: Double-check your settings.py has this EXACT configuration
"""
import cloudinary

# Get from environment
CLOUDINARY_CLOUD_NAME = os.environ.get('CLOUDINARY_CLOUD_NAME')
CLOUDINARY_API_KEY = os.environ.get('CLOUDINARY_API_KEY')
CLOUDINARY_API_SECRET = os.environ.get('CLOUDINARY_API_SECRET')

# Configure cloudinary
cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET,
    secure=True
)

# THIS LINE IS CRITICAL - must be EXACTLY this
DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'

# Cloudinary storage settings
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': CLOUDINARY_CLOUD_NAME,
    'API_KEY': CLOUDINARY_API_KEY,
    'API_SECRET': CLOUDINARY_API_SECRET,
}
"""


# Step 5: Verify INSTALLED_APPS order
"""
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # CRITICAL: These MUST be in this order and BEFORE 'api'
    'cloudinary_storage',  # ← FIRST
    'cloudinary',          # ← SECOND
    
    # Third party
    'corsheaders',
    'rest_framework',
    'channels',
    'channels_redis',
    'rest_framework_simplejwt.token_blacklist',
    
    # Your app LAST
    'api',  # ← MUST BE AFTER CLOUDINARY
    'django_celery_beat',
]
"""