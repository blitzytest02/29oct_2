"""
User Test Fixtures Module

This module provides comprehensive pytest fixtures for user-related test data,
supporting all user testing scenarios including creation, validation, CRUD operations,
authentication, and authorization testing.

The fixtures follow pytest best practices with proper dependency injection,
automatic setup/teardown, and reusable test data patterns. They integrate
seamlessly with the db_session fixture for database operations and use the
Faker library for generating realistic test data.

Fixtures Provided:
    Data Fixtures (dictionaries):
        - valid_user_data: Dictionary with valid user attributes
        - invalid_user_data: Dictionary with invalid data for validation testing
        - user_with_minimum_fields: User data with only required fields
        - user_with_maximum_length_strings: User data at field length limits
    
    Model Instance Fixtures (User objects):
        - existing_user: Persisted User instance in test database
        - admin_user: User instance with admin role
        - multiple_users: List of multiple persisted User instances
    
    Factory Fixtures:
        - user_factory: Factory function for creating custom User instances

Usage Examples:
    # Test with valid user data dictionary
    def test_user_creation(client, valid_user_data):
        response = client.post('/api/users', json=valid_user_data)
        assert response.status_code == 201
    
    # Test with existing user from database
    def test_get_user(client, existing_user):
        response = client.get(f'/api/users/{existing_user.id}')
        assert response.status_code == 200
        assert response.json['email'] == existing_user.email
    
    # Test with multiple users for pagination
    def test_list_users(client, multiple_users):
        response = client.get('/api/users')
        assert response.status_code == 200
        assert len(response.json['users']) >= 5
    
    # Test with user factory for custom attributes
    def test_custom_user(db_session, user_factory):
        user = user_factory(email='custom@example.com', role='admin')
        assert user.email == 'custom@example.com'
        assert user.role == 'admin'
    
    # Test validation with invalid data
    def test_invalid_user(client, invalid_user_data):
        response = client.post('/api/users', json=invalid_user_data)
        assert response.status_code == 400

Notes:
    - All fixtures that create User instances require db_session fixture
    - User passwords are properly hashed using User.set_password()
    - Faker library generates realistic test data for diversity
    - Fixtures support edge cases, boundary conditions, and error scenarios
    - Factory pattern enables flexible test data creation with custom attributes
"""

from typing import Callable, Dict, Any, List
import pytest
from faker import Faker

from app.models import User


# Initialize Faker instance for generating realistic test data
# Using seed for reproducibility in tests while maintaining data diversity
fake = Faker()


# ============================================================================
# VALID USER DATA FIXTURES
# ============================================================================


@pytest.fixture
def valid_user_data() -> Dict[str, Any]:
    """
    Provide dictionary with valid user attributes for testing user creation.
    
    This fixture returns a dictionary containing all required and common optional
    fields for creating a valid user. The data satisfies all validation rules:
    - Valid email format (RFC 5321 compliant)
    - Strong password meeting all requirements (8+ chars, upper, lower, digit, special)
    - Valid first and last names
    - Default user role
    
    The fixture generates slightly varied data on each call using Faker to
    ensure test independence and catch edge cases related to data diversity.
    
    Returns:
        Dict[str, Any]: Dictionary containing:
            - email (str): Valid email address (unique per call)
            - password (str): Strong password meeting all requirements
            - first_name (str): Valid first name
            - last_name (str): Valid last name
            - role (str): Default 'user' role
    
    Example:
        def test_create_user_with_valid_data(client, valid_user_data):
            response = client.post('/api/users', json=valid_user_data)
            assert response.status_code == 201
            assert 'id' in response.json
            assert response.json['email'] == valid_user_data['email']
    
    Note:
        This returns plain password (not hashed) suitable for API requests.
        For creating User model instances directly, use existing_user fixture
        or user_factory which handle password hashing automatically.
    """
    return {
        'email': fake.email(),
        'password': 'SecurePass123!',  # Meets all password strength requirements
        'first_name': fake.first_name(),
        'last_name': fake.last_name(),
        'role': 'user'
    }


