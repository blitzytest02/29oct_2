"""
Authentication Routes Blueprint

This module implements Flask routes for authentication API endpoints.
Provides user authentication, registration, logout, and token refresh.

Endpoints:
    - POST /api/auth/login - Authenticate user with credentials
    - POST /api/auth/register - Register new user account
    - POST /api/auth/logout - Logout and invalidate token
    - POST /api/auth/refresh - Refresh access token
"""

import re
from flask import Blueprint, request, jsonify, abort
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt

from app.services.auth_service import AuthService
from app.models.user import User

# Create authentication blueprint
auth_bp = Blueprint('auth', __name__)

# Rate limiter placeholder (can be configured with Flask-Limiter in production)
rate_limiter = None


# Email validation regex pattern
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

# Password strength requirements
PASSWORD_MIN_LENGTH = 8
PASSWORD_REQUIREMENTS = {
    'uppercase': r'[A-Z]',
    'lowercase': r'[a-z]',
    'digit': r'\d',
    'special': r'[!@#$%^&*(),.?":{}|<>]'
}


def validate_email(email: str) -> bool:
    """
    Validate email format.
    
    Args:
        email (str): Email address to validate
    
    Returns:
        bool: True if email is valid, False otherwise
    """
    if not email or not isinstance(email, str):
        return False
    return bool(EMAIL_REGEX.match(email.strip()))


def validate_password_strength(password: str) -> tuple:
    """
    Validate password meets strength requirements.
    
    Requirements:
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character
    
    Args:
        password (str): Password to validate
    
    Returns:
        tuple: (is_valid: bool, error_message: str or None)
    """
    if not password or not isinstance(password, str):
        return False, "Password is required"
    
    if len(password) < PASSWORD_MIN_LENGTH:
        return False, f"Password must be at least {PASSWORD_MIN_LENGTH} characters long"
    
    # Check for uppercase letter
    if not re.search(PASSWORD_REQUIREMENTS['uppercase'], password):
        return False, "Password must contain at least one uppercase letter"
    
    # Check for lowercase letter
    if not re.search(PASSWORD_REQUIREMENTS['lowercase'], password):
        return False, "Password must contain at least one lowercase letter"
    
    # Check for digit
    if not re.search(PASSWORD_REQUIREMENTS['digit'], password):
        return False, "Password must contain at least one digit"
    
    # Check for special character
    if not re.search(PASSWORD_REQUIREMENTS['special'], password):
        return False, "Password must contain at least one special character"
    
    return True, None


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Authenticate user and generate access token.
    
    Request Body:
        email (str): User email address
        password (str): User password
    
    Returns:
        JSON response:
            - 200 OK: {user: {...}, token: '...'} on successful authentication
            - 400 Bad Request: Missing or invalid credentials
            - 401 Unauthorized: Invalid email or password
            - 429 Too Many Requests: Rate limit exceeded
    """
    try:
        # Check rate limiting if rate_limiter is configured
        if rate_limiter is not None:
            if hasattr(rate_limiter, 'is_allowed') and not rate_limiter.is_allowed():
                # Get retry after time if available
                retry_after = 60  # Default
                if hasattr(rate_limiter, 'get_retry_after'):
                    retry_after = rate_limiter.get_retry_after()
                abort(429, description=f"Too many requests. Please try again in {retry_after} seconds.")
        
        # Get request data
        data = request.get_json()
        
        if not data:
            abort(400, description="Request body is required")
        
        # Validate required fields
        email = data.get('email', '').strip()
        password = data.get('password', '')
        
        if not email:
            abort(400, description="Email is required")
        
        if not password:
            abort(400, description="Password is required")
        
        # Create service instance (allows mocking in tests)
        auth_service = AuthService()
        
        # Authenticate user
        result = auth_service.authenticate_user(email=email, password=password)
        
        if result is None:
            abort(401, description="Invalid email or password")
        
        return jsonify(result), 200
        
    except Exception as e:
        if hasattr(e, 'code'):
            # Re-raise HTTP exceptions
            raise
        abort(500, description=str(e))


@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Register a new user account.
    
    Request Body:
        email (str): User email address (must be unique)
        password (str): User password (must meet strength requirements)
        first_name (str): User's first name
        last_name (str): User's last name
    
    Returns:
        JSON response:
            - 201 Created: {user: {...}, token: '...'} on successful registration
            - 400 Bad Request: Missing fields, invalid email, or weak password
            - 409 Conflict: Email already registered
    """
    try:
        # Get request data
        data = request.get_json()
        
        if not data:
            abort(400, description="Request body is required")
        
        # Validate required fields
        email = data.get('email', '').strip() if data.get('email') else ''
        password = data.get('password', '')
        first_name = data.get('first_name', '').strip() if data.get('first_name') else ''
        last_name = data.get('last_name', '').strip() if data.get('last_name') else ''
        
        # Check for missing required fields
        missing_fields = []
        if not email:
            missing_fields.append('email')
        if not password:
            missing_fields.append('password')
        if not first_name:
            missing_fields.append('first_name')
        if not last_name:
            missing_fields.append('last_name')
        
        if missing_fields:
            abort(400, description=f"Missing required fields: {', '.join(missing_fields)}")
        
        # Validate email format
        if not validate_email(email):
            abort(400, description="Invalid email format")
        
        # Validate password strength
        is_valid_password, password_error = validate_password_strength(password)
        if not is_valid_password:
            abort(400, description=password_error)
        
        # Create service instance (allows mocking in tests)
        auth_service = AuthService()
        
        # Register user
        try:
            result = auth_service.register_user(
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )
            return jsonify(result), 201
            
        except ValueError as e:
            # Handle duplicate email or other validation errors
            error_message = str(e).lower()
            if 'email' in error_message and ('exists' in error_message or 'registered' in error_message):
                abort(409, description=str(e))
            else:
                abort(400, description=str(e))
        
    except Exception as e:
        if hasattr(e, 'code'):
            # Re-raise HTTP exceptions
            raise
        abort(500, description=str(e))


@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """
    Logout user and invalidate authentication token.
    
    Requires authentication via JWT token in Authorization header.
    
    Headers:
        Authorization: Bearer <jwt_token>
    
    Returns:
        JSON response:
            - 200 OK: {message: '...'} on successful logout
            - 401 Unauthorized: Missing or invalid JWT token
    """
    try:
        # Get JWT token info
        jwt_data = get_jwt()
        token_jti = jwt_data.get('jti')  # JWT ID for token blacklisting
        
        # Create service instance (allows mocking in tests)
        auth_service = AuthService()
        
        # Logout user (invalidate token)
        result = auth_service.logout_user(token=token_jti)
        
        return jsonify(result), 200
        
    except Exception as e:
        if hasattr(e, 'code'):
            # Re-raise HTTP exceptions
            raise
        abort(500, description=str(e))


@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """
    Refresh access token using refresh token.
    
    Requires refresh token in Authorization header.
    
    Headers:
        Authorization: Bearer <refresh_token>
    
    Returns:
        JSON response:
            - 200 OK: {access_token: '...', refresh_token: '...', token_type: 'Bearer', expires_in: 3600} on success
            - 401 Unauthorized: Missing or invalid refresh token
    """
    try:
        # Get current user identity from refresh token
        current_user_id = get_jwt_identity()
        
        # Create service instance (allows mocking in tests)
        auth_service = AuthService()
        
        # Generate new tokens via service
        result = auth_service.refresh_token(user_id=current_user_id)
        
        return jsonify(result), 200
        
    except Exception as e:
        if hasattr(e, 'code'):
            # Re-raise HTTP exceptions
            raise
        abort(500, description=str(e))
