from django.contrib import admin
from .models import (User, Otp, AdultProfile, VisitorProfile, StudentProfile, DoctorProfile, PharmacistProfile, LabTechProfile, HealthCard, ScanLog,
                     
                     Facility, 
                     Notification, 
                     Appointment, ChatRoom, ChatNotification, Message, 
                     Consultation, Drug, PharmacyInventory, Prescription, PrescriptionItem, 
                     
                     Symptom, VideoConsultation)
# Register your models here.
reg = admin.site.register

reg(User)
reg(Otp)

reg(AdultProfile)
reg(VisitorProfile)
reg(StudentProfile)
reg(HealthCard)

reg(DoctorProfile)
reg(PharmacistProfile)
reg(LabTechProfile)



reg(ScanLog)

reg(Facility)
reg(Appointment)
reg(Consultation)

reg(Notification)
reg(Drug)
reg(PharmacyInventory)
reg(Prescription)
reg(PrescriptionItem)
reg(Symptom)
reg(VideoConsultation)
reg(ChatRoom)
reg(ChatNotification)
reg(Message)
