"""
Authentication Service Module

This module provides the AuthService class which encapsulates all business logic
related to authentication and user session management operations.

The service handles:
- User authentication (login)
- User registration
- Token generation and validation
- Logout and token invalidation
- Token refresh operations
"""

from typing import Dict, Optional
from flask_jwt_extended import create_access_token, create_refresh_token
from sqlalchemy import func
from app.models.user import User
from app.extensions import db


class AuthService:
    """
    Service class for authentication business logic.
    
    Provides methods for:
    - User authentication with credentials validation
    - New user registration with email uniqueness check
    - JWT token generation
    - Token invalidation (logout)
    - Token refresh functionality
    """
    
    def authenticate_user(self, email: str, password: str) -> Optional[Dict]:
        """
        Authenticate user with email and password.
        
        Args:
            email (str): User email address (case-insensitive)
            password (str): Plain text password
        
        Returns:
            dict: Dictionary containing user data and JWT token if authentication succeeds:
                {
                    'user': {...},  # User dictionary without password
                    'token': '...'  # JWT access token
                }
            None: If authentication fails (user not found or password incorrect)
        """
        # Find user by email (case-insensitive comparison)
        user = User.query.filter(func.lower(User.email) == func.lower(email)).first()
        
        # Check if user exists and password is correct
        if user is None or not user.check_password(password):
            return None
        
        # Check if user is active (inactive users cannot authenticate)
        if not user.is_active:
            return None
        
        # Generate JWT token
        access_token = create_access_token(identity=str(user.id))
        
        # Return user data and token
        return {
            'user': user.to_dict(),
            'token': access_token
        }
    
    def register_user(
        self,
        email: str,
        password: str,
        first_name: str = None,
        last_name: str = None,
        **kwargs
    ) -> Dict:
        """
        Register a new user account.
        
        Args:
            email (str): User email address (must be unique)
            password (str): Plain text password (will be hashed)
            first_name (str, optional): User's first name
            last_name (str, optional): User's last name
            **kwargs: Additional user attributes
        
        Returns:
            dict: Dictionary containing new user data and JWT token:
                {
                    'user': {...},  # User dictionary without password
                    'token': '...'  # JWT access token for immediate login
                }
        
        Raises:
            ValueError: If email already exists or validation fails
        """
        # Check if email already exists (case-insensitive comparison)
        existing_user = User.query.filter(func.lower(User.email) == func.lower(email)).first()
        if existing_user:
            raise ValueError('Email already registered')
        
        # Create new user instance
        user = User(
            email=email,
            first_name=first_name,
            last_name=last_name
        )
        
        # Set password (will be hashed by User model)
        user.set_password(password)
        
        # Add to database
        db.session.add(user)
        db.session.commit()
        
        # Generate JWT tokens for immediate authentication
        access_token = create_access_token(identity=str(user.id))
        refresh_token = create_refresh_token(identity=str(user.id))
        
        # Return user data and tokens
        return {
            'user': user.to_dict(),
            'token': access_token,
            'refresh_token': refresh_token
        }
    
    def logout_user(self, token: str = None) -> Dict:
        """
        Logout user by invalidating their token.
        
        Note: In a production system, this would add the token to a blacklist
        or revoke it in a token store. For this implementation, we simply
        return a success message as token validation happens on each request.
        
        Args:
            token (str, optional): JWT token to invalidate
        
        Returns:
            dict: Success message indicating logout completed
        """
        # In production, would blacklist token in Redis or database
        # For now, just return success message
        return {
            'message': 'Successfully logged out',
            'success': True
        }
    
    def refresh_token(self, user_id: str) -> Dict:
        """
        Generate new access and refresh tokens for a user.
        
        Args:
            user_id (str): User ID to generate tokens for
        
        Returns:
            dict: New access token and refresh token with metadata:
                {
                    'access_token': '...',      # New JWT access token
                    'refresh_token': '...',      # New JWT refresh token  
                    'token_type': 'Bearer',      # Token type
                    'expires_in': 3600           # Token expiration in seconds
                }
        
        Raises:
            ValueError: If user_id is invalid
        """
        if not user_id:
            raise ValueError('User ID is required for token refresh')
        
        # Generate new access and refresh tokens
        new_access_token = create_access_token(identity=str(user_id))
        new_refresh_token = create_refresh_token(identity=str(user_id))
        
        # Return tokens with metadata
        return {
            'access_token': new_access_token,
            'refresh_token': new_refresh_token,
            'token_type': 'Bearer',
            'expires_in': 3600  # 1 hour default expiration
        }
