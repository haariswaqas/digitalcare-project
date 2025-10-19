from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from ..models import Shift
from ..serializers import ShiftSerializer
from ..permissions import IsOwnerDoctorOrFacilityAdmin
from ..utils import ShiftValidator
from datetime import datetime


class ShiftViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing doctor shifts
    - Facility admins can CRUD all shifts at their facility
    - Doctors can only CRUD their own shifts
    """
    queryset = Shift.objects.all()
    serializer_class = ShiftSerializer
    permission_classes = [IsAuthenticated, IsOwnerDoctorOrFacilityAdmin]
    
    def get_queryset(self):
        """Filter shifts based on user role"""
        user = self.request.user
        
        # Superuser sees all
        if user.is_superuser:
            return Shift.objects.all()
        
        # Facility admin sees all shifts at their facility
        if hasattr(user, 'facility'):
            return Shift.objects.filter(facility=user.facility)
        
        # Doctor sees only their own shifts
        if hasattr(user, 'doctorprofile'):
            return Shift.objects.filter(doctor=user.doctorprofile)
        
        return Shift.objects.none()
    
    def perform_create(self, serializer):
        """Set doctor automatically if user is a doctor"""
        user = self.request.user
        
        if hasattr(user, 'doctorprofile'):
            serializer.save(doctor=user.doctorprofile)
        else:
            serializer.save()
        
    
    @action(detail=False, methods=['get'])
    def available_slots(self, request):
        """
        Get available time slots for a doctor at a facility on a specific date
        Query params: doctor_id, facility_id, date (YYYY-MM-DD), duration (optional)
        """
        doctor_id = request.query_params.get('doctor_id')
        facility_id = request.query_params.get('facility_id')
        date_str = request.query_params.get('date')
        duration = int(request.query_params.get('duration', 30))
        
        if not all([doctor_id, facility_id, date_str]):
            return Response(
                {"error": "doctor_id, facility_id, and date are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from ..profile_models import DoctorProfile
            from ..facility_models import Facility
            
            doctor = DoctorProfile.objects.get(id=doctor_id)
            facility = Facility.objects.get(id=facility_id)
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            slots = ShiftValidator.get_available_slots(doctor, facility, date, duration)
            
            return Response({
                "date": date_str,
                "doctor": f"Dr. {doctor.first_name} {doctor.last_name}",
                "facility": facility.name,
                "available_slots": [slot.isoformat() for slot in slots]
            })
        
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )