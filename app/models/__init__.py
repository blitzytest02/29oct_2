"""
Models Package

This package contains all SQLAlchemy ORM models for the Flask application.
It provides a centralized import location for database models, enabling clean
imports throughout the application and in tests.

The models package follows Flask-SQLAlchemy best practices by organizing each
model in its own module and re-exporting them through this __init__.py file.

Usage:
    # Import models from the package
    from app.models import User
    
    # Instead of the more verbose
    from app.models.user import User
    
    # In tests
    def test_user_creation():
        from app.models import User
        user = User(email='test@example.com')
        assert user.email == 'test@example.com'

Available Models:
    User: SQLAlchemy model for user authentication and profile management
          Includes fields for email, password_hash, profile data, role-based
          access control, and account status tracking.
    
    Future models can be added here as the application grows:
    - Post: Blog posts or content items
    - Comment: User comments on content
    - Category: Content categorization
    - etc.

Module Organization:
    app/models/
    ├── __init__.py          (this file - package initialization)
    ├── user.py              (User model definition)
    └── [future models...]   (additional model modules)

Testing Support:
    This module enables integration tests to import models cleanly:
    - tests/integration/test_user_api.py imports User for database verification
    - tests/unit/models/test_user_model.py imports User for unit testing
    - All test fixtures can use 'from app.models import User'

Notes:
    - All models inherit from db.Model (SQLAlchemy)
    - The db instance is defined in app/extensions.py
    - Models are imported and re-exported in __all__ for explicit exports
    - This pattern supports IDE autocomplete and type checking
"""

# Import all model classes from their respective modules
from app.models.user import User

# Explicit exports list for 'from app.models import *'
# This provides IDE autocomplete support and makes available models clear
__all__ = [
    'User',
    # Future model exports will be added here as the application grows:
    # 'Post',
    # 'Comment',
    # 'Category',
]