@pytest.fixture
def user_with_minimum_fields() -> Dict[str, Any]:
    """
    Provide user data with only required fields for edge case testing.
    
    This fixture returns a minimal valid user data dictionary containing only
    the absolutely required fields (email and password). Optional fields like
    first_name, last_name, and profile_picture are omitted to test that the
    system correctly handles users with minimal data.
    
    Use this fixture to test:
    - Minimum data requirements for user creation
    - Optional field handling (None/null values)
    - Edge cases where users have incomplete profiles
    - Default value population for optional fields
    
    Returns:
        Dict[str, Any]: Dictionary containing:
            - email (str): Valid email address
            - password (str): Strong password
    
    Example:
        def test_create_user_with_minimum_data(client, user_with_minimum_fields):
            response = client.post('/api/users', json=user_with_minimum_fields)
            assert response.status_code == 201
            # Optional fields should be None or default values
            assert response.json.get('first_name') is None
            assert response.json.get('last_name') is None
    """
    return {
        'email': fake.email(),
        'password': 'MinPass123!'  # Minimum valid password
    }


@pytest.fixture
def user_with_maximum_length_strings() -> Dict[str, Any]:
    """
    Provide user data at field length limits for boundary testing.
    
    This fixture tests the upper bounds of string field lengths to ensure
    proper validation and database schema compliance. Based on User model
    field definitions:
    - email: Max 254 characters (RFC 5321 maximum)
    - password: Max 128 characters (before hashing)
    - first_name: Max 100 characters
    - last_name: Max 100 characters
    - profile_picture: Max 500 characters (URL)
    
    Use this fixture to test:
    - Maximum field length validation
    - Database column width constraints
    - Input truncation or rejection behavior
    - UI display of long values
    
    Returns:
        Dict[str, Any]: Dictionary with maximum-length string values:
            - email (str): 254 character valid email
            - password (str): 128 character password
            - first_name (str): 100 character first name
            - last_name (str): 100 character last name
            - profile_picture (str): 500 character URL
    
    Example:
        def test_create_user_with_max_length_strings(client, user_with_maximum_length_strings):
            response = client.post('/api/users', json=user_with_maximum_length_strings)
            assert response.status_code == 201
            # Verify long strings are stored correctly
            user_data = response.json
            assert len(user_data['first_name']) == 100
    """
    # Generate maximum length email (254 chars total)
    # Format: local@domain.tld where total is exactly 254 characters
    local_part = 'a' * 64  # Maximum local part length (RFC 5321)
    # Domain part: 254 - 64 (local) - 1 (@) = 189 chars
    domain_part = 'b' * 180 + '.example'  # 189 chars total with .example
    max_email = f"{local_part}@{domain_part}.com"
    
    # Ensure email is exactly 254 characters
    if len(max_email) > 254:
        max_email = max_email[:254]
    
    # Generate maximum length password (128 chars) with all requirements
    # Must include upper, lower, digit, special for validation
    max_password = 'A' + 'a' * 100 + '1' * 20 + '!' * 6  # 128 chars total
    
    return {
        'email': max_email,
        'password': max_password,
        'first_name': 'F' * 100,  # Maximum first_name length
        'last_name': 'L' * 100,   # Maximum last_name length
        'profile_picture': 'https://example.com/' + 'p' * 476  # 500 chars total URL
    }


# ============================================================================
# INVALID USER DATA FIXTURES
# ============================================================================


