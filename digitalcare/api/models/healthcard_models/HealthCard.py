# api/models/health_card.py (Enhanced version)
import io
import json
import uuid
from datetime import timedelta
from typing import Optional, Dict, Any
from api.utils import default_expiry
from django.conf import settings
from django.core.files.base import ContentFile
from django.db import models
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.contrib.auth.hashers import make_password, check_password
from django.core.exceptions import ValidationError
from django.urls import reverse

import qrcode

from ..authentication_models import User


class HealthCard(models.Model):
    class CardType(models.TextChoices):
        SMART = "smart", "Smart Health Card"
        NHIS = "nhis", "NHIS Card (Linked)"
        HYBRID = "hybrid", "Smart Card with NHIS Link"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        REVOKED = "revoked", "Revoked"
        EXPIRED = "expired", "Expired"
        PENDING_VERIFICATION = "pending", "Pending NHIS Verification"

    class NHISLinkStatus(models.TextChoices):
        NOT_LINKED = "not_linked", "Not Linked to NHIS"
        PENDING = "pending", "NHIS Verification Pending"
        VERIFIED = "verified", "NHIS Verified and Linked"
        FAILED = "failed", "NHIS Verification Failed"
        EXPIRED = "expired", "NHIS Link Expired"
  

    # UUID for secure external references
    external_id = models.UUIDField(
        default=uuid.uuid4, 
        editable=False, 
        unique=True,
        help_text="UUID for external API references and QR codes"
    )
    
    # Secure access token for QR code data retrieval
    access_token = models.CharField(
        max_length=64,
        unique=True,
         null=True, blank=True,
        help_text="Secure token for accessing patient data via QR scan"
    )
    
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="health_card"
    )

    # Card configuration
    card_type = models.CharField(
        max_length=10, choices=CardType.choices, default=CardType.SMART
    )
    
    # NHIS Integration Fields
    nhis_number = models.CharField(
        max_length=20, blank=True, null=True, 
        help_text="NHIS card number for linking",
        db_index=True
    )
    nhis_link_status = models.CharField(
        max_length=15, choices=NHISLinkStatus.choices, 
        default=NHISLinkStatus.NOT_LINKED
    )
    nhis_verified_at = models.DateTimeField(null=True, blank=True)
    nhis_verification_attempts = models.PositiveIntegerField(default=0)
    nhis_last_sync = models.DateTimeField(null=True, blank=True)
    nhis_verification_data = models.JSONField(null=True, blank=True)

    # Identification
    card_number = models.CharField(
        max_length=32, unique=True, editable=False,
        help_text="Human-readable card number (e.g. SMART-XXXX-XXXX)"
    )
    nfc_uid = models.CharField(
        max_length=64, blank=True, null=True,
        help_text="NFC chip UID if physical card exists"
    )

    # Access control
    pin_hash = models.CharField(
        max_length=128, blank=True, null=True,
        help_text="Hashed PIN for verification"
    )

    # QR Code
    qr_image = models.ImageField(
        upload_to="qr/health_cards/", blank=True, null=True
    )

    # Lifecycle
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.ACTIVE
    )
    issued_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(default=default_expiry)

    # Access tracking
    last_scanned_at = models.DateTimeField(null=True, blank=True)
    scan_count = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['nhis_number', 'nhis_link_status']),
            models.Index(fields=['external_id']),
            models.Index(fields=['card_number']),
            models.Index(fields=['access_token']),
        ]

    def __str__(self):
        nhis_info = f" (NHIS: {self.nhis_number})" if self.nhis_number else ""
        return f"{self.get_card_type_display()} · {self.card_number}{nhis_info} · {self.user.email}"

    # Generate secure access token
    @staticmethod
    def _generate_access_token():
        """Generate a secure random token for data access"""
        return get_random_string(64, allowed_chars='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')

    # QR Code Methods
    def qr_payload(self) -> str:
        """
        Generate QR payload with secure access URL
        The QR contains a URL that points to an endpoint that retrieves patient data
        """
        # Build the data retrieval URL
       
        data_url = f"http://localhost:5173/api/health-card/scan/{self.access_token}/"
        
        payload = {
            "v": 3,  # Version 3 with data retrieval
            "type": self.card_type,
            "url": data_url,
            "card_id": self.card_number,
            "nhis_linked": bool(
                self.nhis_number and 
                self.nhis_link_status == self.NHISLinkStatus.VERIFIED
            )
        }
        return json.dumps(payload, separators=(",", ":"))

    def build_qr_image(self):
        """Generate QR image from payload"""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(self.qr_payload())
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        filename = f"card_{self.external_id}.png"
        self.qr_image.save(filename, ContentFile(buf.getvalue()), save=False)

    # Data Aggregation Methods
    def get_patient_profile(self) -> Optional[Dict[str, Any]]:
        """Get patient profile data based on user role"""
        user = self.user
        profile_data = None
        
        try:
            if user.role == User.STUDENT:
                profile = user.studentprofile
                profile_data = {
                    "type": "student",
                    "first_name": profile.first_name,
                    "middle_name": profile.middle_name,
                    "last_name": profile.last_name,
                    "student_id": profile.student_id,
                    "program": profile.program_of_study,
                    "level": profile.level,
                    "hall": profile.hall,
                    "blood_group": getattr(profile, 'blood_group', None),
                    "allergies": profile.allergies,
                    "chronic_conditions": profile.chronic_conditions,
                    "current_medications": profile.current_medications,
                    "emergency_contact": {
                        "name": profile.emergency_contact_name,
                        "phone": profile.emergency_contact_phone
                    },
                    "parent_guardian": {
                        "name": profile.parent_guardian_name,
                        "phone": profile.parent_guardian_phone
                    }
                }
            elif user.role == User.ADULT:
                profile = user.adultprofile
                profile_data = {
                    "type": "adult",
                    "first_name": profile.first_name,
                    "middle_name": profile.middle_name,
                    "last_name": profile.last_name,
                    "employee_id": profile.employee_id,
                    "department": profile.department,
                    "job_title": profile.job_title,
                    "blood_group": getattr(profile, 'blood_group', None),
                    "allergies": profile.allergies,
                    "chronic_conditions": profile.chronic_conditions,
                    "current_medications": profile.current_medications,
                    "emergency_contact": {
                        "name": profile.emergency_contact_name,
                        "phone": profile.emergency_contact_phone
                    },
                    "insurance": {
                        "provider": profile.insurance_provider,
                        "policy_number": profile.insurance_policy_number
                    }
                }
            elif user.role == User.VISITOR:
                profile = user.visitorprofile
                profile_data = {
                    "type": "visitor",
                    "first_name": profile.first_name,
                    "middle_name": profile.middle_name,
                    "last_name": profile.last_name,
                    "visiting_purpose": profile.visiting_purpose,
                    "expected_stay": profile.expected_stay_duration,
                    "blood_group": getattr(profile, 'blood_group', None),
                    "allergies": profile.allergies,
                    "chronic_conditions": profile.chronic_conditions,
                    "emergency_contact": {
                        "name": profile.emergency_contact_name,
                        "phone": profile.emergency_contact_phone
                    },
                    "host": {
                        "name": profile.host_contact_name,
                        "phone": profile.host_contact_phone
                    }
                }
        except Exception as e:
            print(f"Error fetching profile: {e}")
            
        return profile_data

    def get_medical_records(self, limit: int = 10) -> Dict[str, Any]:
        """
        Aggregate all medical records for this patient
        Based on your Appointment, Consultation, and Prescription models
        """
        user = self.user
        
        records = {
            "appointments": [],
            "consultations": [],
            "prescriptions": [],
            "summary": {
                "total_appointments": 0,
                "total_consultations": 0,
                "total_prescriptions": 0,
                "recent_diagnoses": []
            }
        }
        
        # Get Appointments
        try:
            appointments = user.appointments.select_related(
                'doctor__user', 'facility'
            ).order_by('-scheduled_at')[:limit]
            
            records["summary"]["total_appointments"] = user.appointments.count()
            
            records["appointments"] = [
                {
                    "id": appt.id,
                    "scheduled_at": appt.scheduled_at.isoformat(),
                    "duration_minutes": appt.duration_minutes,
                    "type": appt.get_appointment_type_display(),
                    "status": appt.get_status_display(),
                    "reason": appt.reason,
                    "doctor": {
                        "name": f"{appt.doctor.user.first_name} {appt.doctor.user.last_name}".strip() 
                                if appt.doctor else None,
                        "specialization": appt.doctor.specialization if appt.doctor else None
                    } if appt.doctor else None,
                    "facility": {
                        "name": appt.facility.name if appt.facility else None,
                        "location": getattr(appt.facility, 'location', None) if appt.facility else None
                    } if appt.facility else None,
                    "has_consultation": hasattr(appt, 'consultation')
                }
                for appt in appointments
            ]
        except Exception as e:
            records["appointments"] = []
            print(f"Error fetching appointments: {e}")
        
        # Get Consultations with diagnoses
        try:
            # Get consultations through appointments
            consultations = []
            consultation_objs = []
            
            for appt in user.appointments.select_related('consultation').order_by('-scheduled_at')[:limit]:
                if hasattr(appt, 'consultation'):
                    consultation_objs.append(appt.consultation)
            
            records["summary"]["total_consultations"] = len(consultation_objs)
            
            # Collect recent diagnoses
            recent_diagnoses = []
            
            for consultation in consultation_objs:
                consult_data = {
                    "id": consultation.id,
                    "appointment_id": consultation.appointment.id,
                    "appointment_date": consultation.appointment.scheduled_at.isoformat(),
                    "notes": consultation.notes,
                    "diagnosis": consultation.diagnosis,
                    "started_at": consultation.started_at.isoformat() if consultation.started_at else None,
                    "ended_at": consultation.ended_at.isoformat() if consultation.ended_at else None,
                    "doctor": {
                        "name": f"{consultation.appointment.doctor.user.first_name} {consultation.appointment.doctor.user.last_name}".strip()
                                if consultation.appointment.doctor else None
                    } if consultation.appointment.doctor else None,
                    "prescription_count": consultation.prescriptions.count()
                }
                consultations.append(consult_data)
                
                # Add diagnosis to summary if present
                if consultation.diagnosis:
                    recent_diagnoses.append({
                        "diagnosis": consultation.diagnosis,
                        "date": consultation.appointment.scheduled_at.isoformat(),
                        "doctor": consult_data["doctor"]["name"] if consult_data["doctor"] else "Unknown"
                    })
            
            records["consultations"] = consultations
            records["summary"]["recent_diagnoses"] = recent_diagnoses[:5]  # Last 5 diagnoses
            
        except Exception as e:
            records["consultations"] = []
            print(f"Error fetching consultations: {e}")
        
        # Get Prescriptions
        try:
            # Get all prescriptions through consultations through appointments
           
            from ..prescription_models import Prescription
            
            prescription_list = []
            total_prescriptions = 0
            
            for appt in user.appointments.select_related('consultation').order_by('-scheduled_at'):
                if hasattr(appt, 'consultation'):
                    prescriptions = appt.consultation.prescriptions.all()
                    total_prescriptions += prescriptions.count()
                    
                    for prescription in prescriptions:
                        prescription_list.append({
                            "id": prescription.id,
                            "medicine_name": prescription.medicine_name,
                            "dosage": prescription.dosage,
                            "frequency": prescription.frequency,
                            "duration": prescription.duration,
                            "instructions": prescription.instructions,
                            "prescribed_date": prescription.created_at.isoformat(),
                            "consultation_id": prescription.consultation.id,
                            "appointment_date": appt.scheduled_at.isoformat(),
                            "doctor": {
                                "name": f"{appt.doctor.user.first_name} {appt.doctor.user.last_name}".strip()
                                        if appt.doctor else None
                            } if appt.doctor else None
                        })
                    
                    # Limit to most recent prescriptions
                    if len(prescription_list) >= limit:
                        break
            
            records["prescriptions"] = prescription_list[:limit]
            records["summary"]["total_prescriptions"] = total_prescriptions
            
        except Exception as e:
            records["prescriptions"] = []
            print(f"Error fetching prescriptions: {e}")
        
        return records

    def get_complete_card_data(self, include_full_history: bool = True, limit: int = 10) -> Dict[str, Any]:
        """
        Get all patient data for the smart card
        This is what gets returned when QR is scanned
        
        Args:
            include_full_history: If True, include all medical records. If False, only summary
            limit: Maximum number of records to return for each category
        """
        medical_records = self.get_medical_records(limit=limit)
        
        # Create a summary view if full history not requested
        if not include_full_history:
            medical_records = {
                "summary": medical_records.get("summary", {}),
                "note": "Full medical history available with authentication"
            }
        
        return {
            "card_info": {
                "card_number": self.card_number,
                "card_type": self.get_card_type_display(),
                "status": self.get_status_display(),
                "issued_at": self.issued_at.isoformat(),
                "expires_at": self.expires_at.isoformat(),
                "nhis_number": self.nhis_number,
                "nhis_verified": self.nhis_link_status == self.NHISLinkStatus.VERIFIED
            },
            "patient_profile": self.get_patient_profile(),
            "medical_records": medical_records,
            "last_updated": self.updated_at.isoformat(),
            "scan_info": {
                "total_scans": self.scan_count,
                "last_scanned": self.last_scanned_at.isoformat() if self.last_scanned_at else None
            }
        }

    def record_scan(self):
        """Record that this card was scanned"""
        self.last_scanned_at = timezone.now()
        self.scan_count += 1
        self.save(update_fields=['last_scanned_at', 'scan_count'])

    # PIN helpers
    def set_pin(self, raw_pin: str):
        """Store a hashed PIN."""
        self.pin_hash = make_password(raw_pin)

    def check_pin(self, raw_pin: str) -> bool:
        if not self.pin_hash:
            return False
        return check_password(raw_pin, self.pin_hash)

    # NHIS Integration Methods (kept from original)
    def can_link_nhis(self) -> bool:
        return (
            self.card_type in [self.CardType.NHIS, self.CardType.HYBRID] and
            self.nhis_link_status in [self.NHISLinkStatus.NOT_LINKED, self.NHISLinkStatus.FAILED] and
            self.nhis_verification_attempts < 3
        )

    def initiate_nhis_verification(self, nhis_number: str) -> bool:
        if not self.can_link_nhis():
            return False
        
        self.nhis_number = nhis_number
        self.nhis_link_status = self.NHISLinkStatus.PENDING
        self.nhis_verification_attempts += 1
        self.save(update_fields=['nhis_number', 'nhis_link_status', 'nhis_verification_attempts'])
        return True

    # Card number generation
    @staticmethod
    def _generate_card_number(prefix="SMART"):
        part1 = get_random_string(4, allowed_chars="ABCDEFGHJKLMNPQRSTUVWXYZ23456789")
        part2 = get_random_string(4, allowed_chars="ABCDEFGHJKLMNPQRSTUVWXYZ23456789")
        return f"{prefix}-{part1}-{part2}"

    def save(self, *args, **kwargs):
        # Generate access token if new
        if not self.access_token:
            token = self._generate_access_token()
            while HealthCard.objects.filter(access_token=token).exists():
                token = self._generate_access_token()
            self.access_token = token
        
        # Auto-generate card number if needed
        if not self.card_number:
            if self.card_type == self.CardType.NHIS:
                prefix = "NHIS"
            elif self.card_type == self.CardType.HYBRID:
                prefix = "HYBRID"
            else:
                prefix = "SMART"
            
            cn = self._generate_card_number(prefix=prefix)
            while HealthCard.objects.filter(card_number=cn).exists():
                cn = self._generate_card_number(prefix=prefix)
            self.card_number = cn

        super().save(*args, **kwargs)
        
        # Build QR if missing
        if not self.qr_image:
            self.build_qr_image()
            super().save(update_fields=["qr_image"])