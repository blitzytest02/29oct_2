"""
Flask Configuration Module

This module provides configuration classes for different environments
(Development, Testing, Production) for the Flask application.

The configuration classes inherit from a base Config class and can be
selected based on the FLASK_ENV environment variable.

Usage:
    from config import Config, DevelopmentConfig, TestConfig, ProductionConfig
    
    # In app factory:
    app.config.from_object(TestConfig)
"""

import os
from datetime import timedelta


class Config:
    """
    Base configuration class with settings common to all environments.
    
    This class contains default configuration values that are shared
    across all environments. Environment-specific classes inherit from
    this base class and override settings as needed.
    """
    
    # Application Settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Flask Settings
    DEBUG = False
    TESTING = False
    
    # Database Configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///app.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False
    SQLALCHEMY_RECORD_QUERIES = True
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'pool_recycle': 3600,
        'pool_pre_ping': True,
    }
    
    # JWT Configuration
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'jwt-secret-key-change-in-production'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    JWT_TOKEN_LOCATION = ['headers']
    JWT_HEADER_NAME = 'Authorization'
    JWT_HEADER_TYPE = 'Bearer'
    
    # CORS Configuration
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*').split(',')
    CORS_METHODS = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS']
    CORS_ALLOW_HEADERS = ['Content-Type', 'Authorization']
    CORS_EXPOSE_HEADERS = ['Content-Type', 'Authorization']
    CORS_SUPPORTS_CREDENTIALS = True
    CORS_MAX_AGE = 3600
    
    # Redis Configuration
    REDIS_URL = os.environ.get('REDIS_URL') or 'redis://localhost:6379/0'
    
    # Session Configuration
    SESSION_TYPE = 'redis'
    SESSION_PERMANENT = False
    SESSION_USE_SIGNER = True
    SESSION_KEY_PREFIX = 'session:'
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    
    # File Upload Configuration
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload size
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or 'uploads'
    ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx'}
    
    # Email Configuration
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'localhost'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 25)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'false').lower() in ['true', '1', 't']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER') or 'noreply@example.com'
    
    # Logging Configuration
    LOG_LEVEL = os.environ.get('LOG_LEVEL') or 'INFO'
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    LOG_FILE = os.environ.get('LOG_FILE')
    
    # Pagination
    ITEMS_PER_PAGE = 20
    MAX_ITEMS_PER_PAGE = 100
    
    # Rate Limiting
    RATELIMIT_ENABLED = True
    RATELIMIT_STORAGE_URL = os.environ.get('REDIS_URL') or 'redis://localhost:6379/0'
    RATELIMIT_STRATEGY = 'fixed-window'
    RATELIMIT_DEFAULT = '100 per hour'
    
    # Security Headers
    SECURITY_HEADERS = {
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'SAMEORIGIN',
        'X-XSS-Protection': '1; mode=block',
    }
    
    # JSON Configuration
    JSON_SORT_KEYS = False
    JSONIFY_PRETTYPRINT_REGULAR = False
    JSON_AS_ASCII = False


class DevelopmentConfig(Config):
    """
    Development environment configuration.
    
    This configuration is optimized for local development with
    debug mode enabled, verbose logging, and development-friendly settings.
    
    Usage:
        app.config.from_object('config.DevelopmentConfig')
    """
    
    # Enable debug mode for development
    DEBUG = True
    TESTING = False
    
    # Development database (SQLite for simplicity)
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///dev.db'
    SQLALCHEMY_ECHO = True  # Log all SQL queries
    
    # Disable CSRF for easier development (enable in production)
    WTF_CSRF_ENABLED = False
    
    # More verbose logging
    LOG_LEVEL = 'DEBUG'
    
    # Disable rate limiting in development
    RATELIMIT_ENABLED = False
    
    # Shorter token expiry for testing
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=8)
    
    # Pretty print JSON responses for readability
    JSONIFY_PRETTYPRINT_REGULAR = True


