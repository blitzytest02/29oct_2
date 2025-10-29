"""
User Routes Blueprint

This module implements Flask routes for user management API endpoints.
Provides CRUD operations for users with proper authentication and validation.

Endpoints:
    - GET /api/users - List users with pagination
    - POST /api/users - Create new user
    - GET /api/users/:id - Get user by ID
    - PUT /api/users/:id - Update user
    - DELETE /api/users/:id - Delete user
"""

from flask import Blueprint, request, jsonify, abort
from flask_jwt_extended import jwt_required, get_jwt_identity

# Import UserService class (not instance) for dependency injection
from app.services.user_service import UserService

# Create users blueprint
users_bp = Blueprint('users', __name__)


@users_bp.route('', methods=['GET'])
@jwt_required()
def list_users():
    """
    List all users with pagination support.
    
    Requires authentication via JWT token.
    
    Query Parameters:
        page (int): Page number (default: 1)
        limit (int): Results per page (default: 10)
    
    Returns:
        JSON response with users array and pagination metadata
    """
    try:
        # Get pagination parameters from query string
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 10, type=int)
        
        # Create service instance (allows mocking)
        user_service = UserService()
        
        # Get users from service
        result = user_service.list_users(page=page, limit=limit)
        
        return jsonify(result), 200
        
    except Exception as e:
        abort(500, description=str(e))


@users_bp.route('', methods=['POST'])
@jwt_required()
def create_user():
    """
    Create a new user.
    
    Requires authentication via JWT token.
    
    Request Body:
        email (str): User email address
        password (str): User password
        first_name (str): User first name
        last_name (str): User last name
    
    Returns:
        JSON response with created user object (201 Created)
    """
    try:
        # Get request data
        data = request.get_json()
        
        if not data:
            abort(400, description="Request body is required")
        
        # Validate required fields
        required_fields = ['email', 'password', 'first_name', 'last_name']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            abort(400, description=f"Missing required fields: {', '.join(missing_fields)}")
        
        # Validate email format
        email = data.get('email', '')
        if '@' not in email or '.' not in email:
            abort(400, description="Invalid email format")
        
        # Create service instance (allows mocking)
        user_service = UserService()
        
        # Create user via service
        try:
            user = user_service.create_user(data)
            return jsonify(user), 201
        except ValueError as e:
            # Handle duplicate email
            if 'already exists' in str(e).lower():
                abort(409, description=str(e))
            raise
        
    except Exception as e:
        if hasattr(e, 'code'):
            # Re-raise HTTP exceptions
            raise
        abort(500, description=str(e))


@users_bp.route('/<int:user_id>', methods=['GET'])
@jwt_required()
def get_user(user_id):
    """
    Get user by ID.
    
    Requires authentication via JWT token.
    
    Args:
        user_id (int): User ID
    
    Returns:
        JSON response with user object (200 OK)
    """
    try:
        # Create service instance (allows mocking)
        user_service = UserService()
        
        user = user_service.get_user(user_id)
        
        if user is None:
            abort(404, description="User not found")
        
        return jsonify(user), 200
        
    except Exception as e:
        if hasattr(e, 'code'):
            raise
        abort(500, description=str(e))


@users_bp.route('/<int:user_id>', methods=['PUT'])
@jwt_required()
def update_user(user_id):
    """
    Update user by ID.
    
    Requires authentication via JWT token.
    
    Args:
        user_id (int): User ID
    
    Request Body:
        Any user fields to update
    
    Returns:
        JSON response with updated user object (200 OK)
    """
    try:
        data = request.get_json()
        
        if not data:
            abort(400, description="Request body is required")
        
        # Create service instance (allows mocking)
        user_service = UserService()
        
        try:
            user = user_service.update_user(user_id, data)
            
            if user is None:
                abort(404, description="User not found")
            
            return jsonify(user), 200
            
        except PermissionError as e:
            abort(403, description=str(e))
        
    except Exception as e:
        if hasattr(e, 'code'):
            raise
        abort(500, description=str(e))


@users_bp.route('/<int:user_id>', methods=['DELETE'])
@jwt_required()
def delete_user(user_id):
    """
    Delete user by ID.
    
    Requires authentication via JWT token.
    
    Args:
        user_id (int): User ID
    
    Returns:
        Empty response (204 No Content)
    """
    try:
        # Create service instance (allows mocking)
        user_service = UserService()
        
        success = user_service.delete_user(user_id)
        
        if not success:
            abort(404, description="User not found")
        
        return '', 204
        
    except Exception as e:
        if hasattr(e, 'code'):
            raise
        abort(500, description=str(e))
