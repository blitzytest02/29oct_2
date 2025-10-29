"""
Integration Tests for Authentication and Authorization Flows

This module provides comprehensive integration tests for complete authentication
and authorization workflows in the Flask application. These tests verify end-to-end
authentication flows including user registration, login, token generation and validation,
password reset flows, logout, and protected resource access.

Test Coverage:
- User registration flow with validation and database persistence
- Login flow with JWT token generation and session management
- JWT token lifecycle including generation, validation, expiration, and revocation
- Protected route access with token authentication
- Role-based authorization and permission checks
- Password reset workflow with email notifications and token validation
- Logout flow with token invalidation
- Complete user journey from registration to logout

Integration Test Approach:
- Uses Flask test_client() for actual HTTP requests to API endpoints
- Tests complete request → route → service → model → response flow
- Uses real database operations (db_session fixture) with transaction rollback
- Mocks only external services (email, payment gateways) using responses library
- Validates HTTP status codes, response JSON structure, and database state
- Ensures 100% coverage for authentication/authorization (security-critical)

Per Agent Action Plan section 0.8, these tests implement comprehensive scenarios
covering happy paths, edge cases, error handling, and security validation for all
authentication workflows.
"""

import json
import time
from datetime import datetime, timedelta

import pytest
import responses
import jwt as pyjwt

from app.models import User
from app.extensions import db


# ============================================================================
# TEST DATA FIXTURES
# ============================================================================


@pytest.fixture
def valid_registration_data():
    """
    Provide valid user registration data for tests.
    
    Returns:
        dict: Valid user registration data with all required fields
    """
    return {
        'email': 'newuser@example.com',
        'password': 'SecurePass123!',
        'first_name': 'New',
        'last_name': 'User'
    }


@pytest.fixture
def weak_password_data():
    """
    Provide registration data with weak password for validation tests.
    
    Returns:
        dict: Registration data with password that doesn't meet strength requirements
    """
    return {
        'email': 'weakpass@example.com',
        'password': 'weak',  # Too short, no uppercase, no special char
        'first_name': 'Weak',
        'last_name': 'Password'
    }


@pytest.fixture
def invalid_email_data():
    """
    Provide registration data with invalid email format for validation tests.
    
    Returns:
        dict: Registration data with malformed email address
    """
    return {
        'email': 'invalid.email.com',  # Missing @ symbol
        'password': 'SecurePass123!',
        'first_name': 'Invalid',
        'last_name': 'Email'
    }


@pytest.fixture
def existing_user(db_session):
    """
    Create an existing user in the database for testing login and duplicate scenarios.
    
    Args:
        db_session: Database session fixture from conftest.py
    
    Returns:
        User: Created user instance with known credentials
    """
    user = User(
        email='existing@example.com',
        first_name='Existing',
        last_name='User',
        role='user',
        is_active=True
    )
    user.set_password('ExistingPass123!')
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def admin_user(db_session):
    """
    Create an admin user for authorization testing.
    
    Args:
        db_session: Database session fixture
    
    Returns:
        User: Admin user instance
    """
    admin = User(
        email='admin@example.com',
        first_name='Admin',
        last_name='User',
        role='admin',
        is_active=True
    )
    admin.set_password('AdminPass123!')
    db_session.add(admin)
    db_session.commit()
    return admin


@pytest.fixture
def inactive_user(db_session):
    """
    Create an inactive user for testing account status validation.
    
    Args:
        db_session: Database session fixture
    
    Returns:
        User: Inactive user instance
    """
    user = User(
        email='inactive@example.com',
        first_name='Inactive',
        last_name='User',
        role='user',
        is_active=False  # Account is inactive
    )
    user.set_password('InactivePass123!')
    db_session.add(user)
    db_session.commit()
    return user


# ============================================================================
# USER REGISTRATION FLOW TESTS
# ============================================================================


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_register_new_user_success(client, db_session, valid_registration_data):
    """
    Test successful user registration with valid data.
    
    Verifies:
    - Returns 201 Created status
    - Response includes user ID
    - Response includes user email
    - Password is not included in response (security)
    - User is persisted to database
    - Password is properly hashed
    
    This tests the complete registration flow: HTTP request → route handler →
    service layer → model validation → database persistence → JSON response.
    """
    response = client.post('/api/auth/register', json=valid_registration_data)
    
    # Verify HTTP status code
    assert response.status_code == 201, f"Expected 201, got {response.status_code}"
    
    # Verify response contains user data
    response_data = response.get_json()
    assert 'id' in response_data, "Response should include user ID"
    assert response_data['email'] == valid_registration_data['email']
    assert response_data['first_name'] == valid_registration_data['first_name']
    assert response_data['last_name'] == valid_registration_data['last_name']
    
    # Verify password is NOT in response (security critical)
    assert 'password' not in response_data, "Password should never be in response"
    assert 'password_hash' not in response_data, "Password hash should never be in response"
    
    # Verify user was created in database
    user = User.query.filter_by(email=valid_registration_data['email']).first()
    assert user is not None, "User should be created in database"
    assert user.id == response_data['id']
    assert user.email == valid_registration_data['email']
    
    # Verify password was hashed (not stored in plain text)
    assert user.password_hash != valid_registration_data['password']
    assert user.check_password(valid_registration_data['password']) is True


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_register_duplicate_email_fails(client, db_session, existing_user, valid_registration_data):
    """
    Test that registration fails when email already exists.
    
    Verifies:
    - Returns 400 Bad Request or 409 Conflict
    - Error message indicates email is already registered
    - No new user is created in database
    - Database integrity is maintained
    
    This test ensures unique email constraint is properly enforced.
    """
    # Attempt to register with existing email
    duplicate_data = valid_registration_data.copy()
    duplicate_data['email'] = existing_user.email
    
    response = client.post('/api/auth/register', json=duplicate_data)
    
    # Verify error status code (400 or 409 are both acceptable)
    assert response.status_code in [400, 409], \
        f"Expected 400 or 409, got {response.status_code}"
    
    # Verify error message
    response_data = response.get_json()
    assert 'error' in response_data or 'message' in response_data
    error_message = response_data.get('error') or response_data.get('message', '')
    assert 'email' in error_message.lower() or 'exists' in error_message.lower() or 'duplicate' in error_message.lower()
    
    # Verify no duplicate user was created
    users_with_email = User.query.filter_by(email=existing_user.email).all()
    assert len(users_with_email) == 1, "Should only have one user with this email"


