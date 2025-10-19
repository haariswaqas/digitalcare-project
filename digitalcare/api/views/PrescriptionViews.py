# api/views/prescription_views.py
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from ..models import Prescription, Consultation
from ..serializers import PrescriptionSerializer
from ..permissions import PrescriptionPermissions

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.core.exceptions import PermissionDenied
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


class PrescriptionViewSet(viewsets.ModelViewSet):
    queryset = Prescription.objects.all()
    serializer_class = PrescriptionSerializer
    permission_classes = [IsAuthenticated, PrescriptionPermissions]

    def get_queryset(self):
        user = self.request.user

        if user.is_superuser or user.role == "admin":
            return Prescription.objects.all()
        elif user.role == "facility_admin":
            # Get prescriptions for doctors at their facility
            return Prescription.objects.filter(
                doctor__facility__admin=user
            )
        elif user.role == "doctor":
            # Get prescriptions issued by this doctor
            return Prescription.objects.filter(doctor__user=user)
        else:
            # patient - get their own prescriptions
            return Prescription.objects.filter(patient=user)

    def perform_create(self, serializer):
        user = self.request.user
        doctor = serializer.validated_data.get("doctor")
        consultation = serializer.validated_data.get("consultation")

        # Doctors can only create prescriptions for themselves
        if user.role == "doctor":
            user_doctor_profile = user.doctor_profile
            if doctor and doctor != user_doctor_profile:
                raise PermissionDenied("You can only create prescriptions for yourself.")
            # Auto-assign the doctor if not provided
            serializer.validated_data["doctor"] = user_doctor_profile

        # If there's a consultation, verify the doctor is authorized
        if consultation:
            if consultation.appointment.doctor is None or consultation.appointment.doctor.user != user:
                raise PermissionDenied("You are not authorized to prescribe from this consultation.")

        serializer.save()

    @action(detail=True, methods=['get'])
    def download_pdf(self, request, pk=None):
        """Download prescription as PDF"""
        prescription = self.get_object()
        self.check_object_permissions(request, prescription)

        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="prescription_{prescription.id}.pdf"'

        pdf = canvas.Canvas(response, pagesize=letter)
        width, height = letter

        # Title
        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawString(50, height - 50, "PRESCRIPTION")

        # Prescription details
        pdf.setFont("Helvetica", 10)
        y = height - 100

        pdf.drawString(50, y, f"Patient: {prescription.patient.get_full_name()}")
        y -= 20
        pdf.drawString(50, y, f"Doctor: {prescription.doctor.user.get_full_name() if prescription.doctor else 'N/A'}")
        y -= 20
        pdf.drawString(50, y, f"Issued: {prescription.issued_at.strftime('%Y-%m-%d %H:%M')}")
        y -= 20

        if prescription.expires_at:
            pdf.drawString(50, y, f"Expires: {prescription.expires_at.strftime('%Y-%m-%d')}")
            y -= 20

        y -= 20
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(50, y, "Medicine Details:")
        y -= 20

        pdf.setFont("Helvetica", 10)
        pdf.drawString(50, y, f"Medicine: {prescription.medicine_name}")
        y -= 15
        pdf.drawString(50, y, f"Dosage: {prescription.dosage}")
        y -= 15
        pdf.drawString(50, y, f"Frequency: {prescription.frequency}")
        y -= 15
        pdf.drawString(50, y, f"Duration: {prescription.duration}")
        y -= 20

        if prescription.instructions:
            pdf.setFont("Helvetica-Bold", 10)
            pdf.drawString(50, y, "Instructions:")
            y -= 15
            pdf.setFont("Helvetica", 9)
            pdf.drawString(50, y, prescription.instructions)

        pdf.save()
        return response