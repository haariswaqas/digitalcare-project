# api/tasks.py
from celery import shared_task
from django.utils import timezone
from datetime import datetime
from ..models import Notification, User
import logging

logger = logging.getLogger(__name__)


@shared_task
def send_scan_notification(user_id, ip_address, scanned_at):
    """
    Send notification to user when their health card is scanned
    
    Args:
        user_id: ID of the health card owner
        ip_address: IP address that scanned the card
        scanned_at: ISO format timestamp of when scan occurred
    """
    try:
        user = User.objects.get(id=user_id)
        
        # Parse the timestamp
        scan_time = datetime.fromisoformat(scanned_at.replace('Z', '+00:00'))
        formatted_time = scan_time.strftime("%B %d, %Y at %I:%M %p")
        
        # Create notification message
        message = (
            f"Your health card was scanned on {formatted_time}. "
            f"Location: {ip_address}. "
            f"If this wasn't you, please contact support immediately."
        )
        
        # Create notification
        Notification.objects.create(
            recipient=user,
            message=message,
            notification_type='HEALTH_CARD_SCAN',  # Add this field to your Notification model
            metadata={
                'ip_address': ip_address,
                'scanned_at': scanned_at,
                'action': 'health_card_scan'
            }
        )
        
        logger.info(f"Scan notification created for user {user_id}")
        
        # Optional: Send email/SMS for high-value security events
        # send_email_notification.delay(user.email, message)
        # send_sms_notification.delay(user.phone, message)
        
    except User.DoesNotExist:
        logger.error(f"User with ID {user_id} does not exist")
    except Exception as e:
        logger.error(f"Error creating scan notification for user {user_id}: {str(e)}")


@shared_task
def send_suspicious_activity_alert(user_id, activity_type, details):
    """
    Send alert for suspicious activity on health card
    
    Args:
        user_id: ID of the health card owner
        activity_type: Type of suspicious activity (e.g., 'multiple_failed_pins', 'rate_limit_exceeded')
        details: Dictionary with additional details
    """
    try:
        user = User.objects.get(id=user_id)
        
        activity_messages = {
            'multiple_failed_pins': "⚠️ SECURITY ALERT: Multiple failed PIN attempts detected on your health card.",
            'rate_limit_exceeded': "⚠️ SECURITY ALERT: Unusual access patterns detected on your health card.",
            'card_locked': "🔒 Your health card has been temporarily locked due to security concerns.",
            'unauthorized_location': "⚠️ Your health card was accessed from an unusual location."
        }
        
        base_message = activity_messages.get(
            activity_type, 
            "⚠️ SECURITY ALERT: Suspicious activity detected on your health card."
        )
        
        message = f"{base_message} If this wasn't you, please secure your account immediately and contact support."
        
        # Create high-priority notification
        Notification.objects.create(
            recipient=user,
            message=message,
            notification_type='SECURITY_ALERT',
            priority='HIGH',  # Add priority field to your model
            metadata={
                'activity_type': activity_type,
                'details': details,
                'timestamp': timezone.now().isoformat()
            }
        )
        
        logger.warning(f"Security alert sent to user {user_id} for {activity_type}")
        
        # For security alerts, always send email/SMS
        # send_email_notification.delay(user.email, message)
        # if user.phone:
        #     send_sms_notification.delay(user.phone, message)
        
    except User.DoesNotExist:
        logger.error(f"User with ID {user_id} does not exist")
    except Exception as e:
        logger.error(f"Error sending security alert to user {user_id}: {str(e)}")


@shared_task
def send_card_expiry_reminder(user_id, days_until_expiry):
    """
    Send reminder when health card is about to expire
    
    Args:
        user_id: ID of the health card owner
        days_until_expiry: Number of days until card expires
    """
    try:
        user = User.objects.get(id=user_id)
        
        if days_until_expiry <= 7:
            urgency = "expires soon"
        elif days_until_expiry <= 30:
            urgency = "will expire"
        else:
            urgency = "renewal available"
        
        message = (
            f"Your health card {urgency} in {days_until_expiry} day{'s' if days_until_expiry != 1 else ''}. "
            f"Please renew your card to avoid service interruption."
        )
        
        Notification.objects.create(
            recipient=user,
            message=message,
            notification_type='CARD_EXPIRY_REMINDER',
            metadata={
                'days_until_expiry': days_until_expiry,
                'reminder_sent_at': timezone.now().isoformat()
            }
        )
        
        logger.info(f"Expiry reminder sent to user {user_id} ({days_until_expiry} days)")
        
    except User.DoesNotExist:
        logger.error(f"User with ID {user_id} does not exist")
    except Exception as e:
        logger.error(f"Error sending expiry reminder to user {user_id}: {str(e)}")