@pytest.fixture
def invalid_user_data() -> Dict[str, Any]:
    """
    Provide dictionary with invalid user data for validation testing.
    
    This fixture returns user data that violates validation rules to test
    error handling, validation logic, and proper error responses. The data
    includes:
    - Invalid email format (missing @ symbol, no domain)
    - Weak password (too short, missing required character types)
    - Empty or overly long strings
    
    Use this fixture to test:
    - Email validation (format, domain, length)
    - Password strength validation
    - Required field validation
    - Proper error messages and status codes (400 Bad Request)
    - Input sanitization and XSS prevention
    
    Returns:
        Dict[str, Any]: Dictionary with intentionally invalid data:
            - email (str): Invalid email format (no @ or domain)
            - password (str): Weak password (fails strength requirements)
            - first_name (str): Empty string or invalid characters
            - last_name (str): Empty string or invalid characters
    
    Example:
        def test_create_user_with_invalid_email(client, invalid_user_data):
            response = client.post('/api/users', json=invalid_user_data)
            assert response.status_code == 400
            assert 'email' in response.json['errors']
            assert 'invalid format' in response.json['errors']['email'].lower()
        
        def test_create_user_with_weak_password(client, invalid_user_data):
            response = client.post('/api/users', json=invalid_user_data)
            assert response.status_code == 400
            assert 'password' in response.json['errors']
    """
    return {
        'email': 'invalid.email.com',  # Missing @ symbol
        'password': 'weak',             # Too short, no uppercase, no digits, no special
        'first_name': '',               # Empty string (if required)
        'last_name': '',                # Empty string (if required)
        'role': 'invalid_role'          # Invalid role not in VALID_ROLES
    }


# ============================================================================
# PERSISTED USER MODEL FIXTURES
# ============================================================================


@pytest.fixture
def existing_user(db_session) -> User:
    """
    Create and persist a User instance to the test database.
    
    This fixture creates a complete User model instance with all standard
    attributes, properly hashed password, and persists it to the database.
    The user is created with default values suitable for general testing
    scenarios and is automatically cleaned up after the test completes.
    
    The fixture uses Faker to generate varied data, ensuring each test run
    has slightly different user data to catch edge cases and prevent tests
    from depending on specific values.
    
    Args:
        db_session: Database session fixture from conftest.py that provides
            database access with automatic setup, teardown, and rollback.
    
    Returns:
        User: Persisted User model instance with:
            - id: Auto-generated primary key (not None after commit)
            - email: Unique valid email address
            - password_hash: Securely hashed password (via set_password)
            - first_name: Realistic first name
            - last_name: Realistic last name
            - role: 'user' (default role)
            - is_active: True (active account)
            - created_at: Current timestamp
            - updated_at: Current timestamp
    
    Example:
        def test_get_user_by_id(client, existing_user):
            response = client.get(f'/api/users/{existing_user.id}')
            assert response.status_code == 200
            assert response.json['email'] == existing_user.email
        
        def test_update_user(client, existing_user):
            response = client.put(
                f'/api/users/{existing_user.id}',
                json={'first_name': 'Updated'}
            )
            assert response.status_code == 200
            assert response.json['first_name'] == 'Updated'
        
        def test_user_password_verification(existing_user):
            # Test password hashing and verification
            assert existing_user.check_password('DefaultPassword123!')
            assert not existing_user.check_password('WrongPassword')
    
    Note:
        The password is set to 'DefaultPassword123!' and can be verified
        using existing_user.check_password('DefaultPassword123!').
        Use this default password for authentication flow testing.
    """
    # Create User instance with Faker-generated realistic data
    user = User(
        email=fake.email(),
        first_name=fake.first_name(),
        last_name=fake.last_name(),
        role='user',
        is_active=True
    )
    
    # Set password securely using User model's set_password method
    # This hashes the password using Werkzeug's generate_password_hash
    user.set_password('DefaultPassword123!')
    
    # Add user to database session and commit to persist
    db_session.add(user)
    db_session.commit()
    
    # Refresh to ensure all database-generated fields (id, timestamps) are loaded
    db_session.refresh(user)
    
    return user


