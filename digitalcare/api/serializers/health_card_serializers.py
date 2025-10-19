# api/serializers/health_card_serializers.py
from rest_framework import serializers


class HealthCardDataSerializer(serializers.Serializer):
    """Serializer for complete health card data"""
    
    card_info = serializers.DictField()
    patient_profile = serializers.DictField()
    medical_records = serializers.DictField()
    last_updated = serializers.CharField()


class HealthCardScanSerializer(serializers.Serializer):
    """Serializer for QR scan response"""
    
    success = serializers.BooleanField()
    data = HealthCardDataSerializer()
    scanned_at = serializers.DateTimeField()


class HealthCardBasicSerializer(serializers.Serializer):
    """Serializer for basic health card info"""
    
    card_number = serializers.CharField()
    card_type = serializers.CharField()
    status = serializers.CharField()
    qr_code_url = serializers.CharField(allow_null=True)
    issued_at = serializers.DateTimeField()
    expires_at = serializers.DateTimeField()
    last_scanned_at = serializers.DateTimeField(allow_null=True)
    scan_count = serializers.IntegerField()
    nhis_linked = serializers.BooleanField()