class TestConfig(Config):
    """
    Testing environment configuration.
    
    This configuration is optimized for running automated tests with
    in-memory database, disabled features that interfere with testing,
    and fast execution settings.
    
    Usage:
        app.config.from_object('config.TestConfig')
    """
    
    # Enable testing mode
    TESTING = True
    DEBUG = False
    
    # Use in-memory SQLite database for fast tests
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///:memory:'
    SQLALCHEMY_ECHO = False  # Don't log SQL queries during tests
    
    # Configure session to not expire objects on commit (prevents DetachedInstanceError in tests)
    SQLALCHEMY_SESSION_OPTIONS = {
        'expire_on_commit': False
    }
    
    # Disable CSRF protection for testing
    WTF_CSRF_ENABLED = False
    
    # Disable rate limiting during tests
    RATELIMIT_ENABLED = False
    
    # Use simple in-memory session for tests
    SESSION_TYPE = 'filesystem'
    
    # Short token expiry for testing
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=15)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=1)
    
    # Test-specific keys
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'test-secret-key-not-for-production'
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'test-jwt-secret'
    
    # Test Redis configuration
    REDIS_URL = os.environ.get('REDIS_URL') or 'redis://localhost:6379/1'
    
    # Faster password hashing for tests (less secure but faster)
    BCRYPT_LOG_ROUNDS = 4
    
    # Disable email sending in tests
    MAIL_SUPPRESS_SEND = True
    MAIL_SERVER = 'localhost'
    MAIL_PORT = 25
    
    # Smaller file upload limit for tests
    MAX_CONTENT_LENGTH = 1 * 1024 * 1024  # 1 MB for tests
    
    # Minimal logging during tests
    LOG_LEVEL = 'WARNING'
    
    # Preserve exceptions for better test debugging
    PRESERVE_CONTEXT_ON_EXCEPTION = False


class ProductionConfig(Config):
    """
    Production environment configuration.
    
    This configuration is optimized for production deployment with
    security hardening, performance optimizations, and production-ready
    settings. Requires all sensitive values to be set via environment variables.
    
    Note: This class can be imported without production environment variables
    being set. Validation occurs when the configuration is actually loaded
    into a Flask application.
    
    Usage:
        app.config.from_object('config.ProductionConfig')
    """
    
    # Production mode - no debug
    DEBUG = False
    TESTING = False
    
    # Production database - must be set via environment variable
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or None
    
    SQLALCHEMY_ECHO = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 20,
        'pool_recycle': 3600,
        'pool_pre_ping': True,
        'max_overflow': 10,
    }
    
    # Production secrets - must be set via environment variables
    SECRET_KEY = os.environ.get('SECRET_KEY') or None
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or None
    
    # Enable CSRF protection
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None  # No time limit on CSRF tokens
    
    # Enable rate limiting
    RATELIMIT_ENABLED = True
    
    # Stricter CORS settings (allow empty for import, validate on use)
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '').split(',') if os.environ.get('CORS_ORIGINS') else []
    
    # Production logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL') or 'INFO'
    LOG_FILE = os.environ.get('LOG_FILE') or '/var/log/flask/app.log'
    
    # Secure session configuration
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Standard token expiry
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    
    # Stronger password hashing
    BCRYPT_LOG_ROUNDS = 13
    
    @classmethod
    def validate(cls):
        """
        Validate that all required production environment variables are set.
        
        This method should be called when initializing the Flask application
        with ProductionConfig to ensure all required settings are present.
        
        Raises:
            ValueError: If any required environment variables are missing
        """
        if not cls.SQLALCHEMY_DATABASE_URI:
            raise ValueError("DATABASE_URL environment variable must be set in production")
        
        if not cls.SECRET_KEY:
            raise ValueError("SECRET_KEY environment variable must be set in production")
        
        if not cls.JWT_SECRET_KEY:
            raise ValueError("JWT_SECRET_KEY environment variable must be set in production")
        
        if not cls.CORS_ORIGINS:
            raise ValueError("CORS_ORIGINS environment variable must be set in production")


# Configuration dictionary for easy access
config = {
    'development': DevelopmentConfig,
    'testing': TestConfig,
    'test': TestConfig,  # Alias for testing
    'production': ProductionConfig,
    'default': DevelopmentConfig
}


def get_config(config_name=None):
    """
    Get configuration class based on environment name.
    
    Args:
        config_name (str, optional): Name of the configuration to load.
            Can be 'development', 'testing', 'test', or 'production'.
            If None, uses FLASK_ENV environment variable.
            Defaults to 'development' if not specified.
    
    Returns:
        Config: Configuration class for the specified environment
    
    Example:
        >>> config = get_config('testing')
        >>> app.config.from_object(config)
    """
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    return config.get(config_name, DevelopmentConfig)


# Export all configuration classes for convenient imports
__all__ = [
    'Config',
    'DevelopmentConfig',
    'TestConfig',
    'ProductionConfig',
    'config',
    'get_config'
]
