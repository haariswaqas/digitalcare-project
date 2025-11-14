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


class DownloadHealthCardDataTestCase(TestCase):
    """Test suite for downloading health card data"""
    
    def setUp(self):
        """Set up test data before each test"""
        cache.clear()
        
        self.client = APIClient()
        
        # Create test user
        self.user = User.objects.create_user(
            username=f'testuser_{uuid.uuid4().hex[:6]}',  # make username unique per test
            email=f'test_{uuid.uuid4().hex[:6]}@example.com',
            password='testpass123'
        )
        
        # Ensure no existing HealthCard for this user
        HealthCard.objects.filter(user=self.user).delete()
        
        # Create health card
        self.health_card = HealthCard.objects.create(
            user=self.user,
            card_number=f'HC{uuid.uuid4().hex[:6]}',
            status=HealthCard.Status.ACTIVE,
            expires_at=timezone.now() + timedelta(days=365)
        )
        
        self.url = '/api/health-card/download/'
    
    def test_download_unauthenticated(self):
        """Test that unauthenticated users cannot download data"""
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_download_authenticated(self):
        """Test successful data download"""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('data', response.data)
        self.assertIn('exported_at', response.data)
        self.assertEqual(response.data['export_type'], 'complete')
