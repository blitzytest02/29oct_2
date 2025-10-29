"""User factory for generating User model test instances.

This module provides the UserFactory class for creating User model instances with
realistic test data using factory_boy and Faker. It supports simple user creation,
batch generation, custom attribute overrides, and specialized user types via traits.

The factory integrates with the User model's password hashing mechanism and provides
convenient methods for generating users with different roles and states.

Usage Examples:
    # Create a basic user
    user = UserFactory()
    
    # Create an admin user
    admin = UserFactory(admin=True)
    
    # Create a superuser
    superuser = UserFactory(superuser=True)
    
    # Create an inactive user
    inactive_user = UserFactory(inactive=True)
    
    # Create user with custom attributes
    custom_user = UserFactory(
        email='custom@example.com',
        first_name='Jane',
        last_name='Doe'
    )
    
    # Create batch of users
    users = UserFactory.create_batch(5)
    
    # Build user without saving to database
    user_obj = UserFactory.build()
    
    # Build batch without database persistence
    user_objects = UserFactory.build_batch(10)

Attributes:
    email: Unique email address generated via Sequence
    first_name: Realistic first name via Faker
    last_name: Realistic last name via Faker
    password: Plain text password (converted to hash via post_generation)
    profile_picture: Optional profile picture URL via Faker
    role: User role (default 'user', can be 'admin' or 'superuser')
    is_active: Account active status (default True)

Traits:
    admin: Creates user with admin role
    superuser: Creates user with superuser role
    inactive: Creates user with is_active=False
"""

from datetime import datetime

import factory
from factory import Faker, LazyAttribute, Sequence, Trait, post_generation

from tests.factories.base_factory import BaseFactory
from app.models.user import User


class UserFactory(BaseFactory):
    """Factory for generating User model instances with realistic test data.
    
    This factory class uses factory_boy and Faker to generate User model instances
    with realistic, randomized test data. It inherits from BaseFactory to leverage
    SQLAlchemy session management and provides specialized traits for creating
    users with different roles and states.
    
    The factory automatically handles password hashing through the User model's
    set_password() method, ensuring secure password storage even in test data.
    
    Class Attributes:
        Meta.model: User model class
        Meta.sqlalchemy_get_or_create: Tuple of fields to use for get_or_create pattern
    
    Traits:
        admin: Sets role to 'admin' for admin users
        superuser: Sets role to 'superuser' for superuser accounts
        inactive: Sets is_active to False for inactive accounts
    
    Methods:
        create(**kwargs): Create and persist user to database
        build(**kwargs): Build user instance without database persistence
        create_batch(size, **kwargs): Create multiple users
        build_batch(size, **kwargs): Build multiple users without persistence
        stub(**kwargs): Create stub instance (no database interaction)
    
    Examples:
        >>> # Create standard user
        >>> user = UserFactory()
        >>> assert user.role == 'user'
        >>> assert user.is_active == True
        
        >>> # Create admin
        >>> admin = UserFactory(admin=True)
        >>> assert admin.role == 'admin'
        
        >>> # Create with custom email
        >>> custom = UserFactory(email='test@example.com')
        >>> assert custom.email == 'test@example.com'
        
        >>> # Batch creation
        >>> users = UserFactory.create_batch(5)
        >>> assert len(users) == 5
    """
    
    class Meta:
        """Factory metadata configuration.
        
        Attributes:
            model: User model class for factory to create instances of
            sqlalchemy_get_or_create: Fields to check for existing records
                                     Prevents duplicate users with same email
        """
        model = User
        sqlalchemy_get_or_create = ('email',)
    
    # Authentication and identification fields
    email = Sequence(lambda n: f'user{n}@example.com')
    
    # Profile fields with realistic faker data
    first_name = Faker('first_name')
    last_name = Faker('last_name')
    profile_picture = Faker('image_url')
    
    # Authorization and account status with secure defaults
    role = 'user'
    is_active = True
    
    # Timestamps are auto-managed by SQLAlchemy (created_at, updated_at)
    # No need to set them explicitly
    
    @post_generation
    def password(self, create, extracted, **kwargs):
        """Post-generation hook for setting user password securely.
        
        This hook is called after the User instance is created to set the password
        using the User model's set_password() method, which handles secure hashing.
        
        Args:
            create (bool): Whether the instance is being created (True) or built (False)
            extracted: Password value passed during factory call (if any)
            **kwargs: Additional keyword arguments
        
        Behavior:
            - If password is provided during factory call, uses that password
            - Otherwise, uses default password 'DefaultPassword123!'
            - Calls User.set_password() to properly hash the password
            - Works for both create() and build() operations
        
        Examples:
            >>> # Uses default password
            >>> user = UserFactory()
            >>> assert user.check_password('DefaultPassword123!')
            
            >>> # Custom password
            >>> user = UserFactory(password='CustomPass456!')
            >>> assert user.check_password('CustomPass456!')
        """
        # Use provided password or default
        plain_password = extracted if extracted else 'DefaultPassword123!'
        
        # Set password using User model's secure hashing method
        self.set_password(plain_password)
    
    class Params:
        """Factory traits for specialized user types.
        
        Traits provide convenient ways to create users with specific characteristics
        without manually specifying all attributes. Traits can be combined.
        
        Traits:
            admin: Creates user with admin role
            superuser: Creates user with superuser role and admin privileges
            inactive: Creates user with is_active=False (suspended/disabled account)
        
        Examples:
            >>> # Admin user
            >>> admin = UserFactory(admin=True)
            >>> assert admin.role == 'admin'
            
            >>> # Inactive superuser
            >>> inactive_super = UserFactory(superuser=True, inactive=True)
            >>> assert inactive_super.role == 'superuser'
            >>> assert inactive_super.is_active == False
            
            >>> # Combine traits
            >>> custom = UserFactory(admin=True, inactive=True)
            >>> assert custom.role == 'admin' and not custom.is_active
        """
        
        # Admin trait: User with admin role
        admin = Trait(
            role='admin'
        )
        
        # Superuser trait: User with superuser role (highest privilege)
        superuser = Trait(
            role='superuser'
        )
        
        # Inactive trait: Disabled/suspended user account
        inactive = Trait(
            is_active=False
        )
