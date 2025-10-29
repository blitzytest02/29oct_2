"""Factory_boy test data factories for generating model instances.

This package contains factory classes for all domain models using the factory_boy
library. Factories provide a clean, consistent way to generate test data with
realistic values using Faker integration.

The factories package centralizes all factory_boy factories used across the test
suite, providing a single import location and consistent patterns for test data
generation. All factories inherit from BaseFactory to ensure proper SQLAlchemy
session management and database integration.

Package Organization:
    - base_factory.py: Abstract BaseFactory class with SQLAlchemy integration
    - user_factory.py: UserFactory for User model instances
    - (future) post_factory.py: PostFactory for Post model instances
    - (future) product_factory.py: ProductFactory for Product model instances

Usage Examples:
    Basic factory usage with default values:
        >>> from tests.factories import UserFactory
        >>> user = UserFactory()
        >>> assert user.id is not None
        >>> assert user.email.endswith('@example.com')
    
    Create instances with custom attributes:
        >>> admin = UserFactory(role='admin', is_active=True)
        >>> assert admin.role == 'admin'
    
    Use factory traits for specialized instances:
        >>> admin = UserFactory(admin=True)
        >>> superuser = UserFactory(superuser=True)
        >>> inactive = UserFactory(inactive=True)
    
    Batch creation for bulk test data:
        >>> users = UserFactory.create_batch(10)
        >>> assert len(users) == 10
        >>> assert all(user.id is not None for user in users)
    
    Build instances without database persistence:
        >>> user_obj = UserFactory.build()
        >>> assert user_obj.id is None  # Not saved to database
        >>> assert user_obj.email is not None  # Attributes are set
    
    Build batch without persistence:
        >>> user_objects = UserFactory.build_batch(5)
        >>> assert len(user_objects) == 5
        >>> assert all(user.id is None for user in user_objects)

Session Configuration:
    Factories require database session configuration before use. This is typically
    handled automatically by pytest fixtures in tests/conftest.py.
    
    Manual configuration (if needed):
        >>> from tests.factories import BaseFactory
        >>> from app.extensions import db
        >>> BaseFactory.set_session(db.session)
        >>> 
        >>> # Now factories can be used
        >>> user = UserFactory()
        >>> 
        >>> # Clean up after tests
        >>> BaseFactory.set_session(None)
    
    Automatic configuration via pytest fixture:
        ```python
        # In tests/conftest.py
        @pytest.fixture(autouse=True)
        def setup_factories(db_session):
            '''Configure factory_boy factories with database session.'''
            BaseFactory.set_session(db_session)
            yield
            BaseFactory.set_session(None)
        ```

Available Factories:
    BaseFactory:
        Abstract base class for all factories with SQLAlchemy integration.
        Provides session management and common configuration.
        
        Key Methods:
            - set_session(session): Configure database session for all factories
            - _create(model_class, *args, **kwargs): Internal creation method
        
        Usage: Inherit from this class when creating new model factories
    
    UserFactory:
        Factory for User model instances with realistic test data.
        
        Default Attributes:
            - email: Unique sequential emails (user0@example.com, user1@example.com, ...)
            - first_name: Faker-generated realistic first names
            - last_name: Faker-generated realistic last names
            - password_hash: Hashed version of 'DefaultPassword123!'
            - role: 'user' (can be overridden to 'admin' or 'superuser')
            - is_active: True
        
        Available Traits:
            - admin=True: Creates user with admin role
            - superuser=True: Creates user with superuser role
            - inactive=True: Creates user with is_active=False
        
        Key Methods:
            - create(**kwargs): Create and save user to database
            - build(**kwargs): Build user instance without saving
            - create_batch(size, **kwargs): Create multiple users
            - build_batch(size, **kwargs): Build multiple users without saving
        
        Examples:
            >>> user = UserFactory()
            >>> admin = UserFactory(admin=True)
            >>> custom = UserFactory(email='custom@example.com', first_name='Jane')
            >>> users = UserFactory.create_batch(5)

Future Factories (Planned):
    The following factories will be implemented as additional models are added
    to the application:
    
    - PostFactory: For blog post or content post models
    - ProductFactory: For e-commerce product models
    - OrderFactory: For order/transaction models
    - CommentFactory: For comment/feedback models
    
    To add a new factory:
        1. Create <model>_factory.py in tests/factories/
        2. Define factory class inheriting from BaseFactory
        3. Import and export in this __init__.py file
        4. Update __all__ list to include new factory

Integration Points:
    - tests/conftest.py: Configures factory session via pytest fixtures
    - tests/fixtures/: Pytest fixtures can wrap factories for convenience
    - app/models/: Factories create instances of SQLAlchemy models
    - All test files: Import factories for test data generation

Best Practices:
    1. Use factories instead of manual model instantiation in tests
    2. Override only necessary attributes, rely on defaults for others
    3. Use traits for common user types (admin, inactive, etc.)
    4. Use build() for unit tests that don't need database persistence
    5. Use create() for integration tests requiring database interaction
    6. Use create_batch() for performance when creating multiple instances
    7. Keep factory definitions simple - complex logic belongs in model methods

See Also:
    - tests/fixtures/user_fixtures.py: Pytest fixtures wrapping factories
    - tests/conftest.py: Factory session configuration
    - Agent Action Plan sections 0.5, 0.7, 0.9: Factory usage patterns
    - factory_boy documentation: https://factoryboy.readthedocs.io/

Dependencies:
    - factory-boy==3.3.1: Core factory_boy library
    - Faker==30.0.0: Realistic fake data generation
    - SQLAlchemy: Database ORM (via Flask-SQLAlchemy)
    - Werkzeug==3.1.0: Password hashing utilities

Module Attributes:
    __all__: List of public API exports (BaseFactory, UserFactory)
    __version__: Package version identifier
    __author__: Package maintainer information
"""

