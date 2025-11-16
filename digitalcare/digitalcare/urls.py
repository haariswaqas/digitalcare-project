from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from django.contrib import admin

# main urls.py
urlpatterns = [
    path('admin/', admin.site.urls),
    path("api/", include("api.urls")),
]

# Only serve local media files in DEBUG mode (development without Cloudinary)
# When using Cloudinary, media files are served directly from Cloudinary's CDN
# So we don't need to add static() for media in production
if settings.DEBUG and not settings.DEFAULT_FILE_STORAGE == 'cloudinary_storage.storage.MediaCloudinaryStorage':
    # Only add local media serving if NOT using Cloudinary
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Static files are always served by whitenoise in production
# In development, Django's runserver handles them automatically