from django.db.models.signals import post_save
from django.dispatch import receiver
from ..models import HealthCard
from ..tasks import create_notification_task
from django.utils import timezone

# 1️⃣ Notify user when their card is scanned
@receiver(post_save, sender=HealthCard)
def notify_on_card_scan(sender, instance, created, **kwargs):
    """
    Triggered when scan_count changes — notify the card owner.
    """
    # Only notify if this is an update (not creation)
    if not created:
        # Check if scan_count has increased (indicating a new scan)
        if hasattr(instance, '_previous_scan_count') and instance.scan_count > instance._previous_scan_count:
            message = (
                f"Your health card '{instance.card_number}' was just scanned "
                f"at {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}. "
                "If this wasn’t you, please secure your account immediately."
            )
            create_notification_task.delay(user_id=instance.user.id, message=message)

# 2️⃣ Notify user when their card QR is downloaded
@receiver(post_save, sender=HealthCard)
def notify_on_qr_download(sender, instance, created, **kwargs):
    """
    Notify the card owner whenever the QR code is downloaded.
    """
    if not created:
        if hasattr(instance, '_previous_qr_download_count') and instance.qr_download_count > instance._previous_qr_download_count:
            message = (
                f"The QR code for your health card '{instance.card_number}' was just downloaded. "
                "If this wasn’t you, please review your account security."
            )
            create_notification_task.delay(user_id=instance.user.id, message=message)

# 3️⃣ Edge case — alert when card becomes inactive or compromised
@receiver(post_save, sender=HealthCard)
def notify_on_card_status_change(sender, instance, created, **kwargs):
    """
    Notify user when the card status changes to inactive, suspended, or compromised.
    """
    if not created and instance.status in ["inactive", "suspended", "compromised"]:
        message = (
            f"Alert: Your health card '{instance.card_number}' has been marked as {instance.status}. "
            "Please contact support if you did not request this change."
        )
        create_notification_task.delay(user_id=instance.user.id, message=message)
