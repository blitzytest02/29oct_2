"""
User Model

This module defines the User model for the application using SQLAlchemy ORM.
It provides database representation for user accounts with comprehensive authentication
support, profile management, and role-based access control.

The User model includes:
- Authentication fields (email, password_hash)
- Profile information (first_name, last_name, profile_picture)
- Account management (is_active, role)
- Audit timestamps (created_at, updated_at)
- Password hashing and verification methods
- Email and password validation
- JSON serialization for API responses

Usage:
    from app.models.user import User
    
    # Create a new user
    user = User(email='user@example.com', first_name='John', last_name='Doe')
    user.set_password('SecurePassword123!')
    db.session.add(user)
    db.session.commit()
    
    # Verify password
    if user.check_password('SecurePassword123!'):
        print('Password is correct')
    
    # Serialize to JSON
    user_data = user.to_dict()
"""

from datetime import datetime
import re
from typing import Dict, Optional

from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db


class User(db.Model):
    """
    User model for application authentication and user management.
    
    This model represents a user account with complete authentication, profile,
    and authorization capabilities. It uses Werkzeug for secure password hashing
    and provides comprehensive validation and serialization methods.
    
    Attributes:
        id (int): Primary key, unique user identifier
        email (str): User's email address, must be unique and valid format
        password_hash (str): Bcrypt hashed password (never store plain passwords)
        first_name (str): User's first name (optional)
        last_name (str): User's last name (optional)
        profile_picture (str): URL or path to user's profile picture (optional)
        role (str): User role for authorization ('user', 'admin', 'superuser')
        is_active (bool): Whether the user account is active (for soft delete/suspension)
        created_at (datetime): Timestamp when user account was created
        updated_at (datetime): Timestamp when user account was last updated
    
    Table Constraints:
        - Unique constraint on email field
        - NOT NULL constraints on email and password_hash
        - Index on email for fast lookups
        - Check constraint on role (must be 'user', 'admin', or 'superuser')
    """
    
    __tablename__ = 'users'
    
    # Allowed role values for role-based access control
    VALID_ROLES = ('user', 'admin', 'superuser')
    
    # Primary key
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    
    # Authentication fields
    email = db.Column(
        db.String(255),
        unique=True,
        nullable=False,
        index=True,
        doc='User email address, must be unique and valid format'
    )
    password_hash = db.Column(
        db.String(255),
        nullable=False,
        doc='Bcrypt hashed password, never expose in API responses'
    )
    
    # Profile fields
    first_name = db.Column(
        db.String(100),
        nullable=True,
        doc='User first name for profile display'
    )
    last_name = db.Column(
        db.String(100),
        nullable=True,
        doc='User last name for profile display'
    )
    profile_picture = db.Column(
        db.String(500),
        nullable=True,
        doc='URL or file path to user profile picture'
    )
    
    # Authorization and account status
    role = db.Column(
        db.String(50),
        nullable=False,
        default='user',
        doc='User role for access control: user, admin, or superuser'
    )
    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
        doc='Account active status, False for soft delete or suspension'
    )
    
    # Audit timestamps
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        doc='Timestamp when user account was created'
    )
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        doc='Timestamp when user account was last updated'
    )
    
    # Table constraints
    __table_args__ = (
        db.CheckConstraint(
            role.in_(VALID_ROLES),
            name='check_user_role_valid'
        ),
    )
    
    def __repr__(self) -> str:
        """
        String representation of User object for debugging.
        
        Returns:
            str: String representation showing user ID and email
        
        Example:
            >>> user = User(id=1, email='john@example.com')
            >>> print(user)
            <User id=1 email='john@example.com'>
        """
        return f'<User id={self.id} email={self.email}>'
    
    def set_password(self, password: str) -> None:
        """
        Hash and store the user's password securely.
        
        Uses Werkzeug's generate_password_hash with the default method (pbkdf2:sha256)
        which provides secure password hashing with salt. The plain password is never
        stored in the database.
        
        Args:
            password (str): Plain text password to hash and store
        
        Raises:
            ValueError: If password is empty or None
        
        Example:
            >>> user = User(email='john@example.com')
            >>> user.set_password('MySecurePassword123!')
            >>> # password_hash is now set, plain password is not stored
        """
        if not password:
            raise ValueError('Password cannot be empty')
        
        # Generate password hash using Werkzeug's secure hashing (pbkdf2:sha256)
        # This includes salting and multiple iterations for security
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password: str) -> bool:
        """
        Verify a password against the stored hash.
        
        Uses Werkzeug's check_password_hash to securely compare the provided
        password with the stored hash. This method is timing-attack resistant.
        
        Args:
            password (str): Plain text password to verify
        
        Returns:
            bool: True if password matches the stored hash, False otherwise
        
        Example:
            >>> user.set_password('MyPassword123!')
            >>> user.check_password('MyPassword123!')
            True
            >>> user.check_password('WrongPassword')
            False
        """
        if not password:
            return False
        
        if not self.password_hash:
            return False
        
        # Verify password against stored hash using timing-attack resistant comparison
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self, include_email: bool = True) -> Dict[str, any]:
        """
        Serialize User object to dictionary for JSON API responses.
        
        Converts the User model to a dictionary suitable for JSON serialization.
        The password_hash is NEVER included for security. Email inclusion can be
        controlled via the include_email parameter for privacy.
        
        Args:
            include_email (bool): Whether to include email in output, default True
        
        Returns:
            Dict[str, any]: Dictionary representation of user data
        
        Example:
            >>> user = User(id=1, email='john@example.com', first_name='John')
            >>> user.to_dict()
            {
                'id': 1,
                'email': 'john@example.com',
                'first_name': 'John',
                'last_name': None,
                'profile_picture': None,
                'role': 'user',
                'is_active': True,
                'created_at': '2024-10-29T12:00:00',
                'updated_at': '2024-10-29T12:00:00'
            }
            >>> user.to_dict(include_email=False)
            # Same as above but without 'email' key
        """
        user_dict = {
            'id': self.id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'profile_picture': self.profile_picture,
            'role': self.role,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        
        # Conditionally include email based on parameter
        if include_email:
            user_dict['email'] = self.email
        
        return user_dict
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """
        Validate email address format using regex pattern.
        
        Validates that the email follows standard email format:
        - Local part (before @): alphanumeric, dots, underscores, hyphens
        - Domain part (after @): valid domain format with TLD
        
        Args:
            email (str): Email address to validate
        
        Returns:
            bool: True if email format is valid, False otherwise
        
        Example:
            >>> User.validate_email('john@example.com')
            True
            >>> User.validate_email('invalid.email')
            False
            >>> User.validate_email('user@domain')
            False
        """
        if not email or not isinstance(email, str):
            return False
        
        # Email validation regex pattern
        # Matches: user@example.com, john.doe@sub.example.co.uk, etc.
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        # Additional length validation (RFC 5321)
        if len(email) > 254:  # Maximum email length
            return False
        
        # Check email format using regex
        if not re.match(email_pattern, email):
            return False
        
        # Validate local and domain parts separately
        try:
            local_part, domain_part = email.rsplit('@', 1)
            
            # Local part validation
            if len(local_part) > 64:  # Maximum local part length
                return False
            
            # Domain part validation
            if len(domain_part) > 255:  # Maximum domain length
                return False
            
            # Check for consecutive dots (not allowed)
            if '..' in email:
                return False
            
            # Check domain has at least one dot
            if '.' not in domain_part:
                return False
            
            return True
        except ValueError:
            return False
    
    @staticmethod
    def validate_password_strength(password: str) -> bool:
        """
        Validate password meets minimum security requirements.
        
        Password requirements:
        - Minimum 8 characters
        - Maximum 128 characters
        - At least one uppercase letter (A-Z)
        - At least one lowercase letter (a-z)
        - At least one digit (0-9)
        - At least one special character (!@#$%^&*()_+-=[]{}|;:,.<>?)
        
        Args:
            password (str): Password to validate
        
        Returns:
            bool: True if password meets all requirements, False otherwise
        
        Example:
            >>> User.validate_password_strength('MyPass123!')
            True
            >>> User.validate_password_strength('weak')
            False
            >>> User.validate_password_strength('NoDigitsOrSpecial')
            False
        """
        if not password or not isinstance(password, str):
            return False
        
        # Length requirements
        if len(password) < 8:
            return False
        
        if len(password) > 128:
            return False
        
        # Check for at least one uppercase letter
        if not re.search(r'[A-Z]', password):
            return False
        
        # Check for at least one lowercase letter
        if not re.search(r'[a-z]', password):
            return False
        
        # Check for at least one digit
        if not re.search(r'[0-9]', password):
            return False
        
        # Check for at least one special character
        if not re.search(r'[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]', password):
            return False
        
        return True
