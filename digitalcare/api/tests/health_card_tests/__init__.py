"""
To run all tests:
    python manage.py test api.tests.test_health_card_views

To run specific test class:
    python manage.py test api.tests.test_health_card_views.HealthCardScanTestCase

To run specific test:
    python manage.py test api.tests.test_health_card_views.HealthCardScanTestCase.test_successful_scan_without_pin

To run with coverage:
    coverage run --source='api' manage.py test api.tests.test_health_card_views
    coverage report
    coverage html

To run with verbose output:
    python manage.py test api.tests.test_health_card_views --verbosity=2
"""

from .DownloadHealthCardDataTestCase import *
from .EdgeCaseTestCase import *
from .HealthCardScanTestCase import *
from .IntegrationTestCase import *
from .MyHealthCardTestCase import *
from .PerformanceTestCase import *
from .RegenerateQRCodeTestCase import *
from .RemoveCardPinTestCase import *
from .ScanHistoryTestCase import *
from .SetCardPinTestCase import *
from .SecurityTestCase import *




