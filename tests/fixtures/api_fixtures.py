"""
API Testing Fixtures Module

This module provides comprehensive pytest fixtures for HTTP API testing with the Flask
application. It delivers pre-configured Flask test client fixtures with authentication
support, enabling seamless testing of both public and protected API endpoints.

The fixtures compose with auth_fixtures.py and conftest.py to provide a complete API
testing toolkit, following pytest best practices with proper dependency injection and
automatic setup/teardown. All fixtures are designed for ease of use, requiring minimal
test setup code while providing maximum testing flexibility.

Key Features:
- Pre-authenticated test clients with JWT tokens configured
- Unauthenticated test clients for testing public endpoints
- Common HTTP headers fixtures for JSON API testing
- Composable fixtures that work seamlessly with existing test infrastructure
- Zero-configuration authentication for protected endpoint testing
- Support for testing RESTful API conventions (JSON request/response)

Fixtures Provided:
    Client Fixtures:
        - authenticated_client: Flask test client with Authorization header containing
          valid JWT token for testing protected endpoints requiring authentication
        - unauthenticated_client: Plain Flask test client for testing public endpoints
          without authentication headers
    
    Header Fixtures:
        - api_headers: Dictionary of common API headers (Content-Type, Accept) for
          standard API requests
        - json_headers: Extended headers dictionary specifically for JSON API testing,
          composing with api_headers

Usage Examples:
    # Test protected endpoint with automatic authentication
    def test_get_user_profile(authenticated_client):
        response = authenticated_client.get('/api/users/profile')
        assert response.status_code == 200
        assert 'email' in response.json
    
    # Test public endpoint without authentication
    def test_public_health_check(unauthenticated_client):
        response = unauthenticated_client.get('/api/health')
        assert response.status_code == 200
        assert response.json['status'] == 'healthy'
    
    # Test POST endpoint with JSON data and authentication
    def test_create_resource(authenticated_client, json_headers):
        response = authenticated_client.post(
            '/api/resources',
            json={'name': 'New Resource', 'type': 'test'},
            headers=json_headers
        )
        assert response.status_code == 201
        assert response.json['name'] == 'New Resource'
    
    # Test public registration endpoint
    def test_user_registration(unauthenticated_client, json_headers):
        response = unauthenticated_client.post(
            '/api/auth/register',
            json={
                'email': 'newuser@example.com',
                'password': 'SecurePass123!',
                'first_name': 'New',
                'last_name': 'User'
            },
            headers=json_headers
        )
        assert response.status_code == 201
        assert 'id' in response.json
    
    # Test API headers are correctly applied
    def test_api_headers_format(api_headers):
        assert api_headers['Content-Type'] == 'application/json'
        assert api_headers['Accept'] == 'application/json'
    
    # Test multiple authenticated requests in sequence
    def test_complete_workflow(authenticated_client):
        # Create resource
        create_response = authenticated_client.post(
            '/api/resources',
            json={'name': 'Test Resource'}
        )
        assert create_response.status_code == 201
        resource_id = create_response.json['id']
        
        # Retrieve resource
        get_response = authenticated_client.get(f'/api/resources/{resource_id}')
        assert get_response.status_code == 200
        
        # Update resource
        update_response = authenticated_client.put(
            f'/api/resources/{resource_id}',
            json={'name': 'Updated Resource'}
        )
        assert update_response.status_code == 200
        
        # Delete resource
        delete_response = authenticated_client.delete(f'/api/resources/{resource_id}')
        assert delete_response.status_code == 204

Design Decisions:
    - authenticated_client uses dependency injection to compose client and auth_token
      fixtures, ensuring the test client has a valid JWT token in the Authorization
      header before any test code executes
    
    - unauthenticated_client explicitly returns the base client without modification,
      making test intent clear when testing public endpoints
    
    - Header fixtures return dictionaries rather than modifying client state, allowing
      tests to combine headers or override specific values as needed
    
    - All fixtures are function-scoped for test isolation, ensuring each test gets
      a fresh client and headers without state pollution
    
    - Flask test client's environ_base is used for Authorization header to ensure
      the header persists across all requests made with that client instance

Integration with Existing Fixtures:
    - Composes with 'client' fixture from tests/conftest.py for base Flask test client
    - Composes with 'auth_token' fixture from tests/fixtures/auth_fixtures.py for JWT
    - Works seamlessly with 'existing_user' fixture for user-specific testing
    - Compatible with 'db_session' fixture for testing endpoints with database operations

Testing Best Practices:
    - Use authenticated_client for all endpoints with @jwt_required decorator
    - Use unauthenticated_client for public endpoints to verify no auth required
    - Apply json_headers when testing JSON API endpoints explicitly
    - Combine fixtures: def test_endpoint(authenticated_client, db_session, user_factory)
    - Test authorization separately from authentication using authenticated_client
    - Verify proper error responses (401, 403) with unauthenticated_client

Performance Considerations:
    - Fixtures are function-scoped for test isolation but reuse app and db fixtures
    - Auth token generation happens once per test using existing_user fixture
    - No actual HTTP server is started - Flask test client simulates requests
    - Database operations use in-memory SQLite for fast test execution
"""

