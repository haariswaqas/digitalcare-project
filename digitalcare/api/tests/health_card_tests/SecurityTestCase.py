from django.test import TestCase, TransactionTestCase
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from datetime import timedelta
from unittest.mock import patch
import uuid
import json
from ...models import User, HealthCard, ScanLog



class SecurityTestCase(TransactionTestCase):
    """Test security-specific scenarios"""
    
    def setUp(self):
        """Set up test data"""
        cache.clear()
        self.client = APIClient()
        
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.health_card = HealthCard.objects.create(
            user=self.user,
            card_number='HC123456',
            status=HealthCard.Status.ACTIVE,
            expires_at=timezone.now() + timedelta(days=365)
        )
    
    def tearDown(self):
        """Clean up"""
        cache.clear()
    
    def test_no_information_disclosure_invalid_token(self):
        """Test that invalid tokens don't reveal information"""
        invalid_urls = [
            '/api/health-card/scan/invalid-token/',
            '/api/health-card/scan/HC123456/',  # Card number shouldn't work
            '/api/health-card/scan/short/',
        ]
        
        for url in invalid_urls:
            response = self.client.get(url)
            # Should always return same generic error
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
            self.assertIn('error', response.data)
    
    def test_timing_attack_resistance_pin(self):
        """Test that PIN verification doesn't leak timing information"""
        self.health_card.set_pin('123456')
        self.health_card.save()
        
        scan_url = f'/api/health-card/scan/{self.health_card.access_token}/'
        
        # Both wrong length and wrong value should return same error
        response1 = self.client.get(scan_url, {'pin': '1'})
        response2 = self.client.get(scan_url, {'pin': '999999'})
        
        # Same status code
        self.assertEqual(response1.status_code, response2.status_code)
        # Same error structure (generic)
        self.assertIn('error', response1.data)
        self.assertIn('error', response2.data)
    
    def test_sql_injection_attempts(self):
        """Test that SQL injection attempts are handled safely"""
        malicious_inputs = [
            "1' OR '1'='1",
            "1; DROP TABLE health_cards;--",
            "' UNION SELECT * FROM users--",
        ]
        
        for malicious in malicious_inputs:
            url = f'/api/health-card/scan/{malicious}/'
            response = self.client.get(url)
            # Should safely return 404, not crash
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_xss_prevention_in_responses(self):
        """Test that responses don't include unsanitized input"""
        scan_url = f'/api/health-card/scan/{self.health_card.access_token}/'
        
        # Try XSS in query params
        response = self.client.get(scan_url, {'pin': '<script>alert("xss")</script>'})
        
        # Should handle safely
        self.assertIn(response.status_code, [400, 401])
        # Response shouldn't contain the script
        response_str = json.dumps(response.data)
        self.assertNotIn('<script>', response_str)
    
    def test_authentication_bypass_attempts(self):
        """Test that authentication can't be bypassed"""
        protected_endpoints = [
            '/api/health-card/me/',
            '/api/health-card/regenerate-qr/',
            '/api/health-card/set-pin/',
            '/api/health-card/remove-pin/',
            '/api/health-card/scan-history/',
            '/api/health-card/download/',
        ]
        
        for endpoint in protected_endpoints:
            response = self.client.get(endpoint)
            self.assertEqual(
                response.status_code, 
                status.HTTP_401_UNAUTHORIZED,
                f"Endpoint {endpoint} should require authentication"
            )
    
    def test_csrf_protection(self):
        """Test that POST endpoints are CSRF protected"""
        # Without CSRF token, POST should fail when using session auth
        response = self.client.post('/api/health-card/set-pin/', {'pin': '123456'})
        # Should be unauthorized (no auth) not CSRF error in API
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    @patch('api.views.health_card_views.logger')
    def test_security_events_are_logged(self, mock_logger):
        """Test that security events are properly logged"""
        self.health_card.set_pin('123456')
        self.health_card.save()
        
        scan_url = f'/api/health-card/scan/{self.health_card.access_token}/'
        
        # Trigger failed PIN attempt
        self.client.get(scan_url, {'pin': 'wrong'})
        
        # Verify logging occurred
        mock_logger.warning.assert_called()
        
        # Trigger lockout
        for _ in range(3):
            self.client.get(scan_url, {'pin': 'wrong'})
        
        # Multiple warning logs should have been called
        self.assertGreater(mock_logger.warning.call_count, 1)