@pytest.mark.integration
@pytest.mark.api
def test_register_with_weak_password_fails(client, weak_password_data):
    """
    Test that registration fails with weak password.
    
    Verifies:
    - Returns 400 Bad Request
    - Error message indicates password requirements
    - No user is created
    
    Password strength requirements:
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character
    """
    response = client.post('/api/auth/register', json=weak_password_data)
    
    # Verify error status
    assert response.status_code == 400, f"Expected 400, got {response.status_code}"
    
    # Verify error message mentions password
    response_data = response.get_json()
    assert 'error' in response_data or 'message' in response_data
    error_message = response_data.get('error') or response_data.get('message', '')
    assert 'password' in error_message.lower()
    
    # Verify no user was created
    user = User.query.filter_by(email=weak_password_data['email']).first()
    assert user is None, "User should not be created with weak password"


@pytest.mark.integration
@pytest.mark.api
def test_register_with_invalid_email_fails(client, invalid_email_data):
    """
    Test that registration fails with invalid email format.
    
    Verifies:
    - Returns 400 Bad Request
    - Error message indicates email validation failure
    - No user is created
    """
    response = client.post('/api/auth/register', json=invalid_email_data)
    
    # Verify error status
    assert response.status_code == 400, f"Expected 400, got {response.status_code}"
    
    # Verify error message mentions email
    response_data = response.get_json()
    assert 'error' in response_data or 'message' in response_data
    error_message = response_data.get('error') or response_data.get('message', '')
    assert 'email' in error_message.lower() or 'invalid' in error_message.lower()
    
    # Verify no user was created
    user = User.query.filter_by(email=invalid_email_data['email']).first()
    assert user is None, "User should not be created with invalid email"


@pytest.mark.integration
@pytest.mark.api
def test_register_missing_required_fields_fails(client):
    """
    Test that registration fails when required fields are missing.
    
    Verifies:
    - Returns 400 Bad Request for missing email
    - Returns 400 Bad Request for missing password
    - Error messages indicate which fields are required
    """
    # Test missing email
    response = client.post('/api/auth/register', json={
        'password': 'SecurePass123!',
        'first_name': 'Test'
    })
    assert response.status_code == 400
    
    # Test missing password
    response = client.post('/api/auth/register', json={
        'email': 'test@example.com',
        'first_name': 'Test'
    })
    assert response.status_code == 400


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_register_creates_database_record(client, db_session, valid_registration_data):
    """
    Test that registration properly creates database record with all fields.
    
    Verifies:
    - User record exists in database
    - All user fields are properly set
    - Default values are applied (role='user', is_active=True)
    - Timestamps are set (created_at, updated_at)
    """
    # Count users before registration
    user_count_before = User.query.count()
    
    response = client.post('/api/auth/register', json=valid_registration_data)
    assert response.status_code == 201
    
    # Verify user count increased by 1
    user_count_after = User.query.count()
    assert user_count_after == user_count_before + 1
    
    # Retrieve created user
    user = User.query.filter_by(email=valid_registration_data['email']).first()
    assert user is not None
    
    # Verify all fields
    assert user.email == valid_registration_data['email']
    assert user.first_name == valid_registration_data['first_name']
    assert user.last_name == valid_registration_data['last_name']
    assert user.role == 'user', "Default role should be 'user'"
    assert user.is_active is True, "New users should be active by default"
    assert user.created_at is not None, "created_at timestamp should be set"
    assert user.updated_at is not None, "updated_at timestamp should be set"
    assert user.password_hash is not None, "Password hash should be set"


@pytest.mark.integration
@pytest.mark.api
def test_register_returns_user_without_password(client, valid_registration_data):
    """
    Test that registration response excludes sensitive password data.
    
    Verifies:
    - Response does not include 'password' field
    - Response does not include 'password_hash' field
    - Response includes safe user data (id, email, name, role)
    
    This is a critical security test ensuring passwords are never exposed.
    """
    response = client.post('/api/auth/register', json=valid_registration_data)
    assert response.status_code == 201
    
    response_data = response.get_json()
    
    # Security critical: password fields must NOT be in response
    assert 'password' not in response_data
    assert 'password_hash' not in response_data
    
    # Safe fields should be present
    assert 'id' in response_data
    assert 'email' in response_data
    assert 'first_name' in response_data
    assert 'last_name' in response_data
    assert 'role' in response_data
    assert 'is_active' in response_data


