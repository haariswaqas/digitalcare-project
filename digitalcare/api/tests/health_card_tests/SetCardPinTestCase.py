from django.test import TestCase
from django.utils import timezone
from django.core.cache import cache
from rest_framework.test import APIClient
from rest_framework import status
from datetime import timedelta
import uuid

from ...models import User, HealthCard



class SetCardPINTestCase(TestCase):
    """Test suite for setting/updating card PIN"""
    
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
        
        self.url = '/api/health-card/set-pin/'
    
    def tearDown(self):
        """Clean up after each test"""
        cache.clear()
    
    def test_set_pin_unauthenticated(self):
        """Test that unauthenticated users cannot set PIN"""
        response = self.client.post(self.url, {'pin': '123456'})
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_set_pin_success(self):
        """Test successful PIN setting"""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.post(self.url, {'pin': '123456'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Verify PIN was set
        self.health_card.refresh_from_db()
        self.assertIsNotNone(self.health_card.pin_hash)
        self.assertTrue(self.health_card.check_pin('123456'))
    
    def test_set_pin_too_short(self):
        """Test that PIN must be at least 6 digits"""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.post(self.url, {'pin': '1234'})
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('6 and 8 digits', response.data['error'])
    
    def test_set_pin_non_numeric(self):
        """Test that PIN must be numeric"""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.post(self.url, {'pin': 'abc123'})
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('only digits', response.data['error'])
    
    def test_set_pin_weak_patterns(self):
        """Test rejection of weak PIN patterns"""
        self.client.force_authenticate(user=self.user)
        
        weak_pins = ['111111', '123456', '654321', '12345678']
        
        for weak_pin in weak_pins:
            response = self.client.post(self.url, {'pin': weak_pin})
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn('too weak', response.data['error'])
    
    def test_update_pin_requires_current(self):
        """Test that updating PIN requires current PIN"""
        self.client.force_authenticate(user=self.user)
        
        # Set initial PIN
        self.health_card.set_pin('123456')
        self.health_card.save()
        
        # Try to update without current PIN
        response = self.client.post(self.url, {'pin': '789012'})
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Current PIN required', response.data['error'])
    
    def test_update_pin_with_correct_current(self):
        """Test successful PIN update with correct current PIN"""
        self.client.force_authenticate(user=self.user)
        
        # Set initial PIN
        self.health_card.set_pin('123456')
        self.health_card.save()
        
        # Update with correct current PIN
        response = self.client.post(self.url, {
            'pin': '789012',
            'current_pin': '123456'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify new PIN works
        self.health_card.refresh_from_db()
        self.assertTrue(self.health_card.check_pin('789012'))
        self.assertFalse(self.health_card.check_pin('123456'))
    
    def test_update_pin_with_incorrect_current(self):
        """Test PIN update fails with incorrect current PIN"""
        self.client.force_authenticate(user=self.user)
        
        # Set initial PIN
        self.health_card.set_pin('123456')
        self.health_card.save()
        
        # Try to update with wrong current PIN
        response = self.client.post(self.url, {
            'pin': '789012',
            'current_pin': '999999'
        })
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # Verify PIN didn't change
        self.health_card.refresh_from_db()
        self.assertTrue(self.health_card.check_pin('123456'))
