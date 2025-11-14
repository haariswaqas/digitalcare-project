from django.db import models
from ..drug_models import Drug  # adjust the import path if needed


class PrescriptionItem(models.Model):
    FREQUENCY_CHOICES = [
        ('QD', 'Once daily'),
        ('BID', 'Twice daily'),
        ('TID', 'Three times daily'),
        ('QID', 'Four times daily'),
        ('Q4H', 'Every 4 hours'),
        ('Q6H', 'Every 6 hours'),
        ('Q8H', 'Every 8 hours'),
        ('Q12H', 'Every 12 hours'),
        ('PRN', 'As needed'),
        ('STAT', 'Immediately'),
        ('AC', 'Before meals'),
        ('PC', 'After meals'),
        ('HS', 'At bedtime'),
    ]
    
    DURATION_UNIT_CHOICES = [
        ('DAYS', 'Days'),
        ('WEEKS', 'Weeks'),
        ('MONTHS', 'Months'),
    ]
    
    prescription = models.ForeignKey(
        'Prescription',
        on_delete=models.CASCADE,
        related_name='items'
    )

    # Instead of CharField, link to the Drug model
    drug = models.ForeignKey(
        Drug,
        on_delete=models.PROTECT,  # prevents deleting a drug still used in prescriptions
        related_name='prescription_items', null=True, blank=True
    )

    dosage = models.CharField(max_length=100)  # e.g., "500mg", "1 tablet"
    frequency = models.CharField(max_length=5, choices=FREQUENCY_CHOICES)
    duration_value = models.PositiveIntegerField(default=1)
    duration_unit = models.CharField(
        max_length=6,
        choices=DURATION_UNIT_CHOICES,
        default='DAYS'
    )
    instructions = models.TextField(blank=True, null=True)
    
    def full_duration(self):
        unit_label = dict(self.DURATION_UNIT_CHOICES).get(self.duration_unit, 'days')
        return f"{self.duration_value} {unit_label.lower()}"
    
    def __str__(self):
        patient_display = getattr(self.prescription.patient, "full_name", str(self.prescription.patient))
        return f"{self.drug.name} for {patient_display} - {self.dosage} {self.frequency} for {self.full_duration()}"
