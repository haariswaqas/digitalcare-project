from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from ..services import LocationService
from ..models import StudentProfile, AdultProfile, VisitorProfile, DoctorProfile
from ..serializers import FacilitySerializer, DoctorProfileSerializer, LabTechProfileSerializer, PharmacistProfileSerializer

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def nearby_providers(request):
    user = request.user

    # Identify the patient's profile
    if user.role == 'student':
        patient_profile = get_object_or_404(StudentProfile, user=user)
    elif user.role == 'adult':
        patient_profile = get_object_or_404(AdultProfile, user=user)
    elif user.role == 'visitor':
        patient_profile = get_object_or_404(VisitorProfile, user=user)
    else:
        return Response(
            {'error': 'Only patients can search for healthcare providers.'},
            status=status.HTTP_403_FORBIDDEN
        )

    # Ensure patient location exists
    if not patient_profile.latitude or not patient_profile.longitude:
        return Response(
            {'error': 'Location not set. Please update your location in profile settings.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Query parameters
    radius_km = float(request.GET.get('radius', 10))
    provider_type = request.GET.get('type', 'both').lower()
    specialty = request.GET.get('specialty', None)

    response_data = {}
    lat, lon = patient_profile.latitude, patient_profile.longitude

    # --- Facilities ---
    if provider_type in ['both', 'clinic', 'pharmacy', 'laboratory']:
        if provider_type == 'both':
            clinics = LocationService.get_nearby_facilities(lat, lon, radius_km, 'clinic')
            pharmacies = LocationService.get_nearby_facilities(lat, lon, radius_km, 'pharmacy')
            laboratories = LocationService.get_nearby_facilities(lat, lon, radius_km, 'laboratory')

            response_data['clinics'] = FacilitySerializer(clinics, many=True).data
            response_data['pharmacies'] = FacilitySerializer(pharmacies, many=True).data
            response_data['laboratories'] = FacilitySerializer(laboratories, many=True).data
        else:
            facilities = LocationService.get_nearby_facilities(lat, lon, radius_km, provider_type)
            plural_map = {'clinic': 'clinics', 'pharmacy': 'pharmacies', 'laboratory': 'laboratories'}
            key = plural_map.get(provider_type, f"{provider_type}s")
            response_data[key] = FacilitySerializer(facilities, many=True).data

    # --- Doctors (only for clinics or both) ---
    if provider_type in ['both', 'clinic']:
        doctors = LocationService.get_nearby_doctors(lat, lon, radius_km, specialty)
        response_data['doctors'] = DoctorProfileSerializer(doctors, many=True).data

    # --- Pharmacists ---
    if provider_type in ['both', 'pharmacy']:
        pharmacists = LocationService.get_nearby_pharmacists(lat, lon, radius_km)
        response_data['pharmacists'] = PharmacistProfileSerializer(pharmacists, many=True).data

    # --- Laboratory Technicians ---
    if provider_type in ['both', 'laboratory']:
        lab_techs = LocationService.get_nearby_lab_techs(lat, lon, radius_km)
        response_data['lab_technicians'] = LabTechProfileSerializer(lab_techs, many=True).data

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