"""
Flask Services Package

This package contains business logic service classes for the Flask application.
Services encapsulate business rules, data validation, and complex operations.

Available Services:
    - UserService: User management business logic
"""

__all__ = ['UserService']

from app.services.user_service import UserService
