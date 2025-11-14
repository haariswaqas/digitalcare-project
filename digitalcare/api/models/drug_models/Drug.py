from django.db import models

class Drug(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True)
    manufacturer = models.CharField(max_length=255, blank=True, null=True)
    strength = models.CharField(max_length=100, blank=True, null=True)  # e.g. "500mg"
    form = models.CharField(max_length=50, blank=True, null=True)  # e.g. "tablet", "syrup"
    is_generic = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} {self.strength or ''}".strip()