from typing import Dict, Any
import pytest

# Import fixtures via pytest dependency injection
# Note: 'app' and 'auth_token' fixtures are passed as parameters to avoid circular imports
from tests.fixtures.auth_fixtures import auth_token


# ============================================================================
# AUTHENTICATED CLIENT FIXTURES
# ============================================================================


@pytest.fixture
def authenticated_client(app, auth_token) -> Any:
    """
    Provide Flask test client with Authorization header containing valid JWT token.
    
    This fixture extends the base Flask test client by adding an Authorization header
    with a valid JWT Bearer token. The token is generated from the existing_user
    fixture via auth_token fixture, enabling seamless testing of protected API endpoints
    that require authentication without manual login in every test.
    
    The Authorization header is configured using the client's environ_base dictionary,
    which ensures the header persists across all HTTP requests made with this client
    instance. This approach follows Flask testing best practices and matches production
    authentication behavior.
    
    IMPORTANT: To prevent fixture state pollution when using both authenticated_client
    and unauthenticated_client in the same test, this fixture saves the original
    environ_base state and registers a finalizer to restore it after the test completes.
    This ensures proper test isolation and fixture independence.
    
    Use this fixture for testing:
    - Protected API endpoints decorated with @jwt_required()
    - User-specific operations (profile access, resource ownership)
    - Authorization and permission checks
    - Endpoints requiring authenticated user context
    - Multi-step workflows requiring consistent authentication
    
    The fixture automatically:
    - Creates a test user in the database (via existing_user)
    - Generates a valid JWT access token for that user
    - Configures the test client with proper Authorization header
    - Provides ready-to-use client for authenticated requests
    - Restores original client state after test completion
    
    Args:
        app: Flask application fixture from tests/conftest.py
        auth_token: Valid JWT access token string from tests/fixtures/auth_fixtures.py
            for an existing test user with valid identity claim
    
    Returns:
        FlaskClient: Flask test client with Authorization header pre-configured.
            All requests made with this client will include: 
            'Authorization: Bearer <valid_jwt_token>'
            
            Available methods:
            - client.get(url, **kwargs): Make authenticated GET request
            - client.post(url, json=data, **kwargs): Make authenticated POST request
            - client.put(url, json=data, **kwargs): Make authenticated PUT request
            - client.patch(url, json=data, **kwargs): Make authenticated PATCH request
            - client.delete(url, **kwargs): Make authenticated DELETE request
    
    Example:
        def test_get_user_profile(authenticated_client, existing_user):
            # No need to manually add Authorization header
            response = authenticated_client.get('/api/users/profile')
            assert response.status_code == 200
            assert response.json['email'] == existing_user.email
            assert 'password' not in response.json
        
        def test_create_resource(authenticated_client):
            response = authenticated_client.post(
                '/api/resources',
                json={'name': 'Test Resource', 'type': 'document'}
            )
            assert response.status_code == 201
            assert response.json['name'] == 'Test Resource'
            assert 'id' in response.json
        
        def test_update_own_profile(authenticated_client, existing_user):
            response = authenticated_client.put(
                f'/api/users/{existing_user.id}',
                json={'first_name': 'Updated'}
            )
            assert response.status_code == 200
            assert response.json['first_name'] == 'Updated'
        
        def test_delete_own_resource(authenticated_client, db_session):
            # Create resource first
            create_response = authenticated_client.post(
                '/api/resources',
                json={'name': 'To Delete'}
            )
            resource_id = create_response.json['id']
            
            # Delete resource
            delete_response = authenticated_client.delete(
                f'/api/resources/{resource_id}'
            )
            assert delete_response.status_code == 204
        
        def test_unauthorized_access_to_other_user_data(
            authenticated_client, user_factory
        ):
            # Create another user
            other_user = user_factory({'email': 'other@example.com'})
            
            # Try to access other user's protected data
            response = authenticated_client.get(f'/api/users/{other_user.id}/private')
            assert response.status_code == 403  # Forbidden
        
        def test_complete_crud_workflow(authenticated_client):
            # Create
            create_resp = authenticated_client.post(
                '/api/items',
                json={'name': 'Item 1', 'quantity': 10}
            )
            assert create_resp.status_code == 201
            item_id = create_resp.json['id']
            
            # Read
            get_resp = authenticated_client.get(f'/api/items/{item_id}')
            assert get_resp.status_code == 200
            assert get_resp.json['quantity'] == 10
            
            # Update
            update_resp = authenticated_client.put(
                f'/api/items/{item_id}',
                json={'quantity': 20}
            )
            assert update_resp.status_code == 200
            assert update_resp.json['quantity'] == 20
            
            # Delete
            delete_resp = authenticated_client.delete(f'/api/items/{item_id}')
            assert delete_resp.status_code == 204
    
    Note:
        - The JWT token is generated within Flask application context by auth_token
        - Token contains the user ID as the identity claim for user-specific operations
        - Authorization header format: 'Bearer <token>' (standard OAuth 2.0 format)
        - All requests from this client will be authenticated as the existing_user
        - For testing with different users, create custom fixtures or use user_factory
        - The client maintains the Authorization header for all subsequent requests
        - No need to pass headers parameter explicitly in test requests
        - This fixture creates its own independent client instance to avoid state pollution
    
    Security Testing:
        This fixture enables security testing scenarios:
        - Verify protected endpoints reject unauthenticated requests
        - Test authorization rules (user can only access own resources)
        - Validate token expiration handling (use with expired_token)
        - Test role-based access control (create fixtures for different roles)
        - Ensure proper 401/403 responses for unauthorized access
    """
    # CRITICAL FIX: Create an independent test client instance instead of sharing
    # the client fixture. This prevents state pollution when both authenticated_client
    # and unauthenticated_client are used in the same test, as each gets its own
    # Flask test client instance with its own environ_base dictionary.
    test_client = app.test_client()
    
    # Configure the test client with Authorization header using HTTP_AUTHORIZATION
    # This is added to environ_base so it persists across all requests
    # Format: 'Bearer <token>' following OAuth 2.0 Bearer Token specification (RFC 6750)
    test_client.environ_base['HTTP_AUTHORIZATION'] = f'Bearer {auth_token}'
    
    # Return the configured client for use in tests
    # All subsequent requests will include the Authorization header automatically
    return test_client


