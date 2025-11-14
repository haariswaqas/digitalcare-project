from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from datetime import timedelta
import uuid
from ...models import User, HealthCard, ScanLog




class ScanHistoryTestCase(TestCase):
    """Test suite for scan history retrieval"""
    
    def setUp(self):
        """Set up test data"""
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
        
        # Create some scan logs
        for i in range(5):
            ScanLog.objects.create(
                card=self.health_card,
                ip_address=f'192.168.1.{i}',
                user_agent='TestAgent',
                success=True,
                timestamp=timezone.now() - timedelta(hours=i)
            )
        
        self.url = '/api/health-card/scan-history/'
    
    def test_scan_history_unauthenticated(self):
        """Test that unauthenticated users cannot access scan history"""
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_scan_history_authenticated(self):
        """Test successful scan history retrieval"""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('recent_scans', response.data)
        self.assertIn('total_scans', response.data)
        self.assertEqual(len(response.data['recent_scans']), 5)
    
    def test_scan_history_with_limit(self):
        """Test scan history with custom limit"""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.get(self.url, {'limit': 3})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['recent_scans']), 3)
    
    def test_scan_history_shows_details(self):
        """Test that scan history includes all necessary details"""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.get(self.url, {'limit': 1})
        
        scan = response.data['recent_scans'][0]
        self.assertIn('timestamp', scan)
        self.assertIn('success', scan)
        self.assertIn('ip_address', scan)
        self.assertIn('user_agent', scan)

