# api/views/prescription_views.py

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from django.http import HttpResponse
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from ..models import (
    Prescription,
    PrescriptionItem,
    DoctorProfile,
)
from ..serializers import PrescriptionSerializer, PrescriptionItemSerializer
from ..permissions import PrescriptionPermission, PrescriptionItemPermission


class PrescriptionViewSet(viewsets.ModelViewSet):
    queryset = Prescription.objects.all().select_related("doctor__user", "patient")
    serializer_class = PrescriptionSerializer
    permission_classes = [IsAuthenticated, PrescriptionPermission]

    def get_queryset(self):
        user = self.request.user

        if user.is_superuser or getattr(user, "role", None) == "admin":
            return Prescription.objects.all()
        
        elif getattr(user, "role", None) == "doctor":
            return Prescription.objects.filter(doctor__user=user)
        
        elif getattr(user, "role", None) == "facility_admin":
            return Prescription.objects.filter(doctor__facility__admin=user)
        
        elif getattr(user, "role", None) == "pharmacist":
            return Prescription.objects.filter(
                items__drug__pharmacy_stocks__pharmacy__pharmacists__user=user
            ).distinct()
        
        elif user.role in ['student', 'adult', 'visitor']:
            # Simple: just filter by patient = current user
            return Prescription.objects.filter(patient=user)
        
        else:
            return Prescription.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        if getattr(user, "role", None) != "doctor":
            raise PermissionDenied("Only doctors can create prescriptions.")
        try:
            doctor_profile = DoctorProfile.objects.get(user=user)
        except DoctorProfile.DoesNotExist:
            raise PermissionDenied("You do not have a doctor profile.")
        serializer.save(doctor=doctor_profile)

    @action(detail=True, methods=["get"])
    def download_pdf(self, request, pk=None):
        """Download prescription as PDF."""
        prescription = self.get_object()
        self.check_object_permissions(request, prescription)

        response = HttpResponse(content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="prescription_{prescription.id}.pdf"'

        pdf = canvas.Canvas(response, pagesize=letter)
        width, height = letter

        # Title
        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawString(50, height - 50, "PRESCRIPTION")

        y = height - 100
        
        # Patient info
        patient = prescription.patient
        patient_profile = prescription.patient_profile
        pdf.setFont("Helvetica", 10)
        pdf.drawString(50, y, f"Patient: {patient.get_full_name()}")
        y -= 15
        
        if patient_profile and patient_profile.nhis_number:
            pdf.drawString(50, y, f"NHIS: {patient_profile.nhis_number}")
            y -= 15
        
        pdf.drawString(50, y, f"Phone: {patient.phone_number}")
        y -= 20

        # Doctor info
        doctor_name = prescription.doctor.user.get_full_name() if prescription.doctor else "N/A"
        pdf.drawString(50, y, f"Doctor: Dr. {doctor_name}")
        y -= 15
        
        if prescription.doctor and prescription.doctor.specialty:
            pdf.drawString(50, y, f"Specialty: {prescription.doctor.specialty}")
            y -= 20

        # Dates
        pdf.drawString(50, y, f"Issued: {prescription.valid_from.strftime('%Y-%m-%d')}")
        y -= 15
        if prescription.valid_until:
            pdf.drawString(50, y, f"Valid Until: {prescription.valid_until.strftime('%Y-%m-%d')}")
            y -= 20

        # Diagnosis
        if prescription.diagnosis:
            pdf.setFont("Helvetica-Bold", 12)
            pdf.drawString(50, y, "Diagnosis:")
            y -= 15
            pdf.setFont("Helvetica", 10)
            for line in prescription.diagnosis.split("\n"):
                pdf.drawString(60, y, line)
                y -= 12
            y -= 5

        # Instructions
        if prescription.instructions:
            pdf.setFont("Helvetica-Bold", 12)
            pdf.drawString(50, y, "Instructions:")
            y -= 15
            pdf.setFont("Helvetica", 10)
            for line in prescription.instructions.split("\n"):
                pdf.drawString(60, y, line)
                y -= 12
            y -= 5

        # Prescription Items
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(50, y, "Medications:")
        y -= 15
        pdf.setFont("Helvetica", 10)

        for item in prescription.items.all():
            drug_name = item.drug.name if item.drug else "Unknown"
            pdf.drawString(
                60, y,
                f"- {drug_name}: {item.dosage}, {item.get_frequency_display()} "
                f"for {item.full_duration()}"
            )
            y -= 15
            if item.instructions:
                pdf.setFont("Helvetica-Oblique", 9)
                pdf.drawString(75, y, f"({item.instructions})")
                pdf.setFont("Helvetica", 10)
                y -= 12

        # Signature section
        y -= 20
        pdf.setFont("Helvetica", 10)
        pdf.drawString(50, y, "_" * 40)
        y -= 15
        pdf.drawString(50, y, f"Dr. {doctor_name}")
        y -= 12
        if prescription.doctor and prescription.doctor.license_number:
            pdf.drawString(50, y, f"License: {prescription.doctor.license_number}")

        pdf.save()
        return response


class PrescriptionItemViewSet(viewsets.ModelViewSet):
    queryset = PrescriptionItem.objects.select_related(
        "prescription__doctor__user",
        "prescription__patient",
        "drug"
    )
    serializer_class = PrescriptionItemSerializer
    permission_classes = [IsAuthenticated, PrescriptionItemPermission]

    def get_queryset(self):
        user = self.request.user

        if user.is_superuser or getattr(user, "role", None) == "admin":
            return PrescriptionItem.objects.all()
        
        elif getattr(user, "role", None) == "doctor":
            return PrescriptionItem.objects.filter(prescription__doctor__user=user)
        
        elif getattr(user, "role", None) == "facility_admin":
            return PrescriptionItem.objects.filter(prescription__doctor__facility__admin=user)
        
        elif getattr(user, "role", None) == "pharmacist":
            return PrescriptionItem.objects.filter(
                drug__pharmacy_stocks__pharmacy__pharmacists__user=user
            ).distinct()
        
        elif user.role in ['student', 'adult', 'visitor']:
            # Simple: just filter by prescription patient = current user
            return PrescriptionItem.objects.filter(prescription__patient=user)
        
        else:
            return PrescriptionItem.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        if getattr(user, "role", None) != "doctor":
            raise PermissionDenied("Only doctors can create prescription items.")
        doctor_profile = DoctorProfile.objects.get(user=user)
        prescription = serializer.validated_data.get("prescription")
        if prescription.doctor != doctor_profile:
            raise PermissionDenied("You can only add items to your own prescriptions.")
        serializer.save()

    def perform_update(self, serializer):
        user = self.request.user
        instance = self.get_object()
        if getattr(user, "role", None) != "doctor" or instance.prescription.doctor.user != user:
            raise PermissionDenied("You cannot update items not belonging to your prescriptions.")
        serializer.save()

    def perform_destroy(self, instance):
        user = self.request.user
        if getattr(user, "role", None) != "doctor" or instance.prescription.doctor.user != user:
            raise PermissionDenied("You cannot delete items not belonging to your prescriptions.")
        instance.delete()