@pytest.fixture
def admin_user(db_session) -> User:
    """
    Create and persist a User instance with admin role for authorization testing.
    
    This fixture creates a User with the 'admin' role, enabling tests for
    role-based access control, privileged operations, and admin-specific
    functionality. The admin user has the same structure as a regular user
    but with elevated permissions.
    
    Use this fixture to test:
    - Admin-only API endpoints
    - Role-based authorization middleware
    - Permission checks for privileged operations
    - Admin user management capabilities
    - Audit logging of admin actions
    
    Args:
        db_session: Database session fixture for persistence
    
    Returns:
        User: Persisted admin User instance with:
            - role: 'admin' (elevated permissions)
            - is_active: True
            - All other standard User attributes
    
    Example:
        def test_admin_can_delete_users(client, admin_user, existing_user):
            # Admin should be able to delete other users
            token = generate_token(admin_user)
            headers = {'Authorization': f'Bearer {token}'}
            response = client.delete(
                f'/api/users/{existing_user.id}',
                headers=headers
            )
            assert response.status_code == 204
        
        def test_admin_can_view_all_users(client, admin_user):
            token = generate_token(admin_user)
            headers = {'Authorization': f'Bearer {token}'}
            response = client.get('/api/admin/users', headers=headers)
            assert response.status_code == 200
        
        def test_regular_user_cannot_access_admin_endpoint(client, existing_user):
            token = generate_token(existing_user)
            headers = {'Authorization': f'Bearer {token}'}
            response = client.get('/api/admin/users', headers=headers)
            assert response.status_code == 403  # Forbidden
    """
    # Create admin user with distinct email pattern for easy identification
    admin = User(
        email=f'admin_{fake.user_name()}@example.com',
        first_name=fake.first_name(),
        last_name=fake.last_name(),
        role='admin',  # Admin role for elevated permissions
        is_active=True
    )
    
    # Set strong password for admin account
    admin.set_password('AdminPassword123!')
    
    # Persist to database
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)
    
    return admin


@pytest.fixture
def multiple_users(db_session) -> List[User]:
    """
    Create and persist multiple User instances for batch testing scenarios.
    
    This fixture creates a list of 5 diverse users with varied attributes,
    enabling tests for pagination, list endpoints, search functionality,
    and bulk operations. Each user has unique data generated by Faker to
    ensure realistic and diverse test scenarios.
    
    The users include a mix of:
    - Different roles (user, admin)
    - Different active states (active, inactive)
    - Varied profile completeness (some with all fields, some minimal)
    - Diverse names and emails
    
    Use this fixture to test:
    - User listing and pagination
    - Search and filtering operations
    - Batch operations (bulk delete, bulk update)
    - Performance with multiple records
    - Sorting and ordering
    
    Args:
        db_session: Database session fixture for persistence
    
    Returns:
        List[User]: List of 5 persisted User instances with diverse attributes
    
    Example:
        def test_list_users_pagination(client, multiple_users):
            # Test paginated user listing
            response = client.get('/api/users?page=1&per_page=2')
            assert response.status_code == 200
            assert len(response.json['users']) == 2
            assert response.json['total'] >= 5
        
        def test_search_users_by_email(client, multiple_users):
            # Test user search functionality
            search_email = multiple_users[0].email
            response = client.get(f'/api/users/search?email={search_email}')
            assert response.status_code == 200
            assert any(u['email'] == search_email for u in response.json['users'])
        
        def test_bulk_delete_users(client, admin_user, multiple_users):
            # Test bulk delete operation
            user_ids = [u.id for u in multiple_users[:3]]
            response = client.post(
                '/api/users/bulk-delete',
                json={'user_ids': user_ids}
            )
            assert response.status_code == 200
    """
    users = []
    
    # Create 5 diverse users with varied attributes
    for i in range(5):
        user = User(
            email=fake.unique.email(),  # Ensure unique emails
            first_name=fake.first_name(),
            last_name=fake.last_name(),
            role='admin' if i == 0 else 'user',  # First user is admin
            is_active=True if i < 4 else False,  # Last user is inactive
            profile_picture=fake.image_url() if i % 2 == 0 else None  # Some have profile pictures
        )
        
        # Set password using secure hashing
        user.set_password(f'TestPassword{i}123!')
        
        users.append(user)
    
    # Bulk insert all users
    db_session.add_all(users)
    db_session.commit()
    
    # Refresh all users to load database-generated fields
    for user in users:
        db_session.refresh(user)
    
    return users


