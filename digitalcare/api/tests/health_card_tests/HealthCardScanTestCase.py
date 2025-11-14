# api/tests/test_health_card_views/HealthCardScanTestCase.py
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.cache import cache
from rest_framework.test import APIClient
from datetime import timedelta
from unittest.mock import patch, MagicMock
import io
from PIL import Image
from ...models import User, HealthCard, ScanLog



class HealthCardScanTestCase(TestCase):
    """Test cases for the scan_health_card public endpoint"""
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        cache.clear()
        
        # Create test user and health card
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Get the auto-created health card from signal
        self.health_card = self.user.health_card
        self.health_card.status = HealthCard.Status.ACTIVE
        self.health_card.expires_at = timezone.now() + timedelta(days=365)
        self.health_card.save()
        
        self.scan_url = f'/api/health-card/scan/{self.health_card.access_token}/'
    
    def tearDown(self):
        """Clean up after tests"""
        cache.clear()
    
    def test_successful_scan_without_pin(self):
        """Test successful scan of health card without PIN"""
        response = self.client.get(self.scan_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['success'])
        self.assertIn('data', response.data)
        self.assertIn('scanned_at', response.data)
        
        # Verify scan was logged
        self.health_card.refresh_from_db()
        self.assertEqual(self.health_card.scan_count, 1)
        self.assertIsNotNone(self.health_card.last_scanned_at)
        
        # Verify scan log was created
        scan_log = ScanLog.objects.filter(card=self.health_card).first()
        self.assertIsNotNone(scan_log)
        self.assertTrue(scan_log.success)
    
    def test_successful_scan_with_valid_pin(self):
        """Test successful scan with correct PIN"""
        # Set PIN on health card
        self.health_card.set_pin('123456')
        self.health_card.save()
        
        response = self.client.get(self.scan_url, {'pin': '123456'})
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['success'])
        self.assertEqual(self.health_card.scan_count, 1)
    
    def test_scan_requires_pin_when_set(self):
        """Test that PIN is required when set on card"""
        self.health_card.set_pin('123456')
        self.health_card.save()
        
        response = self.client.get(self.scan_url)
        
        self.assertEqual(response.status_code, 401)
        self.assertIn('error', response.data)
        self.assertTrue(response.data.get('requires_pin'))
    
    def test_scan_with_invalid_pin(self):
        """Test scan attempt with incorrect PIN"""
        self.health_card.set_pin('123456')
        self.health_card.save()
        
        response = self.client.get(self.scan_url, {'pin': '999999'})
        
        self.assertEqual(response.status_code, 401)
        self.assertIn('error', response.data)
        
        # Verify failed attempt was logged
        scan_log = ScanLog.objects.filter(card=self.health_card, success=False).first()
        self.assertIsNotNone(scan_log)
    
    def test_pin_lockout_after_three_attempts(self):
        """Test that card locks after 3 failed PIN attempts"""
        self.health_card.set_pin('123456')
        self.health_card.save()
        
        # Make 3 failed attempts
        for i in range(3):
            response = self.client.get(self.scan_url, {'pin': '999999'})
            self.assertEqual(response.status_code, 401)
        
        # 4th attempt should be locked
        response = self.client.get(self.scan_url, {'pin': '123456'})
        self.assertEqual(response.status_code, 423)
        self.assertIn('locked', response.data['error'].lower())
    
    def test_pin_cache_cleared_on_success(self):
        """Test that failed PIN attempts are cleared after successful scan"""
        self.health_card.set_pin('123456')
        self.health_card.save()
        
        # Make 2 failed attempts
        for i in range(2):
            self.client.get(self.scan_url, {'pin': '999999'})
        
        # Successful scan
        response = self.client.get(self.scan_url, {'pin': '123456'})
        self.assertEqual(response.status_code, 200)
        
        # Should be able to scan again without lockout
        response = self.client.get(self.scan_url, {'pin': '123456'})
        self.assertEqual(response.status_code, 200)
    
    def test_scan_expired_card(self):
        """Test scanning an expired health card"""
        self.health_card.expires_at = timezone.now() - timedelta(days=1)
        self.health_card.save()
        
        response = self.client.get(self.scan_url)
        
        self.assertEqual(response.status_code, 403)
        self.assertIn('error', response.data)
    
    def test_scan_inactive_card(self):
        """Test scanning an inactive health card"""
        self.health_card.status = HealthCard.Status.SUSPENDED
        self.health_card.save()
        
        response = self.client.get(self.scan_url)
        
        self.assertEqual(response.status_code, 403)
        self.assertIn('error', response.data)
    
    def test_scan_with_invalid_token(self):
        """Test scanning with non-existent access token"""
        invalid_url = '/api/health-card/scan/invalid-token-12345/'
        response = self.client.get(invalid_url)
        
        self.assertEqual(response.status_code, 404)
        self.assertIn('error', response.data)
    
    def test_rate_limiting_per_ip(self):
        """Test that IP-based rate limiting works"""
        # Make 11 requests (limit is 10)
        for i in range(11):
            response = self.client.get(self.scan_url)
        
        # 11th request should be rate limited
        self.assertEqual(response.status_code, 429)
        self.assertIn('Too many requests', response.data['error'])
    
    def test_sensitive_data_redaction(self):
        """Test that sensitive data is redacted in public scan response"""
        response = self.client.get(self.scan_url)
        
        self.assertEqual(response.status_code, 200)
        data = response.data['data']
        
        # Check that sensitive fields are redacted
        if 'medical_records' in data:
            self.assertIn('note', data['medical_records'])
        
        # These should be redacted if present
        sensitive_fields = ['social_security_number', 'national_id', 'financial_info']
        for field in sensitive_fields:
            if field in data:
                self.assertEqual(data[field], '[REDACTED]')
    
    def test_client_ip_extraction(self):
        """Test that client IP is correctly extracted"""
        # Test with X-Forwarded-For header
        response = self.client.get(
            self.scan_url,
            HTTP_X_FORWARDED_FOR='192.168.1.100, 10.0.0.1'
        )
        
        scan_log = ScanLog.objects.filter(card=self.health_card).first()
        self.assertEqual(scan_log.ip_address, '192.168.1.100')
    
    @patch('api.views.health_card_views.notify_card_owner')
    def test_owner_notification_sent(self, mock_notify):
        """Test that card owner is notified of successful scan"""
        response = self.client.get(self.scan_url)
        
        self.assertEqual(response.status_code, 200)
        mock_notify.assert_called_once()
    
    def test_scan_increments_counter(self):
        """Test that scan count is incremented"""
        initial_count = self.health_card.scan_count
        
        self.client.get(self.scan_url)
        
        self.health_card.refresh_from_db()
        self.assertEqual(self.health_card.scan_count, initial_count + 1)
    
    def test_scan_updates_last_scanned_at(self):
        """Test that last_scanned_at timestamp is updated"""
        self.assertIsNone(self.health_card.last_scanned_at)
        
        self.client.get(self.scan_url)
        
        self.health_card.refresh_from_db()
        self.assertIsNotNone(self.health_card.last_scanned_at)
    
    def test_multiple_successful_scans(self):
        """Test multiple successful scans increment counter correctly"""
        for i in range(5):
            response = self.client.get(self.scan_url)
            self.assertEqual(response.status_code, 200)
        
        self.health_card.refresh_from_db()
        self.assertEqual(self.health_card.scan_count, 5)
    
    def test_scan_log_contains_metadata(self):
        """Test that scan log contains all required metadata"""
        user_agent = 'TestBrowser/1.0'
        response = self.client.get(
            self.scan_url,
            HTTP_USER_AGENT=user_agent
        )
        
        scan_log = ScanLog.objects.filter(card=self.health_card).first()
        self.assertIsNotNone(scan_log.ip_address)
        self.assertEqual(scan_log.user_agent, user_agent)
        self.assertIsNotNone(scan_log.timestamp)
        self.assertTrue(scan_log.success)
    
    def test_generic_error_messages(self):
        """Test that error messages don't reveal system details"""
        # Expired card
        self.health_card.expires_at = timezone.now() - timedelta(days=1)
        self.health_card.save()
        
        response = self.client.get(self.scan_url)
        self.assertEqual(response.data['error'], 'Unable to access health card')
        
        # Invalid PIN
        self.health_card.expires_at = timezone.now() + timedelta(days=365)
        self.health_card.set_pin('123456')
        self.health_card.save()
        
        response = self.client.get(self.scan_url, {'pin': '999999'})
        self.assertEqual(response.data['error'], 'Unable to access health card')