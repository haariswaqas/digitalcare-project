from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from ..services import LocationService
from ..models import StudentProfile, AdultProfile, VisitorProfile, DoctorProfile
from ..serializers import FacilitySerializer, DoctorProfileSerializer

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def nearby_providers(request):
    user = request.user

    # Get patient profile
    patient_profile = None
    if user.role == 'student':
        patient_profile = get_object_or_404(StudentProfile, user=user)
    elif user.role == 'adult':
        patient_profile = get_object_or_404(AdultProfile, user=user)
    elif user.role == 'visitor':
        patient_profile = get_object_or_404(VisitorProfile, user=user)
    else:
        return Response(
            {'error': 'Only patients can search for providers'},
            status=status.HTTP_403_FORBIDDEN
        )

    # Ensure patient location is set
    if not patient_profile.latitude or not patient_profile.longitude:
        return Response(
            {'error': 'Location not set. Please update your location in profile settings.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Query parameters
    radius_km = float(request.GET.get('radius', 10))
    provider_type = request.GET.get('type', 'both')
    specialty = request.GET.get('specialty', None)

    response_data = {}

    # Facilities
    if provider_type in ['both', 'clinic', 'pharmacy']:
        if provider_type == 'both':
            clinics = LocationService.get_nearby_facilities(
                patient_profile.latitude, patient_profile.longitude,
                radius_km, 'clinic'
            )
            pharmacies = LocationService.get_nearby_facilities(
                patient_profile.latitude, patient_profile.longitude,
                radius_km, 'pharmacy'
            )
            response_data['clinics'] = FacilitySerializer(clinics, many=True).data
            response_data['pharmacies'] = FacilitySerializer(pharmacies, many=True).data
        else:
            facilities = LocationService.get_nearby_facilities(
                patient_profile.latitude, patient_profile.longitude,
                radius_km, provider_type
            )
            response_data[f'{provider_type}s'] = FacilitySerializer(facilities, many=True).data

    # Doctors
    if provider_type in ['both', 'clinic']:
        doctors = LocationService.get_nearby_doctors(
            patient_profile.latitude, patient_profile.longitude,
            radius_km, specialty
        )
        response_data['doctors'] = DoctorProfileSerializer(doctors, many=True).data

    return Response(response_data, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_user_location(request):
    """
    Update location for patient or doctor.
    Body: {'latitude': float, 'longitude': float}
    """
    user = request.user
    latitude = request.data.get('latitude')
    longitude = request.data.get('longitude')
    
    if not latitude or not longitude:
        return Response(
            {'error': 'Both latitude and longitude are required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    updated = False

    # Patients
    if user.role == 'student':
        profile = get_object_or_404(StudentProfile, user=user)
    elif user.role == 'adult':
        profile = get_object_or_404(AdultProfile, user=user)
    elif user.role == 'visitor':
        profile = get_object_or_404(VisitorProfile, user=user)
    elif user.role == 'doctor':
        profile = get_object_or_404(DoctorProfile, user=user)
    else:
        return Response(
            {'error': 'Only patients or doctors can update location'}, 
            status=status.HTTP_403_FORBIDDEN
        )

    # Update location
    profile.latitude = float(latitude)
    profile.longitude = float(longitude)
    profile.save()
    updated = True
    
    if updated:
        return Response(
            {'message': 'Location updated successfully'}, 
            status=status.HTTP_200_OK
        )
    else:
        return Response(
            {'error': 'Unable to update location'}, 
            status=status.HTTP_400_BAD_REQUEST
        )