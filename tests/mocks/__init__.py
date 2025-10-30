"""
Mock Implementations Package for Flask Testing

This package provides comprehensive mock implementations for all external dependencies
used in the Flask application testing suite. These mocks enable unit and integration
tests to run in complete isolation without requiring actual external services, databases,
or third-party APIs.

The package includes mocks for:
- Database operations (SQLAlchemy Session, Query, Transaction)
- External API services (Email, Payment, SMS, OAuth, Monitoring)
- File system operations (Storage, Upload, File handling)
- Cache systems (Redis, Memcached)
- Message queues (RabbitMQ, Redis Pub/Sub, Celery)
- Cloud storage (AWS S3, Google Cloud Storage)

Usage:
    # Import individual mock classes
    from tests.mocks import MockDatabaseSession, MockEmailService
    
    # Use in test functions
    def test_user_creation():
        db = MockDatabaseSession()
        email = MockEmailService()
        # Test code here
    
    # Or import all at once
    from tests.mocks import *

Design Principles:
- Complete test isolation: No real network calls or database connections
- Comprehensive API coverage: All essential methods mocked
- State tracking: All mocks track calls and history for verification
- Configurable behavior: Mocks can be configured for different test scenarios
- pytest integration: Includes pytest fixtures for easy test setup

Organization:
- mock_database.py: Database session, query, and transaction mocks
- mock_external_api.py: External service mocks (email, payment, SMS, OAuth, monitoring)
- mock_file_system.py: File storage and upload mocks
- mock_cache.py: Redis and Memcached cache mocks
- mock_message_queue.py: Message queue and background task mocks
- mock_cloud_storage.py: Cloud storage service mocks

Best Practices:
1. Use mocks for unit tests to ensure isolation
2. Configure mock behavior using return values and side effects
3. Verify mock interactions using history tracking methods
4. Reset mock state between tests using pytest fixtures
5. Use integration tests with real services for end-to-end validation
"""

# Database Mocks
from tests.mocks.mock_database import (
    MockDatabaseSession,
    MockQuery,
    MockTransaction,
)

# External API Mocks
from tests.mocks.mock_external_api import (
    MockEmailService,
    MockPaymentGateway,
    MockSMSService,
    MockOAuthProvider,
    MockMonitoringService,
)

# File System Mocks
from tests.mocks.mock_file_system import (
    MockFileStorage,
    MockFileSystem,
    create_mock_uploaded_file,
)

# Cache Mocks
from tests.mocks.mock_cache import (
    MockRedisCache,
    MockMemcachedCache,
)

# Message Queue Mocks
from tests.mocks.mock_message_queue import (
    MockRabbitMQChannel,
    MockRedisPublisher,
    MockCeleryTask,
)

# Cloud Storage Mocks
from tests.mocks.mock_cloud_storage import (
    MockS3Client,
    MockGCSClient,
)

# Public API - explicitly define what gets exported with "from tests.mocks import *"
__all__ = [
    # Database mocks
    'MockDatabaseSession',
    'MockQuery',
    'MockTransaction',
    
    # External API mocks
    'MockEmailService',
    'MockPaymentGateway',
    'MockSMSService',
    'MockOAuthProvider',
    'MockMonitoringService',
    
    # File system mocks
    'MockFileStorage',
    'MockFileSystem',
    'create_mock_uploaded_file',
    
    # Cache mocks
    'MockRedisCache',
    'MockMemcachedCache',
    
    # Message queue mocks
    'MockRabbitMQChannel',
    'MockRedisPublisher',
    'MockCeleryTask',
    
    # Cloud storage mocks
    'MockS3Client',
    'MockGCSClient',
]


# Package-level convenience functions for common mock scenarios

def get_all_database_mocks():
    """
    Get all database-related mock classes.
    
    Returns:
        Dict[str, type]: Dictionary mapping mock names to mock classes
    """
    return {
        'MockDatabaseSession': MockDatabaseSession,
        'MockQuery': MockQuery,
        'MockTransaction': MockTransaction,
    }


def get_all_external_api_mocks():
    """
    Get all external API mock classes.
    
    Returns:
        Dict[str, type]: Dictionary mapping mock names to mock classes
    """
    return {
        'MockEmailService': MockEmailService,
        'MockPaymentGateway': MockPaymentGateway,
        'MockSMSService': MockSMSService,
        'MockOAuthProvider': MockOAuthProvider,
        'MockMonitoringService': MockMonitoringService,
    }


def get_all_storage_mocks():
    """
    Get all storage-related mock classes (file system and cloud).
    
    Returns:
        Dict[str, type]: Dictionary mapping mock names to mock classes
    """
    return {
        'MockFileStorage': MockFileStorage,
        'MockFileSystem': MockFileSystem,
        'MockS3Client': MockS3Client,
        'MockGCSClient': MockGCSClient,
    }


def get_all_cache_mocks():
    """
    Get all cache-related mock classes.
    
    Returns:
        Dict[str, type]: Dictionary mapping mock names to mock classes
    """
    return {
        'MockRedisCache': MockRedisCache,
        'MockMemcachedCache': MockMemcachedCache,
    }


def get_all_messaging_mocks():
    """
    Get all messaging and queue-related mock classes.
    
    Returns:
        Dict[str, type]: Dictionary mapping mock names to mock classes
    """
    return {
        'MockRabbitMQChannel': MockRabbitMQChannel,
        'MockRedisPublisher': MockRedisPublisher,
        'MockCeleryTask': MockCeleryTask,
    }


# Version information
__version__ = '1.0.0'
__author__ = 'Blitzy Testing Infrastructure Team'
__status__ = 'Production'
