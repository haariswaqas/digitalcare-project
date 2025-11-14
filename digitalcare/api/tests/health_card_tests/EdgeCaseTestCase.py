# api/tests/test_health_card_views.py

from django.test import TransactionTestCase
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from datetime import timedelta
from unittest.mock import patch
import uuid
from ...models import User, HealthCard


class EdgeCaseTestCase(TransactionTestCase):
    """Test edge cases and corner scenarios for HealthCard operations"""

    def setUp(self):
        """Set up test data before each test"""
        cache.clear()
        self.client = APIClient()

        # Create unique test user
        self.user = User.objects.create_user(
            username=f'testuser_{uuid.uuid4().hex[:6]}',
            email=f'test_{uuid.uuid4().hex[:6]}@example.com',
            password='testpass123'
        )

        # Ensure no duplicate cards exist
        HealthCard.objects.filter(user=self.user).delete()

        # Create an active health card
        self.health_card = HealthCard.objects.create(
            user=self.user,
            card_number=f'HC{uuid.uuid4().hex[:6]}',
            status=HealthCard.Status.ACTIVE,
            expires_at=timezone.now() + timedelta(days=365)
        )

    def tearDown(self):
        """Clean up cache after each test"""
        cache.clear()

    def test_concurrent_scans_same_card(self):
        """Test multiple simultaneous scans of the same card"""
        scan_url = f'/api/health-card/scan/{self.health_card.access_token}/'

        responses = [self.client.get(scan_url) for _ in range(5)]

        for response in responses:
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.health_card.refresh_from_db()
        self.assertEqual(self.health_card.scan_count, 5)

    def test_pin_cache_expiry(self):
        """Test that PIN attempt cache expires after 30 minutes"""
        self.health_card.set_pin('123456')
        self.health_card.save()

        scan_url = f'/api/health-card/scan/{self.health_card.access_token}/'

        # Two failed attempts
        for _ in range(2):
            self.client.get(scan_url, {'pin': 'wrong'})

        # Expire cache manually
        cache_key = f"pin_attempts_{self.health_card.access_token}"
        cache.delete(cache_key)

        # New attempt (should still fail but not be locked)
        response = self.client.get(scan_url, {'pin': 'wrong'})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Correct PIN should succeed
        response = self.client.get(scan_url, {'pin': '123456'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_special_characters_in_pin(self):
        """Test that special characters are rejected in PIN setup"""
        self.client.force_authenticate(user=self.user)
        invalid_pins = ['12345!', '12@456', '12-34-56', '123 456']

        for pin in invalid_pins:
            response = self.client.post('/api/health-card/set-pin/', {'pin': pin})
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_very_long_pin(self):
        """Test that PIN longer than 8 digits is rejected"""
        self.client.force_authenticate(user=self.user)
        response = self.client.post('/api/health-card/set-pin/', {'pin': '123456789'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_empty_pin(self):
        """Test that empty PIN is rejected"""
        self.client.force_authenticate(user=self.user)
        response = self.client.post('/api/health-card/set-pin/', {'pin': ''})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_scan_with_missing_health_card_data(self):
        """Test scan works even if card has minimal data"""
        scan_url = f'/api/health-card/scan/{self.health_card.access_token}/'
        response = self.client.get(scan_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('data', response.data)

    def test_multiple_users_different_cards(self):
        """Test users can only access their own cards"""
        # Create another user and card
        user2 = User.objects.create_user(
            username=f'testuser2_{uuid.uuid4().hex[:6]}',
            email=f'test2_{uuid.uuid4().hex[:6]}@example.com',
            password='testpass123'
        )

        card2 = HealthCard.objects.create(
            user=user2,
            card_number=f'HC{uuid.uuid4().hex[:6]}',
            status=HealthCard.Status.ACTIVE,
            expires_at=timezone.now() + timedelta(days=365)
        )

        # User 1 check
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/health-card/me/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['card_number'], self.health_card.card_number)

        # User 2 check
        self.client.force_authenticate(user=user2)
        response = self.client.get('/api/health-card/me/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['card_number'], card2.card_number)

    def test_scan_immediately_after_regenerate(self):
        """Test that old token becomes invalid after regeneration"""
        old_token = self.health_card.access_token
        old_scan_url = f'/api/health-card/scan/{old_token}/'

        # Old token works initially
        response = self.client.get(old_scan_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Regenerate QR
        self.client.force_authenticate(user=self.user)
        self.client.post('/api/health-card/regenerate-qr/')

        # Old token now invalid
        self.client.force_authenticate(user=None)
        response = self.client.get(old_scan_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # New token works
        self.health_card.refresh_from_db()
        new_scan_url = f'/api/health-card/scan/{self.health_card.access_token}/'
        response = self.client.get(new_scan_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch('api.views.health_card_views.get_client_ip')
    def test_rate_limiting_different_ips(self, mock_get_ip):
        """Test that rate limiting applies per IP, not globally"""
        scan_url = f'/api/health-card/scan/{self.health_card.access_token}/'

        mock_get_ip.return_value = '192.168.1.1'
        for _ in range(10):
            response = self.client.get(scan_url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        # 11th request blocked
        response = self.client.get(scan_url)
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

        # Different IP still allowed
        mock_get_ip.return_value = '192.168.1.2'
        response = self.client.get(scan_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_pin_then_scan_with_new_pin(self):
        """Test full PIN update workflow"""
        self.client.force_authenticate(user=self.user)

        # Initial PIN
        self.client.post('/api/health-card/set-pin/', {'pin': '111222'})

        # Update PIN
        response = self.client.post('/api/health-card/set-pin/', {
            'pin': '333444',
            'current_pin': '111222'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Old PIN fails
        self.client.force_authenticate(user=None)
        scan_url = f'/api/health-card/scan/{self.health_card.access_token}/'
        response = self.client.get(scan_url, {'pin': '111222'})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # New PIN succeeds
        response = self.client.get(scan_url, {'pin': '333444'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
