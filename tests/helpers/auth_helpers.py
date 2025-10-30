"""
Authentication Helper Utilities for Testing

This module provides comprehensive authentication helper functions that simplify
testing of authentication and authorization workflows in the Flask application.
These utilities abstract common authentication patterns, reducing code duplication
in tests and providing a consistent approach to authentication testing.

The module provides functions for:
- Test user creation with various roles and permissions
- Login and registration operations
- JWT token generation (valid, expired, and invalid tokens)
- Authentication header creation
- Authenticated test client creation
- Token validation and verification
- Logout operations

These helpers integrate seamlessly with pytest fixtures and Flask test client,
enabling clean and maintainable authentication tests.

Usage Example:
    # Create a test user and get authentication token
    user, token = create_test_user(db_session, email='test@example.com')
    
    # Create authenticated client for testing protected endpoints
    auth_client = create_authenticated_client(client, token)
    response = auth_client.get('/api/protected-resource')
    
    # Create admin user for authorization testing
    admin_user, admin_token = create_admin_user(db_session)
    
    # Generate expired token for testing token expiry
    expired_token = generate_expired_token(user.id)

Functions:
    create_test_user: Create a test user in database with default or custom attributes
    login_user: Perform login via API and return authentication token
    register_user: Register new user via API and return token
    generate_jwt_token: Generate valid JWT token for testing
    generate_expired_token: Generate expired JWT token for expiry testing
    generate_invalid_token: Generate malformed token for negative testing
    create_auth_headers: Create Authorization header dictionary
    create_authenticated_client: Create Flask test client with pre-configured auth
    logout_user: Perform logout and clear session
    verify_token: Verify JWT token validity and decode claims
    create_admin_user: Create user with admin role
    create_user_with_role: Create user with specific role for RBAC testing
"""

from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple
from uuid import uuid4

import jwt
from flask.testing import FlaskClient
from flask_jwt_extended import create_access_token, decode_token

from app.extensions import db
from app.models import User


# ============================================================================
# USER CREATION HELPERS
# ============================================================================


def create_test_user(
    db_session,
    email: Optional[str] = None,
    password: str = 'TestPassword123!',
    first_name: str = 'Test',
    last_name: str = 'User',
    role: str = 'user',
    is_active: bool = True,
    **kwargs
) -> Tuple[User, str]:
    """
    Create a test user in the database for authentication testing.
    
    This function creates a User instance with the specified attributes, persists
    it to the database, and generates a valid JWT access token for the user.
    The function automatically generates a unique email if none is provided,
    ensuring no collisions when running concurrent tests.
    
    Args:
        db_session: SQLAlchemy database session for persisting the user
        email (str, optional): User email address. If None, generates unique email
            using UUID to prevent conflicts. Default: None
        password (str): Plain text password to hash and store. 
            Default: 'TestPassword123!'
        first_name (str): User's first name. Default: 'Test'
        last_name (str): User's last name. Default: 'User'
        role (str): User role for RBAC ('user', 'admin', 'superuser').
            Default: 'user'
        is_active (bool): Whether user account is active. Default: True
        **kwargs: Additional User model attributes (profile_picture, etc.)
    
    Returns:
        Tuple[User, str]: A tuple containing:
            - User: The created User model instance with id populated
            - str: JWT access token for authentication in tests
    
    Raises:
        ValueError: If password is empty or role is invalid
        IntegrityError: If email already exists in database
    
    Example:
        >>> user, token = create_test_user(db_session)
        >>> assert user.id is not None
        >>> assert user.email is not None
        >>> assert len(token) > 0
        
        >>> # Create user with specific email
        >>> user, token = create_test_user(
        ...     db_session,
        ...     email='admin@example.com',
        ...     role='admin'
        ... )
    """
    # Generate unique email if not provided to prevent test collisions
    if email is None:
        unique_id = str(uuid4())[:8]
        email = f'test_{unique_id}@example.com'
    
    # Validate password is provided
    if not password:
        raise ValueError('Password cannot be empty')
    
    # Validate role is one of the allowed values
    if role not in User.VALID_ROLES:
        raise ValueError(
            f'Invalid role "{role}". Must be one of: {User.VALID_ROLES}'
        )
    
    # Create user instance with provided attributes
    user = User(
        email=email,
        first_name=first_name,
        last_name=last_name,
        role=role,
        is_active=is_active,
        **kwargs
    )
    
    # Hash and store password securely
    user.set_password(password)
    
    # Persist user to database
    db_session.add(user)
    db_session.commit()
    
    # Refresh user instance to ensure id is populated
    db_session.refresh(user)
    
    # Generate JWT access token for authentication
    access_token = create_access_token(identity=str(user.id))
    
    return user, access_token


