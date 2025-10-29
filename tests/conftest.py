"""
Pytest Configuration and Shared Fixtures Module

This module provides comprehensive pytest configuration and shared fixtures for the Flask
application test suite. It implements the testing infrastructure required for the Node.js
to Flask migration project, ensuring proper test isolation, database management, and
reusable test utilities.

The module provides:
- Flask application factory fixture for creating test app instances
- Database session fixtures with automatic setup, teardown, and transaction rollback
- Flask test client fixtures for HTTP request testing
- Application and request context fixtures for testing Flask-specific functionality
- Authentication fixtures for testing protected endpoints
- Custom pytest markers for test categorization
- Environment configuration loading from .env.test

Fixtures are designed to be composable and follow pytest best practices with proper
scoping (function, class, module, session) for optimal test performance and isolation.

Core Fixtures:
    - app: Session-scoped Flask application configured for testing
    - db_session: Function-scoped database session with automatic rollback
    - client: Function-scoped Flask test client for HTTP testing
    - app_context: Function-scoped application context manager
    - authenticated_client: Test client with authentication headers configured

Usage Example:
    def test_user_creation(client, db_session):
        response = client.post('/api/users', json={'email': 'test@example.com'})
        assert response.status_code == 201
        
    def test_protected_endpoint(authenticated_client):
        response = authenticated_client.get('/api/protected')
        assert response.status_code == 200
"""

import os
import sys
import pytest
from dotenv import load_dotenv


# Load test environment variables from .env.test file
# This must be done before importing Flask application to ensure
# test configuration is properly loaded
load_dotenv('.env.test')


# Configure pytest markers for test categorization
# These markers allow running specific test subsets and provide metadata
def pytest_configure(config):
    """
    Configure pytest with custom markers for test categorization.
    
    This hook is called during pytest initialization and registers custom markers
    that can be used to tag and filter tests. Tests can be marked with decorators
    like @pytest.mark.unit, @pytest.mark.integration, etc.
    
    Args:
        config: Pytest configuration object
    
    Registered Markers:
        unit: Fast, isolated unit tests with mocked dependencies
        integration: Integration tests involving multiple components or database
        functional: End-to-end functional tests covering complete workflows
        slow: Tests that take longer than 1 second to execute
        smoke: Critical smoke tests that should always pass
        api: API endpoint tests using Flask test client
        database: Tests requiring database operations
        external: Tests involving external services (should be mocked)
    """
    config.addinivalue_line(
        "markers", "unit: Unit tests (fast, isolated, mocked dependencies)"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests (multiple components, database)"
    )
    config.addinivalue_line(
        "markers", "functional: Functional tests (end-to-end workflows)"
    )
    config.addinivalue_line(
        "markers", "slow: Tests that take longer than 1 second"
    )
    config.addinivalue_line(
        "markers", "smoke: Critical smoke tests"
    )
    config.addinivalue_line(
        "markers", "api: API endpoint tests"
    )
    config.addinivalue_line(
        "markers", "database: Tests requiring database operations"
    )
    config.addinivalue_line(
        "markers", "external: Tests involving external services (mocked)"
    )


# ============================================================================
# CORE APPLICATION FIXTURES
# ============================================================================


@pytest.fixture(scope='session')
def app():
    """
    Create and configure a Flask application instance for testing (session scope).
    
    This fixture creates a Flask application using the application factory pattern
    with TestConfig configuration. It's session-scoped, meaning the application
    instance is created once per test session and reused across all tests for
    performance optimization.
    
    The application is configured with:
    - In-memory SQLite database for fast, isolated testing
    - Disabled CSRF protection for easier API testing
    - Test-specific secret keys
    - Testing mode enabled (TESTING=True)
    
    Yields:
        Flask: Fully configured Flask application instance for testing.
            Provides access to app.config, app.test_client(), app.app_context(),
            and app.test_request_context() for comprehensive testing capabilities.
    
    Example:
        def test_app_configuration(app):
            assert app.config['TESTING'] is True
            assert app.config['SQLALCHEMY_DATABASE_URI'] == 'sqlite:///:memory:'
    """
    # Import create_app from the application factory module
    from app import create_app
    
    # Create Flask application with testing configuration
    # The 'testing' parameter tells create_app to load TestConfig
    test_app = create_app('testing')
    
    # Establish application context for the entire test session
    # This makes the app available throughout the test session
    with test_app.app_context():
        yield test_app


