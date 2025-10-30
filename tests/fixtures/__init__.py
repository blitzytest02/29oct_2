"""
Test Fixtures Package Initialization Module

This module serves as the package initialization file for the tests/fixtures directory,
establishing it as a Python package and enabling pytest fixture discovery across all
fixture modules. It provides a centralized import location for all test fixtures,
allowing test files to import fixtures from a single namespace rather than importing
from individual fixture modules.

Package Purpose:
    - Makes tests/fixtures/ a Python package (required by Python import system)
    - Enables pytest to discover and register all fixture modules automatically
    - Provides convenient centralized imports for test files
    - Supports fixture composition across modules
    - Follows pytest best practices for test fixture organization

Key Features:
    - Centralized fixture exports from all fixture modules
    - Simplified import syntax: 'from tests.fixtures import valid_user_data, auth_token'
    - Automatic pytest fixture discovery (fixtures available without explicit imports)
    - Module organization following Agent Action Plan sections 0.5 and 0.8
    - Support for fixture composition and dependency injection

Available Fixture Modules:
    - user_fixtures.py: User data fixtures, model instances, and factory patterns
    - auth_fixtures.py: Authentication tokens, credentials, and auth context fixtures
    - api_fixtures.py: HTTP test clients, headers, and API testing utilities

Fixture Organization:
    The fixtures are organized into three main categories:
    
    1. User Fixtures (from user_fixtures.py):
       - valid_user_data: Dictionary with valid user attributes for API requests
       - existing_user: Persisted User model instance in test database
       - invalid_user_data: Invalid user data for validation testing
       - user_factory: Factory function for creating custom User instances
    
    2. Authentication Fixtures (from auth_fixtures.py):
       - auth_token: Valid JWT access token for existing user
       - expired_token: Expired JWT token for testing expiration handling
       - invalid_token: Malformed JWT token for testing error scenarios
       - authenticated_user: Tuple of (user, token) for complete auth context
    
    3. API Testing Fixtures (from api_fixtures.py):
       - authenticated_client: Flask test client with JWT token in Authorization header
       - api_headers: Common API request headers (Content-Type, Accept)

Usage Examples:
    # Import fixtures from centralized package namespace
    from tests.fixtures import valid_user_data, auth_token, authenticated_client
    
    # Use fixtures in test functions via pytest dependency injection
    def test_user_creation(client, valid_user_data):
        response = client.post('/api/users', json=valid_user_data)
        assert response.status_code == 201
    
    def test_protected_endpoint(authenticated_client, existing_user):
        response = authenticated_client.get('/api/users/profile')
        assert response.status_code == 200
        assert response.json['email'] == existing_user.email
    
    def test_token_expiration(client, expired_token):
        headers = {'Authorization': f'Bearer {expired_token}'}
        response = client.get('/api/users/profile', headers=headers)
        assert response.status_code == 401
    
    # Fixtures can also be used without explicit imports (pytest auto-discovery)
    def test_user_authentication(client, login_credentials, existing_user):
        # pytest automatically finds these fixtures from fixture modules
        credentials = {
            'email': existing_user.email,
            'password': 'DefaultPassword123!'
        }
        response = client.post('/api/auth/login', json=credentials)
        assert response.status_code == 200

Pytest Fixture Discovery:
    Pytest automatically discovers fixtures in the following order:
    1. Test module's conftest.py
    2. Parent directory's conftest.py (recursively up to project root)
    3. Fixture modules imported in conftest.py or __init__.py
    4. Built-in pytest fixtures
    
    This __init__.py file enables method #3 by providing a centralized import point.
    However, pytest will also discover fixtures directly from fixture modules without
    needing explicit imports, as long as the modules contain properly decorated
    @pytest.fixture functions.

Fixture Composition:
    Fixtures in one module can depend on fixtures from another module:
    
    Example in auth_fixtures.py:
        @pytest.fixture
        def auth_token(existing_user, app):  # Depends on user_fixtures.existing_user
            with app.app_context():
                token = create_access_token(identity=str(existing_user.id))
                return token
    
    Example in api_fixtures.py:
        @pytest.fixture
        def authenticated_client(client, auth_token):  # Depends on auth_fixtures.auth_token
            client.environ_base['HTTP_AUTHORIZATION'] = f'Bearer {auth_token}'
            return client
    
    This composition works automatically through pytest's dependency injection system.

Best Practices:
    1. Import specific fixtures needed for each test:
       from tests.fixtures import valid_user_data, auth_token
    
    2. Use fixture function signatures for dependency injection:
       def test_endpoint(authenticated_client, existing_user):
    
    3. Combine fixtures for complex test scenarios:
       def test_workflow(authenticated_client, db_session, user_factory):
    
    4. Let pytest handle fixture lifecycle and cleanup automatically
    
    5. Use fixture composition to build complex fixtures from simpler ones
    
    6. Keep fixture modules focused on specific domains (users, auth, API)

Module Structure:
    tests/
    ├── fixtures/
    │   ├── __init__.py (this file)
    │   ├── user_fixtures.py
    │   ├── auth_fixtures.py
    │   └── api_fixtures.py
    ├── unit/
    ├── integration/
    ├── functional/
    └── conftest.py

Dependencies:
    This module depends on the following fixture modules:
    - tests/fixtures/user_fixtures.py: User-related test fixtures
    - tests/fixtures/auth_fixtures.py: Authentication-related test fixtures
    - tests/fixtures/api_fixtures.py: API testing-related test fixtures
    
    All fixture modules are part of the Flask testing infrastructure as defined
    in the Agent Action Plan section 0.5.

Notes:
    - This file can remain minimal (just package marker) or include fixture exports
    - Pytest automatically discovers fixtures without requiring __init__.py imports
    - Explicit imports here provide convenience but are not strictly necessary
    - The __all__ list controls what's available when using 'from tests.fixtures import *'
    - Follow Agent Action Plan sections 0.5 and 0.8 for testing infrastructure standards
"""

