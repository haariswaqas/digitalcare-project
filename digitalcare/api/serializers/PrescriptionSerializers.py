# api/serializers/prescription_serializers.py

from rest_framework import serializers
from ..models import Drug, Prescription, PrescriptionItem, DoctorProfile, User
from .DrugSerializers import DrugMiniSerializer


class PrescriptionItemSerializer(serializers.ModelSerializer):
    drug = serializers.PrimaryKeyRelatedField(
        queryset=Drug.objects.all(), write_only=True
    )
    drug_details = DrugMiniSerializer(source="drug", read_only=True)

    class Meta:
        model = PrescriptionItem
        fields = [
            "id",
            "drug",
            "drug_details",
            "dosage",
            "frequency",
            "duration_value",
            "duration_unit",
            "instructions",
        ]
        read_only_fields = ["id"]


class PrescriptionSerializer(serializers.ModelSerializer):
    doctor = serializers.SerializerMethodField(read_only=True)
    patient = serializers.SerializerMethodField(read_only=True)
    items = PrescriptionItemSerializer(many=True, required=False)

    # Write-only field for creating prescription - now just User ID
    patient_id = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = Prescription
        fields = [
            "id",
            "doctor",
            "patient",
            "patient_id",
            "instructions",
            "diagnosis",
            "notes",
            "status",
            "valid_from",
            "valid_until",
            "issued_at",
            "items",
        ]
        read_only_fields = ["id", "doctor", "valid_from", "status", "issued_at"]

    def get_patient(self, obj):
        """Return patient information"""
        patient = obj.patient
        if not patient:
            return None
        
        # Get patient profile for additional info
        profile = obj.patient_profile
        
        patient_data = {
            "id": patient.id,
            "email": patient.email,
            "full_name": patient.get_full_name(),
            "phone_number": patient.phone_number,
            "role": patient.role,
        }
        
        # Add profile data if available
        if profile:
            patient_data.update({
                "first_name": profile.first_name,
                "last_name": profile.last_name,
                "nhis_number": profile.nhis_number,
                "allergies": profile.allergies,
            })
        
        return patient_data

    def get_doctor(self, obj):
        """Return doctor information"""
        doctor = obj.doctor
        if not doctor:
            return None
        
        user = doctor.user
        return {
            "id": doctor.id,
            "full_name": user.get_full_name(),
            "email": user.email,
            "specialty": doctor.specialty,
        }

    def validate_patient_id(self, value):
        """Validate patient exists and has valid role"""
        try:
            user = User.objects.get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User with this ID does not exist.")
        
        if user.role not in ['student', 'adult', 'visitor']:
            raise serializers.ValidationError(
                f"User must be a patient (student/adult/visitor), not {user.role}."
            )
        
        return value

    def create(self, validated_data):
        """Create prescription with items"""
        items_data = validated_data.pop("items", [])
        patient_id = validated_data.pop("patient_id")

        # Get patient user
        patient_user = User.objects.get(id=patient_id)

        # Get doctor from authenticated user
        request = self.context.get("request")
        if not request or not hasattr(request, "user"):
            raise serializers.ValidationError("Authenticated user required to create a prescription.")

        try:
            doctor_profile = DoctorProfile.objects.get(user=request.user)
        except DoctorProfile.DoesNotExist:
            raise serializers.ValidationError("Logged-in user does not have a doctor profile.")

        # Create prescription
        prescription = Prescription.objects.create(
            doctor=doctor_profile,
            patient=patient_user,
            **validated_data
        )

        # Create prescription items
        for item_data in items_data:
            drug = item_data.get("drug")
            if not drug:
                raise serializers.ValidationError({"drug": "Each item must include a drug ID."})
            PrescriptionItem.objects.create(prescription=prescription, **item_data)

        return prescription

    def update(self, instance, validated_data):
        """Update prescription"""
        items_data = validated_data.pop("items", None)
        validated_data.pop("patient_id", None)  # Can't change patient
        
        # Update prescription fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update items if provided
        if items_data is not None:
            instance.items.all().delete()
            for item_data in items_data:
                PrescriptionItem.objects.create(prescription=instance, **item_data)
        
        return instance