def create_admin_user(
    db_session,
    email: Optional[str] = None,
    password: str = 'AdminPassword123!',
    **kwargs
) -> Tuple[User, str]:
    """
    Create a test user with admin role for authorization testing.
    
    This is a convenience wrapper around create_test_user() that automatically
    sets the role to 'admin' and provides admin-specific defaults. Use this
    function when testing endpoints or operations that require admin privileges.
    
    Args:
        db_session: SQLAlchemy database session for persisting the user
        email (str, optional): Admin user email. If None, generates unique email.
            Default: None
        password (str): Plain text password for admin user.
            Default: 'AdminPassword123!'
        **kwargs: Additional User model attributes passed to create_test_user()
    
    Returns:
        Tuple[User, str]: A tuple containing:
            - User: The created admin User model instance
            - str: JWT access token for authentication in tests
    
    Example:
        >>> admin, token = create_admin_user(db_session)
        >>> assert admin.role == 'admin'
        >>> assert admin.id is not None
        
        >>> # Use token to test admin-only endpoint
        >>> headers = create_auth_headers(token)
        >>> response = client.get('/api/admin/users', headers=headers)
    """
    # Generate admin-specific email if not provided
    if email is None:
        unique_id = str(uuid4())[:8]
        email = f'admin_{unique_id}@example.com'
    
    # Create user with admin role
    return create_test_user(
        db_session=db_session,
        email=email,
        password=password,
        first_name='Admin',
        last_name='User',
        role='admin',
        **kwargs
    )


def create_user_with_role(
    db_session,
    role: str,
    email: Optional[str] = None,
    password: str = 'TestPassword123!',
    **kwargs
) -> Tuple[User, str]:
    """
    Create a test user with specific role for role-based access control (RBAC) testing.
    
    This function provides an explicit way to create users with any valid role,
    making it clear in tests which role is being tested. It's particularly useful
    for testing role-based authorization logic and permissions.
    
    Args:
        db_session: SQLAlchemy database session for persisting the user
        role (str): User role ('user', 'admin', 'superuser'). Required.
        email (str, optional): User email address. If None, generates unique email
            based on role. Default: None
        password (str): Plain text password for the user.
            Default: 'TestPassword123!'
        **kwargs: Additional User model attributes passed to create_test_user()
    
    Returns:
        Tuple[User, str]: A tuple containing:
            - User: The created User model instance with specified role
            - str: JWT access token for authentication in tests
    
    Raises:
        ValueError: If role is not one of User.VALID_ROLES
    
    Example:
        >>> # Test superuser permissions
        >>> superuser, token = create_user_with_role(
        ...     db_session,
        ...     role='superuser'
        ... )
        >>> assert superuser.role == 'superuser'
        
        >>> # Test regular user cannot access admin endpoint
        >>> regular_user, token = create_user_with_role(
        ...     db_session,
        ...     role='user'
        ... )
        >>> headers = create_auth_headers(token)
        >>> response = client.get('/api/admin/settings', headers=headers)
        >>> assert response.status_code == 403
    """
    # Validate role before proceeding
    if role not in User.VALID_ROLES:
        raise ValueError(
            f'Invalid role "{role}". Must be one of: {User.VALID_ROLES}'
        )
    
    # Generate role-specific email if not provided
    if email is None:
        unique_id = str(uuid4())[:8]
        email = f'{role}_{unique_id}@example.com'
    
    # Create user with specified role
    return create_test_user(
        db_session=db_session,
        email=email,
        password=password,
        first_name=role.capitalize(),
        last_name='User',
        role=role,
        **kwargs
    )