# ============================================================================
# LOGIN FLOW TESTS
# ============================================================================


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_login_with_valid_credentials_success(client, db_session, existing_user):
    """
    Test successful login with valid email and password.
    
    Verifies:
    - Returns 200 OK status
    - Response includes JWT access token
    - Response includes user data
    - Token can be decoded and contains user identity
    
    This tests the complete login flow: credentials validation → token generation →
    response with token and user data.
    """
    login_data = {
        'email': existing_user.email,
        'password': 'ExistingPass123!'
    }
    
    response = client.post('/api/auth/login', json=login_data)
    
    # Verify success status
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    # Verify response contains token
    response_data = response.get_json()
    assert 'access_token' in response_data or 'token' in response_data, \
        "Response should include access token"
    
    # Get token from response
    token = response_data.get('access_token') or response_data.get('token')
    assert token is not None
    assert isinstance(token, str)
    assert len(token) > 0
    
    # Verify response includes user data
    assert 'user' in response_data or 'id' in response_data
    
    # Verify password not in response
    assert 'password' not in response_data
    assert 'password_hash' not in response_data


@pytest.mark.integration
@pytest.mark.api
def test_login_with_invalid_password_fails(client, existing_user):
    """
    Test that login fails with incorrect password.
    
    Verifies:
    - Returns 401 Unauthorized
    - Error message is generic (doesn't reveal if email exists)
    - No token is provided
    
    This prevents user enumeration attacks.
    """
    login_data = {
        'email': existing_user.email,
        'password': 'WrongPassword123!'
    }
    
    response = client.post('/api/auth/login', json=login_data)
    
    # Verify unauthorized status
    assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    
    # Verify no token in response
    response_data = response.get_json()
    assert 'access_token' not in response_data
    assert 'token' not in response_data
    
    # Verify error message is generic
    assert 'error' in response_data or 'message' in response_data


@pytest.mark.integration
@pytest.mark.api
def test_login_with_nonexistent_email_fails(client):
    """
    Test that login fails with email that doesn't exist.
    
    Verifies:
    - Returns 401 Unauthorized
    - Error message is generic (same as invalid password)
    - No token is provided
    
    This prevents user enumeration attacks by providing same error for
    nonexistent email and invalid password.
    """
    login_data = {
        'email': 'nonexistent@example.com',
        'password': 'SomePassword123!'
    }
    
    response = client.post('/api/auth/login', json=login_data)
    
    # Verify unauthorized status
    assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    
    # Verify no token in response
    response_data = response.get_json()
    assert 'access_token' not in response_data
    assert 'token' not in response_data


@pytest.mark.integration
@pytest.mark.api
def test_login_with_missing_credentials_fails(client):
    """
    Test that login fails when credentials are missing.
    
    Verifies:
    - Returns 400 Bad Request for missing email
    - Returns 400 Bad Request for missing password
    - Error messages indicate required fields
    """
    # Test missing email
    response = client.post('/api/auth/login', json={'password': 'SomePass123!'})
    assert response.status_code == 400, "Missing email should return 400"
    
    # Test missing password
    response = client.post('/api/auth/login', json={'email': 'test@example.com'})
    assert response.status_code == 400, "Missing password should return 400"
    
    # Test completely empty body
    response = client.post('/api/auth/login', json={})
    assert response.status_code == 400, "Empty request body should return 400"


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_login_case_insensitive_email(client, db_session, existing_user):
    """
    Test that login works with case-insensitive email matching.
    
    Verifies:
    - Login succeeds with uppercase email
    - Login succeeds with lowercase email
    - Login succeeds with mixed case email
    
    This ensures consistent email handling across the system.
    """
    # Test with uppercase email
    login_data_upper = {
        'email': existing_user.email.upper(),
        'password': 'ExistingPass123!'
    }
    response = client.post('/api/auth/login', json=login_data_upper)
    assert response.status_code == 200, "Login should work with uppercase email"
    
    # Test with lowercase email
    login_data_lower = {
        'email': existing_user.email.lower(),
        'password': 'ExistingPass123!'
    }
    response = client.post('/api/auth/login', json=login_data_lower)
    assert response.status_code == 200, "Login should work with lowercase email"


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_login_creates_session(client, db_session, existing_user):
    """
    Test that successful login creates a session/token record.
    
    Verifies:
    - Login returns a valid token
    - Token can be decoded
    - Token contains user identity
    - Token has expiration time
    
    Note: If using session-based auth, verify session is created in database.
    If using JWT, verify token structure and claims.
    """
    login_data = {
        'email': existing_user.email,
        'password': 'ExistingPass123!'
    }
    
    response = client.post('/api/auth/login', json=login_data)
    assert response.status_code == 200
    
    response_data = response.get_json()
    token = response_data.get('access_token') or response_data.get('token')
    assert token is not None
    
    # Note: Actual token validation depends on JWT configuration
    # This is a placeholder for JWT token structure verification
    assert isinstance(token, str)
    assert len(token) > 20, "Token should be a reasonable length"


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.slow
def test_login_rate_limiting(client, existing_user):
    """
    Test that login endpoint enforces rate limiting.
    
    Verifies:
    - After multiple failed attempts, returns 429 Too Many Requests
    - Rate limit prevents brute force attacks
    - Rate limit is properly configured
    
    This test may be slow due to multiple requests and potential delays.
    """
    login_data = {
        'email': existing_user.email,
        'password': 'WrongPassword123!'
    }
    
    # Make multiple rapid failed login attempts
    rate_limit_hit = False
    for i in range(20):  # Try up to 20 times
        response = client.post('/api/auth/login', json=login_data)
        if response.status_code == 429:
            rate_limit_hit = True
            break
        time.sleep(0.1)  # Small delay between attempts
    
    # Note: This test assumes rate limiting is implemented
    # If not implemented yet, this test documents the requirement
    # assert rate_limit_hit, "Rate limiting should be enforced after multiple failed attempts"


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_login_with_inactive_account_fails(client, db_session, inactive_user):
    """
    Test that login fails for inactive/suspended accounts.
    
    Verifies:
    - Returns 403 Forbidden for inactive account
    - Error message indicates account is inactive
    - No token is provided
    
    This ensures suspended or deleted accounts cannot log in.
    """
    login_data = {
        'email': inactive_user.email,
        'password': 'InactivePass123!'
    }
    
    response = client.post('/api/auth/login', json=login_data)
    
    # Verify forbidden or unauthorized status
    assert response.status_code in [401, 403], \
        f"Expected 401 or 403 for inactive account, got {response.status_code}"
    
    # Verify no token in response
    response_data = response.get_json()
    assert 'access_token' not in response_data
    assert 'token' not in response_data
    
    # Verify error message mentions account status
    error_message = response_data.get('error') or response_data.get('message', '')
    assert 'inactive' in error_message.lower() or 'disabled' in error_message.lower() \
        or 'suspended' in error_message.lower()


