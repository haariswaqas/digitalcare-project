from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.colors import black, blue, red, darkblue
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.units import inch, cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from datetime import datetime
from ..models import Prescription
import os

def PrescriptionPDF(request, pk):
    prescription = get_object_or_404(Prescription, pk=pk)
    
    # Create the HTTP response with PDF mime type
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="prescription_{prescription.id}.pdf"'
    
    # Create PDF document
    doc = SimpleDocTemplate(
        response,
        pagesize=A4,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=18
    )
    
    # Container for the 'Flowable' objects
    story = []
    
    # Get styles
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor=darkblue,
        fontName='Helvetica-Bold'
    )
    
    header_style = ParagraphStyle(
        'CustomHeader',
        parent=styles['Heading2'],
        fontSize=16,
        spaceAfter=12,
        alignment=TA_CENTER,
        textColor=blue,
        fontName='Helvetica-Bold'
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=12,
        spaceAfter=6,
        alignment=TA_LEFT,
        fontName='Helvetica'
    )
    
    bold_style = ParagraphStyle(
        'CustomBold',
        parent=styles['Normal'],
        fontSize=12,
        spaceAfter=6,
        alignment=TA_LEFT,
        fontName='Helvetica-Bold'
    )
    
    # Hospital Header
    hospital_name = "General Hospital"  # Replace with your hospital name
    hospital_address = "123 Medical Drive, Healthcare City, State 12345"  # Replace with actual address
    hospital_phone = "Tel: (555) 123-4567 | Emergency: (555) 911-HELP"  # Replace with actual numbers
    
    story.append(Paragraph(hospital_name, title_style))
    story.append(Paragraph(hospital_address, normal_style))
    story.append(Paragraph(hospital_phone, normal_style))
    story.append(Spacer(1, 20))
    
    # Prescription header
    story.append(Paragraph("PRESCRIPTION", header_style))
    story.append(Spacer(1, 20))
    
    # Patient and Doctor Information Table
    patient_info = [
        ["Patient Information", "Doctor Information"],
        [f"Patient ID: {prescription.consultation.patient.id if hasattr(prescription.consultation, 'patient') else 'N/A'}", 
         f"Dr. {prescription.consultation.doctor.first_name if hasattr(prescription.consultation, 'doctor') else 'N/A'}"],
        [f"Name: {prescription.consultation.patient.get_full_name() if hasattr(prescription.consultation, 'patient') else 'N/A'}", 
         f"License: {getattr(prescription.consultation.doctor, 'license_number', 'N/A') if hasattr(prescription.consultation, 'doctor') else 'N/A'}"],
        [f"Date of Birth: {getattr(prescription.consultation.patient, 'date_of_birth', 'N/A') if hasattr(prescription.consultation, 'patient') else 'N/A'}", 
         f"Department: {getattr(prescription.consultation.doctor, 'department', 'N/A') if hasattr(prescription.consultation, 'doctor') else 'N/A'}"],
        [f"Phone: {getattr(prescription.consultation.patient, 'phone', 'N/A') if hasattr(prescription.consultation, 'patient') else 'N/A'}", 
         f"Contact: {getattr(prescription.consultation.doctor, 'phone', 'N/A') if hasattr(prescription.consultation, 'doctor') else 'N/A'}"]
    ]
    
    patient_table = Table(patient_info, colWidths=[3*inch, 3*inch])
    patient_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), blue),
        ('TEXTCOLOR', (0, 0), (-1, 0), black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), '#f0f0f0'),
        ('GRID', (0, 0), (-1, -1), 1, black),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    
    story.append(patient_table)
    story.append(Spacer(1, 20))
    
    # Consultation Information
    story.append(Paragraph("Consultation Details", bold_style))
    
    # Safely get consultation data
    try:
        consultation_diagnosis = getattr(prescription.consultation, 'diagnosis', 'Not specified')
    except:
        consultation_diagnosis = 'Not specified'
    
    consultation_info = [
        ["Consultation ID:", str(prescription.consultation.id)],
        ["Date:", prescription.created_at.strftime('%B %d, %Y')],
        ["Time:", prescription.created_at.strftime('%I:%M %p')],
        ["Diagnosis:", consultation_diagnosis],
    ]
    
    consultation_table = Table(consultation_info, colWidths=[2*inch, 4*inch])
    consultation_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    
    story.append(consultation_table)
    story.append(Spacer(1, 20))
    
    # Prescription Details - Main Section
    story.append(Paragraph("℞ PRESCRIPTION DETAILS", header_style))
    story.append(Spacer(1, 10))
    
    # Medicine information in a professional table format
    prescription_data = [
        ["Medicine", "Dosage", "Frequency", "Duration"],
        [prescription.medicine_name, prescription.dosage, prescription.frequency, prescription.duration]
    ]
    
    prescription_table = Table(prescription_data, colWidths=[2*inch, 1.5*inch, 1.5*inch, 1.5*inch])
    prescription_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), 'white'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), '#f8f8f8'),
        ('GRID', (0, 0), (-1, -1), 1, black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), ['white', '#f0f0f0']),
    ]))
    
    story.append(prescription_table)
    story.append(Spacer(1, 20))
    
    # Instructions Section
    if prescription.instructions:
        story.append(Paragraph("INSTRUCTIONS FOR USE:", bold_style))
        story.append(Spacer(1, 5))
        instructions_style = ParagraphStyle(
            'Instructions',
            parent=styles['Normal'],
            fontSize=11,
            spaceAfter=10,
            alignment=TA_JUSTIFY,
            fontName='Helvetica',
            leftIndent=20,
            borderWidth=1,
            borderColor=black,
            borderPadding=10,
            backColor='#f9f9f9'
        )
        story.append(Paragraph(prescription.instructions, instructions_style))
        story.append(Spacer(1, 20))
    
    # Important Notes
    notes_style = ParagraphStyle(
        'Notes',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=5,
        alignment=TA_LEFT,
        fontName='Helvetica-Oblique',
        textColor=red
    )
    
    story.append(Paragraph("IMPORTANT NOTES:", bold_style))
    story.append(Paragraph("• Take medication as prescribed by your doctor", notes_style))
    story.append(Paragraph("• Complete the full course even if you feel better", notes_style))
    story.append(Paragraph("• Contact your doctor if you experience any adverse reactions", notes_style))
    story.append(Paragraph("• Keep this prescription for your records", notes_style))
    story.append(Spacer(1, 30))
    
    # Footer with signature area
    footer_data = [
        ["Doctor's Signature:", "Date:", "Pharmacy Use Only:"],
        ["", prescription.created_at.strftime('%m/%d/%Y'), ""],
        ["", "", ""],
        ["_" * 20, "_" * 15, "_" * 20]
    ]
    
    footer_table = Table(footer_data, colWidths=[2.5*inch, 1.5*inch, 2.5*inch])
    footer_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    
    story.append(footer_table)
    story.append(Spacer(1, 20))
    
    # Disclaimer
    disclaimer_style = ParagraphStyle(
        'Disclaimer',
        parent=styles['Normal'],
        fontSize=8,
        alignment=TA_CENTER,
        fontName='Helvetica-Oblique',
        textColor='gray'
    )
    
    story.append(Paragraph(
        "This prescription is valid for 30 days from the date of issue. "
        "Generic substitution permitted unless marked otherwise. "
        "For questions, contact the prescribing physician.",
        disclaimer_style
    ))
    
    # Build PDF
    doc.build(story)
    return response


# Alternative simpler version using canvas (if you prefer the original approach but enhanced)
def PrescriptionPDF_Canvas_Version(request, pk):
    prescription = get_object_or_404(Prescription, pk=pk)
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="prescription_{prescription.id}.pdf"'
    
    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4
    
    # Colors and styling
    header_color = blue
    text_color = black
    
    # Header Section
    p.setFillColor(header_color)
    p.setFont("Helvetica-Bold", 20)
    p.drawCentredString(width/2, height - 50, "GENERAL HOSPITAL")
    
    p.setFillColor(text_color)
    p.setFont("Helvetica", 12)
    p.drawCentredString(width/2, height - 70, "123 Medical Drive, Healthcare City, State 12345")
    p.drawCentredString(width/2, height - 85, "Tel: (555) 123-4567 | Emergency: (555) 911-HELP")
    
    # Draw a line under header
    p.setStrokeColor(header_color)
    p.setLineWidth(2)
    p.line(50, height - 100, width - 50, height - 100)
    
    # Prescription Title
    p.setFont("Helvetica-Bold", 18)
    p.setFillColor(header_color)
    p.drawCentredString(width/2, height - 130, "℞ PRESCRIPTION")
    
    # Patient Information Box
    p.setStrokeColor(black)
    p.setLineWidth(1)
    p.setFillColor('#f0f0f0')
    p.rect(50, height - 220, width - 100, 60, fill=1, stroke=1)
    
    p.setFillColor(text_color)
    p.setFont("Helvetica-Bold", 12)
    p.drawString(60, height - 180, "PATIENT INFORMATION")
    p.setFont("Helvetica", 10)
    p.drawString(60, height - 195, f"Consultation ID: {prescription.consultation.id}")
    p.drawString(60, height - 208, f"Date: {prescription.created_at.strftime('%B %d, %Y at %I:%M %p')}")
    
    # Prescription Details
    y_position = height - 260
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, y_position, "PRESCRIPTION DETAILS:")
    
    y_position -= 30
    p.setFont("Helvetica-Bold", 11)
    p.drawString(70, y_position, "Medicine:")
    p.setFont("Helvetica", 11)
    p.drawString(150, y_position, prescription.medicine_name)
    
    y_position -= 20
    p.setFont("Helvetica-Bold", 11)
    p.drawString(70, y_position, "Dosage:")
    p.setFont("Helvetica", 11)
    p.drawString(150, y_position, prescription.dosage)
    
    y_position -= 20
    p.setFont("Helvetica-Bold", 11)
    p.drawString(70, y_position, "Frequency:")
    p.setFont("Helvetica", 11)
    p.drawString(150, y_position, prescription.frequency)
    
    y_position -= 20
    p.setFont("Helvetica-Bold", 11)
    p.drawString(70, y_position, "Duration:")
    p.setFont("Helvetica", 11)
    p.drawString(150, y_position, prescription.duration)
    
    # Instructions Box
    if prescription.instructions:
        y_position -= 40
        p.setStrokeColor(black)
        p.setFillColor('#fffacd')
        p.rect(50, y_position - 60, width - 100, 60, fill=1, stroke=1)
        
        p.setFillColor(text_color)
        p.setFont("Helvetica-Bold", 11)
        p.drawString(60, y_position - 20, "INSTRUCTIONS:")
        p.setFont("Helvetica", 10)
        # Handle long instructions by wrapping text
        instructions = prescription.instructions
        if len(instructions) > 70:
            instructions = instructions[:67] + "..."
        p.drawString(60, y_position - 35, instructions)
        y_position -= 80
    
    # Footer with signature
    y_position = 150
    p.setFont("Helvetica-Bold", 10)
    p.drawString(50, y_position, "Doctor's Signature: ________________________")
    p.drawString(350, y_position, f"Date: {prescription.created_at.strftime('%m/%d/%Y')}")
    
    # Disclaimer
    p.setFont("Helvetica-Oblique", 8)
    p.drawCentredString(width/2, 50, "This prescription is valid for 30 days from date of issue.")
    p.drawCentredString(width/2, 35, "For questions, contact the prescribing physician.")
    
    p.showPage()
    p.save()
    return response