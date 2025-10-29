"""
User Model

This module defines the User model for the application using SQLAlchemy ORM.
It provides database representation for user accounts with authentication support.
"""

from app.extensions import db


class User(db.Model):
    """
    User model for application authentication and user management.
    
    This model represents a user account with basic authentication fields.
    It integrates with Flask-SQLAlchemy for database operations.
    
    Attributes:
        id (int): Primary key, unique user identifier
        email (str): User's email address, must be unique
        password (str): Hashed password for authentication
        is_active (bool): Whether the user account is active
    """
    
    __tablename__ = 'users'
    
    # Primary key
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    
    # User credentials
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password = db.Column(db.String(255), nullable=True)
    
    # User status
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    def __repr__(self):
        """String representation of User object."""
        return f'<User {self.email}>'
