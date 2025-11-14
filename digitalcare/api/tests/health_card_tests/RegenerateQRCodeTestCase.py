from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from datetime import timedelta
import uuid
from ...models import User, HealthCard



class RegenerateQRCodeTestCase(TestCase):
    """Test suite for QR code regeneration"""
    
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
        
        self.url = '/api/health-card/regenerate-qr/'
    
    def test_regenerate_qr_unauthenticated(self):
        """Test that unauthenticated users cannot regenerate QR"""
        response = self.client.post(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_regenerate_qr_authenticated(self):
        """Test successful QR code regeneration"""
        self.client.force_authenticate(user=self.user)
        
        old_token = self.health_card.access_token
        
        response = self.client.post(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('qr_url', response.data)
        
        # Verify token changed
        self.health_card.refresh_from_db()
        self.assertNotEqual(self.health_card.access_token, old_token)
    
    def test_regenerate_qr_no_card(self):
        """Test regeneration when user has no health card"""
        user_without_card = User.objects.create_user(
            username='nocard',
            email='nocard@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=user_without_card)
        
        response = self.client.post(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