@pytest.fixture(scope='function')
def app_context(app):
    """
    Provide Flask application context for tests requiring app-level access.
    
    This fixture creates an application context for the duration of a single test
    function. The application context is required for operations that need access
    to Flask's current_app, g, or other application-level globals.
    
    The fixture is function-scoped, ensuring each test gets a fresh context and
    proper isolation from other tests.
    
    Args:
        app: The Flask application fixture (session-scoped)
    
    Yields:
        Flask application context manager that provides access to app-level globals
        and configuration during test execution.
    
    Example:
        def test_with_app_context(app_context):
            from flask import current_app
            assert current_app.config['TESTING'] is True
    """
    with app.app_context():
        yield


# ============================================================================
# DATABASE FIXTURES
# ============================================================================


@pytest.fixture(scope='function')
def db_session(app):
    """
    Provide a database session with automatic setup, teardown, and transaction rollback.
    
    This fixture creates a fresh database for each test function, ensuring complete
    test isolation. It performs the following operations:
    
    1. Setup: Creates all database tables using db.create_all()
    2. Yield: Provides db.session for test use
    3. Teardown: Rolls back any uncommitted transactions using db.session.rollback()
    4. Cleanup: Drops all tables using db.drop_all()
    
    The fixture is function-scoped, meaning each test gets a completely fresh database
    with no persistent state from previous tests. This ensures test independence and
    prevents test pollution.
    
    Args:
        app: The Flask application fixture (provides app context)
    
    Yields:
        SQLAlchemy database session (db.session) with the following methods available:
        - db.session.add(): Add object to session
        - db.session.commit(): Commit transaction
        - db.session.rollback(): Rollback transaction
        - db.session.delete(): Delete object from session
        - db.session.query(): Query database
    
    Example:
        def test_user_creation(db_session):
            from app.models import User
            user = User(email='test@example.com', password='hashed_password')
            db_session.add(user)
            db_session.commit()
            
            assert user.id is not None
            assert User.query.filter_by(email='test@example.com').first() == user
    """
    # Import database instance from extensions module
    from app.extensions import db
    from tests.factories.base_factory import BaseFactory
    
    # Ensure we're within application context
    # create_all() requires application context to access database URI
    with app.app_context():
        # Create all database tables defined in models
        # This includes all tables from SQLAlchemy models with __tablename__
        db.create_all()
        
        # Configure factory_boy factories to use this database session
        # This allows UserFactory and other factories to work seamlessly in tests
        BaseFactory.set_session(db.session)
        
        # Yield the database session for test usage
        # Tests can now use db.session to interact with the database
        yield db.session
        
        # Teardown: Rollback any uncommitted transactions
        # This ensures no test changes persist and maintains test isolation
        db.session.rollback()
        
        # Cleanup: Drop all database tables
        # This provides a completely clean slate for the next test
        db.drop_all()
        
        # Cleanup: Clear factory session to prevent stale references
        BaseFactory.set_session(None)



@pytest.fixture(scope='function')
def empty_db(app):
    """
    Provide an empty database with tables created but no data.
    
    This fixture is similar to db_session but explicitly emphasizes that the
    database starts empty. Useful for tests that need to verify behavior with
    no existing data or tests that populate specific test data.
    
    Args:
        app: The Flask application fixture
    
    Yields:
        SQLAlchemy database session for an empty database
    
    Example:
        def test_first_user_registration(empty_db):
            from app.models import User
            # Verify no users exist
            assert User.query.count() == 0
    """
    from app.extensions import db
    
    with app.app_context():
        db.create_all()
        yield db.session
        db.session.rollback()
        db.drop_all()


# ============================================================================
# FLASK TEST CLIENT FIXTURES
# ============================================================================


@pytest.fixture(scope='function')
def client(app):
    """
    Provide Flask test client for making HTTP requests to the application.
    
    This fixture creates a test client that can be used to make requests to the
    Flask application without running an actual HTTP server. The test client
    simulates HTTP requests and returns response objects with status codes,
    headers, and data.
    
    The test client supports all HTTP methods (GET, POST, PUT, DELETE, PATCH)
    and handles JSON serialization/deserialization automatically.
    
    Args:
        app: The Flask application fixture
    
    Yields:
        FlaskClient: Test client with the following methods:
        - client.get(url, **kwargs): Make GET request
        - client.post(url, json=data, **kwargs): Make POST request with JSON
        - client.put(url, json=data, **kwargs): Make PUT request with JSON
        - client.delete(url, **kwargs): Make DELETE request
        - client.patch(url, json=data, **kwargs): Make PATCH request with JSON
    
    Example:
        def test_user_api(client):
            response = client.post('/api/users', json={
                'email': 'test@example.com',
                'password': 'SecurePass123'
            })
            assert response.status_code == 201
            assert 'id' in response.json
    """
    # Create test client using Flask's built-in test_client() method
    # Using context manager ensures proper setup and teardown
    with app.test_client() as test_client:
        yield test_client


