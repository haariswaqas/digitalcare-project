from django.db import models
from .Drug import Drug
from ..facility_models import Facility

class PharmacyInventory(models.Model):
    pharmacy = models.ForeignKey(
        Facility,
        limit_choices_to={'facility_type': 'pharmacy'},
        on_delete=models.CASCADE,
        related_name='inventory'
    )
    drug = models.ForeignKey(Drug, on_delete=models.CASCADE, related_name='pharmacy_stocks')
    quantity = models.PositiveIntegerField(default=0)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('pharmacy', 'drug')

    def __str__(self):
        return f"{self.drug.name} - {self.pharmacy.name} ({self.quantity} units)"