# ============================================================================
# AUTHENTICATION OPERATION HELPERS
# ============================================================================


def login_user(
    client: FlaskClient,
    email: str,
    password: str
) -> Dict[str, Any]:
    """
    Perform login operation via API and return authentication response.
    
    This function makes an HTTP POST request to the /api/auth/login endpoint
    with the provided credentials and returns the full response. Use this
    function to test the login flow end-to-end, including request validation,
    authentication logic, and response formatting.
    
    Args:
        client (FlaskClient): Flask test client for making HTTP requests
        email (str): User email address for authentication
        password (str): Plain text password for authentication
    
    Returns:
        Dict[str, Any]: Dictionary containing the login response with keys:
            - status_code (int): HTTP status code (200 for success, 401 for failure)
            - data (dict): Response JSON data including 'user' and 'token' on success
            - response: Full Flask response object for additional assertions
    
    Example:
        >>> # Successful login
        >>> result = login_user(client, 'test@example.com', 'TestPassword123!')
        >>> assert result['status_code'] == 200
        >>> assert 'token' in result['data']
        >>> assert result['data']['user']['email'] == 'test@example.com'
        
        >>> # Failed login with invalid password
        >>> result = login_user(client, 'test@example.com', 'WrongPassword')
        >>> assert result['status_code'] == 401
    """
    # Make POST request to login endpoint
    response = client.post(
        '/api/auth/login',
        json={
            'email': email,
            'password': password
        },
        content_type='application/json'
    )
    
    # Parse response data
    data = response.get_json() if response.status_code == 200 else {}
    
    # Return structured response
    return {
        'status_code': response.status_code,
        'data': data,
        'response': response
    }


def register_user(
    client: FlaskClient,
    email: str,
    password: str,
    first_name: str = 'Test',
    last_name: str = 'User'
) -> Dict[str, Any]:
    """
    Register a new user via API and return authentication response.
    
    This function makes an HTTP POST request to the /api/auth/register endpoint
    with the provided user data and returns the full response. Use this function
    to test the registration flow end-to-end, including validation, user creation,
    and immediate authentication.
    
    Args:
        client (FlaskClient): Flask test client for making HTTP requests
        email (str): Email address for new user account
        password (str): Plain text password for new user account
        first_name (str): User's first name. Default: 'Test'
        last_name (str): User's last name. Default: 'User'
    
    Returns:
        Dict[str, Any]: Dictionary containing the registration response with keys:
            - status_code (int): HTTP status code (201 for success, 400/409 for errors)
            - data (dict): Response JSON data including 'user', 'token', 'refresh_token'
            - response: Full Flask response object for additional assertions
    
    Example:
        >>> # Successful registration
        >>> result = register_user(
        ...     client,
        ...     email='newuser@example.com',
        ...     password='SecurePass123!',
        ...     first_name='John',
        ...     last_name='Doe'
        ... )
        >>> assert result['status_code'] == 201
        >>> assert 'token' in result['data']
        >>> assert result['data']['user']['email'] == 'newuser@example.com'
        
        >>> # Registration with duplicate email
        >>> result2 = register_user(client, 'newuser@example.com', 'Pass123!')
        >>> assert result2['status_code'] == 409  # Conflict
    """
    # Make POST request to registration endpoint
    response = client.post(
        '/api/auth/register',
        json={
            'email': email,
            'password': password,
            'first_name': first_name,
            'last_name': last_name
        },
        content_type='application/json'
    )
    
    # Parse response data
    data = response.get_json() if response.status_code == 201 else {}
    
    # Return structured response
    return {
        'status_code': response.status_code,
        'data': data,
        'response': response
    }