# Import all fixtures from fixture modules for centralized access
# These imports enable test files to use:
#   from tests.fixtures import valid_user_data, auth_token
# Instead of:
#   from tests.fixtures.user_fixtures import valid_user_data
#   from tests.fixtures.auth_fixtures import auth_token

# User Fixtures - User data, model instances, and factory patterns
from tests.fixtures.user_fixtures import (
    valid_user_data,        # Dictionary with valid user attributes
    existing_user,          # Persisted User instance in test database
    invalid_user_data,      # Invalid user data for validation testing
    user_factory,           # Factory function for creating custom Users
)

# Authentication Fixtures - JWT tokens, credentials, and auth context
from tests.fixtures.auth_fixtures import (
    auth_token,             # Valid JWT access token for existing user
    expired_token,          # Expired JWT token for expiration testing
    invalid_token,          # Malformed JWT token for error testing
    authenticated_user,     # Tuple of (user, token) for complete auth context
)

# API Testing Fixtures - HTTP clients, headers, and API utilities
from tests.fixtures.api_fixtures import (
    authenticated_client,   # Flask test client with JWT token configured
    api_headers,            # Common API headers (Content-Type, Accept)
)


# Define __all__ to control what's available with 'from tests.fixtures import *'
# This list includes all commonly used fixtures for convenient access
# Following Python best practices for explicit exports
__all__ = [
    # User Fixtures
    'valid_user_data',      # Valid user data dictionary for API testing
    'existing_user',        # Persisted User model instance
    'invalid_user_data',    # Invalid user data for negative testing
    'user_factory',         # Factory for creating custom User instances
    
    # Authentication Fixtures
    'auth_token',           # Valid JWT token string
    'expired_token',        # Expired JWT token for expiration testing
    'invalid_token',        # Invalid JWT token for error testing
    'authenticated_user',   # (user, token) tuple for auth context
    
    # API Testing Fixtures
    'authenticated_client', # Test client with authentication configured
    'api_headers',          # Standard API request headers
]


# ============================================================================
# PACKAGE DOCUMENTATION
# ============================================================================

