from rest_framework import serializers
from ..models import (
    StudentProfile, 
    VisitorProfile, 
    AdultProfile, 
    DoctorProfile, 
    PharmacistProfile, 
    LabTechProfile
)


class BaseProfileSerializer(serializers.ModelSerializer):
    """Base serializer with common fields and methods"""
    
    # Read-only field that returns the full Cloudinary URL
    profile_picture_url = serializers.SerializerMethodField()
    
    # Optional: Add thumbnail URL
    profile_picture_thumbnail = serializers.SerializerMethodField()
    
    def get_profile_picture_url(self, obj):
        """Return full Cloudinary URL for profile picture"""
        if obj.profile_picture:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.profile_picture.url)
            return obj.profile_picture.url
        return None
    
    def get_profile_picture_thumbnail(self, obj):
        """Return thumbnail version of profile picture"""
        if obj.profile_picture:
            # Cloudinary automatically handles transformations
            # You can append transformations to the URL
            url = obj.profile_picture.url
            # Example: Insert transformation parameters
            # This works if using cloudinary_storage
            if 'cloudinary' in url:
                # Insert transformation before the version number
                parts = url.split('/upload/')
                if len(parts) == 2:
                    transformed_url = f"{parts[0]}/upload/w_150,h_150,c_fill,g_face/{parts[1]}"
                    return transformed_url
            return url
        return None
    
    def validate_profile_picture(self, value):
        """Validate profile picture file"""
        if value:
            # Check file size (5MB limit)
            if value.size > 5 * 1024 * 1024:
                raise serializers.ValidationError(
                    "Profile picture size should not exceed 5MB."
                )
            
            # Check file type
            allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp']
            if hasattr(value, 'content_type') and value.content_type not in allowed_types:
                raise serializers.ValidationError(
                    "Only JPEG, PNG, GIF, and WebP images are allowed."
                )
        
        return value
    
    def validate(self, data):
        """Validate latitude and longitude together"""
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        
        # If one is provided, both should be provided
        if (latitude is not None and longitude is None) or (longitude is not None and latitude is None):
            raise serializers.ValidationError(
                "Both latitude and longitude must be provided together."
            )
        
        # Validate ranges
        if latitude is not None and (latitude < -90 or latitude > 90):
            raise serializers.ValidationError(
                "Latitude must be between -90 and 90."
            )
        
        if longitude is not None and (longitude < -180 or longitude > 180):
            raise serializers.ValidationError(
                "Longitude must be between -180 and 180."
            )
        
        return data


class StudentProfileSerializer(BaseProfileSerializer):
    class Meta:
        model = StudentProfile
        fields = '__all__'
        read_only_fields = ('user', 'profile_picture_url', 'profile_picture_thumbnail')
        extra_kwargs = {
            'profile_picture': {'required': False, 'allow_null': True},
            'latitude': {'required': False, 'allow_null': True},
            'longitude': {'required': False, 'allow_null': True},
        }


class VisitorProfileSerializer(BaseProfileSerializer):
    class Meta:
        model = VisitorProfile
        fields = '__all__'
        read_only_fields = ('user', 'profile_picture_url', 'profile_picture_thumbnail')
        extra_kwargs = {
            'profile_picture': {'required': False, 'allow_null': True},
            'latitude': {'required': False, 'allow_null': True},
            'longitude': {'required': False, 'allow_null': True},
        }


class AdultProfileSerializer(BaseProfileSerializer):
    class Meta:
        model = AdultProfile
        fields = '__all__'
        read_only_fields = ('user', 'profile_picture_url', 'profile_picture_thumbnail')
        extra_kwargs = {
            'profile_picture': {'required': False, 'allow_null': True},
            'latitude': {'required': False, 'allow_null': True},
            'longitude': {'required': False, 'allow_null': True},
        }


class DoctorProfileSerializer(BaseProfileSerializer):
    class Meta:
        model = DoctorProfile
        fields = '__all__'
        read_only_fields = ('user', 'profile_picture_url', 'profile_picture_thumbnail')
        extra_kwargs = {
            'profile_picture': {'required': False, 'allow_null': True},
            'latitude': {'required': False, 'allow_null': True},
            'longitude': {'required': False, 'allow_null': True},
        }


class PharmacistProfileSerializer(BaseProfileSerializer):
    class Meta:
        model = PharmacistProfile
        fields = '__all__'
        read_only_fields = ('user', 'profile_picture_url', 'profile_picture_thumbnail')
        extra_kwargs = {
            'profile_picture': {'required': False, 'allow_null': True},
            'latitude': {'required': False, 'allow_null': True},
            'longitude': {'required': False, 'allow_null': True},
        }


class LabTechProfileSerializer(BaseProfileSerializer):
    class Meta:
        model = LabTechProfile
        fields = '__all__'
        read_only_fields = ('user', 'profile_picture_url', 'profile_picture_thumbnail')
        extra_kwargs = {
            'profile_picture': {'required': False, 'allow_null': True},
            'latitude': {'required': False, 'allow_null': True},
            'longitude': {'required': False, 'allow_null': True},
        }