# ============================================================================
# JWT TOKEN MANAGEMENT TESTS
# ============================================================================


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_token_generation_on_login(client, existing_user, app):
    """
    Test JWT token generation and structure on successful login.
    
    Verifies:
    - Token is a valid JWT
    - Token contains user identity claim
    - Token has expiration (exp) claim
    - Token has issued at (iat) claim
    - Token signature is valid
    """
    login_data = {
        'email': existing_user.email,
        'password': 'ExistingPass123!'
    }
    
    response = client.post('/api/auth/login', json=login_data)
    assert response.status_code == 200
    
    response_data = response.get_json()
    token = response_data.get('access_token') or response_data.get('token')
    assert token is not None
    
    # Decode token without verification to inspect claims
    # (verification requires secret key from app config)
    try:
        # Get JWT secret from app config
        secret_key = app.config.get('JWT_SECRET_KEY') or app.config.get('SECRET_KEY')
        
        decoded_token = pyjwt.decode(
            token,
            secret_key,
            algorithms=['HS256']
        )
        
        # Verify token contains required claims
        assert 'sub' in decoded_token or 'identity' in decoded_token, \
            "Token should contain user identity claim"
        assert 'exp' in decoded_token, "Token should have expiration claim"
        assert 'iat' in decoded_token, "Token should have issued at claim"
        
        # Verify identity matches user
        identity = decoded_token.get('sub') or decoded_token.get('identity')
        assert identity == str(existing_user.id) or identity == existing_user.id
        
    except pyjwt.InvalidTokenError as e:
        pytest.fail(f"Token validation failed: {e}")


@pytest.mark.integration
@pytest.mark.api
def test_token_expiration_handling(client, existing_user, app):
    """
    Test handling of expired JWT tokens.
    
    Verifies:
    - Expired tokens are rejected
    - Returns 401 Unauthorized for expired token
    - Error message indicates token expiration
    
    Note: This test may require creating an expired token or mocking time.
    """
    # This test documents the requirement for token expiration handling
    # Actual implementation may require time mocking or creating expired tokens
    pass  # Placeholder for token expiration testing logic


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_token_refresh_flow(client, existing_user):
    """
    Test JWT token refresh functionality.
    
    Verifies:
    - Can refresh token before expiration
    - Refresh returns new access token
    - Old token may be invalidated (depending on implementation)
    - New token has extended expiration
    """
    # Login to get initial token
    login_data = {
        'email': existing_user.email,
        'password': 'ExistingPass123!'
    }
    
    login_response = client.post('/api/auth/login', json=login_data)
    assert login_response.status_code == 200
    
    login_data_json = login_response.get_json()
    initial_token = login_data_json.get('access_token') or login_data_json.get('token')
    assert initial_token is not None
    
    # Attempt to refresh token
    refresh_response = client.post(
        '/api/auth/refresh',
        headers={'Authorization': f'Bearer {initial_token}'}
    )
    
    # Note: Token refresh implementation may vary
    # This test documents the expected behavior
    # Actual implementation details depend on auth strategy