def logout_user(
    client: FlaskClient,
    token: str
) -> Dict[str, Any]:
    """
    Perform logout operation via API and return response.
    
    This function makes an HTTP POST request to the /api/auth/logout endpoint
    with the provided JWT token in the Authorization header. Use this function
    to test logout functionality, token invalidation, and session management.
    
    Args:
        client (FlaskClient): Flask test client for making HTTP requests
        token (str): JWT access token to use for authentication
    
    Returns:
        Dict[str, Any]: Dictionary containing the logout response with keys:
            - status_code (int): HTTP status code (200 for success, 401 if unauthorized)
            - data (dict): Response JSON data with logout confirmation message
            - response: Full Flask response object for additional assertions
    
    Example:
        >>> # Successful logout
        >>> user, token = create_test_user(db_session)
        >>> result = logout_user(client, token)
        >>> assert result['status_code'] == 200
        >>> assert result['data']['success'] is True
        
        >>> # Logout with invalid token
        >>> result = logout_user(client, 'invalid_token')
        >>> assert result['status_code'] == 401
    """
    # Create Authorization header with token
    headers = create_auth_headers(token)
    
    # Make POST request to logout endpoint
    response = client.post(
        '/api/auth/logout',
        headers=headers
    )
    
    # Parse response data
    data = response.get_json() if response.status_code == 200 else {}
    
    # Return structured response
    return {
        'status_code': response.status_code,
        'data': data,
        'response': response
    }


# ============================================================================
# JWT TOKEN GENERATION HELPERS
# ============================================================================


def generate_jwt_token(
    user_id: int,
    additional_claims: Optional[Dict[str, Any]] = None
) -> str:
    """
    Generate a valid JWT access token for testing authenticated requests.
    
    This function creates a JWT token using Flask-JWT-Extended's create_access_token
    with the specified user ID as the identity. The token is valid and can be used
    to authenticate requests to protected endpoints in tests.
    
    Args:
        user_id (int): User ID to encode in the token's identity claim
        additional_claims (dict, optional): Additional claims to include in token
            payload (e.g., {'role': 'admin', 'permissions': ['read', 'write']}).
            Default: None
    
    Returns:
        str: Valid JWT access token that can be used in Authorization headers
    
    Example:
        >>> user, _ = create_test_user(db_session)
        >>> token = generate_jwt_token(user.id)
        >>> headers = create_auth_headers(token)
        >>> response = client.get('/api/users/profile', headers=headers)
        >>> assert response.status_code == 200
        
        >>> # Generate token with custom claims
        >>> token = generate_jwt_token(
        ...     user.id,
        ...     additional_claims={'role': 'admin', 'custom': 'value'}
        ... )
    """
    # Convert user_id to string as required by Flask-JWT-Extended
    identity = str(user_id)
    
    # Create access token with optional additional claims
    if additional_claims:
        token = create_access_token(
            identity=identity,
            additional_claims=additional_claims
        )
    else:
        token = create_access_token(identity=identity)
    
    return token


