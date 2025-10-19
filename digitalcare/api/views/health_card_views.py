# api/views/health_card_views.py
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import timedelta

from ..models import HealthCard
from ..serializers import (
    HealthCardDataSerializer,
    HealthCardScanSerializer
)


@api_view(['GET'])
@permission_classes([AllowAny])  # Public endpoint for QR scanning
def scan_health_card(request, access_token):
    """
    Public endpoint to retrieve patient data when QR code is scanned
    
    URL: /api/health-card/scan/{access_token}/
    
    Optional query parameters:
    - pin: PIN for additional verification (if card has PIN)
    - include_sensitive: Include sensitive medical data (default: True)
    """
    try:
        health_card = get_object_or_404(HealthCard, access_token=access_token)
        
        # Check card status
        if health_card.status != HealthCard.Status.ACTIVE:
            return Response(
                {
                    "error": "Card is not active",
                    "status": health_card.get_status_display()
                },
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check expiration
        if health_card.expires_at < timezone.now():
            return Response(
                {"error": "Card has expired"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Optional PIN verification
        pin = request.query_params.get('pin')
        if health_card.pin_hash and not pin:
            return Response(
                {
                    "error": "PIN required",
                    "requires_pin": True
                },
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        if health_card.pin_hash and pin:
            if not health_card.check_pin(pin):
                return Response(
                    {"error": "Invalid PIN"},
                    status=status.HTTP_401_UNAUTHORIZED
                )
        
        # Record the scan
        health_card.record_scan()
        
        # Get complete patient data
        include_sensitive = request.query_params.get('include_sensitive', 'true').lower() == 'true'
        card_data = health_card.get_complete_card_data()
        
        # Optionally filter sensitive data
        if not include_sensitive:
            if 'medical_records' in card_data:
                card_data['medical_records'] = {
                    "note": "Medical records require authentication"
                }
        
        serializer = HealthCardDataSerializer(card_data)
        
        return Response({
            "success": True,
            "data": serializer.data,
            "scanned_at": timezone.now().isoformat()
        })
        
    except HealthCard.DoesNotExist:
        return Response(
            {"error": "Invalid or expired card"},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {"error": f"Error retrieving card data: {str(e)}"},
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
        
        # Generate new access token
        health_card.access_token = HealthCard._generate_access_token()
        
        # Regenerate QR
        health_card.qr_image.delete(save=False)  # Delete old QR
        health_card.build_qr_image()
        health_card.save()
        
        return Response({
            "success": True,
            "message": "QR code regenerated successfully",
            "qr_url": request.build_absolute_uri(health_card.qr_image.url)
        })
        
    except HealthCard.DoesNotExist:
        return Response(
            {"error": "No health card found for this user"},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {"error": f"Error regenerating QR: {str(e)}"},
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
            "nhis_linked": health_card.nhis_link_status == HealthCard.NHISLinkStatus.VERIFIED
        })
        
    except HealthCard.DoesNotExist:
        return Response(
            {"error": "No health card found for this user"},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def download_health_card_data(request):
    """
    Download complete health card data as JSON
    For the authenticated user only
    
    GET /api/health-card/download/
    """
    try:
        health_card = request.user.health_card
        complete_data = health_card.get_complete_card_data()
        
        return Response({
            "success": True,
            "data": complete_data,
            "exported_at": timezone.now().isoformat()
        })
        
    except HealthCard.DoesNotExist:
        return Response(
            {"error": "No health card found for this user"},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def set_card_pin(request):
    """
    Set or update PIN for health card
    
    POST /api/health-card/set-pin/
    Body: { "pin": "1234" }
    """
    try:
        health_card = request.user.health_card
        pin = request.data.get('pin')
        
        if not pin or len(pin) < 4:
            return Response(
                {"error": "PIN must be at least 4 characters"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        health_card.set_pin(pin)
        health_card.save()
        
        return Response({
            "success": True,
            "message": "PIN set successfully"
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
    Get scan history for user's health card
    
    GET /api/health-card/scan-history/
    """
    try:
        health_card = request.user.health_card
        
        return Response({
            "card_number": health_card.card_number,
            "total_scans": health_card.scan_count,
            "last_scanned_at": health_card.last_scanned_at,
            "issued_at": health_card.issued_at
        })
        
    except HealthCard.DoesNotExist:
        return Response(
            {"error": "No health card found for this user"},
            status=status.HTTP_404_NOT_FOUND
        )