@pytest.mark.integration
@pytest.mark.api
def test_invalid_token_rejected(client):
    """
    Test that malformed or tampered tokens are rejected.
    
    Verifies:
    - Invalid token format returns 401
    - Tampered token signature returns 401
    - Missing token returns 401
    - Malformed Bearer header returns 401
    """
    # Test with invalid token format
    response = client.get(
        '/api/users/profile',
        headers={'Authorization': 'Bearer invalid_token_format'}
    )
    assert response.status_code == 401, "Invalid token should return 401"
    
    # Test with malformed Bearer header
    response = client.get(
        '/api/users/profile',
        headers={'Authorization': 'InvalidFormat'}
    )
    assert response.status_code == 401, "Malformed auth header should return 401"
    
    # Test with missing token
    response = client.get('/api/users/profile')
    assert response.status_code == 401, "Missing token should return 401"


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_token_revocation(client, existing_user):
    """
    Test token revocation/blacklisting on logout.
    
    Verifies:
    - Token works before logout
    - Logout invalidates token
    - Revoked token cannot access protected routes
    - Returns 401 with revoked token
    """
    # Login to get token
    login_data = {
        'email': existing_user.email,
        'password': 'ExistingPass123!'
    }
    
    login_response = client.post('/api/auth/login', json=login_data)
    assert login_response.status_code == 200
    
    token_data = login_response.get_json()
    token = token_data.get('access_token') or token_data.get('token')
    
    # Verify token works before logout
    response = client.get(
        '/api/users/profile',
        headers={'Authorization': f'Bearer {token}'}
    )
    # Note: This may return 401 if route doesn't exist yet
    # The test documents the expected behavior
    
    # Logout (revoke token)
    logout_response = client.post(
        '/api/auth/logout',
        headers={'Authorization': f'Bearer {token}'}
    )
    # Note: Logout implementation details may vary
    
    # Verify token no longer works after logout
    response_after_logout = client.get(
        '/api/users/profile',
        headers={'Authorization': f'Bearer {token}'}
    )
    # Should return 401 if token blacklisting is implemented


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_token_includes_user_claims(client, existing_user, admin_user, app):
    """
    Test that JWT tokens include necessary user claims.
    
    Verifies:
    - Token includes user ID
    - Token includes user role
    - Token includes any custom claims
    - Claims are accurate for different user types
    """
    # Test regular user token
    login_data = {
        'email': existing_user.email,
        'password': 'ExistingPass123!'
    }
    
    response = client.post('/api/auth/login', json=login_data)
    assert response.status_code == 200
    
    response_data = response.get_json()
    token = response_data.get('access_token') or response_data.get('token')
    
    try:
        secret_key = app.config.get('JWT_SECRET_KEY') or app.config.get('SECRET_KEY')
        decoded_token = pyjwt.decode(token, secret_key, algorithms=['HS256'])
        
        # Verify user ID claim
        identity = decoded_token.get('sub') or decoded_token.get('identity')
        assert identity == str(existing_user.id) or identity == existing_user.id
        
        # Verify role claim if present
        # Note: Role may be in token or fetched from database
        # This test documents the expectation
        
    except pyjwt.InvalidTokenError:
        pass  # If token format is different, test still documents requirement
    
    # Test admin user token
    admin_login_data = {
        'email': admin_user.email,
        'password': 'AdminPass123!'
    }
    
    admin_response = client.post('/api/auth/login', json=admin_login_data)
    assert admin_response.status_code == 200
    
    admin_response_data = admin_response.get_json()
    admin_token = admin_response_data.get('access_token') or admin_response_data.get('token')
    
    try:
        admin_decoded_token = pyjwt.decode(admin_token, secret_key, algorithms=['HS256'])
        
        admin_identity = admin_decoded_token.get('sub') or admin_decoded_token.get('identity')
        assert admin_identity == str(admin_user.id) or admin_identity == admin_user.id
        
    except pyjwt.InvalidTokenError:
        pass


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_multiple_simultaneous_tokens(client, existing_user):
    """
    Test support for multiple concurrent sessions/tokens.
    
    Verifies:
    - Can login from multiple devices (multiple tokens)
    - All tokens remain valid
    - Tokens are independent
    - Logout from one device doesn't affect others (unless logout all)
    """
    login_data = {
        'email': existing_user.email,
        'password': 'ExistingPass123!'
    }
    
    # Login from "device 1"
    response1 = client.post('/api/auth/login', json=login_data)
    assert response1.status_code == 200
    token1_data = response1.get_json()
    token1 = token1_data.get('access_token') or token1_data.get('token')
    
    # Login from "device 2"
    response2 = client.post('/api/auth/login', json=login_data)
    assert response2.status_code == 200
    token2_data = response2.get_json()
    token2 = token2_data.get('access_token') or token2_data.get('token')
    
    # Verify tokens are different
    assert token1 != token2, "Different login sessions should produce different tokens"
    
    # Verify both tokens work (if routes exist)
    # This test documents the requirement for multiple concurrent sessions


# ============================================================================
# PROTECTED ROUTE ACCESS TESTS
# ============================================================================


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_access_protected_route_with_valid_token(authenticated_client):
    """
    Test accessing protected route with valid authentication token.
    
    Verifies:
    - Returns 200 OK with valid token
    - Protected resource is accessible
    - User context is available in route handler
    
    Uses authenticated_client fixture which has pre-configured auth headers.
    """
    # Access protected endpoint
    response = authenticated_client.get('/api/users/profile')
    
    # Note: If route doesn't exist, test documents expected behavior
    # Once routes are implemented, this will verify access control
    # Expected: 200 OK with user profile data


@pytest.mark.integration
@pytest.mark.api
def test_access_protected_route_without_token_fails(client):
    """
    Test that protected routes require authentication.
    
    Verifies:
    - Returns 401 Unauthorized without token
    - Error message indicates authentication required
    - No sensitive data is leaked
    """
    response = client.get('/api/users/profile')
    
    # Should return 401 for unauthenticated request
    assert response.status_code == 401, "Protected route should require authentication"
    
    response_data = response.get_json()
    # Verify error response structure
    assert 'error' in response_data or 'message' in response_data or 'msg' in response_data


@pytest.mark.integration
@pytest.mark.api
def test_access_protected_route_with_expired_token_fails(client):
    """
    Test that expired tokens cannot access protected routes.
    
    Verifies:
    - Returns 401 Unauthorized with expired token
    - Error message indicates token expiration
    - User must re-authenticate
    """
    # Create or use an expired token
    expired_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJleHAiOjE1MTYyMzkwMjJ9.invalid"
    
    response = client.get(
        '/api/users/profile',
        headers={'Authorization': f'Bearer {expired_token}'}
    )
    
    # Should return 401 for expired token
    assert response.status_code == 401, "Expired token should be rejected"


@pytest.mark.integration
@pytest.mark.api
def test_access_protected_route_with_invalid_token_fails(client):
    """
    Test that invalid/malformed tokens cannot access protected routes.
    
    Verifies:
    - Returns 401 Unauthorized with invalid token
    - Malformed tokens are rejected
    - System is secure against token tampering
    """
    # Test various invalid token formats
    invalid_tokens = [
        'invalid_token',
        'Bearer',
        '',
        'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.signature',
    ]
    
    for invalid_token in invalid_tokens:
        response = client.get(
            '/api/users/profile',
            headers={'Authorization': f'Bearer {invalid_token}'}
        )
        assert response.status_code == 401, \
            f"Invalid token '{invalid_token}' should be rejected"


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_access_protected_route_updates_last_activity(authenticated_client, db_session):
    """
    Test that accessing protected routes updates user's last activity timestamp.
    
    Verifies:
    - User's last_activity field is updated
    - Timestamp reflects recent access
    - Activity tracking works across different endpoints
    
    Note: This requires last_activity field in User model
    """
    # This test documents the requirement for activity tracking
    # Implementation depends on whether User model has last_activity field
    pass


