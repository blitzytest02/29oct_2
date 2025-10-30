"""
Flask Services Package

This package contains business logic service classes for the Flask application.
Services encapsulate business rules, data validation, and complex operations.

Available Services:
    - UserService: User management business logic
    - AuthService: Authentication and authorization business logic
"""

__all__ = ['UserService', 'AuthService']

from app.services.user_service import UserService
from app.services.auth_service import AuthService
