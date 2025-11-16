from rest_framework.generics import GenericAPIView
from rest_framework.mixins import (
    RetrieveModelMixin,
    CreateModelMixin,
    UpdateModelMixin,
    DestroyModelMixin,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.shortcuts import get_object_or_404

from ..models import StudentProfile, VisitorProfile, AdultProfile, DoctorProfile, PharmacistProfile, LabTechProfile
from ..serializers import (
    StudentProfileSerializer,
    VisitorProfileSerializer,
    AdultProfileSerializer,
    DoctorProfileSerializer,
    PharmacistProfileSerializer,
    LabTechProfileSerializer
)


# Base class for CRUD on user-owned profiles
class BaseProfileView(
    RetrieveModelMixin,
    CreateModelMixin,
    UpdateModelMixin,
    DestroyModelMixin,
    GenericAPIView,
):
    permission_classes = [IsAuthenticated]
    # Add parsers to handle file uploads
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    serializer_class = None
    model_class = None
    role = None  # To be set in each subclass

    def get_object(self):
        """Get the profile object for the authenticated user"""
        if self.request.user.role != self.role:
            raise PermissionDenied({"detail": "Access Denied. Invalid role."})
        return get_object_or_404(self.model_class, user=self.request.user)

    def get(self, request, *args, **kwargs):
        """Retrieve logged-in user's profile"""
        return self.retrieve(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        """Create profile if not already existing"""
        if self.model_class.objects.filter(user=request.user).exists():
            return Response(
                {"detail": "Profile already exists. Use PUT to update."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return self.create(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        """Full update of logged-in user's profile"""
        return self.update(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        """Partial update of logged-in user's profile"""
        return self.partial_update(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        """Delete logged-in user's profile"""
        return self.destroy(request, *args, **kwargs)

    def perform_create(self, serializer):
        """Automatically set the user when creating a profile"""
        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        """Ensure user cannot be changed during update"""
        serializer.save(user=self.request.user)


class StudentProfileView(BaseProfileView):
    serializer_class = StudentProfileSerializer
    model_class = StudentProfile
    role = "student"


class VisitorProfileView(BaseProfileView):
    serializer_class = VisitorProfileSerializer
    model_class = VisitorProfile
    role = "visitor"


class AdultProfileView(BaseProfileView):
    serializer_class = AdultProfileSerializer
    model_class = AdultProfile
    role = "adult"


class DoctorProfileView(BaseProfileView):
    serializer_class = DoctorProfileSerializer
    model_class = DoctorProfile
    role = "doctor"


class PharmacistProfileView(BaseProfileView):
    serializer_class = PharmacistProfileSerializer
    model_class = PharmacistProfile
    role = "pharmacist"


class LabTechProfileView(BaseProfileView):
    serializer_class = LabTechProfileSerializer
    model_class = LabTechProfile
    role = "lab_tech"