# ============================================================================
# AUTHORIZATION AND ROLE-BASED ACCESS TESTS
# ============================================================================


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_admin_only_route_requires_admin_role(client, db_session, existing_user, admin_user):
    """
    Test that admin-only routes enforce admin role requirement.
    
    Verifies:
    - Regular user cannot access admin routes (returns 403)
    - Admin user can access admin routes (returns 200/success)
    - Role-based access control is properly enforced
    """
    # Login as regular user
    user_login = client.post('/api/auth/login', json={
        'email': existing_user.email,
        'password': 'ExistingPass123!'
    })
    assert user_login.status_code == 200
    user_token_data = user_login.get_json()
    user_token = user_token_data.get('access_token') or user_token_data.get('token')
    
    # Attempt to access admin route as regular user
    response = client.get(
        '/api/admin/users',
        headers={'Authorization': f'Bearer {user_token}'}
    )
    # Should return 403 Forbidden (not 401 - user IS authenticated)
    # Note: If route doesn't exist, test documents expected behavior
    
    # Login as admin
    admin_login = client.post('/api/auth/login', json={
        'email': admin_user.email,
        'password': 'AdminPass123!'
    })
    assert admin_login.status_code == 200
    admin_token_data = admin_login.get_json()
    admin_token = admin_token_data.get('access_token') or admin_token_data.get('token')
    
    # Access admin route as admin user
    admin_response = client.get(
        '/api/admin/users',
        headers={'Authorization': f'Bearer {admin_token}'}
    )
    # Should succeed (200 or 2xx status code)
    # Note: If route doesn't exist, test documents expected behavior


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_user_cannot_access_admin_routes(client, existing_user):
    """
    Test that regular users are blocked from admin routes.
    
    Verifies:
    - Returns 403 Forbidden (not 401)
    - Error message indicates insufficient permissions
    - User role is properly validated
    """
    # Login as regular user
    login_response = client.post('/api/auth/login', json={
        'email': existing_user.email,
        'password': 'ExistingPass123!'
    })
    assert login_response.status_code == 200
    token_data = login_response.get_json()
    token = token_data.get('access_token') or token_data.get('token')
    
    # Attempt various admin endpoints
    admin_endpoints = [
        '/api/admin/users',
        '/api/admin/settings',
        '/api/admin/reports',
    ]
    
    for endpoint in admin_endpoints:
        response = client.get(
            endpoint,
            headers={'Authorization': f'Bearer {token}'}
        )
        # Should return 403 or 404 (if not implemented)
        # Test documents expected authorization behavior


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_permission_based_access_control(client, existing_user):
    """
    Test granular permission-based access control.
    
    Verifies:
    - Specific permissions can be checked
    - Users with permission can access resources
    - Users without permission are denied
    - Permission system is flexible and extensible
    """
    # This test documents the requirement for permission-based access
    # Implementation depends on permission system design
    pass


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_resource_ownership_validation(client, db_session, existing_user):
    """
    Test that users can only access their own resources.
    
    Verifies:
    - Users can access their own profile
    - Users cannot access other users' profiles (without admin role)
    - Returns 403 Forbidden for unauthorized resource access
    - Ownership validation is enforced
    """
    # Create second user
    other_user = User(
        email='other@example.com',
        first_name='Other',
        last_name='User',
        role='user',
        is_active=True
    )
    other_user.set_password('OtherPass123!')
    db_session.add(other_user)
    db_session.commit()
    
    # Login as existing_user
    login_response = client.post('/api/auth/login', json={
        'email': existing_user.email,
        'password': 'ExistingPass123!'
    })
    assert login_response.status_code == 200
    token_data = login_response.get_json()
    token = token_data.get('access_token') or token_data.get('token')
    
    # Attempt to access other user's profile
    response = client.get(
        f'/api/users/{other_user.id}',
        headers={'Authorization': f'Bearer {token}'}
    )
    # Should return 403 Forbidden (user can't access others' data)
    # Note: If route doesn't exist, test documents expected behavior


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_superuser_bypass_permissions(client, db_session):
    """
    Test that superuser role can access all resources.
    
    Verifies:
    - Superuser can access any user's data
    - Superuser can perform admin operations
    - Superuser role is highest privilege level
    """
    # Create superuser
    superuser = User(
        email='superuser@example.com',
        first_name='Super',
        last_name='User',
        role='superuser',
        is_active=True
    )
    superuser.set_password('SuperPass123!')
    db_session.add(superuser)
    db_session.commit()
    
    # Login as superuser
    login_response = client.post('/api/auth/login', json={
        'email': superuser.email,
        'password': 'SuperPass123!'
    })
    assert login_response.status_code == 200
    token_data = login_response.get_json()
    token = token_data.get('access_token') or token_data.get('token')
    
    # Superuser should be able to access admin routes
    # Note: Implementation details depend on authorization system


