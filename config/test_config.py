"""
Test Configuration Module

This module defines the TestConfig class containing Flask application settings
specifically for the testing environment. It provides configuration that enables
proper test isolation, fast test execution, and secure testing practices.

The configuration is designed to:
- Use in-memory SQLite database for fast, isolated tests
- Disable CSRF protection for easier API testing
- Provide test-specific secret keys (NOT suitable for production)
- Enable testing mode flags for proper Flask test behavior
- Allow flexible host configuration for testing
- Enable proper exception handling during tests

This configuration is loaded by tests/conftest.py when creating the test Flask
application instance.

Example Usage:
    from config.test_config import TestConfig
    
    app = Flask(__name__)
    app.config.from_object(TestConfig)
"""


class TestConfig:
    """
    Test environment configuration class.
    
    This class defines all Flask application settings required for running
    tests in an isolated, fast, and secure manner. All settings are optimized
    for test execution rather than production use.
    
    Attributes:
        TESTING (bool): Enable Flask testing mode. This disables error catching
            during request handling so that you get better error reports when
            performing test requests against the application.
        
        DEBUG (bool): Disable debug mode during tests to match production
            behavior and prevent debug toolbar interference.
        
        SQLALCHEMY_DATABASE_URI (str): In-memory SQLite database URI. Using
            ':memory:' ensures each test run starts with a fresh database and
            provides maximum test execution speed.
        
        SQLALCHEMY_TRACK_MODIFICATIONS (bool): Disable SQLAlchemy modification
            tracking to reduce overhead and prevent warnings during tests.
        
        WTF_CSRF_ENABLED (bool): Disable CSRF protection for forms during
            testing. This allows easier testing of POST/PUT/DELETE endpoints
            without needing to generate CSRF tokens.
        
        SECRET_KEY (str): Test-specific secret key for session management and
            cryptographic signing. WARNING: This key is intentionally weak and
            should NEVER be used in production.
        
        JWT_SECRET_KEY (str): Test-specific secret key for JWT token generation
            and validation. WARNING: This key is intentionally weak and should
            NEVER be used in production.
        
        SERVER_NAME (None): Set to None to allow flexible host configuration
            during testing. This enables tests to run with various host headers
            and makes it easier to test with the Flask test client.
        
        PRESERVE_CONTEXT_ON_EXCEPTION (bool): Set to False to allow proper
            exception testing. When False, the request context is torn down
            on exceptions, which is the normal behavior and allows tests to
            properly verify error handling.
    """
    
    # Enable Flask testing mode
    # This disables error catching during requests for better error reports
    TESTING = True
    
    # Disable debug mode in tests to match production behavior
    # Debug mode can interfere with proper error handling tests
    DEBUG = False
    
    # Use in-memory SQLite database for fast, isolated tests
    # Each test run gets a fresh database with no persistent state
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    
    # Disable SQLAlchemy modification tracking to reduce overhead
    # This prevents warnings and improves test performance
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Disable CSRF protection for easier testing of forms and API endpoints
    # Tests can submit POST/PUT/DELETE requests without CSRF tokens
    WTF_CSRF_ENABLED = False
    
    # Test-specific secret key - NOT FOR PRODUCTION USE
    # This key is intentionally simple and publicly known for testing purposes
    SECRET_KEY = 'test-secret-key-not-for-production'
    
    # Test-specific JWT secret key - NOT FOR PRODUCTION USE
    # This key is intentionally simple and publicly known for testing purposes
    JWT_SECRET_KEY = 'test-jwt-secret-key'
    
    # Allow flexible host configuration during testing
    # None allows the test client to work with any host header
    SERVER_NAME = None
    
    # Disable context preservation on exception for proper error testing
    # This allows the normal exception handling flow to be tested
    PRESERVE_CONTEXT_ON_EXCEPTION = False