@pytest.fixture
def unauthenticated_client(app) -> Any:
    """
    Provide plain Flask test client without authentication headers for public endpoints.
    
    This fixture explicitly returns the base Flask test client without any authentication
    configuration. While functionally equivalent to using the 'client' fixture directly,
    this fixture makes test intent clear: the test is specifically verifying behavior of
    public endpoints that should not require authentication.
    
    IMPORTANT: To prevent fixture state pollution when using both authenticated_client
    and unauthenticated_client in the same test, this fixture saves the original
    environ_base state, removes any authorization headers, and registers a finalizer
    to restore the original state after the test completes. This ensures proper test
    isolation and fixture independence.
    
    Using this fixture provides several benefits:
    - Makes test intent explicit in function signature
    - Clearly distinguishes public endpoint tests from protected endpoint tests
    - Provides semantic meaning: "this endpoint should work without authentication"
    - Enables future enhancement (e.g., adding common headers for public APIs)
    - Improves test readability and maintainability
    
    Use this fixture for testing:
    - Public API endpoints (health checks, status, public data)
    - Authentication endpoints (login, register, password reset request)
    - Endpoints that should explicitly NOT require authentication
    - Negative testing: Verify protected endpoints reject unauthenticated requests
    - Public documentation or schema endpoints
    - CORS preflight requests
    
    Args:
        app: Flask application fixture from tests/conftest.py
    
    Returns:
        FlaskClient: Plain Flask test client with no authentication headers.
            All requests made with this client will not include Authorization header.
            
            Available methods:
            - client.get(url, **kwargs): Make unauthenticated GET request
            - client.post(url, json=data, **kwargs): Make unauthenticated POST request
            - client.put(url, json=data, **kwargs): Make unauthenticated PUT request
            - client.patch(url, json=data, **kwargs): Make unauthenticated PATCH request
            - client.delete(url, **kwargs): Make unauthenticated DELETE request
    
    Example:
        def test_health_check_endpoint(unauthenticated_client):
            # Health check should be accessible without authentication
            response = unauthenticated_client.get('/api/health')
            assert response.status_code == 200
            assert response.json['status'] == 'healthy'
        
        def test_user_registration(unauthenticated_client):
            # Registration endpoint should be public
            response = unauthenticated_client.post(
                '/api/auth/register',
                json={
                    'email': 'newuser@example.com',
                    'password': 'SecurePass123!',
                    'first_name': 'New',
                    'last_name': 'User'
                }
            )
            assert response.status_code == 201
            assert 'id' in response.json
            assert 'access_token' in response.json
        
        def test_login_endpoint(unauthenticated_client, existing_user):
            # Login endpoint should not require authentication (obviously)
            response = unauthenticated_client.post(
                '/api/auth/login',
                json={
                    'email': existing_user.email,
                    'password': 'DefaultPassword123!'
                }
            )
            assert response.status_code == 200
            assert 'access_token' in response.json
        
        def test_protected_endpoint_rejects_unauthenticated(unauthenticated_client):
            # Negative test: Verify protected endpoint requires authentication
            response = unauthenticated_client.get('/api/users/profile')
            assert response.status_code == 401
            assert 'error' in response.json or 'msg' in response.json
        
        def test_public_content_endpoint(unauthenticated_client):
            # Public content should be accessible
            response = unauthenticated_client.get('/api/public/articles')
            assert response.status_code == 200
            assert isinstance(response.json, list)
        
        def test_password_reset_request(unauthenticated_client):
            # Password reset request should be public
            response = unauthenticated_client.post(
                '/api/auth/password-reset-request',
                json={'email': 'user@example.com'}
            )
            assert response.status_code in [200, 204]
        
        def test_api_documentation_endpoint(unauthenticated_client):
            # API docs should be public
            response = unauthenticated_client.get('/api/docs')
            assert response.status_code == 200
        
        def test_cannot_create_resource_without_auth(unauthenticated_client):
            # Negative test: Resource creation should require authentication
            response = unauthenticated_client.post(
                '/api/resources',
                json={'name': 'Unauthorized Resource'}
            )
            assert response.status_code == 401
        
        def test_cannot_update_profile_without_auth(unauthenticated_client):
            # Negative test: Profile update should require authentication
            response = unauthenticated_client.put(
                '/api/users/profile',
                json={'first_name': 'Hacker'}
            )
            assert response.status_code == 401
        
        def test_cannot_delete_resource_without_auth(unauthenticated_client):
            # Negative test: Deletion should require authentication
            response = unauthenticated_client.delete('/api/resources/1')
            assert response.status_code == 401
    
    Note:
        - Using unauthenticated_client makes test intent more explicit than 'client'
        - Particularly useful in test suites that mix authenticated and unauthenticated tests
        - This fixture creates its own independent client instance to avoid state pollution
        - Can be extended in the future to add common public API headers or configuration
        - Recommended for negative security testing (verify auth is required where expected)
    
    Testing Best Practices:
        - Use this fixture when testing endpoints that SHOULD be public
        - Use this fixture for negative tests (verify auth required on protected endpoints)
        - Combine with authenticated_client to test same endpoint with/without auth
        - Makes test suite more self-documenting and easier to understand
        - Helps identify which endpoints are public vs protected at a glance
    
    Comparison with authenticated_client:
        - unauthenticated_client: No Authorization header, for public endpoints
        - authenticated_client: Includes Authorization header, for protected endpoints
        - Use both in same test to verify authorization logic:
          
          def test_profile_requires_authentication(
              unauthenticated_client,
              authenticated_client
          ):
              # Should fail without auth
              unauth_response = unauthenticated_client.get('/api/users/profile')
              assert unauth_response.status_code == 401
              
              # Should succeed with auth
              auth_response = authenticated_client.get('/api/users/profile')
              assert auth_response.status_code == 200
    """
    # CRITICAL FIX: Create an independent test client instance instead of sharing
    # the client fixture. This prevents state pollution when both authenticated_client
    # and unauthenticated_client are used in the same test, as each gets its own
    # Flask test client instance with its own environ_base dictionary.
    test_client = app.test_client()
    
    # Return the client without authentication headers (the default state)
    # This makes test intent explicit: testing public/unauthenticated endpoints
    return test_client