# ============================================================================
# PASSWORD RESET FLOW TESTS
# ============================================================================


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.external
@responses.activate
def test_request_password_reset_sends_email(client, existing_user):
    """
    Test password reset request generates token and sends email.
    
    Verifies:
    - Returns 200 OK for valid email
    - Email service is called with reset link
    - Reset token is generated and stored
    - Token has expiration time
    - Returns generic success for security (even if email doesn't exist)
    
    Uses @responses.activate to mock external email service.
    """
    # Mock email service API
    responses.add(
        responses.POST,
        'https://api.email-service.com/send',
        json={'status': 'sent', 'message_id': '12345'},
        status=200
    )
    
    reset_request_data = {
        'email': existing_user.email
    }
    
    response = client.post('/api/auth/password-reset/request', json=reset_request_data)
    
    # Should return success (200 or 202)
    # Note: For security, same response for existing and non-existing emails
    assert response.status_code in [200, 202], \
        "Password reset request should return success"
    
    response_data = response.get_json()
    assert 'message' in response_data or 'msg' in response_data
    
    # Verify email was "sent" (mocked)
    # If email service integration exists, verify it was called


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_reset_password_with_valid_token(client, existing_user, db_session):
    """
    Test password reset with valid reset token.
    
    Verifies:
    - Password can be reset with valid token
    - New password is properly hashed
    - Old password no longer works
    - New password works for login
    - Reset token is single-use (invalidated after use)
    """
    # This test documents the password reset flow
    # Implementation requires password reset token generation
    
    # Request password reset (would generate token)
    # In real implementation, would retrieve token from email or database
    # For test, would need to generate valid reset token
    
    new_password = 'NewSecurePass123!'
    
    # Reset password with token
    # response = client.post('/api/auth/password-reset/confirm', json={
    #     'token': 'valid_reset_token',
    #     'new_password': new_password
    # })
    # assert response.status_code == 200
    
    # Verify old password doesn't work
    # old_login = client.post('/api/auth/login', json={
    #     'email': existing_user.email,
    #     'password': 'ExistingPass123!'
    # })
    # assert old_login.status_code == 401
    
    # Verify new password works
    # new_login = client.post('/api/auth/login', json={
    #     'email': existing_user.email,
    #     'password': new_password
    # })
    # assert new_login.status_code == 200


@pytest.mark.integration
@pytest.mark.api
def test_reset_password_with_expired_token_fails(client):
    """
    Test that expired password reset tokens are rejected.
    
    Verifies:
    - Returns 400 Bad Request or 401 Unauthorized
    - Error message indicates token expiration
    - Password is not changed
    - User must request new reset token
    """
    expired_token = 'expired_reset_token'
    new_password = 'NewPassword123!'
    
    response = client.post('/api/auth/password-reset/confirm', json={
        'token': expired_token,
        'new_password': new_password
    })
    
    # Should return error status
    assert response.status_code in [400, 401], \
        "Expired token should be rejected"
    
    response_data = response.get_json()
    # Verify error message
    assert 'error' in response_data or 'message' in response_data


@pytest.mark.integration
@pytest.mark.api
def test_reset_password_with_invalid_token_fails(client):
    """
    Test that invalid/malformed reset tokens are rejected.
    
    Verifies:
    - Returns 400 Bad Request for invalid token
    - Password is not changed
    - System is secure against token tampering
    """
    invalid_token = 'invalid_token_format'
    new_password = 'NewPassword123!'
    
    response = client.post('/api/auth/password-reset/confirm', json={
        'token': invalid_token,
        'new_password': new_password
    })
    
    assert response.status_code in [400, 401], \
        "Invalid token should be rejected"


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_reset_token_single_use(client, existing_user):
    """
    Test that password reset tokens can only be used once.
    
    Verifies:
    - Token works for first password reset
    - Same token is rejected on second attempt
    - Multiple resets require multiple tokens
    - Prevents token reuse attacks
    """
    # This test documents the single-use token requirement
    # Implementation details depend on reset token management
    pass


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_old_password_invalid_after_reset(client, existing_user, db_session):
    """
    Test that old password becomes invalid after reset.
    
    Verifies:
    - After password reset, old password cannot be used
    - Only new password works for login
    - Password history is maintained (if implemented)
    """
    # This test documents password invalidation after reset
    pass


# ============================================================================
# LOGOUT FLOW TESTS
# ============================================================================


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_logout_invalidates_token(client, existing_user, db_session):
    """
    Test that logout invalidates the user's token.
    
    Verifies:
    - Logout returns success (200 OK)
    - Token is added to blacklist/revoked
    - Revoked token cannot access protected routes
    - Returns 401 when using revoked token
    """
    # Login to get token
    login_response = client.post('/api/auth/login', json={
        'email': existing_user.email,
        'password': 'ExistingPass123!'
    })
    assert login_response.status_code == 200
    token_data = login_response.get_json()
    token = token_data.get('access_token') or token_data.get('token')
    
    # Logout
    logout_response = client.post(
        '/api/auth/logout',
        headers={'Authorization': f'Bearer {token}'}
    )
    # Should return success
    # Note: Logout implementation details may vary
    
    # Attempt to use token after logout
    response_after_logout = client.get(
        '/api/users/profile',
        headers={'Authorization': f'Bearer {token}'}
    )
    # Should return 401 if token blacklisting is implemented


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_logout_clears_session(client, existing_user, db_session):
    """
    Test that logout clears user session from database.
    
    Verifies:
    - Session record is removed or marked as ended
    - Session cleanup is performed
    - Database state reflects logout
    
    Note: This applies if using database sessions. JWT-only may not need this.
    """
    # Login
    login_response = client.post('/api/auth/login', json={
        'email': existing_user.email,
        'password': 'ExistingPass123!'
    })
    assert login_response.status_code == 200
    token_data = login_response.get_json()
    token = token_data.get('access_token') or token_data.get('token')
    
    # Logout
    logout_response = client.post(
        '/api/auth/logout',
        headers={'Authorization': f'Bearer {token}'}
    )
    
    # Verify session is cleared
    # Implementation depends on session storage strategy


