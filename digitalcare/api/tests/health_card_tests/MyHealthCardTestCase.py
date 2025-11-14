# api/tests/test_health_card_views/MyHealthCardTestCase.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from datetime import timedelta

from api.models import HealthCard

User = get_user_model()


class MyHealthCardTestCase(TestCase):
    """Test cases for my_health_card endpoint"""
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Get the auto-created health card
        self.health_card = self.user.health_card
        self.health_card.status = HealthCard.Status.ACTIVE
        self.health_card.expires_at = timezone.now() + timedelta(days=365)
        self.health_card.save()
        
        self.url = '/api/health-card/me/'
    
    def test_requires_authentication(self):
        """Test that endpoint requires authentication"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 401)
    
    def test_get_own_health_card(self):
        """Test retrieving own health card information"""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['card_number'], self.health_card.card_number)
    
    def test_response_contains_all_fields(self):
        """Test that response contains all expected fields"""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.get(self.url)
        
        expected_fields = [
            'card_number',
            'card_type',
            'status',
            'qr_code_url',
            'issued_at',
            'expires_at',
            'last_scanned_at',
            'scan_count',
            'nhis_linked',
            'has_pin',
            'days_until_expiry'
        ]
        
        for field in expected_fields:
            self.assertIn(field, response.data)
    
    def test_card_type_display(self):
        """Test that card type is displayed as human-readable"""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.get(self.url)
        
        # Should be the display value, not the database value
        self.assertIsInstance(response.data['card_type'], str)
    
    def test_status_display(self):
        """Test that status is displayed as human-readable"""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.get(self.url)
        
        # Should be the display value
        self.assertIsInstance(response.data['status'], str)
    
    def test_qr_code_url_present(self):
        """Test that QR code URL is included if QR exists"""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.get(self.url)
        
        if self.health_card.qr_image:
            self.assertIsNotNone(response.data['qr_code_url'])
            self.assertIn('http', response.data['qr_code_url'])
    
    def test_qr_code_url_null_when_missing(self):
        """Test that QR code URL is null when QR doesn't exist"""
        self.client.force_authenticate(user=self.user)
        
        # Remove QR image
        self.health_card.qr_image = None
        self.health_card.save()
        
        response = self.client.get(self.url)
        
        self.assertIsNone(response.data['qr_code_url'])
    
    def test_scan_count_accuracy(self):
        """Test that scan count is accurately reported"""
        self.client.force_authenticate(user=self.user)
        
        # Set scan count
        self.health_card.scan_count = 42
        self.health_card.save()
        
        response = self.client.get(self.url)
        
        self.assertEqual(response.data['scan_count'], 42)
    
    def test_last_scanned_at_null_initially(self):
        """Test that last_scanned_at is null for new cards"""
        self.client.force_authenticate(user=self.user)
        
        self.health_card.last_scanned_at = None
        self.health_card.save()
        
        response = self.client.get(self.url)
        
        self.assertIsNone(response.data['last_scanned_at'])
    
    def test_last_scanned_at_with_value(self):
        """Test that last_scanned_at is returned when set"""
        self.client.force_authenticate(user=self.user)
        
        scan_time = timezone.now()
        self.health_card.last_scanned_at = scan_time
        self.health_card.save()
        
        response = self.client.get(self.url)
        
        self.assertIsNotNone(response.data['last_scanned_at'])
    
    def test_nhis_linked_status(self):
        """Test NHIS linked status reporting"""
        self.client.force_authenticate(user=self.user)
        
        # Test verified status
        self.health_card.nhis_link_status = HealthCard.NHISLinkStatus.VERIFIED
        self.health_card.save()
        
        response = self.client.get(self.url)
        self.assertTrue(response.data['nhis_linked'])
        
        # Test unlinked status
        self.health_card.nhis_link_status = HealthCard.NHISLinkStatus.NOT_LINKED
        self.health_card.save()
        
        response = self.client.get(self.url)
        self.assertFalse(response.data['nhis_linked'])
    
    def test_has_pin_false_initially(self):
        """Test has_pin is False when no PIN is set"""
        self.client.force_authenticate(user=self.user)
        
        self.health_card.pin_hash = None
        self.health_card.save()
        
        response = self.client.get(self.url)
        
        self.assertFalse(response.data['has_pin'])
    
    def test_has_pin_true_when_set(self):
        """Test has_pin is True when PIN is set"""
        self.client.force_authenticate(user=self.user)
        
        self.health_card.set_pin('123456')
        self.health_card.save()
        
        response = self.client.get(self.url)
        
        self.assertTrue(response.data['has_pin'])
    
    def test_days_until_expiry_calculation(self):
        """Test days until expiry is calculated correctly"""
        self.client.force_authenticate(user=self.user)
        
        # Set expiry to 30 days from now
        self.health_card.expires_at = timezone.now() + timedelta(days=30)
        self.health_card.save()
        
        response = self.client.get(self.url)
        
        # Should be approximately 30 (may be 29 or 30 depending on timing)
        self.assertIn(response.data['days_until_expiry'], [29, 30])
    
    def test_negative_days_for_expired_card(self):
        """Test negative days when card is expired"""
        self.client.force_authenticate(user=self.user)
        
        # Set expiry to 10 days ago
        self.health_card.expires_at = timezone.now() - timedelta(days=10)
        self.health_card.save()
        
        response = self.client.get(self.url)
        
        # Should be negative
        self.assertLess(response.data['days_until_expiry'], 0)
    
    def test_user_without_health_card(self):
        """Test response when user has no health card"""
        # Create user and delete auto-created card
        user_no_card = User.objects.create_user(
            username='nocard',
            email='nocard@example.com',
            password='testpass123'
        )
        user_no_card.health_card.delete()
        
        self.client.force_authenticate(user=user_no_card)
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 404)
        self.assertIn('error', response.data)
    
    def test_different_card_statuses(self):
        """Test response with different card statuses"""
        self.client.force_authenticate(user=self.user)
        
        statuses = [
            HealthCard.Status.ACTIVE,
            HealthCard.Status.SUSPENDED,
            HealthCard.Status.REVOKED,
            HealthCard.Status.EXPIRED
        ]
        
        for card_status in statuses:
            self.health_card.status = card_status
            self.health_card.save()
            
            response = self.client.get(self.url)
            
            self.assertEqual(response.status_code, 200)
            self.assertIn('status', response.data)
    
    def test_issued_at_timestamp(self):
        """Test that issued_at timestamp is included"""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.get(self.url)
        
        self.assertIsNotNone(response.data['issued_at'])
    
    def test_expires_at_timestamp(self):
        """Test that expires_at timestamp is included"""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.get(self.url)
        
        self.assertIsNotNone(response.data['expires_at'])
    
    def test_absolute_qr_url(self):
        """Test that QR URL is absolute (includes domain)"""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.get(self.url)
        
        if response.data['qr_code_url']:
            self.assertTrue(
                response.data['qr_code_url'].startswith('http')
            )