# ============================================================================
# FACTORY PATTERN FIXTURES
# ============================================================================


@pytest.fixture
def user_factory(db_session) -> Callable[[Dict[str, Any]], User]:
    """
    Provide factory function for creating custom User instances with flexible attributes.
    
    This fixture returns a factory function that creates User instances with
    custom attributes while handling all the boilerplate of password hashing,
    database persistence, and session management. It implements the factory
    pattern recommended in the Agent Action Plan section 0.9.
    
    The factory function accepts any valid User model attributes and returns
    a fully persisted User instance, making it ideal for tests that need
    specific user configurations without repeating setup code.
    
    Args:
        db_session: Database session fixture for persistence
    
    Returns:
        Callable[[Dict[str, Any]], User]: Factory function that accepts a
            dictionary of user attributes and returns a persisted User instance.
    
    Factory Function Signature:
        def factory(attributes: Dict[str, Any] = None) -> User
        
        Args:
            attributes (Dict[str, Any], optional): Dictionary of user attributes
                to override defaults. Can include:
                - email: Custom email (default: Faker-generated)
                - password: Plain password to hash (default: 'FactoryPassword123!')
                - first_name: Custom first name (default: Faker-generated)
                - last_name: Custom last name (default: Faker-generated)
                - role: User role (default: 'user')
                - is_active: Active status (default: True)
                - profile_picture: Profile picture URL (default: None)
                And any other valid User model attributes
        
        Returns:
            User: Persisted User instance with specified attributes
    
    Example:
        def test_user_with_custom_email(user_factory):
            user = user_factory({'email': 'custom@example.com'})
            assert user.email == 'custom@example.com'
            assert user.id is not None  # Persisted to database
        
        def test_superuser_creation(user_factory):
            superuser = user_factory({
                'email': 'super@example.com',
                'role': 'superuser',
                'first_name': 'Super',
                'last_name': 'User'
            })
            assert superuser.role == 'superuser'
            assert superuser.first_name == 'Super'
        
        def test_inactive_user(user_factory):
            inactive_user = user_factory({'is_active': False})
            assert inactive_user.is_active is False
        
        def test_multiple_custom_users(user_factory):
            # Create multiple users with different attributes
            users = [
                user_factory({'email': f'user{i}@example.com', 'role': 'admin'})
                for i in range(3)
            ]
            assert len(users) == 3
            assert all(u.role == 'admin' for u in users)
    
    Note:
        The factory automatically handles:
        - Password hashing via User.set_password()
        - Database session add and commit
        - Session refresh to load generated fields
        - Faker-generated defaults for missing attributes
        
        This provides the flexibility of factory_boy while working seamlessly
        with pytest fixtures and database sessions.
    """
    def factory(attributes: Dict[str, Any] = None) -> User:
        """
        Create and persist a User instance with custom attributes.
        
        Args:
            attributes: Dictionary of user attributes to override defaults
        
        Returns:
            User: Persisted User instance
        """
        # Default attributes with Faker-generated realistic data
        user_data = {
            'email': fake.unique.email(),
            'first_name': fake.first_name(),
            'last_name': fake.last_name(),
            'role': 'user',
            'is_active': True,
            'profile_picture': None
        }
        
        # Extract password separately as it needs special handling
        password = 'FactoryPassword123!'
        
        # Override defaults with provided attributes
        if attributes:
            # Handle password specially
            if 'password' in attributes:
                password = attributes.pop('password')
            
            # Update user_data with remaining attributes
            user_data.update(attributes)
        
        # Create User instance
        user = User(**user_data)
        
        # Set password using secure hashing
        user.set_password(password)
        
        # Persist to database
        db_session.add(user)
        db_session.commit()
        
        # Refresh to load database-generated fields
        db_session.refresh(user)
        
        return user
    
    return factory
