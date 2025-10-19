from rest_framework.permissions import BasePermission


class IsOwnerDoctorOrFacilityAdmin(BasePermission):
    """
    Custom permission:
    - Facility admins can manage all shifts at their facility
    - Doctors can only manage their own shifts
    """
    
    def has_permission(self, request, view):
        # Must be authenticated
        if not request.user.is_authenticated:
            return False
        
        # Allow superusers
        if request.user.is_superuser:
            return True
        
        # Must be either a facility admin or a doctor
        return hasattr(request.user, 'facility') or hasattr(request.user, 'doctorprofile')
    
    def has_object_permission(self, request, view, obj):
        # Allow superusers
        if request.user.is_superuser:
            return True
        
        # Facility admin can manage all shifts at their facility
        if hasattr(request.user, 'facility'):
            return obj.facility == request.user.facility
        
        # Doctor can only manage their own shifts
        if hasattr(request.user, 'doctorprofile'):
            return obj.doctor == request.user.doctorprofile
        
        return False


