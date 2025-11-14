# api/tests/test_health_card_performance.py

from django.test import TestCase
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from datetime import timedelta
import uuid
from ...models import User, HealthCard, ScanLog


class PerformanceTestCase(TestCase):
    """Test performance, scalability, and logging efficiency of HealthCard features"""

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

        # Ensure no existing card for this user
        HealthCard.objects.filter(user=self.user).delete()

        # Create an active health card
        self.health_card = HealthCard.objects.create(
            user=self.user,
            card_number=f'HC{uuid.uuid4().hex[:6]}',
            status=HealthCard.Status.ACTIVE,
            expires_at=timezone.now() + timedelta(days=365)
        )

    def tearDown(self):
        """Clean up after each test"""
        cache.clear()

    def test_scan_history_with_many_logs(self):
        """Test scan history retrieval performance with a large number of logs"""
        # Generate 100 scan logs
        for i in range(100):
            ScanLog.objects.create(
                card=self.health_card,
                ip_address=f'192.168.1.{i % 255}',
                user_agent='TestAgent',
                success=True,
                timestamp=timezone.now() - timedelta(hours=i)
            )

        self.client.force_authenticate(user=self.user)

        # Should only return requested limit
        response = self.client.get('/api/health-card/scan-history/', {'limit': 10})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['recent_scans']), 10)

        # Verify most recent scans are returned
        first_scan = response.data['recent_scans'][0]
        self.assertIn('timestamp', first_scan)

    def test_multiple_failed_scans_logging(self):
        """Test that all failed scan attempts are correctly logged"""
        self.health_card.set_pin('123456')
        self.health_card.save()

        scan_url = f'/api/health-card/scan/{self.health_card.access_token}/'

        initial_log_count = ScanLog.objects.filter(card=self.health_card).count()

        # Simulate 5 failed scans
        for _ in range(5):
            self.client.get(scan_url, {'pin': 'wrong'})

        # Verify all 5 failures were logged
        final_log_count = ScanLog.objects.filter(card=self.health_card).count()
        self.assertEqual(final_log_count - initial_log_count, 5)

        # Verify failures are marked correctly
        failed_logs = ScanLog.objects.filter(card=self.health_card, success=False).count()
        self.assertGreaterEqual(failed_logs, 5)
