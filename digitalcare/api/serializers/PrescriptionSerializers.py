# api/serializers/prescription_serializer.py
from rest_framework import serializers
from ..models import Prescription, Consultation
from ..models import DoctorProfile, User
from .ConsultationSerializers import ConsultationSerializer


class PrescriptionSerializer(serializers.ModelSerializer):
    # Read-only nested representations
    consultation = ConsultationSerializer(read_only=True)
    doctor = serializers.StringRelatedField(read_only=True)
    patient = serializers.StringRelatedField(read_only=True)
    
    # Write-only IDs for relationships
    consultation_id = serializers.PrimaryKeyRelatedField(
        queryset=Consultation.objects.all(),
        write_only=True,
        source="consultation",
        required=False,
        allow_null=True
    )
    doctor_id = serializers.PrimaryKeyRelatedField(
        queryset=DoctorProfile.objects.all(),
        write_only=True,
        source="doctor",
        required=False,
        allow_null=True
    )
    patient_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        write_only=True,
        source="patient"
    )

    class Meta:
        model = Prescription
        fields = [
            "id",
            "patient",
            "patient_id",
            "doctor",
            "doctor_id",
            "consultation",
            "consultation_id",
            "medicine_name",
            "dosage",
            "frequency",
            "duration",
            "instructions",
            "status",
         
            "expires_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "issued_at", "created_at", "updated_at"]