@pytest.fixture(scope='function')
def authenticated_client(app, client, db_session):
    """
    Provide Flask test client with authentication headers pre-configured.
    
    This fixture extends the standard client fixture by adding authentication
    headers (typically a JWT token) to the test client. This is useful for
    testing protected endpoints that require authentication without having to
    manually authenticate in every test.
    
    The fixture performs the following:
    1. Creates a test user in the database
    2. Generates an authentication token (JWT) for the user
    3. Configures the client with Authorization header
    4. Returns the authenticated client
    
    Args:
        app: The Flask application fixture
        client: The Flask test client fixture
        db_session: The database session fixture
    
    Yields:
        FlaskClient: Test client with authentication headers configured.
            All requests made with this client will include the Authorization header.
    
    Example:
        def test_protected_endpoint(authenticated_client):
            response = authenticated_client.get('/api/users/profile')
            assert response.status_code == 200
            assert 'email' in response.json
    
    Note:
        This fixture creates a default test user. For tests requiring specific
        user roles or permissions, create custom authentication fixtures.
    """
    # This is a basic implementation that can be extended based on
    # the specific authentication mechanism used in the application
    
    # Import necessary modules for user creation and token generation
    # Note: Actual imports will depend on your authentication implementation
    try:
        from app.models import User
        from flask_jwt_extended import create_access_token
        
        # Create a test user
        test_user = User(
            email='test_user@example.com',
            # Note: Ensure password is properly hashed if User model requires it
        )
        
        # Add user to database
        db_session.add(test_user)
        db_session.commit()
        
        # Generate access token for the test user
        access_token = create_access_token(identity=test_user.id)
        
        # Configure client with Authorization header
        client.environ_base['HTTP_AUTHORIZATION'] = f'Bearer {access_token}'
        
        yield client
        
    except ImportError:
        # If User model or JWT components not available, return unauthenticated client
        # This allows tests to run even if authentication isn't fully implemented yet
        yield client


# ============================================================================
# CLI TEST FIXTURES
# ============================================================================


@pytest.fixture(scope='function')
def runner(app):
    """
    Provide Flask CLI test runner for testing command-line interface commands.
    
    This fixture creates a test runner that can be used to test Flask CLI commands
    without actually executing them in a shell. Useful for testing custom Flask
    commands, database migrations, and other CLI operations.
    
    Args:
        app: The Flask application fixture
    
    Returns:
        FlaskCliRunner: Test runner for CLI commands with invoke() method
    
    Example:
        def test_custom_cli_command(runner):
            result = runner.invoke(args=['custom-command', '--option', 'value'])
            assert result.exit_code == 0
            assert 'Success' in result.output
    """
    return app.test_cli_runner()


# ============================================================================
# REQUEST CONTEXT FIXTURES
# ============================================================================


@pytest.fixture(scope='function')
def request_context(app):
    """
    Provide Flask request context for tests requiring request-level access.
    
    This fixture creates a request context for tests that need access to Flask's
    request object, session, or other request-level globals. The request context
    is required for operations like url_for(), request.args, request.form, etc.
    
    Args:
        app: The Flask application fixture
    
    Yields:
        Flask request context manager
    
    Example:
        def test_with_request_context(request_context):
            from flask import request, url_for
            with request_context:
                assert request.method == 'GET'
                url = url_for('users.get_user', user_id=1)
                assert '/api/users/1' in url
    """
    with app.test_request_context():
        yield


# ============================================================================
# PYTEST HOOKS FOR ENHANCED TEST REPORTING
# ============================================================================


def pytest_collection_modifyitems(config, items):
    """
    Modify collected test items to add markers and configure test execution.
    
    This hook is called after test collection and allows modification of test
    items before execution. It automatically adds markers based on test location
    and name patterns, ensuring consistent test categorization.
    
    Args:
        config: Pytest configuration object
        items: List of collected test items
    
    Behavior:
        - Tests in tests/unit/ automatically get @pytest.mark.unit
        - Tests in tests/integration/ automatically get @pytest.mark.integration
        - Tests in tests/functional/ automatically get @pytest.mark.functional
        - Tests with 'slow' in name get @pytest.mark.slow
        - Tests with 'api' in path get @pytest.mark.api
        - Tests with 'db' or 'database' in path get @pytest.mark.database
    """
    for item in items:
        # Get the test file path relative to the tests directory
        test_path = str(item.fspath)
        
        # Automatically mark tests based on directory structure
        if '/unit/' in test_path or '\\unit\\' in test_path:
            item.add_marker(pytest.mark.unit)
        
        if '/integration/' in test_path or '\\integration\\' in test_path:
            item.add_marker(pytest.mark.integration)
        
        if '/functional/' in test_path or '\\functional\\' in test_path:
            item.add_marker(pytest.mark.functional)
        
        # Mark tests that involve API testing
        if '/routes/' in test_path or '\\routes\\' in test_path or 'api' in test_path.lower():
            item.add_marker(pytest.mark.api)
        
        # Mark tests that involve database operations
        if 'db' in test_path.lower() or 'database' in test_path.lower() or '/models/' in test_path:
            item.add_marker(pytest.mark.database)
        
        # Mark tests with 'slow' in their name
        if 'slow' in item.name.lower():
            item.add_marker(pytest.mark.slow)


