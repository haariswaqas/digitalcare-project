from rest_framework import serializers
from ..models import Shift, DoctorProfile


class ShiftSerializer(serializers.ModelSerializer):
    doctor_name = serializers.SerializerMethodField()
    facility_name = serializers.SerializerMethodField()
    day_name = serializers.CharField(source='get_day_of_week_display', read_only=True)
    doctor = serializers.PrimaryKeyRelatedField(
        queryset=DoctorProfile.objects.all(),
        required=False,
        allow_null=True
    )
    
    class Meta:
        model = Shift
        fields = [
            'id', 'doctor', 'doctor_name', 'facility', 'facility_name',
            'day_of_week', 'day_name', 'start_time', 'end_time',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_doctor_name(self, obj):
        return f"Dr. {obj.doctor.first_name} {obj.doctor.last_name}"
    
    def get_facility_name(self, obj):
        return obj.facility.name
    
    def validate(self, data):
        request = self.context.get('request')
        user = request.user if request else None
        
        # Facility admin validation
        if user and hasattr(user, 'facility'):
            facility = data.get('facility', getattr(self.instance, 'facility', None))
            if facility != user.facility:
                raise serializers.ValidationError(
                    "You can only manage shifts for your own facility"
                )
            
            # Facility admin must provide doctor
            if 'doctor' not in data and not self.instance:
                raise serializers.ValidationError(
                    {"doctor": "This field is required for facility admins"}
                )
        
        # Doctor validation
        if user and hasattr(user, 'doctorprofile'):
            # Check if doctor was provided and if it matches current user's doctor profile
            provided_doctor = data.get('doctor')
            
            if provided_doctor and provided_doctor != user.doctorprofile:
                raise serializers.ValidationError(
                    {"doctor": "You can only manage your own shifts"}
                )
            
            # Verify doctor is associated with the facility
            facility = data.get('facility', getattr(self.instance, 'facility', None))
            if facility and not user.doctorprofile.clinics.filter(id=facility.id).exists():
                raise serializers.ValidationError(
                    {"facility": "You are not associated with this facility"}
                )
        
        return data