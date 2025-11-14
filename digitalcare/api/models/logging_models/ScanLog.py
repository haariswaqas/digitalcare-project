from django.db import models
from django.utils import timezone

class ScanLog(models.Model):
    """
    Audit trail for all HealthCard scan attempts (both successful and failed).
    Tracks metadata for security monitoring and analytics.
    """
    card = models.ForeignKey(
        'HealthCard',
        on_delete=models.CASCADE,
        related_name='scan_logs',
        help_text="The health card that was scanned."
    )
    timestamp = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        help_text="Time of the scan event."
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address of the device that performed the scan."
    )
    user_agent = models.TextField(
        null=True,
        blank=True,
        help_text="Browser or device user agent string."
    )
    success = models.BooleanField(
        default=True,
        help_text="Whether the scan was successful."
    )
    failure_reason = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Reason for failure, if any (e.g., invalid PIN, expired card)."
    )

    class Meta:
        ordering = ['-timestamp']
        verbose_name = "Scan Log"
        verbose_name_plural = "Scan Logs"
        indexes = [
            models.Index(fields=['card', 'timestamp']),
            models.Index(fields=['ip_address']),
        ]

    def __str__(self):
        status = "Success" if self.success else "Failed"
        return f"{status} scan of {self.card.card_number} at {self.timestamp:%Y-%m-%d %H:%M:%S}"
