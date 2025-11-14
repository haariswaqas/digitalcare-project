# api/views/health_card_views.py
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.core.cache import cache
from datetime import timedelta
import logging

from ..models import HealthCard, ScanLog
from ..serializers import (
    HealthCardDataSerializer,
    HealthCardScanSerializer
)

logger = logging.getLogger(__name__)


def get_client_ip(request):
    """Get real client IP address"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def log_scan_event(health_card, request, success=True, reason=None):
    """Log scan event with security metadata for audit trail"""
    ip = get_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    
    log_data = {
        'card': health_card,
        'ip_address': ip,
        'user_agent': user_agent,
        'success': success,
        'timestamp': timezone.now()
    }
    
    if reason:
        log_data['failure_reason'] = reason
    
    # Store in database for audit trail
    try:
        ScanLog.objects.create(**log_data)
    except Exception as e:
        logger.error(f"Failed to create scan log: {str(e)}")
    
    if success:
        logger.info(f"Card scanned successfully: {health_card.card_number} from IP: {ip}")
    else:
        logger.warning(f"Failed scan attempt for card {health_card.card_number} from IP: {ip}. Reason: {reason}")


def notify_card_owner(health_card, ip_address):
    """Send notification to card owner about scan event"""
    try:
        from ..tasks import send_scan_notification  # Celery task
        send_scan_notification.delay(
            user_id=health_card.user.id,
            ip_address=ip_address,
            scanned_at=timezone.now().isoformat()
        )
    except Exception as e:
        logger.error(f"Failed to send scan notification: {str(e)}")


@api_view(['GET'])
@permission_classes([AllowAny])
def scan_health_card(request, access_token):
    """
    Public endpoint to retrieve patient data when QR code is scanned
    
    URL: /api/health-card/scan/{access_token}/
    
    Optional query parameters:
    - pin: PIN for additional verification (if card has PIN)
    
    Security features:
    - Rate limiting per IP
    - PIN attempt limiting
    - Generic error messages to prevent enumeration
    - Audit logging
    - Owner notifications
    """
    ip_address = get_client_ip(request)
    
    # Rate limiting per IP - 10 scans per hour
    ip_cache_key = f"scan_attempts_{ip_address}"
    ip_attempts = cache.get(ip_cache_key, 0)
    
    if ip_attempts > 10:
        logger.warning(f"Rate limit exceeded for IP: {ip_address}")
        return Response(
            {"error": "Too many requests. Please try again later."},
            status=status.HTTP_429_TOO_MANY_REQUESTS
        )
    
    cache.set(ip_cache_key, ip_attempts + 1, 3600)
    
    # Generic error message to prevent token enumeration
    generic_error = {"error": "Unable to access health card"}
    
    try:
        health_card = get_object_or_404(HealthCard, access_token=access_token)
        
        # Consolidated check for all invalid states
        if (health_card.status != HealthCard.Status.ACTIVE or 
            health_card.expires_at < timezone.now()):
            log_scan_event(health_card, request, success=False, reason="Invalid card state")
            return Response(generic_error, status=status.HTTP_403_FORBIDDEN)
        
        # PIN verification with attempt limiting
        if health_card.pin_hash:
            pin = request.query_params.get('pin')
            pin_cache_key = f"pin_attempts_{access_token}"
            pin_attempts = cache.get(pin_cache_key, 0)
            
            # Lock card after 3 failed PIN attempts (30 min lockout)
            if pin_attempts >= 3:
                log_scan_event(health_card, request, success=False, reason="Card locked - too many PIN attempts")
                return Response(
                    {
                        "error": "Card temporarily locked due to multiple failed attempts.",
                        "locked_until": "30 minutes from first failed attempt"
                    },
                    status=status.HTTP_423_LOCKED
                )
            
            if not pin:
                return Response(
                    {
                        "error": "PIN required",
                        "requires_pin": True
                    },
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # Verify PIN
            if not health_card.check_pin(pin):
                cache.set(pin_cache_key, pin_attempts + 1, 1800)  # 30 min expiry
                log_scan_event(health_card, request, success=False, reason="Invalid PIN")
                
                # Don't reveal how many attempts are left
                return Response(generic_error, status=status.HTTP_401_UNAUTHORIZED)
            
            # Reset PIN attempts on success
            cache.delete(pin_cache_key)
        
        # Successful scan - log and record
        log_scan_event(health_card, request, success=True)
        health_card.record_scan()
        
        # Get card data with sensitive info redacted for public endpoint
        card_data = health_card.get_complete_card_data()
        
        # Always redact sensitive medical data in public scans
        if 'medical_records' in card_data:
            card_data['medical_records'] = {
                "note": "Full medical records require authenticated access",
                "available": True
            }
        
        # Redact other sensitive fields if needed
        sensitive_fields = ['social_security_number', 'national_id', 'financial_info']
        for field in sensitive_fields:
            if field in card_data:
                card_data[field] = "[REDACTED]"
        
        # Notify card owner of scan
        notify_card_owner(health_card, ip_address)
        
        serializer = HealthCardDataSerializer(card_data)
        
        return Response({
            "success": True,
            "data": serializer.data,
            "scanned_at": timezone.now().isoformat(),
            "message": "Health card accessed successfully"
        })
        
    except HealthCard.DoesNotExist:
        logger.warning(f"Invalid token scan attempt from {ip_address}: {access_token[:8]}...")
        return Response(generic_error, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error in scan_health_card: {str(e)}", exc_info=True)
        return Response(
            {"error": "An error occurred while processing your request"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def regenerate_qr_code(request):
    """
    Regenerate QR code for user's health card
    Useful if QR is compromised or needs to be refreshed
    
    POST /api/health-card/regenerate-qr/
    """
    try:
        health_card = request.user.health_card
        
        # Log the regeneration for security audit
        logger.info(f"QR code regeneration requested by user: {request.user.id}")
        
        # Generate new access token
        old_token = health_card.access_token
        health_card.access_token = HealthCard._generate_access_token()
        
        # Regenerate QR
        if health_card.qr_image:
            health_card.qr_image.delete(save=False)
        
        health_card.build_qr_image()
        health_card.save()
        
        # Clear any PIN attempt caches for old token
        cache.delete(f"pin_attempts_{old_token}")
        
        logger.info(f"QR code regenerated successfully for user: {request.user.id}")
        
        return Response({
            "success": True,
            "message": "QR code regenerated successfully",
            "qr_url": request.build_absolute_uri(health_card.qr_image.url),
            "regenerated_at": timezone.now().isoformat()
        })
        
    except HealthCard.DoesNotExist:
        return Response(
            {"error": "No health card found for this user"},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error regenerating QR: {str(e)}", exc_info=True)
        return Response(
            {"error": "Failed to regenerate QR code. Please try again."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_health_card(request):
    """
    Get current user's health card information
    
    GET /api/health-card/me/
    """
    try:
        health_card = request.user.health_card
        
        return Response({
            "card_number": health_card.card_number,
            "card_type": health_card.get_card_type_display(),
            "status": health_card.get_status_display(),
            "qr_code_url": request.build_absolute_uri(health_card.qr_image.url) if health_card.qr_image else None,
            "issued_at": health_card.issued_at,
            "expires_at": health_card.expires_at,
            "last_scanned_at": health_card.last_scanned_at,
            "scan_count": health_card.scan_count,
            "nhis_linked": health_card.nhis_link_status == HealthCard.NHISLinkStatus.VERIFIED,
            "has_pin": bool(health_card.pin_hash),
            "days_until_expiry": (health_card.expires_at - timezone.now()).days
        })
        
    except HealthCard.DoesNotExist:
        return Response(
            {"error": "No health card found for this user"},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error fetching health card: {str(e)}", exc_info=True)
        return Response(
            {"error": "Failed to retrieve health card information"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def download_health_card_data(request):
    """
    Download complete health card data as JSON
    For the authenticated user only - includes all sensitive data
    
    GET /api/health-card/download/
    """
    try:
        health_card = request.user.health_card
        complete_data = health_card.get_complete_card_data()
        
        # Log data export for audit
        logger.info(f"Health card data exported by user: {request.user.id}")
        
        return Response({
            "success": True,
            "data": complete_data,
            "exported_at": timezone.now().isoformat(),
            "export_type": "complete"
        })
        
    except HealthCard.DoesNotExist:
        return Response(
            {"error": "No health card found for this user"},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error downloading card data: {str(e)}", exc_info=True)
        return Response(
            {"error": "Failed to export health card data"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def set_card_pin(request):
    """
    Set or update PIN for health card
    
    POST /api/health-card/set-pin/
    Body: { 
        "pin": "123456",
        "current_pin": "optional - required if PIN already exists"
    }
    
    Requirements:
    - PIN must be 6-8 digits
    - Cannot be sequential (123456, 111111)
    - If updating, must provide current PIN
    """
    try:
        health_card = request.user.health_card
        new_pin = request.data.get('pin')
        current_pin = request.data.get('current_pin')
        
        # Validate PIN format
        if not new_pin:
            return Response(
                {"error": "PIN is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not new_pin.isdigit():
            return Response(
                {"error": "PIN must contain only digits"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if len(new_pin) < 6 or len(new_pin) > 8:
            return Response(
                {"error": "PIN must be between 6 and 8 digits"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check for weak PINs
        weak_patterns = [
            new_pin == new_pin[0] * len(new_pin),  # All same digits
            new_pin in ['123456', '654321', '12345678', '87654321'],  # Sequential
        ]
        
        if any(weak_patterns):
            return Response(
                {"error": "PIN is too weak. Please choose a stronger PIN."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # If PIN already exists, verify current PIN
        if health_card.pin_hash:
            if not current_pin:
                return Response(
                    {"error": "Current PIN required to update"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if not health_card.check_pin(current_pin):
                return Response(
                    {"error": "Current PIN is incorrect"},
                    status=status.HTTP_401_UNAUTHORIZED
                )
        
        # Set new PIN
        health_card.set_pin(new_pin)
        health_card.save()
        
        # Clear any failed PIN attempt caches
        cache.delete(f"pin_attempts_{health_card.access_token}")
        
        logger.info(f"PIN {'updated' if current_pin else 'set'} for user: {request.user.id}")
        
        return Response({
            "success": True,
            "message": "PIN set successfully"
        })
        
    except HealthCard.DoesNotExist:
        return Response(
            {"error": "No health card found for this user"},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error setting PIN: {str(e)}", exc_info=True)
        return Response(
            {"error": "Failed to set PIN. Please try again."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def remove_card_pin(request):
    """
    Remove PIN from health card
    
    DELETE /api/health-card/remove-pin/
    Body: { "pin": "current_pin" }
    """
    try:
        health_card = request.user.health_card
        current_pin = request.data.get('pin')
        
        if not health_card.pin_hash:
            return Response(
                {"error": "No PIN is currently set"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not current_pin or not health_card.check_pin(current_pin):
            return Response(
                {"error": "Invalid PIN"},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        health_card.pin_hash = None
        health_card.save()
        
        # Clear PIN attempt cache
        cache.delete(f"pin_attempts_{health_card.access_token}")
        
        logger.info(f"PIN removed for user: {request.user.id}")
        
        return Response({
            "success": True,
            "message": "PIN removed successfully"
        })
        
    except HealthCard.DoesNotExist:
        return Response(
            {"error": "No health card found for this user"},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def scan_history(request):
    """
    Get detailed scan history for user's health card
    
    GET /api/health-card/scan-history/
    Query params:
    - limit: Number of recent scans to return (default: 10)
    """
    try:
        health_card = request.user.health_card
        limit = int(request.query_params.get('limit', 10))
        
        # Get recent scan logs
        recent_scans = ScanLog.objects.filter(
            card=health_card
        ).order_by('-timestamp')[:limit]
        
        scan_data = [{
            'timestamp': scan.timestamp,
            'success': scan.success,
            'ip_address': scan.ip_address,
            'user_agent': scan.user_agent[:100] if scan.user_agent else None,
            'failure_reason': getattr(scan, 'failure_reason', None)
        } for scan in recent_scans]
        
        return Response({
            "card_number": health_card.card_number,
            "total_scans": health_card.scan_count,
            "last_scanned_at": health_card.last_scanned_at,
            "issued_at": health_card.issued_at,
            "recent_scans": scan_data
        })
        
    except HealthCard.DoesNotExist:
        return Response(
            {"error": "No health card found for this user"},
            status=status.HTTP_404_NOT_FOUND
        )
    except ValueError:
        return Response(
            {"error": "Invalid limit parameter"},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Error fetching scan history: {str(e)}", exc_info=True)
        return Response(
            {"error": "Failed to retrieve scan history"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )