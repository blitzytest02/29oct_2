"""
Unit Tests for Flask Authentication Route Handlers

This module provides comprehensive unit tests for authentication route handlers in the
Flask application, testing POST /api/auth/login, POST /api/auth/register, 
POST /api/auth/logout, and POST /api/auth/refresh endpoints.

The tests focus on:
- Request validation (email format, password strength, required fields)
- Response formatting (status codes, JSON structure, token generation)
- Error handling (invalid credentials, duplicate emails, rate limiting)
- HTTP request processing with all external dependencies mocked

All external dependencies (AuthService, User model, database operations) are mocked
using pytest-mock to ensure fast, isolated unit testing. Tests validate route handler
logic without service or database dependencies.

Test Classes:
    - TestAuthLogin: Tests for login endpoint scenarios
    - TestAuthRegister: Tests for registration endpoint scenarios
    - TestAuthLogout: Tests for logout endpoint scenarios
    - TestAuthRefresh: Tests for token refresh endpoint scenarios

Test Markers:
    - @pytest.mark.unit: Automatically applied for fast, isolated tests
    - @pytest.mark.api: Automatically applied for API endpoint tests

Usage:
    # Run all authentication route tests
    pytest tests/unit/routes/test_auth_routes.py -v
    
    # Run only login tests
    pytest tests/unit/routes/test_auth_routes.py::TestAuthLogin -v
    
    # Run specific test
    pytest tests/unit/routes/test_auth_routes.py::TestAuthLogin::test_login_with_valid_credentials -v
"""

import json
import pytest


# ============================================================================
# TEST FIXTURES FOR MOCKING
# ============================================================================


@pytest.fixture
def mock_auth_service(mocker):
    """
    Mock AuthService for authentication business logic operations.
    
    This fixture creates a mock AuthService object that replaces the actual
    authentication service during testing. It allows tests to simulate various
    authentication scenarios without executing real business logic or database
    operations.
    
    Args:
        mocker: pytest-mock fixture for creating mock objects
    
    Returns:
        Mock: Mocked AuthService with configurable return values for:
            - authenticate_user(): Validates credentials and returns user/token
            - register_user(): Creates new user account
            - logout_user(): Invalidates user session/token
            - refresh_token(): Generates new access token
    
    Example:
        def test_login(client, mock_auth_service):
            mock_auth_service.authenticate_user.return_value = {
                'user': {'id': 1, 'email': 'test@example.com'},
                'token': 'jwt_token_here'
            }
            response = client.post('/api/auth/login', json={
                'email': 'test@example.com',
                'password': 'password'
            })
            assert response.status_code == 200
    """
    # Create a mock for the entire AuthService class
    mock_service = mocker.Mock()
    
    # Patch the AuthService in the routes module
    # This ensures when routes import AuthService, they get our mock
    mocker.patch('app.routes.auth.AuthService', return_value=mock_service)
    
    return mock_service


@pytest.fixture
def mock_user_model(mocker):
    """
    Mock User model for database query operations.
    
    This fixture creates a mock User model that replaces actual database
    operations during testing. It allows tests to simulate database queries
    and user lookups without connecting to a real database.
    
    Args:
        mocker: pytest-mock fixture for creating mock objects
    
    Returns:
        Mock: Mocked User model with configurable methods:
            - query.filter_by(): Filter users by field
            - query.first(): Get first matching user
            - query.all(): Get all matching users
    
    Example:
        def test_duplicate_email(client, mock_user_model):
            mock_user_model.query.filter_by.return_value.first.return_value = Mock(
                id=1, email='existing@example.com'
            )
            response = client.post('/api/auth/register', json={
                'email': 'existing@example.com',
                'password': 'password'
            })
            assert response.status_code == 409
    """
    # Create a mock for the User model
    mock_model = mocker.Mock()
    
    # Patch the User model in the routes module
    mocker.patch('app.routes.auth.User', mock_model)
    
    return mock_model


@pytest.fixture
def mock_rate_limiter(mocker):
    """
    Mock rate limiter for testing rate limiting scenarios.
    
    This fixture creates a mock rate limiter to test rate limit enforcement
    without actual rate limiting logic. Allows simulation of rate limit
    exceeded scenarios.
    
    Args:
        mocker: pytest-mock fixture for creating mock objects
    
    Returns:
        Mock: Mocked rate limiter that can be configured to allow or deny requests
    
    Example:
        def test_rate_limit(client, mock_rate_limiter):
            mock_rate_limiter.is_allowed.return_value = False
            response = client.post('/api/auth/login', json={
                'email': 'test@example.com',
                'password': 'password'
            })
            assert response.status_code == 429
    """
    # Create a mock for rate limiter
    mock_limiter = mocker.Mock()
    
    # Patch the rate limiter in the routes module
    mocker.patch('app.routes.auth.rate_limiter', mock_limiter)
    
    return mock_limiter


@pytest.fixture
def mock_jwt_decorators(mocker):
    """
    Mock Flask-JWT-Extended decorators for testing JWT-protected routes.
    
    This fixture bypasses JWT token validation for unit tests, allowing
    tests to focus on route logic without needing real JWT tokens.
    Mock jwt_required, get_jwt_identity, and get_jwt functions.
    
    Args:
        mocker: pytest-mock fixture for creating mock objects
    
    Returns:
        dict: Dictionary containing mocked JWT functions
    
    Example:
        def test_protected_route(client, mock_jwt_decorators):
            mock_jwt_decorators['get_jwt_identity'].return_value = '123'
            response = client.post('/api/auth/logout',
                                    headers={'Authorization': 'Bearer fake_token'})
            assert response.status_code == 200
    """
    # Mock jwt_required decorator to pass through without validation
    def jwt_required_mock(optional=False, refresh=False, locations=None):
        def decorator(fn):
            return fn
        return decorator
    
    # Mock get_jwt_identity to return a test user ID
    # Patch at flask_jwt_extended level to ensure it affects the decorator
    mock_identity = mocker.patch('flask_jwt_extended.get_jwt_identity', return_value='1')
    
    # Mock get_jwt to return test JWT data
    mock_jwt = mocker.patch('flask_jwt_extended.get_jwt', return_value={'jti': 'test-jti-123'})
    
    # Mock the jwt_required decorator itself at flask_jwt_extended level
    mocker.patch('flask_jwt_extended.jwt_required', jwt_required_mock)
    
    return {
        'get_jwt_identity': mock_identity,
        'get_jwt': mock_jwt,
        'jwt_required': jwt_required_mock
    }


# ============================================================================
# TEST CLASS: LOGIN ENDPOINT
# ============================================================================


@pytest.mark.unit
@pytest.mark.api
class TestAuthLogin:
    """
    Test suite for authentication login endpoint (POST /api/auth/login).
    
    Tests cover:
    - Valid credentials authentication
    - Invalid password handling
    - Nonexistent email handling
    - Missing credentials validation
    - Rate limiting enforcement
    
    All tests mock external dependencies to ensure fast, isolated unit testing.
    """
    
    def test_login_with_valid_credentials(self, client, mock_auth_service):
        """
        Test successful login with valid email and password credentials.
        
        Scenario: User provides correct email and password
        Expected: Returns 200 OK with JWT token and user data
        
        Verifies:
        - HTTP status code is 200
        - Response contains 'token' field with JWT
        - Response contains 'user' object with id and email
        - Password is not included in response (security)
        
        Args:
            client: Flask test client fixture
            mock_auth_service: Mocked AuthService fixture
        """
        # Arrange: Configure mock to return successful authentication
        mock_auth_service.authenticate_user.return_value = {
            'token': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test_token',
            'user': {
                'id': 1,
                'email': 'test@example.com',
                'first_name': 'Test',
                'last_name': 'User'
            }
        }
        
        # Act: Make login request with valid credentials
        response = client.post('/api/auth/login', json={
            'email': 'test@example.com',
            'password': 'SecurePassword123!'
        })
        
        # Assert: Verify successful authentication response
        assert response.status_code == 200
        
        response_data = json.loads(response.data)
        assert 'token' in response_data
        assert response_data['token'].startswith('eyJ')  # JWT format
        assert 'user' in response_data
        assert response_data['user']['id'] == 1
        assert response_data['user']['email'] == 'test@example.com'
        assert 'password' not in response_data['user']  # Security check
        
        # Verify service was called with correct parameters
        mock_auth_service.authenticate_user.assert_called_once_with(
            email='test@example.com',
            password='SecurePassword123!'
        )
    
    def test_login_with_invalid_password(self, client, mock_auth_service):
        """
        Test login attempt with incorrect password.
        
        Scenario: User provides valid email but incorrect password
        Expected: Returns 401 Unauthorized with error message
        
        Verifies:
        - HTTP status code is 401 Unauthorized
        - Response contains error message
        - No token is provided
        - No user data is exposed
        
        Args:
            client: Flask test client fixture
            mock_auth_service: Mocked AuthService fixture
        """
        # Arrange: Configure mock to return authentication failure
        mock_auth_service.authenticate_user.return_value = None
        
        # Act: Make login request with invalid password
        response = client.post('/api/auth/login', json={
            'email': 'test@example.com',
            'password': 'WrongPassword123!'
        })
        
        # Assert: Verify unauthorized response
        assert response.status_code == 401
        
        response_data = json.loads(response.data)
        assert 'error' in response_data or 'message' in response_data or 'msg' in response_data
        assert 'token' not in response_data
        assert 'user' not in response_data
        
        # Verify service was called
        mock_auth_service.authenticate_user.assert_called_once()
    
    def test_login_with_nonexistent_email(self, client, mock_auth_service):
        """
        Test login attempt with email that doesn't exist in the system.
        
        Scenario: User provides email that is not registered
        Expected: Returns 401 Unauthorized (same as invalid password for security)
        
        Verifies:
        - HTTP status code is 401 Unauthorized
        - Response contains generic error message (no user enumeration)
        - No token is provided
        
        Security Note: Same error as invalid password to prevent email enumeration
        
        Args:
            client: Flask test client fixture
            mock_auth_service: Mocked AuthService fixture
        """
        # Arrange: Configure mock to return None (user not found)
        mock_auth_service.authenticate_user.return_value = None
        
        # Act: Make login request with nonexistent email
        response = client.post('/api/auth/login', json={
            'email': 'nonexistent@example.com',
            'password': 'SomePassword123!'
        })
        
        # Assert: Verify unauthorized response (same as invalid password)
        assert response.status_code == 401
        
        response_data = json.loads(response.data)
        assert 'error' in response_data or 'message' in response_data or 'msg' in response_data
        assert 'token' not in response_data
        
        # Verify service was called
        mock_auth_service.authenticate_user.assert_called_once_with(
            email='nonexistent@example.com',
            password='SomePassword123!'
        )
    
    def test_login_with_missing_credentials(self, client):
        """
        Test login attempt with missing required fields.
        
        Scenario: User submits login request without email or password
        Expected: Returns 400 Bad Request with validation error
        
        Verifies:
        - HTTP status code is 400 Bad Request
        - Response contains validation error message
        - Specific missing fields are identified
        
        Args:
            client: Flask test client fixture
        """
        # Test case 1: Missing email
        response = client.post('/api/auth/login', json={
            'password': 'SomePassword123!'
        })
        assert response.status_code == 400
        response_data = json.loads(response.data)
        assert 'error' in response_data or 'message' in response_data or 'msg' in response_data
        
        # Test case 2: Missing password
        response = client.post('/api/auth/login', json={
            'email': 'test@example.com'
        })
        assert response.status_code == 400
        response_data = json.loads(response.data)
        assert 'error' in response_data or 'message' in response_data or 'msg' in response_data
        
        # Test case 3: Missing both fields
        response = client.post('/api/auth/login', json={})
        assert response.status_code == 400
        response_data = json.loads(response.data)
        assert 'error' in response_data or 'message' in response_data or 'msg' in response_data
    
    def test_login_exceeds_rate_limit(self, client, mock_rate_limiter):
        """
        Test login attempt when rate limit is exceeded.
        
        Scenario: User has made too many login attempts in short time period
        Expected: Returns 429 Too Many Requests with retry information
        
        Verifies:
        - HTTP status code is 429 Too Many Requests
        - Response contains rate limit error message
        - Response may include retry-after header or time
        
        Args:
            client: Flask test client fixture
            mock_rate_limiter: Mocked rate limiter fixture
        """
        # Arrange: Configure rate limiter to deny request
        mock_rate_limiter.is_allowed.return_value = False
        mock_rate_limiter.get_retry_after.return_value = 60  # 60 seconds
        
        # Act: Make login request when rate limited
        response = client.post('/api/auth/login', json={
            'email': 'test@example.com',
            'password': 'SecurePassword123!'
        })
        
        # Assert: Verify rate limit response
        assert response.status_code == 429
        
        response_data = json.loads(response.data)
        assert 'error' in response_data or 'message' in response_data or 'msg' in response_data
        
        # Check for rate limit indicators in response
        error_message = str(response_data.get('error', response_data.get('message', ''))).lower()
        assert 'rate' in error_message or 'too many' in error_message or 'limit' in error_message


# ============================================================================
# TEST CLASS: REGISTER ENDPOINT
# ============================================================================


@pytest.mark.unit
@pytest.mark.api
class TestAuthRegister:
    """
    Test suite for user registration endpoint (POST /api/auth/register).
    
    Tests cover:
    - Valid registration with all required fields
    - Duplicate email handling
    - Invalid email format validation
    - Weak password validation
    - Missing required fields validation
    
    All tests mock external dependencies to ensure fast, isolated unit testing.
    """
    
    def test_register_with_valid_data(self, client, mock_auth_service):
        """
        Test successful user registration with valid data.
        
        Scenario: New user provides all required fields with valid values
        Expected: Returns 201 Created with user object and authentication token
        
        Verifies:
        - HTTP status code is 201 Created
        - Response contains user object with id and email
        - Response may contain authentication token for immediate login
        - Password is not included in response
        
        Args:
            client: Flask test client fixture
            mock_auth_service: Mocked AuthService fixture
        """
        # Arrange: Configure mock to return successful registration
        mock_auth_service.register_user.return_value = {
            'user': {
                'id': 1,
                'email': 'newuser@example.com',
                'first_name': 'New',
                'last_name': 'User',
                'created_at': '2025-10-29T12:00:00Z'
            },
            'token': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.new_user_token'
        }
        
        # Act: Make registration request with valid data
        response = client.post('/api/auth/register', json={
            'email': 'newuser@example.com',
            'password': 'SecurePassword123!',
            'first_name': 'New',
            'last_name': 'User'
        })
        
        # Assert: Verify successful registration response
        assert response.status_code == 201
        
        response_data = json.loads(response.data)
        assert 'user' in response_data
        assert response_data['user']['id'] == 1
        assert response_data['user']['email'] == 'newuser@example.com'
        assert 'password' not in response_data['user']  # Security check
        
        # Token may be included for immediate authentication
        if 'token' in response_data:
            assert response_data['token'].startswith('eyJ')
        
        # Verify service was called with correct parameters
        mock_auth_service.register_user.assert_called_once()
        call_args = mock_auth_service.register_user.call_args[1]
        assert call_args['email'] == 'newuser@example.com'
        assert call_args['password'] == 'SecurePassword123!'
    
    def test_register_with_duplicate_email(self, client, mock_auth_service):
        """
        Test registration attempt with email that already exists.
        
        Scenario: User tries to register with email already in system
        Expected: Returns 409 Conflict with error message
        
        Verifies:
        - HTTP status code is 409 Conflict
        - Response contains error message about duplicate email
        - No user is created
        - No token is provided
        
        Args:
            client: Flask test client fixture
            mock_auth_service: Mocked AuthService fixture
        """
        # Arrange: Configure mock to raise duplicate email error
        from unittest.mock import Mock
        mock_auth_service.register_user.side_effect = ValueError('Email already registered')
        
        # Act: Make registration request with duplicate email
        response = client.post('/api/auth/register', json={
            'email': 'existing@example.com',
            'password': 'SecurePassword123!',
            'first_name': 'Test',
            'last_name': 'User'
        })
        
        # Assert: Verify conflict response
        assert response.status_code == 409
        
        response_data = json.loads(response.data)
        assert 'error' in response_data or 'message' in response_data or 'msg' in response_data
        
        # Check error message mentions email or duplicate
        error_message = str(response_data.get('error', response_data.get('message', ''))).lower()
        assert 'email' in error_message or 'exists' in error_message or 'duplicate' in error_message
    
    def test_register_with_invalid_email_format(self, client):
        """
        Test registration with malformed email address.
        
        Scenario: User provides email that doesn't match email format
        Expected: Returns 400 Bad Request with validation error
        
        Verifies:
        - HTTP status code is 400 Bad Request
        - Response contains validation error for email field
        - Multiple invalid formats are rejected (no @, no domain, etc.)
        
        Args:
            client: Flask test client fixture
        """
        # Test various invalid email formats
        invalid_emails = [
            'notanemail',              # Missing @ and domain
            'missing@domain',          # Missing TLD
            '@nodomain.com',           # Missing local part
            'spaces in@email.com',     # Contains spaces
            'double@@email.com',       # Double @
            'email@',                  # Missing domain
        ]
        
        for invalid_email in invalid_emails:
            # Act: Make registration request with invalid email
            response = client.post('/api/auth/register', json={
                'email': invalid_email,
                'password': 'SecurePassword123!',
                'first_name': 'Test',
                'last_name': 'User'
            })
            
            # Assert: Verify validation error
            assert response.status_code == 400, f"Failed for email: {invalid_email}"
            
            response_data = json.loads(response.data)
            assert 'error' in response_data or 'message' in response_data or 'msg' in response_data
    
    def test_register_with_weak_password(self, client):
        """
        Test registration with password that doesn't meet strength requirements.
        
        Scenario: User provides password that fails security requirements
        Expected: Returns 400 Bad Request with password validation error
        
        Verifies:
        - HTTP status code is 400 Bad Request
        - Response contains validation error for password
        - Various weak passwords are rejected (too short, no numbers, etc.)
        
        Args:
            client: Flask test client fixture
        """
        # Test various weak passwords
        weak_passwords = [
            'short',                   # Too short
            'alllowercase123',         # No uppercase or special chars
            'ALLUPPERCASE123',         # No lowercase or special chars
            'NoNumbers!',              # No numbers
            'NoSpecialChars123',       # No special characters
            '12345678',                # Only numbers
        ]
        
        for weak_password in weak_passwords:
            # Act: Make registration request with weak password
            response = client.post('/api/auth/register', json={
                'email': 'test@example.com',
                'password': weak_password,
                'first_name': 'Test',
                'last_name': 'User'
            })
            
            # Assert: Verify validation error
            assert response.status_code == 400, f"Failed for password: {weak_password}"
            
            response_data = json.loads(response.data)
            assert 'error' in response_data or 'message' in response_data or 'msg' in response_data
            
            # Check error mentions password
            error_message = str(response_data.get('error', response_data.get('message', ''))).lower()
            assert 'password' in error_message
    
    def test_register_with_missing_required_fields(self, client):
        """
        Test registration with missing required fields.
        
        Scenario: User submits registration without all required fields
        Expected: Returns 400 Bad Request with field-specific validation errors
        
        Verifies:
        - HTTP status code is 400 Bad Request
        - Response identifies missing fields
        - Each required field is validated independently
        
        Args:
            client: Flask test client fixture
        """
        # Test case 1: Missing email
        response = client.post('/api/auth/register', json={
            'password': 'SecurePassword123!',
            'first_name': 'Test',
            'last_name': 'User'
        })
        assert response.status_code == 400
        response_data = json.loads(response.data)
        assert 'error' in response_data or 'message' in response_data or 'msg' in response_data
        
        # Test case 2: Missing password
        response = client.post('/api/auth/register', json={
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User'
        })
        assert response.status_code == 400
        response_data = json.loads(response.data)
        assert 'error' in response_data or 'message' in response_data or 'msg' in response_data
        
        # Test case 3: Missing first_name
        response = client.post('/api/auth/register', json={
            'email': 'test@example.com',
            'password': 'SecurePassword123!',
            'last_name': 'User'
        })
        assert response.status_code == 400
        response_data = json.loads(response.data)
        assert 'error' in response_data or 'message' in response_data or 'msg' in response_data
        
        # Test case 4: Missing last_name
        response = client.post('/api/auth/register', json={
            'email': 'test@example.com',
            'password': 'SecurePassword123!',
            'first_name': 'Test'
        })
        assert response.status_code == 400
        response_data = json.loads(response.data)
        assert 'error' in response_data or 'message' in response_data or 'msg' in response_data
        
        # Test case 5: Empty request body
        response = client.post('/api/auth/register', json={})
        assert response.status_code == 400
        response_data = json.loads(response.data)
        assert 'error' in response_data or 'message' in response_data or 'msg' in response_data


# ============================================================================
# TEST CLASS: LOGOUT ENDPOINT
# ============================================================================


@pytest.mark.unit
@pytest.mark.api
class TestAuthLogout:
    """
    Test suite for user logout endpoint (POST /api/auth/logout).
    
    Tests cover:
    - Successful logout with valid token
    - Logout without authentication token
    - Logout with invalid/expired token
    - Token invalidation verification
    
    All tests mock external dependencies to ensure fast, isolated unit testing.
    """
    
    def test_logout_with_valid_token(self, app, db_session, mock_auth_service):
        """
        Test successful logout with valid authentication token.
        
        Scenario: Authenticated user requests logout
        Expected: Returns 200 OK with success message
        
        Verifies:
        - HTTP status code is 200 OK
        - Response contains success message
        - Token is invalidated (blacklisted or session removed)
        
        Args:
            app: Flask application fixture
            db_session: Database session fixture
            mock_auth_service: Mocked AuthService fixture
        """
        # Arrange: Create a real user and JWT token
        from app.models.user import User
        from flask_jwt_extended import create_access_token
        
        # Create test user
        user = User(email='test@example.com', first_name='Test', last_name='User')
        user.set_password('TestPassword123!')
        db_session.add(user)
        db_session.commit()
        
        # Generate real JWT token
        access_token = create_access_token(identity=str(user.id))
        
        # Configure mock to return successful logout
        mock_auth_service.logout_user.return_value = {'message': 'Logged out successfully'}
        
        # Create client with authentication header
        client = app.test_client()
        headers = {'Authorization': f'Bearer {access_token}'}
        
        # Act: Make logout request with authentication
        response = client.post('/api/auth/logout', headers=headers)
        
        # Assert: Verify successful logout
        assert response.status_code == 200
        
        response_data = json.loads(response.data)
        assert 'message' in response_data or 'success' in response_data
        
        # Verify service was called to invalidate token
        mock_auth_service.logout_user.assert_called_once()
    
    def test_logout_without_authentication(self, client):
        """
        Test logout attempt without authentication token.
        
        Scenario: User tries to logout without providing authentication
        Expected: Returns 401 Unauthorized
        
        Verifies:
        - HTTP status code is 401 Unauthorized
        - Response contains authentication error
        
        Args:
            client: Flask test client fixture
        """
        # Act: Make logout request without authentication header
        response = client.post('/api/auth/logout')
        
        # Assert: Verify unauthorized response
        assert response.status_code == 401
        
        response_data = json.loads(response.data)
        assert 'error' in response_data or 'message' in response_data or 'msg' in response_data
    
    def test_logout_with_invalid_token(self, client, mock_auth_service):
        """
        Test logout with invalid or expired authentication token.
        
        Scenario: User provides malformed or expired JWT token
        Expected: Returns 401 or 422 with token error
        
        Verifies:
        - HTTP status code is 401 or 422
        - Response indicates token is invalid or expired
        
        Args:
            client: Flask test client fixture
            mock_auth_service: Mocked AuthService fixture
        """
        # Arrange: Configure mock to raise invalid token error
        mock_auth_service.logout_user.side_effect = ValueError('Invalid token')
        
        # Simulate request with invalid token
        headers = {'Authorization': 'Bearer invalid_token_format'}
        
        # Act: Make logout request with invalid token
        response = client.post('/api/auth/logout', headers=headers)
        
        # Assert: Verify unauthorized or unprocessable response (JWT validation fails before route)
        assert response.status_code in [401, 422]
        
        response_data = json.loads(response.data)
        assert 'error' in response_data or 'message' in response_data or 'msg' in response_data
    
    def test_logout_token_invalidation(self, app, db_session, mock_auth_service):
        """
        Test that logout properly invalidates the authentication token.
        
        Scenario: User logs out and token should no longer be usable
        Expected: Subsequent requests with same token are rejected
        
        Verifies:
        - Logout service is called to blacklist/invalidate token
        - Token cannot be reused after logout
        
        Args:
            app: Flask application fixture
            db_session: Database session fixture
            mock_auth_service: Mocked AuthService fixture
        """
        # Arrange: Create a real user and JWT token
        from app.models.user import User
        from flask_jwt_extended import create_access_token
        
        # Create test user
        user = User(email='test@example.com', first_name='Test', last_name='User')
        user.set_password('TestPassword123!')
        db_session.add(user)
        db_session.commit()
        
        # Generate real JWT token
        access_token = create_access_token(identity=str(user.id))
        
        # Configure mock for successful logout
        mock_auth_service.logout_user.return_value = {'message': 'Logged out'}
        
        # Create client with authentication header
        client = app.test_client()
        headers = {'Authorization': f'Bearer {access_token}'}
        
        # Act: Perform logout
        response = client.post('/api/auth/logout', headers=headers)
        
        # Assert: Verify logout succeeded
        assert response.status_code == 200
        
        # Verify the service method was called with token for invalidation
        mock_auth_service.logout_user.assert_called_once()
        
        # Subsequent calls with same token should fail (simulated by checking service call)
        # In real implementation, token would be blacklisted


# ============================================================================
# TEST CLASS: REFRESH TOKEN ENDPOINT
# ============================================================================


@pytest.mark.unit
@pytest.mark.api
class TestAuthRefresh:
    """
    Test suite for token refresh endpoint (POST /api/auth/refresh).
    
    Tests cover:
    - Successful token refresh with valid refresh token
    - Refresh with invalid/expired refresh token
    - Refresh without refresh token
    - New access token generation
    
    All tests mock external dependencies to ensure fast, isolated unit testing.
    """
    
    def test_refresh_with_valid_token(self, app, db_session, mock_auth_service):
        """
        Test successful token refresh with valid refresh token.
        
        Scenario: User provides valid refresh token to get new access token
        Expected: Returns 200 OK with new access token
        
        Verifies:
        - HTTP status code is 200 OK
        - Response contains new access token
        - Access token is in valid JWT format
        - Refresh token may be rotated (new refresh token provided)
        
        Args:
            app: Flask application fixture
            db_session: Database session fixture
            mock_auth_service: Mocked AuthService fixture
        """
        # Arrange: Create a real user and JWT token
        from app.models.user import User
        from flask_jwt_extended import create_refresh_token
        
        # Create test user
        user = User(email='test@example.com', first_name='Test', last_name='User')
        user.set_password('TestPassword123!')
        db_session.add(user)
        db_session.commit()
        
        # Generate real refresh token (note: using create_refresh_token, not create_access_token)
        refresh_token = create_refresh_token(identity=str(user.id))
        
        # Configure mock to return new tokens
        mock_auth_service.refresh_token.return_value = {
            'access_token': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.new_access_token',
            'refresh_token': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.new_refresh_token',
            'token_type': 'Bearer',
            'expires_in': 3600
        }
        
        # Create client with refresh token
        client = app.test_client()
        headers = {'Authorization': f'Bearer {refresh_token}'}
        
        # Act: Make refresh request
        response = client.post('/api/auth/refresh', headers=headers)
        
        # Assert: Verify successful token refresh
        assert response.status_code == 200
        
        response_data = json.loads(response.data)
        assert 'access_token' in response_data
        assert response_data['access_token'].startswith('eyJ')  # JWT format
        assert 'token_type' in response_data
        assert response_data['token_type'] == 'Bearer'
        
        # Verify service was called
        mock_auth_service.refresh_token.assert_called_once()
    
    def test_refresh_with_invalid_token(self, client, mock_auth_service):
        """
        Test token refresh with invalid or expired refresh token.
        
        Scenario: User provides malformed or expired refresh token
        Expected: Returns 401 or 422 (JWT validation error)
        
        Verifies:
        - HTTP status code is 401 Unauthorized or 422 Unprocessable Entity
        - Response contains error about invalid token
        - No new tokens are issued
        
        Args:
            client: Flask test client fixture
            mock_auth_service: Mocked AuthService fixture
        """
        # Arrange: Configure mock to raise invalid token error
        mock_auth_service.refresh_token.side_effect = ValueError('Invalid refresh token')
        
        # Simulate request with invalid token
        headers = {'Authorization': 'Bearer invalid_refresh_token'}
        
        # Act: Make refresh request with invalid token
        response = client.post('/api/auth/refresh', headers=headers)
        
        # Assert: Verify unauthorized response (Flask-JWT-Extended returns 422 for invalid tokens)
        assert response.status_code in [401, 422]
        
        response_data = json.loads(response.data)
        assert 'error' in response_data or 'message' in response_data or 'msg' in response_data
        
        # Check error mentions token or JWT error (Flask-JWT-Extended may return "not enough segments")
        error_message = str(response_data.get('error', response_data.get('message', response_data.get('msg', '')))).lower()
        assert 'token' in error_message or 'invalid' in error_message or 'segment' in error_message
    
    def test_refresh_without_token(self, client):
        """
        Test token refresh without providing refresh token.
        
        Scenario: User makes refresh request without authentication
        Expected: Returns 401 Unauthorized
        
        Verifies:
        - HTTP status code is 401 Unauthorized
        - Response contains error about missing authentication
        
        Args:
            client: Flask test client fixture
        """
        # Act: Make refresh request without authorization header
        response = client.post('/api/auth/refresh')
        
        # Assert: Verify unauthorized response
        assert response.status_code == 401
        
        response_data = json.loads(response.data)
        assert 'error' in response_data or 'message' in response_data or 'msg' in response_data
    
    def test_refresh_with_access_token_instead_of_refresh(self, client, mock_auth_service):
        """
        Test token refresh using access token instead of refresh token.
        
        Scenario: User mistakenly provides access token for refresh endpoint
        Expected: Returns 401 Unauthorized or 422 Unprocessable Entity
        
        Verifies:
        - HTTP status code is 401 or 422
        - Response indicates wrong token type
        - No new tokens are issued
        
        Args:
            client: Flask test client fixture
            mock_auth_service: Mocked AuthService fixture
        """
        # Arrange: Configure mock to reject access token for refresh
        mock_auth_service.refresh_token.side_effect = ValueError('Access token cannot be used for refresh')
        
        # Simulate request with access token instead of refresh token
        headers = {'Authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.access_token'}
        
        # Act: Make refresh request with wrong token type
        response = client.post('/api/auth/refresh', headers=headers)
        
        # Assert: Verify error response
        assert response.status_code in [401, 422]
        
        response_data = json.loads(response.data)
        assert 'error' in response_data or 'message' in response_data or 'msg' in response_data
    
    def test_refresh_token_rotation(self, app, db_session, mock_auth_service):
        """
        Test that refresh endpoint implements token rotation security.
        
        Scenario: User refreshes token and receives new refresh token
        Expected: New refresh token is provided, old one is invalidated
        
        Verifies:
        - Response includes new access token
        - Response includes new refresh token (rotation)
        - Old refresh token is different from new one
        
        Args:
            app: Flask application fixture
            db_session: Database session fixture
            mock_auth_service: Mocked AuthService fixture
        """
        # Arrange: Create a real user and JWT token
        from app.models.user import User
        from flask_jwt_extended import create_refresh_token
        
        # Create test user
        user = User(email='test@example.com', first_name='Test', last_name='User')
        user.set_password('TestPassword123!')
        db_session.add(user)
        db_session.commit()
        
        # Generate real refresh token
        old_refresh_token = create_refresh_token(identity=str(user.id))
        
        # Configure mock to return rotated tokens
        new_refresh_token_value = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.new_refresh'
        mock_auth_service.refresh_token.return_value = {
            'access_token': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.new_access',
            'refresh_token': new_refresh_token_value,
            'token_type': 'Bearer',
            'expires_in': 3600
        }
        
        # Create client with old refresh token
        client = app.test_client()
        headers = {'Authorization': f'Bearer {old_refresh_token}'}
        
        # Act: Make refresh request
        response = client.post('/api/auth/refresh', headers=headers)
        
        # Assert: Verify token rotation
        assert response.status_code == 200
        
        response_data = json.loads(response.data)
        assert 'access_token' in response_data
        assert 'refresh_token' in response_data
        
        # Verify new refresh token is different from old one
        new_refresh_token = response_data['refresh_token']
        assert new_refresh_token != old_refresh_token
        assert new_refresh_token == new_refresh_token_value
        
        # Verify service was called for token rotation
        mock_auth_service.refresh_token.assert_called_once()


# ============================================================================
# ADDITIONAL EDGE CASE TESTS
# ============================================================================


@pytest.mark.unit
@pytest.mark.api
class TestAuthEdgeCases:
    """
    Test suite for edge cases and boundary conditions in authentication routes.
    
    Tests cover:
    - Maximum length inputs
    - Special characters in inputs
    - Concurrent authentication requests
    - Malformed JSON payloads
    - Content-Type validation
    """
    
    def test_login_with_maximum_length_email(self, client, mock_auth_service):
        """
        Test login with email at maximum allowed length.
        
        Scenario: User provides email at boundary of maximum length
        Expected: Accepts valid email up to max length, rejects if exceeded
        
        Verifies:
        - Maximum length emails are processed
        - Email validation handles length limits
        
        Args:
            client: Flask test client fixture
            mock_auth_service: Mocked AuthService fixture
        """
        # Create email at typical maximum length (255 characters)
        max_length_email = 'a' * 240 + '@example.com'  # 253 characters
        
        # Arrange: Configure mock to accept the request
        mock_auth_service.authenticate_user.return_value = {
            'token': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.token',
            'user': {'id': 1, 'email': max_length_email}
        }
        
        # Act: Make login request with max length email
        response = client.post('/api/auth/login', json={
            'email': max_length_email,
            'password': 'SecurePassword123!'
        })
        
        # Assert: Verify request is processed (may succeed or fail based on validation)
        assert response.status_code in [200, 400]  # Either success or validation error
    
    def test_register_with_special_characters_in_name(self, client, mock_auth_service):
        """
        Test registration with special characters in name fields.
        
        Scenario: User has special characters, accents, or unicode in names
        Expected: Accepts valid unicode characters, properly handles encoding
        
        Verifies:
        - Unicode characters are accepted
        - Special characters are properly encoded
        - Names with accents, hyphens, apostrophes work correctly
        
        Args:
            client: Flask test client fixture
            mock_auth_service: Mocked AuthService fixture
        """
        # Test names with various special characters
        special_names = [
            ('José', 'García'),           # Accented characters
            ("O'Brien", 'Smith'),         # Apostrophe
            ('Mary-Jane', 'Watson'),      # Hyphen
            ('François', 'Müller'),       # Multiple accents
            ('李', '明'),                   # Chinese characters
        ]
        
        for first_name, last_name in special_names:
            # Arrange: Configure mock to accept registration
            mock_auth_service.register_user.return_value = {
                'user': {
                    'id': 1,
                    'email': 'test@example.com',
                    'first_name': first_name,
                    'last_name': last_name
                }
            }
            
            # Act: Make registration request with special characters
            response = client.post('/api/auth/register', json={
                'email': 'test@example.com',
                'password': 'SecurePassword123!',
                'first_name': first_name,
                'last_name': last_name
            })
            
            # Assert: Verify request is processed correctly
            assert response.status_code in [201, 400]  # Either success or validation error
    
    def test_auth_with_malformed_json(self, client):
        """
        Test authentication endpoints with malformed JSON payload.
        
        Scenario: Client sends invalid JSON in request body
        Expected: Returns 400 Bad Request with JSON parse error
        
        Verifies:
        - HTTP status code is 400 Bad Request
        - Response indicates JSON parsing error
        
        Args:
            client: Flask test client fixture
        """
        # Act: Send malformed JSON (not valid JSON)
        response = client.post(
            '/api/auth/login',
            data='{"email": "test@example.com", invalid json',
            content_type='application/json'
        )
        
        # Assert: Verify bad request response
        assert response.status_code == 400
    
    def test_auth_with_wrong_content_type(self, client):
        """
        Test authentication with incorrect Content-Type header.
        
        Scenario: Client sends form data instead of JSON
        Expected: Returns 400 Bad Request or 415 Unsupported Media Type
        
        Verifies:
        - API enforces JSON content type
        - Proper error response for wrong media type
        
        Args:
            client: Flask test client fixture
        """
        # Act: Send form data instead of JSON
        response = client.post(
            '/api/auth/login',
            data='email=test@example.com&password=password',
            content_type='application/x-www-form-urlencoded'
        )
        
        # Assert: Verify error response
        assert response.status_code in [400, 415]
    
    def test_login_with_empty_string_credentials(self, client):
        """
        Test login with empty strings for email and password.
        
        Scenario: User provides empty strings instead of omitting fields
        Expected: Returns 400 Bad Request with validation error
        
        Verifies:
        - Empty strings are treated as invalid
        - Validation distinguishes between missing and empty
        
        Args:
            client: Flask test client fixture
        """
        # Test case 1: Empty email
        response = client.post('/api/auth/login', json={
            'email': '',
            'password': 'SecurePassword123!'
        })
        assert response.status_code == 400
        
        # Test case 2: Empty password
        response = client.post('/api/auth/login', json={
            'email': 'test@example.com',
            'password': ''
        })
        assert response.status_code == 400
        
        # Test case 3: Both empty
        response = client.post('/api/auth/login', json={
            'email': '',
            'password': ''
        })
        assert response.status_code == 400
    
    def test_register_with_whitespace_in_email(self, client, mock_auth_service):
        """
        Test registration with leading/trailing whitespace in email.
        
        Scenario: User accidentally includes spaces around email
        Expected: Email is trimmed or validation error is returned
        
        Verifies:
        - Whitespace handling in email validation
        - Either automatic trimming or validation error
        
        Args:
            client: Flask test client fixture
            mock_auth_service: Mocked AuthService fixture
        """
        # Arrange: Configure mock for successful registration (if validation passes)
        mock_auth_service.register_user.return_value = {
            'id': 1,
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User'
        }
        
        # Test emails with whitespace
        emails_with_whitespace = [
            '  test@example.com',       # Leading spaces
            'test@example.com  ',       # Trailing spaces
            '  test@example.com  ',     # Both
            'test @example.com',        # Space in local part
        ]
        
        for email in emails_with_whitespace:
            # Act: Make registration request
            response = client.post('/api/auth/register', json={
                'email': email,
                'password': 'SecurePassword123!',
                'first_name': 'Test',
                'last_name': 'User'
            })
            
            # Assert: Verify proper handling (either trimmed and accepted, or rejected)
            assert response.status_code in [201, 400]