# Import base factory and session configuration
from tests.factories.base_factory import BaseFactory

# Import model factories
from tests.factories.user_factory import UserFactory

# Future model factories will be imported here when implemented:
# Example placeholders (uncomment when these factories are created):
#
# from tests.factories.post_factory import PostFactory
# from tests.factories.product_factory import ProductFactory
# from tests.factories.order_factory import OrderFactory
# from tests.factories.comment_factory import CommentFactory

# Define public API for the package
# Only items in __all__ will be exported with 'from tests.factories import *'
__all__ = [
    # Base factory and configuration utilities
    'BaseFactory',
    
    # Model factories (currently implemented)
    'UserFactory',
    
    # Future factories (uncomment when implemented):
    # 'PostFactory',
    # 'ProductFactory',
    # 'OrderFactory',
    # 'CommentFactory',
]

# Package metadata
__version__ = '1.0.0'
__author__ = 'Test Infrastructure Team'
__maintainer__ = 'Test Infrastructure Team'
__email__ = 'test-infra@example.com'
__status__ = 'Production'
__description__ = 'Factory_boy test data factories for generating model instances'

# Package-level documentation shortcuts
# Provides quick access to commonly used factory patterns

def get_available_factories():
    """Return a list of all available factory classes in this package.
    
    This utility function provides introspection of available factories,
    useful for dynamic factory loading or documentation generation.
    
    Returns:
        list: List of factory class names currently available in the package
    
    Example:
        >>> from tests.factories import get_available_factories
        >>> factories = get_available_factories()
        >>> print(factories)
        ['BaseFactory', 'UserFactory']
    """
    return [name for name in __all__ if name.endswith('Factory')]


def get_factory_version():
    """Return the current version of the factories package.
    
    Returns:
        str: Version string in semantic versioning format
    
    Example:
        >>> from tests.factories import get_factory_version
        >>> version = get_factory_version()
        >>> print(version)
        '1.0.0'
    """
    return __version__


# Convenience exports for commonly used factory_boy utilities
# These re-exports allow importing factory_boy features directly from tests.factories
# Example: from tests.factories import Faker, Sequence
# Instead of: from factory import Faker, Sequence

# Note: These are optional convenience imports. Factories can still import
# directly from factory_boy if preferred. Uncomment if desired:
#
# from factory import (
#     Faker,
#     Sequence,
#     LazyAttribute,
#     LazyFunction,
#     SubFactory,
#     RelatedFactory,
#     PostGeneration,
#     post_generation,
#     Trait,
# )
#
# __all__.extend([
#     'Faker',
#     'Sequence',
#     'LazyAttribute',
#     'LazyFunction',
#     'SubFactory',
#     'RelatedFactory',
#     'PostGeneration',
#     'post_generation',
#     'Trait',
# ])