def pytest_sessionstart(session):
    """
    Called after the Session object has been created and before performing collection.
    
    This hook can be used to perform setup operations that should happen once at the
    beginning of the entire test session, such as:
    - Setting up test environment variables
    - Initializing logging configuration
    - Creating necessary test directories
    
    Args:
        session: Pytest session object
    """
    # Ensure test environment is properly configured
    os.environ['FLASK_ENV'] = 'testing'
    os.environ['TESTING'] = 'True'
    
    # Log test session start
    print("\n" + "=" * 70)
    print("Starting Flask Test Suite")
    print("=" * 70)


def pytest_sessionfinish(session, exitstatus):
    """
    Called after whole test run finished, right before returning the exit status.
    
    This hook can be used to perform cleanup operations or generate test reports
    after all tests have completed.
    
    Args:
        session: Pytest session object
        exitstatus: The status which pytest will return to the system
    """
    # Log test session completion
    print("\n" + "=" * 70)
    print(f"Test Suite Completed with exit status: {exitstatus}")
    print("=" * 70 + "\n")


# ============================================================================
# UTILITY FUNCTIONS FOR TEST FIXTURES
# ============================================================================


def create_test_user(db_session, email='test@example.com', **kwargs):
    """
    Utility function to create a test user with default or custom attributes.
    
    This helper function simplifies test user creation by providing sensible
    defaults while allowing customization for specific test scenarios.
    
    Args:
        db_session: SQLAlchemy database session
        email (str): User email address (default: 'test@example.com')
        **kwargs: Additional user attributes to override defaults
    
    Returns:
        User: Created user instance with all attributes set
    
    Example:
        def test_user_creation(db_session):
            user = create_test_user(db_session, email='custom@example.com')
            assert user.id is not None
            assert user.email == 'custom@example.com'
    
    Note:
        This function will be fully implemented once User model is available.
        Currently provides structure for future implementation.
    """
    try:
        from app.models import User
        
        # Default user attributes
        user_data = {
            'email': email,
            'password': 'TestPassword123!',  # Should be hashed by User model
            'first_name': kwargs.get('first_name', 'Test'),
            'last_name': kwargs.get('last_name', 'User'),
        }
        
        # Override defaults with any provided kwargs
        user_data.update(kwargs)
        
        # Create user instance
        user = User(**user_data)
        
        # Add to database session and commit
        db_session.add(user)
        db_session.commit()
        
        return user
        
    except ImportError:
        # User model not yet implemented
        # Return None to allow tests to handle gracefully
        return None


def get_auth_headers(user_id=1):
    """
    Generate authentication headers for API requests.
    
    This utility function creates JWT authentication headers that can be
    passed to the test client for authenticated requests.
    
    Args:
        user_id (int): User ID to generate token for (default: 1)
    
    Returns:
        dict: Dictionary containing Authorization header with Bearer token
    
    Example:
        def test_protected_route(client, db_session):
            user = create_test_user(db_session)
            headers = get_auth_headers(user.id)
            response = client.get('/api/protected', headers=headers)
            assert response.status_code == 200
    
    Note:
        This function will be fully implemented once JWT authentication is available.
    """
    try:
        from flask_jwt_extended import create_access_token
        
        # Generate access token for user
        access_token = create_access_token(identity=user_id)
        
        # Return headers dictionary
        return {
            'Authorization': f'Bearer {access_token}'
        }
        
    except ImportError:
        # JWT not yet configured
        return {}


# ============================================================================
# MODULE-LEVEL CONFIGURATION
# ============================================================================


# Ensure Python path includes the parent directory for imports
# This allows tests to import from the app package
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


# Configure pytest plugins for additional functionality
# These plugins extend pytest capabilities with specialized features
pytest_plugins = [
    # Can add plugin references here if needed
    # Example: 'pytest_flask', 'pytest_asyncio', etc.
]