def generate_expired_token(user_id: int) -> str:
    """
    Generate an expired JWT token for testing token expiry scenarios.
    
    This function creates a JWT token that expired in the past, allowing you to
    test how the application handles expired tokens. It uses PyJWT directly to
    manually set the expiration time (exp claim) to a past datetime.
    
    Args:
        user_id (int): User ID to encode in the token's identity claim
    
    Returns:
        str: Expired JWT access token that should fail authentication
    
    Example:
        >>> user, _ = create_test_user(db_session)
        >>> expired_token = generate_expired_token(user.id)
        >>> headers = create_auth_headers(expired_token)
        >>> response = client.get('/api/users/profile', headers=headers)
        >>> assert response.status_code == 401
        >>> assert 'expired' in response.get_json()['message'].lower()
        
        >>> # Test token refresh with expired token
        >>> response = client.post(
        ...     '/api/auth/refresh',
        ...     headers=headers
        ... )
        >>> assert response.status_code == 401
    """
    # Import Flask app context to access JWT settings
    from flask import current_app
    
    # Get JWT secret key from app config
    secret_key = current_app.config.get('JWT_SECRET_KEY', 'test-jwt-secret-key')
    
    # Create token payload with expired timestamp
    # Set expiration to 1 hour in the past
    expiration = datetime.utcnow() - timedelta(hours=1)
    
    payload = {
        'sub': str(user_id),  # Subject (user identity)
        'exp': expiration,    # Expiration time (in the past)
        'iat': datetime.utcnow() - timedelta(hours=2),  # Issued at
        'type': 'access'      # Token type
    }
    
    # Encode token using PyJWT with HS256 algorithm (Flask-JWT-Extended default)
    token = jwt.encode(payload, secret_key, algorithm='HS256')
    
    return token


def generate_invalid_token() -> str:
    """
    Generate a malformed or invalid JWT token for negative testing scenarios.
    
    This function creates a token that is intentionally invalid, allowing you to
    test error handling when receiving malformed tokens. The token may have an
    invalid signature, incorrect format, or missing required claims.
    
    Returns:
        str: Invalid JWT token that should fail authentication and validation
    
    Example:
        >>> invalid_token = generate_invalid_token()
        >>> headers = create_auth_headers(invalid_token)
        >>> response = client.get('/api/users/profile', headers=headers)
        >>> assert response.status_code == 401
        >>> assert 'invalid' in response.get_json()['message'].lower()
        
        >>> # Test multiple types of invalid tokens
        >>> for _ in range(3):
        ...     bad_token = generate_invalid_token()
        ...     headers = create_auth_headers(bad_token)
        ...     response = client.get('/api/protected', headers=headers)
        ...     assert response.status_code == 401
    """
    # Generate several types of invalid tokens randomly
    import random
    
    invalid_token_types = [
        # Type 1: Random string that looks like a token
        'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid_payload.invalid_signature',
        
        # Type 2: Token with wrong secret key signature
        lambda: jwt.encode(
            {'sub': '999', 'exp': datetime.utcnow() + timedelta(hours=1)},
            'wrong-secret-key',
            algorithm='HS256'
        ),
        
        # Type 3: Malformed token structure
        'not.a.valid.token.structure.at.all',
        
        # Type 4: Token with missing claims
        lambda: jwt.encode(
            {'random': 'data'},  # Missing 'sub' and 'exp' claims
            'test-jwt-secret-key',
            algorithm='HS256'
        ),
    ]
    
    # Randomly select an invalid token type
    token_generator = random.choice(invalid_token_types)
    
    # If it's a lambda function, call it; otherwise return the string
    if callable(token_generator):
        return token_generator()
    else:
        return token_generator


# ============================================================================
# AUTHENTICATION HEADER AND CLIENT HELPERS
# ============================================================================


def create_auth_headers(token: str) -> Dict[str, str]:
    """
    Create Authorization header dictionary with Bearer token for HTTP requests.
    
    This function formats the JWT token into a proper Authorization header
    dictionary that can be passed to Flask test client requests. It follows
    the Bearer token authentication scheme as per RFC 6750.
    
    Args:
        token (str): JWT access token to include in the Authorization header
    
    Returns:
        Dict[str, str]: Dictionary with Authorization header in format:
            {'Authorization': 'Bearer <token>'}
    
    Example:
        >>> user, token = create_test_user(db_session)
        >>> headers = create_auth_headers(token)
        >>> 
        >>> # Use headers in GET request
        >>> response = client.get('/api/users/profile', headers=headers)
        >>> assert response.status_code == 200
        >>> 
        >>> # Use headers in POST request
        >>> response = client.post(
        ...     '/api/users',
        ...     json={'name': 'New User'},
        ...     headers=headers
        ... )
        >>> 
        >>> # Combine with other headers
        >>> headers.update({'Content-Type': 'application/json'})
        >>> response = client.put('/api/users/1', json={...}, headers=headers)
    """
    return {
        'Authorization': f'Bearer {token}'
    }


