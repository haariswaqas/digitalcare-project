from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from datetime import timedelta
from unittest.mock import patch, MagicMock
import json
import uuid
from ...models import User, HealthCard, ScanLog
from ...tasks import send_scan_notification



class IntegrationTestCase(TransactionTestCase):
    """Integration tests for complete workflows"""
    
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
        """Clean up after each test"""
        cache.clear()
    
    @patch('api.views.health_card_views.notify_card_owner')
    def test_complete_scan_workflow_with_pin(self, mock_notify):
        """Test complete workflow: set PIN, scan with PIN, check history"""
        # Step 1: Set PIN
        self.client.force_authenticate(user=self.user)
        response = self.client.post('/api/health-card/set-pin/', {'pin': '567890'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Step 2: Scan card with PIN (unauthenticated)
        self.client.force_authenticate(user=None)
        scan_url = f'/api/health-card/scan/{self.health_card.access_token}/'
        response = self.client.get(scan_url, {'pin': '567890'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Step 3: Check scan history
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/health-card/scan-history/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_scans'], 1)
    
    def test_security_workflow_pin_lockout_and_regenerate(self):
        """Test security workflow: PIN lockout, then regenerate QR"""
        # Set PIN
        self.client.force_authenticate(user=self.user)
        self.client.post('/api/health-card/set-pin/', {'pin': '567890'})
        
        # Trigger lockout
        self.client.force_authenticate(user=None)
        scan_url = f'/api/health-card/scan/{self.health_card.access_token}/'
        for _ in range(3):
            self.client.get(scan_url, {'pin': 'wrong'})
        
        # Verify locked
        response = self.client.get(scan_url, {'pin': '567890'})
        self.assertEqual(response.status_code, status.HTTP_423_LOCKED)
        
        # Regenerate QR (new token should clear lockout)
        self.client.force_authenticate(user=self.user)
        response = self.client.post('/api/health-card/regenerate-qr/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Get new token and verify it works
        self.health_card.refresh_from_db()
        new_scan_url = f'/api/health-card/scan/{self.health_card.access_token}/'
        self.client.force_authenticate(user=None)
        response = self.client.get(new_scan_url, {'pin': '567890'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)


