"""
User Service Module

This module provides the UserService class which encapsulates all business logic
related to user management operations including CRUD operations, validation,
and data transformations.

The service layer separates business logic from route handlers, making the
application more maintainable and testable.
"""

from typing import Dict, List, Optional
from app.models.user import User
from app.extensions import db


class UserService:
    """
    Service class for user management business logic.
    
    Provides methods for:
    - User creation with validation
    - User retrieval and querying
    - User updates
    - User deletion
    - Pagination support
    """
    
    def list_users(self, page: int = 1, limit: int = 10) -> Dict:
        """
        List users with pagination.
        
        Args:
            page (int): Page number (1-indexed)
            limit (int): Number of results per page
        
        Returns:
            dict: Dictionary containing:
                - users: List of user dictionaries
                - total: Total number of users
                - page: Current page number
                - limit: Results per page
                - pages: Total number of pages
        """
        # Calculate offset
        offset = (page - 1) * limit
        
        # Query users with pagination
        query = User.query
        total = query.count()
        users = query.offset(offset).limit(limit).all()
        
        # Calculate total pages
        pages = (total + limit - 1) // limit if total > 0 else 0
        
        # Serialize users
        user_list = [user.to_dict() for user in users]
        
        return {
            'users': user_list,
            'total': total,
            'page': page,
            'limit': limit,
            'pages': pages
        }
    
    def create_user(self, user_data: Dict) -> Dict:
        """
        Create a new user with validation.
        
        Args:
            user_data (dict): User attributes (email, password, first_name, last_name)
        
        Returns:
            dict: Created user dictionary (without password)
        
        Raises:
            ValueError: If email already exists or validation fails
        """
        # Check if email already exists
        existing_user = User.query.filter_by(email=user_data['email']).first()
        if existing_user:
            raise ValueError('Email already exists')
        
        # Create new user
        user = User(
            email=user_data['email'],
            first_name=user_data.get('first_name'),
            last_name=user_data.get('last_name')
        )
        
        # Set password (will be hashed by User model)
        user.set_password(user_data['password'])
        
        # Add to database
        db.session.add(user)
        db.session.commit()
        
        # Return user dictionary without password
        return user.to_dict()
    
    def get_user(self, user_id: int) -> Optional[Dict]:
        """
        Get user by ID.
        
        Args:
            user_id (int): User ID
        
        Returns:
            dict: User dictionary if found, None otherwise
        """
        user = User.query.get(user_id)
        if user is None:
            return None
        return user.to_dict()
    
    def update_user(self, user_id: int, update_data: Dict) -> Optional[Dict]:
        """
        Update user by ID.
        
        Args:
            user_id (int): User ID
            update_data (dict): Fields to update
        
        Returns:
            dict: Updated user dictionary if found, None otherwise
        
        Raises:
            PermissionError: If attempting to update another user (placeholder)
        """
        user = User.query.get(user_id)
        if user is None:
            return None
        
        # Update allowed fields
        allowed_fields = ['first_name', 'last_name', 'email']
        for field in allowed_fields:
            if field in update_data:
                setattr(user, field, update_data[field])
        
        # Handle password update separately
        if 'password' in update_data:
            user.set_password(update_data['password'])
        
        db.session.commit()
        
        return user.to_dict()
    
    def delete_user(self, user_id: int) -> bool:
        """
        Delete user by ID (soft delete).
        
        Args:
            user_id (int): User ID
        
        Returns:
            bool: True if user was deleted, False if not found
        """
        user = User.query.get(user_id)
        if user is None:
            return False
        
        # Perform soft delete
        user.delete()
        db.session.commit()
        
        return True