def create_authenticated_client(
    client: FlaskClient,
    token: str
) -> FlaskClient:
    """
    Create Flask test client with pre-configured authentication headers.
    
    This function returns a test client that automatically includes the
    Authorization header with the provided JWT token in all requests. This
    eliminates the need to manually pass headers in every request when testing
    protected endpoints.
    
    The function modifies the client's environ_base to include the Authorization
    header, which will be included in all subsequent requests made with this client.
    
    Args:
        client (FlaskClient): Flask test client to configure with authentication
        token (str): JWT access token to use for authentication
    
    Returns:
        FlaskClient: Test client with Authorization header pre-configured.
            All requests will include 'Authorization: Bearer <token>'
    
    Example:
        >>> # Create authenticated client
        >>> user, token = create_test_user(db_session)
        >>> auth_client = create_authenticated_client(client, token)
        >>> 
        >>> # All requests automatically include authorization
        >>> response = auth_client.get('/api/users/profile')
        >>> assert response.status_code == 200
        >>> 
        >>> response = auth_client.post('/api/posts', json={...})
        >>> assert response.status_code == 201
        >>> 
        >>> # No need to pass headers manually - already configured
        >>> response = auth_client.delete('/api/posts/1')
        >>> assert response.status_code == 200
    """
    # Set Authorization header in client's environment base
    # This header will be included in all subsequent requests
    client.environ_base['HTTP_AUTHORIZATION'] = f'Bearer {token}'
    
    return client


# ============================================================================
# TOKEN VALIDATION HELPERS
# ============================================================================


def verify_token(token: str) -> Dict[str, Any]:
    """
    Verify JWT token validity and decode claims for testing assertions.
    
    This function decodes and validates a JWT token, returning the token's
    payload claims if valid. Use this function to verify token contents in
    tests without making HTTP requests, or to test token validation logic
    directly.
    
    Args:
        token (str): JWT access token to verify and decode
    
    Returns:
        Dict[str, Any]: Dictionary containing token validation result:
            - valid (bool): True if token is valid, False otherwise
            - claims (dict): Token payload claims if valid (sub, exp, iat, etc.)
            - error (str): Error message if token is invalid
    
    Example:
        >>> user, token = create_test_user(db_session)
        >>> result = verify_token(token)
        >>> assert result['valid'] is True
        >>> assert result['claims']['sub'] == str(user.id)
        >>> assert 'exp' in result['claims']
        >>> 
        >>> # Verify expired token fails validation
        >>> expired_token = generate_expired_token(user.id)
        >>> result = verify_token(expired_token)
        >>> assert result['valid'] is False
        >>> assert 'expired' in result['error'].lower()
        >>> 
        >>> # Verify invalid token fails validation
        >>> invalid_token = generate_invalid_token()
        >>> result = verify_token(invalid_token)
        >>> assert result['valid'] is False
    """
    try:
        # Decode token using Flask-JWT-Extended's decode_token
        # This validates signature, expiration, and token structure
        decoded_token = decode_token(token)
        
        # Token is valid - return claims
        return {
            'valid': True,
            'claims': decoded_token,
            'error': None
        }
        
    except jwt.ExpiredSignatureError:
        # Token has expired
        return {
            'valid': False,
            'claims': None,
            'error': 'Token has expired'
        }
        
    except jwt.InvalidTokenError as e:
        # Token is invalid (bad signature, malformed, etc.)
        return {
            'valid': False,
            'claims': None,
            'error': f'Invalid token: {str(e)}'
        }
        
    except Exception as e:
        # Unexpected error during token verification
        return {
            'valid': False,
            'claims': None,
            'error': f'Token verification failed: {str(e)}'
        }