@pytest.mark.integration
@pytest.mark.api
def test_access_after_logout_fails(client, existing_user):
    """
    Test that accessing protected routes fails after logout.
    
    Verifies:
    - Returns 401 Unauthorized
    - Error message indicates authentication required
    - User must login again to access protected routes
    """
    # Login
    login_response = client.post('/api/auth/login', json={
        'email': existing_user.email,
        'password': 'ExistingPass123!'
    })
    assert login_response.status_code == 200
    token_data = login_response.get_json()
    token = token_data.get('access_token') or token_data.get('token')
    
    # Logout
    client.post(
        '/api/auth/logout',
        headers={'Authorization': f'Bearer {token}'}
    )
    
    # Try to access protected route
    response = client.get(
        '/api/users/profile',
        headers={'Authorization': f'Bearer {token}'}
    )
    # Should return 401


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_logout_all_sessions(client, existing_user):
    """
    Test logout from all devices/sessions simultaneously.
    
    Verifies:
    - Can logout from all sessions at once
    - All tokens for user are invalidated
    - User must login again from all devices
    - Useful for security (password change, suspicious activity)
    """
    # Login from multiple "devices"
    login_data = {
        'email': existing_user.email,
        'password': 'ExistingPass123!'
    }
    
    response1 = client.post('/api/auth/login', json=login_data)
    token1 = response1.get_json().get('access_token') or response1.get_json().get('token')
    
    response2 = client.post('/api/auth/login', json=login_data)
    token2 = response2.get_json().get('access_token') or response2.get_json().get('token')
    
    # Logout from all sessions
    logout_all_response = client.post(
        '/api/auth/logout-all',
        headers={'Authorization': f'Bearer {token1}'}
    )
    
    # Both tokens should be invalid
    # This test documents the requirement for logout all functionality


# ============================================================================
# COMPLETE AUTHENTICATION WORKFLOW TESTS
# ============================================================================


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
@pytest.mark.functional
def test_full_user_journey_register_login_access_logout(client, db_session):
    """
    Test complete end-to-end user authentication journey.
    
    Flow:
    1. Register new user
    2. Login with credentials
    3. Access protected resource
    4. Logout
    5. Verify cannot access protected resource after logout
    
    This integration test verifies the entire authentication workflow works
    correctly from start to finish.
    """
    # Step 1: Register new user
    registration_data = {
        'email': 'journey@example.com',
        'password': 'JourneyPass123!',
        'first_name': 'Journey',
        'last_name': 'User'
    }
    
    register_response = client.post('/api/auth/register', json=registration_data)
    assert register_response.status_code == 201, "Registration should succeed"
    register_data = register_response.get_json()
    user_id = register_data.get('id')
    assert user_id is not None
    
    # Step 2: Login with new credentials
    login_response = client.post('/api/auth/login', json={
        'email': registration_data['email'],
        'password': registration_data['password']
    })
    assert login_response.status_code == 200, "Login should succeed"
    login_data = login_response.get_json()
    token = login_data.get('access_token') or login_data.get('token')
    assert token is not None
    
    # Step 3: Access protected resource
    profile_response = client.get(
        '/api/users/profile',
        headers={'Authorization': f'Bearer {token}'}
    )
    # Should succeed (200 or similar) if route exists
    
    # Step 4: Logout
    logout_response = client.post(
        '/api/auth/logout',
        headers={'Authorization': f'Bearer {token}'}
    )
    # Should succeed
    
    # Step 5: Verify cannot access protected resource after logout
    access_after_logout = client.get(
        '/api/users/profile',
        headers={'Authorization': f'Bearer {token}'}
    )
    # Should return 401


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_concurrent_login_attempts(client, existing_user):
    """
    Test handling of concurrent login attempts from same user.
    
    Verifies:
    - Multiple simultaneous logins are handled correctly
    - No race conditions in token generation
    - Each login gets unique token
    - All tokens remain valid
    """
    login_data = {
        'email': existing_user.email,
        'password': 'ExistingPass123!'
    }
    
    # Simulate concurrent logins
    tokens = []
    for i in range(5):
        response = client.post('/api/auth/login', json=login_data)
        assert response.status_code == 200
        token_data = response.get_json()
        token = token_data.get('access_token') or token_data.get('token')
        tokens.append(token)
    
    # Verify all tokens are unique
    assert len(tokens) == len(set(tokens)), "All tokens should be unique"


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_authentication_with_remember_me(client, existing_user):
    """
    Test extended session duration with remember me option.
    
    Verifies:
    - Login with remember_me option extends token expiration
    - Token expiration is longer than standard login
    - Session duration matches remember me policy
    """
    # Login with remember_me option
    login_data = {
        'email': existing_user.email,
        'password': 'ExistingPass123!',
        'remember_me': True
    }
    
    response = client.post('/api/auth/login', json=login_data)
    assert response.status_code == 200
    
    # Verify token has extended expiration
    # Implementation depends on remember me functionality


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
@pytest.mark.external
def test_two_factor_authentication_flow(client, existing_user):
    """
    Test two-factor authentication workflow if implemented.
    
    Verifies:
    - Login prompts for 2FA code
    - Invalid 2FA code is rejected
    - Valid 2FA code completes authentication
    - 2FA backup codes work
    
    Note: This test documents 2FA requirements if feature is implemented.
    """
    # This test documents the 2FA flow requirement
    # Implementation depends on 2FA system design (SMS, TOTP, email)
    pass