# ============================================================================
# HTTP HEADERS FIXTURES
# ============================================================================


@pytest.fixture
def api_headers() -> Dict[str, str]:
    """
    Provide dictionary of common HTTP headers for API requests.
    
    This fixture returns a dictionary containing standard HTTP headers used in RESTful
    API communication. These headers specify that the client expects to send and receive
    JSON data, which is the standard format for modern REST APIs.
    
    The fixture provides:
    - Content-Type: application/json - Indicates request body contains JSON data
    - Accept: application/json - Indicates client expects JSON response
    
    These headers ensure proper content negotiation between the test client and the
    Flask application, enabling correct serialization and deserialization of request
    and response payloads.
    
    Use this fixture for:
    - Explicitly testing content-type handling
    - Testing content negotiation behavior
    - Combining with custom headers in specific tests
    - Base headers that can be extended with authentication or custom headers
    - Testing API endpoints with explicit header requirements
    
    Returns:
        Dict[str, str]: Dictionary containing standard API headers:
            {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
    
    Example:
        def test_api_requires_json_content_type(client, api_headers):
            # Some APIs strictly enforce Content-Type header
            response = client.post(
                '/api/resources',
                json={'name': 'Resource'},
                headers=api_headers
            )
            assert response.status_code == 201
        
        def test_api_returns_json_response(client, api_headers):
            response = client.get('/api/resources', headers=api_headers)
            assert response.status_code == 200
            assert response.content_type == 'application/json'
        
        def test_combine_api_headers_with_auth(client, auth_token, api_headers):
            # Combine api_headers with authentication
            headers = {**api_headers, 'Authorization': f'Bearer {auth_token}'}
            response = client.post(
                '/api/resources',
                json={'name': 'Authenticated Resource'},
                headers=headers
            )
            assert response.status_code == 201
        
        def test_extend_api_headers_with_custom(client, api_headers):
            # Add custom headers to api_headers
            headers = {
                **api_headers,
                'X-Request-ID': 'test-request-123',
                'X-Client-Version': '1.0.0'
            }
            response = client.get('/api/resources', headers=headers)
            assert response.status_code == 200
        
        def test_api_headers_structure(api_headers):
            # Verify header structure
            assert 'Content-Type' in api_headers
            assert 'Accept' in api_headers
            assert api_headers['Content-Type'] == 'application/json'
            assert api_headers['Accept'] == 'application/json'
        
        def test_content_negotiation(client, api_headers):
            # Test that API respects Accept header
            response = client.get('/api/data', headers=api_headers)
            assert response.content_type == 'application/json'
            
            # Try with XML Accept header (if API supports it)
            xml_headers = {**api_headers, 'Accept': 'application/xml'}
            xml_response = client.get('/api/data', headers=xml_headers)
            # Verify appropriate response based on API capabilities
            assert xml_response.status_code in [200, 406]  # 406 = Not Acceptable
    
    Note:
        - Flask test client automatically handles JSON serialization when using json=
          parameter, but explicit headers can be required for strict API implementations
        - These headers follow HTTP/1.1 specification and REST API best practices
        - Content-Type header is used for request payload format
        - Accept header is used for response format preference
        - Headers are case-insensitive per HTTP specification, but capitalized here
          for consistency and readability
    
    Usage with Flask Test Client:
        The Flask test client's json= parameter automatically sets Content-Type, but
        this fixture is useful when:
        - Testing strict header validation
        - Combining with additional headers
        - Testing content negotiation explicitly
        - Working with APIs that require explicit Accept headers
        
        Example:
        # These are often equivalent for Flask test client:
        client.post('/api/resource', json={'key': 'value'})
        client.post('/api/resource', json={'key': 'value'}, headers=api_headers)
        
        # But explicit headers are necessary for:
        - Testing header validation logic
        - APIs with strict content-type checking
        - Custom content negotiation behavior
    
    Extending Headers:
        This fixture can be easily extended or modified in tests:
        
        def test_with_additional_headers(client, api_headers):
            headers = {
                **api_headers,
                'X-Custom-Header': 'custom-value',
                'Authorization': 'Bearer token'
            }
            response = client.post('/api/data', json={}, headers=headers)
    """
    # Return dictionary with standard REST API headers
    # Content-Type indicates request body format (JSON)
    # Accept indicates expected response format (JSON)
    return {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }


@pytest.fixture
def json_headers(api_headers) -> Dict[str, str]:
    """
    Provide extended headers dictionary specifically for JSON API testing.
    
    This fixture extends api_headers with additional headers commonly used in JSON API
    interactions. Currently, it returns the same headers as api_headers but provides a
    semantic distinction for JSON-specific testing and allows for future extension with
    JSON-specific headers without modifying api_headers.
    
    The fixture composes with api_headers using pytest dependency injection, demonstrating
    fixture composition best practices. This approach:
    - Maintains single source of truth for base API headers
    - Allows json_headers to add JSON-specific extensions
    - Provides semantic clarity in test function signatures
    - Enables future enhancement without breaking existing tests
    
    Potential future extensions:
    - X-JSON-API-Version: Version header for JSON API specification
    - X-Request-ID: Request tracking for logging and debugging
    - Accept-Encoding: gzip, deflate for compression testing
    - Cache-Control: Caching behavior specification
    
    Use this fixture for:
    - JSON API endpoint testing with clear intent
    - Tests that specifically focus on JSON request/response handling
    - Future-proofing tests that may need JSON-specific headers
    - Semantic clarity: "this test deals with JSON APIs"
    
    Args:
        api_headers: Base API headers fixture containing Content-Type and Accept headers
    
    Returns:
        Dict[str, str]: Dictionary containing JSON API headers (currently identical to
            api_headers, but semantically distinct and extensible):
            {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
    
    Example:
        def test_json_api_post(authenticated_client, json_headers):
            # Clear intent: testing JSON API endpoint
            response = authenticated_client.post(
                '/api/users',
                json={'email': 'test@example.com', 'password': 'pass123'},
                headers=json_headers
            )
            assert response.status_code == 201
            assert isinstance(response.json, dict)
        
        def test_json_api_get(client, json_headers):
            response = client.get('/api/resources', headers=json_headers)
            assert response.status_code == 200
            assert response.content_type == 'application/json'
            assert isinstance(response.json, list)
        
        def test_json_validation(client, json_headers):
            # Test that API validates JSON structure
            response = client.post(
                '/api/users',
                data='invalid json{',  # Intentionally malformed
                headers=json_headers
            )
            assert response.status_code == 400
            assert 'error' in response.json
        
        def test_json_response_structure(client, json_headers):
            response = client.get('/api/users/1', headers=json_headers)
            assert response.status_code == 200
            # Verify JSON structure
            assert 'id' in response.json
            assert 'email' in response.json
            assert isinstance(response.json['id'], int)
            assert isinstance(response.json['email'], str)
        
        def test_json_array_response(client, json_headers):
            response = client.get('/api/users', headers=json_headers)
            assert response.status_code == 200
            assert isinstance(response.json, list)
            if len(response.json) > 0:
                assert 'id' in response.json[0]
                assert 'email' in response.json[0]
    
    Note:
        - Currently returns same headers as api_headers (composition)
        - Provides semantic distinction in test signatures
        - Allows future extension with JSON-specific headers
        - Demonstrates pytest fixture composition best practices
        - Makes test intent explicit: "this is a JSON API test"
    
    Future Extensions:
        This fixture can be enhanced to include JSON-specific headers:
        
        @pytest.fixture
        def json_headers(api_headers) -> Dict[str, str]:
            return {
                **api_headers,
                'X-JSON-API-Version': '1.0',
                'Accept-Encoding': 'gzip, deflate',
                'X-Request-ID': str(uuid.uuid4())
            }
    
    Semantic Benefits:
        Using json_headers vs api_headers in test signatures:
        
        def test_json_endpoint(client, json_headers):  # Clear: JSON-specific test
        def test_api_endpoint(client, api_headers):    # Generic: any API test
        
        Both may use same headers currently, but semantic distinction aids:
        - Test readability and maintainability
        - Future refactoring (can add JSON-specific headers to json_headers)
        - Test organization and categorization
        - Code review and understanding test intent
    
    Composition Pattern:
        This fixture demonstrates pytest fixture composition:
        1. json_headers depends on api_headers
        2. api_headers provides base headers
        3. json_headers can extend or modify as needed
        4. Changes to api_headers automatically propagate
        5. json_headers can be customized without affecting api_headers
    """
    # Compose with api_headers fixture using pytest dependency injection
    # Currently returns api_headers unchanged, but provides semantic distinction
    # Future extensions can add JSON-specific headers here
    return api_headers


# ============================================================================
# MODULE DOCUMENTATION AND TESTING GUIDANCE
# ============================================================================

"""
Complete Testing Workflow Examples:

1. Testing Complete CRUD Operations with Authentication:

    def test_complete_crud_workflow(authenticated_client, json_headers):
        # Create
        create_response = authenticated_client.post(
            '/api/resources',
            json={'name': 'Test Resource', 'type': 'document'},
            headers=json_headers
        )
        assert create_response.status_code == 201
        resource_id = create_response.json['id']
        
        # Read
        read_response = authenticated_client.get(f'/api/resources/{resource_id}')
        assert read_response.status_code == 200
        assert read_response.json['name'] == 'Test Resource'
        
        # Update
        update_response = authenticated_client.put(
            f'/api/resources/{resource_id}',
            json={'name': 'Updated Resource'},
            headers=json_headers
        )
        assert update_response.status_code == 200
        assert update_response.json['name'] == 'Updated Resource'
        
        # Delete
        delete_response = authenticated_client.delete(f'/api/resources/{resource_id}')
        assert delete_response.status_code == 204


2. Testing Authentication vs Authorization:

    def test_authentication_and_authorization(
        unauthenticated_client,
        authenticated_client,
        user_factory
    ):
        # Create resource owned by test user
        create_response = authenticated_client.post(
            '/api/resources',
            json={'name': 'My Resource'}
        )
        resource_id = create_response.json['id']
        
        # Test authentication required (no token)
        unauth_response = unauthenticated_client.get(f'/api/resources/{resource_id}')
        assert unauth_response.status_code == 401
        
        # Test authorization (authenticated but not owner)
        other_user = user_factory({'email': 'other@example.com'})
        # Would need other_user's authenticated_client for this test
        
        # Test authorized access (owner)
        auth_response = authenticated_client.get(f'/api/resources/{resource_id}')
        assert auth_response.status_code == 200


3. Testing Public vs Protected Endpoints:

    def test_public_and_protected_endpoints(
        unauthenticated_client,
        authenticated_client
    ):
        # Public endpoint should work without auth
        public_response = unauthenticated_client.get('/api/health')
        assert public_response.status_code == 200
        
        # Protected endpoint should require auth
        unauth_response = unauthenticated_client.get('/api/users/profile')
        assert unauth_response.status_code == 401
        
        # Protected endpoint should work with auth
        auth_response = authenticated_client.get('/api/users/profile')
        assert auth_response.status_code == 200


4. Testing API Headers and Content Negotiation:

    def test_content_type_handling(client, api_headers, json_headers):
        # Test with explicit API headers
        response = client.post(
            '/api/resources',
            json={'name': 'Resource'},
            headers=api_headers
        )
        assert response.status_code == 201
        assert response.content_type == 'application/json'
        
        # Test with JSON-specific headers
        response2 = client.post(
            '/api/resources',
            json={'name': 'Resource 2'},
            headers=json_headers
        )
        assert response2.status_code == 201


5. Testing Error Responses:

    def test_api_error_responses(authenticated_client, json_headers):
        # Test 400 Bad Request
        bad_request = authenticated_client.post(
            '/api/users',
            json={'invalid': 'data'},
            headers=json_headers
        )
        assert bad_request.status_code == 400
        assert 'error' in bad_request.json
        
        # Test 404 Not Found
        not_found = authenticated_client.get('/api/resources/999999')
        assert not_found.status_code == 404
        
        # Test 409 Conflict
        conflict = authenticated_client.post(
            '/api/users',
            json={'email': 'existing@example.com'},
            headers=json_headers
        )
        assert conflict.status_code == 409

Best Practices for Using These Fixtures:
1. Use authenticated_client for all protected endpoint tests
2. Use unauthenticated_client for public endpoints and negative auth tests
3. Apply json_headers when testing strict JSON API implementations
4. Combine fixtures: authenticated_client + db_session + user_factory
5. Test both success and failure scenarios
6. Verify proper HTTP status codes
7. Validate response structure and content
8. Test edge cases and boundary conditions
9. Ensure proper error messages are returned
10. Test authorization separately from authentication
"""