"""
Complete Import Reference:

Available User Fixtures:
    from tests.fixtures import (
        valid_user_data,        # Dict: Valid user attributes for creation
        existing_user,          # User: Persisted user in database
        invalid_user_data,      # Dict: Invalid data for validation tests
        user_factory,           # Callable: Factory for custom users
    )

Available Authentication Fixtures:
    from tests.fixtures import (
        auth_token,             # str: Valid JWT access token
        expired_token,          # str: Expired JWT token
        invalid_token,          # str: Malformed JWT token
        authenticated_user,     # Tuple[User, str]: (user, token) pair
    )

Available API Testing Fixtures:
    from tests.fixtures import (
        authenticated_client,   # FlaskClient: Client with auth header
        api_headers,            # Dict: Standard JSON API headers
    )

Complete Testing Example:

    from tests.fixtures import (
        valid_user_data,
        existing_user,
        authenticated_client,
        auth_token,
        user_factory
    )
    
    def test_user_registration(client, valid_user_data):
        '''Test user registration with valid data.'''
        response = client.post('/api/auth/register', json=valid_user_data)
        assert response.status_code == 201
        assert 'id' in response.json
        assert response.json['email'] == valid_user_data['email']
    
    def test_get_user_profile(authenticated_client, existing_user):
        '''Test retrieving authenticated user profile.'''
        response = authenticated_client.get('/api/users/profile')
        assert response.status_code == 200
        assert response.json['id'] == existing_user.id
        assert response.json['email'] == existing_user.email
    
    def test_update_user_profile(authenticated_client, existing_user):
        '''Test updating authenticated user profile.'''
        response = authenticated_client.put(
            f'/api/users/{existing_user.id}',
            json={'first_name': 'Updated'}
        )
        assert response.status_code == 200
        assert response.json['first_name'] == 'Updated'
    
    def test_token_expiration(client, expired_token):
        '''Test that expired tokens are rejected.'''
        headers = {'Authorization': f'Bearer {expired_token}'}
        response = client.get('/api/users/profile', headers=headers)
        assert response.status_code == 401
        assert 'expired' in response.json['error'].lower()
    
    def test_custom_user_creation(user_factory, db_session):
        '''Test creating user with custom attributes using factory.'''
        admin = user_factory({
            'email': 'admin@example.com',
            'role': 'admin',
            'first_name': 'Admin'
        })
        assert admin.id is not None
        assert admin.role == 'admin'
        assert admin.email == 'admin@example.com'

Fixture Composition Example:

    # auth_token depends on existing_user (from user_fixtures)
    # authenticated_client depends on auth_token (from auth_fixtures)
    # This creates a dependency chain: existing_user -> auth_token -> authenticated_client
    
    def test_complex_workflow(authenticated_client, existing_user, user_factory):
        # authenticated_client automatically includes:
        #   - created existing_user
        #   - generated auth_token for existing_user
        #   - configured Flask test client with Authorization header
        
        # Test accessing own profile
        response = authenticated_client.get('/api/users/profile')
        assert response.status_code == 200
        assert response.json['email'] == existing_user.email
        
        # Create another user for testing
        other_user = user_factory({'email': 'other@example.com'})
        
        # Verify cannot access other user's private data
        response = authenticated_client.get(f'/api/users/{other_user.id}/private')
        assert response.status_code == 403

Advanced Usage:

    # Combine multiple fixtures for comprehensive testing
    def test_complete_auth_flow(
        client,
        db_session,
        valid_user_data,
        authenticated_client,
        user_factory
    ):
        # Register new user
        register_response = client.post('/api/auth/register', json=valid_user_data)
        assert register_response.status_code == 201
        
        # Login with new credentials
        login_response = client.post('/api/auth/login', json={
            'email': valid_user_data['email'],
            'password': valid_user_data['password']
        })
        assert login_response.status_code == 200
        new_token = login_response.json['access_token']
        
        # Access protected endpoint with new token
        headers = {'Authorization': f'Bearer {new_token}'}
        profile_response = client.get('/api/users/profile', headers=headers)
        assert profile_response.status_code == 200

For more details on specific fixtures, see:
    - tests/fixtures/user_fixtures.py: User fixture documentation
    - tests/fixtures/auth_fixtures.py: Authentication fixture documentation
    - tests/fixtures/api_fixtures.py: API testing fixture documentation
"""
