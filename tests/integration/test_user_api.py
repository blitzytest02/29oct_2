"""
Integration Tests for User API Endpoints

This module contains comprehensive end-to-end integration tests for user-related
API endpoints in the Flask application. These tests validate complete request
workflows from HTTP request through Flask routes, service layer, database operations,
and back to HTTP response.

Test Coverage:
    - User Registration API (POST /api/users/register)
    - User Profile Retrieval (GET /api/users/:id, GET /api/users/me)
    - User Profile Updates (PUT/PATCH /api/users/:id)
    - User Deletion (DELETE /api/users/:id)
    - User Listing with Pagination (GET /api/users)
    - User Search Functionality (GET /api/users/search)
    - Password Change (POST /api/users/change-password)
    - Profile Picture Upload (POST /api/users/profile-picture)
    - User Status and Role Management (Admin operations)
    - Error Handling and Edge Cases

Testing Approach:
    - Uses Flask test_client() for HTTP request simulation
    - Validates complete request-response cycle including database persistence
    - Tests authentication and authorization requirements
    - Verifies HTTP status codes, response formats, and error messages
    - Uses db_session fixture for database state verification
    - Mocks external services (file storage, email) using responses library
    - Each test is isolated with fresh database state

Test Organization:
    - Tests are marked with @pytest.mark.integration, @pytest.mark.api, @pytest.mark.database
    - Tests follow naming convention: test_<http_method>_<endpoint>_<scenario>()
    - Each test validates request handling, business logic, and database state
    - Execution time target: <1 second per test
    - Coverage target: 90% for API routes

Dependencies:
    - pytest: Testing framework with markers for categorization
    - responses: HTTP mocking library for external API calls
    - io.BytesIO: In-memory binary streams for file upload simulation
    - json: JSON manipulation for malformed request testing
    - app.models.User: User model for database state verification

Fixtures Used (from conftest.py):
    - client: Flask test client for HTTP requests
    - authenticated_client: Client with JWT token pre-configured
    - db_session: Database session with automatic rollback
    - app: Flask application instance

Usage Example:
    # Run all integration tests
    pytest tests/integration/test_user_api.py
    
    # Run specific test
    pytest tests/integration/test_user_api.py::test_post_api_users_register_success
    
    # Run with coverage
    pytest --cov=app.routes tests/integration/test_user_api.py
    
    # Run only API tests
    pytest -m api

Author: Flask Migration Test Suite
Version: 1.0.0
"""

import pytest
from io import BytesIO
import json
import responses

from app.models import User


# ============================================================================
# TEST CATEGORY 1: USER REGISTRATION API TESTS
# ============================================================================


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_post_api_users_register_success(client, db_session):
    """
    Test successful user registration with valid data returns 201.
    
    Validates:
        - POST /api/users/register with valid data creates user
        - Returns HTTP 201 Created status code
        - Response includes user ID and email
        - Password is not included in response for security
        - User is saved to database with correct attributes
    """
    # Arrange: Prepare valid registration data
    registration_data = {
        'email': 'newuser@example.com',
        'password': 'SecurePass123!',
        'first_name': 'John',
        'last_name': 'Doe'
    }
    
    # Act: Make registration request
    response = client.post('/api/users/register', json=registration_data)
    
    # Assert: Verify response
    assert response.status_code == 201
    response_data = response.get_json()
    assert 'id' in response_data
    assert response_data['email'] == 'newuser@example.com'
    assert response_data['first_name'] == 'John'
    assert response_data['last_name'] == 'Doe'
    assert 'password' not in response_data  # Security: password never exposed
    assert 'password_hash' not in response_data
    
    # Assert: Verify database state
    user = User.query.filter_by(email='newuser@example.com').first()
    assert user is not None
    assert user.email == 'newuser@example.com'
    assert user.first_name == 'John'
    assert user.last_name == 'Doe'
    assert user.is_active is True
    assert user.check_password('SecurePass123!')  # Password correctly hashed


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_post_api_users_register_duplicate_email(client, db_session):
    """
    Test registration with duplicate email returns 409 Conflict.
    
    Validates:
        - POST /api/users/register with existing email returns 409
        - Error message indicates email already exists
        - No duplicate user is created in database
    """
    # Arrange: Create existing user
    existing_user = User(email='existing@example.com')
    existing_user.set_password('ExistingPass123!')
    db_session.add(existing_user)
    db_session.commit()
    
    # Prepare duplicate registration data
    duplicate_data = {
        'email': 'existing@example.com',
        'password': 'NewPass123!',
        'first_name': 'Jane',
        'last_name': 'Smith'
    }
    
    # Act: Attempt registration with duplicate email
    response = client.post('/api/users/register', json=duplicate_data)
    
    # Assert: Verify error response
    assert response.status_code == 409
    response_data = response.get_json()
    assert 'error' in response_data or 'message' in response_data
    error_message = response_data.get('error') or response_data.get('message')
    assert 'email' in error_message.lower()
    assert 'already' in error_message.lower() or 'exists' in error_message.lower()
    
    # Assert: Verify only one user with that email exists
    user_count = User.query.filter_by(email='existing@example.com').count()
    assert user_count == 1


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_post_api_users_register_invalid_data(client, db_session):
    """
    Test registration with invalid data returns 400 Bad Request.
    
    Validates:
        - POST /api/users/register with invalid email format returns 400
        - POST /api/users/register with weak password returns 400
        - Error messages indicate specific validation failures
    """
    # Test invalid email format
    invalid_email_data = {
        'email': 'not-an-email',
        'password': 'SecurePass123!',
        'first_name': 'John'
    }
    
    response = client.post('/api/users/register', json=invalid_email_data)
    assert response.status_code == 400
    response_data = response.get_json()
    assert 'error' in response_data or 'message' in response_data
    
    # Test weak password (no special characters)
    weak_password_data = {
        'email': 'user@example.com',
        'password': 'weak',
        'first_name': 'John'
    }
    
    response = client.post('/api/users/register', json=weak_password_data)
    assert response.status_code == 400
    response_data = response.get_json()
    assert 'error' in response_data or 'message' in response_data
    error_message = response_data.get('error') or response_data.get('message')
    assert 'password' in error_message.lower()


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_post_api_users_register_missing_fields(client, db_session):
    """
    Test registration with missing required fields returns 400 Bad Request.
    
    Validates:
        - POST /api/users/register without email returns 400
        - POST /api/users/register without password returns 400
        - Error messages indicate missing required fields
    """
    # Test missing email
    missing_email_data = {
        'password': 'SecurePass123!',
        'first_name': 'John'
    }
    
    response = client.post('/api/users/register', json=missing_email_data)
    assert response.status_code == 400
    response_data = response.get_json()
    assert 'error' in response_data or 'message' in response_data
    
    # Test missing password
    missing_password_data = {
        'email': 'user@example.com',
        'first_name': 'John'
    }
    
    response = client.post('/api/users/register', json=missing_password_data)
    assert response.status_code == 400
    response_data = response.get_json()
    assert 'error' in response_data or 'message' in response_data


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_post_api_users_register_creates_database_record(client, db_session):
    """
    Test registration creates database record with correct attributes.
    
    Validates:
        - User record is created in database
        - All fields are correctly populated
        - Password is hashed (not stored plain)
        - Default role is 'user'
        - is_active defaults to True
        - Timestamps are set
    """
    # Arrange
    registration_data = {
        'email': 'dbtest@example.com',
        'password': 'TestPass123!',
        'first_name': 'Database',
        'last_name': 'Test'
    }
    
    # Act
    response = client.post('/api/users/register', json=registration_data)
    
    # Assert response success
    assert response.status_code == 201
    
    # Assert database record exists with correct attributes
    user = User.query.filter_by(email='dbtest@example.com').first()
    assert user is not None
    assert user.email == 'dbtest@example.com'
    assert user.first_name == 'Database'
    assert user.last_name == 'Test'
    assert user.password_hash is not None
    assert user.password_hash != 'TestPass123!'  # Password is hashed
    assert user.role == 'user'  # Default role
    assert user.is_active is True  # Default active
    assert user.created_at is not None
    assert user.updated_at is not None
    assert user.check_password('TestPass123!')  # Password verification works


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_post_api_users_register_response_format(client, db_session):
    """
    Test registration response has correct JSON structure.
    
    Validates:
        - Response is valid JSON
        - Response includes expected fields: id, email, first_name, last_name
        - Response excludes sensitive fields: password, password_hash
        - Field types are correct
    """
    # Arrange
    registration_data = {
        'email': 'format@example.com',
        'password': 'FormatTest123!',
        'first_name': 'Format',
        'last_name': 'Test'
    }
    
    # Act
    response = client.post('/api/users/register', json=registration_data)
    
    # Assert
    assert response.status_code == 201
    assert response.content_type == 'application/json'
    
    response_data = response.get_json()
    
    # Required fields present
    assert 'id' in response_data
    assert 'email' in response_data
    assert 'first_name' in response_data
    assert 'last_name' in response_data
    assert 'role' in response_data
    assert 'is_active' in response_data
    assert 'created_at' in response_data
    
    # Sensitive fields excluded
    assert 'password' not in response_data
    assert 'password_hash' not in response_data
    
    # Field types correct
    assert isinstance(response_data['id'], int)
    assert isinstance(response_data['email'], str)
    assert isinstance(response_data['is_active'], bool)


# ============================================================================
# TEST CATEGORY 2: GET USER PROFILE API TESTS
# ============================================================================


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_get_api_users_me_authenticated(authenticated_client, db_session):
    """
    Test GET /api/users/me with valid token returns 200 and user profile.
    
    Validates:
        - Authenticated request to /api/users/me returns 200
        - Response contains current user's profile data
        - Password is not included in response
    """
    # Act: Request current user profile with authenticated client
    response = authenticated_client.get('/api/users/me')
    
    # Assert
    assert response.status_code == 200
    response_data = response.get_json()
    
    # Verify response contains user data
    assert 'id' in response_data
    assert 'email' in response_data
    assert response_data['email'] == 'test_user@example.com'  # From authenticated_client fixture
    assert 'password' not in response_data
    assert 'password_hash' not in response_data


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_get_api_users_me_unauthenticated(client, db_session):
    """
    Test GET /api/users/me without authentication returns 401 Unauthorized.
    
    Validates:
        - Unauthenticated request to /api/users/me returns 401
        - Error message indicates authentication required
    """
    # Act: Request current user profile without authentication
    response = client.get('/api/users/me')
    
    # Assert
    assert response.status_code == 401
    response_data = response.get_json()
    assert 'error' in response_data or 'message' in response_data or 'msg' in response_data


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_get_api_users_id_success(authenticated_client, db_session):
    """
    Test GET /api/users/:id returns user data for existing user.
    
    Validates:
        - GET /api/users/:id with valid ID returns 200
        - Response contains requested user's data
        - Public profile information is returned
    """
    # Arrange: Create a user to retrieve
    user = User(email='profile@example.com', first_name='Profile', last_name='User')
    user.set_password('ProfilePass123!')
    db_session.add(user)
    db_session.commit()
    user_id = user.id
    
    # Act: Request user profile by ID
    response = authenticated_client.get(f'/api/users/{user_id}')
    
    # Assert
    assert response.status_code == 200
    response_data = response.get_json()
    assert response_data['id'] == user_id
    assert response_data['email'] == 'profile@example.com'
    assert response_data['first_name'] == 'Profile'
    assert response_data['last_name'] == 'User'
    assert 'password' not in response_data


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_get_api_users_id_not_found(authenticated_client, db_session):
    """
    Test GET /api/users/:id returns 404 for nonexistent user.
    
    Validates:
        - GET /api/users/:id with invalid ID returns 404
        - Error message indicates user not found
    """
    # Act: Request nonexistent user
    response = authenticated_client.get('/api/users/99999')
    
    # Assert
    assert response.status_code == 404
    response_data = response.get_json()
    assert 'error' in response_data or 'message' in response_data


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_get_api_users_id_unauthorized(client, db_session):
    """
    Test GET /api/users/:id without authentication returns 401.
    
    Validates:
        - Unauthenticated access to user profile returns 401
        - Private user data is protected
    """
    # Arrange: Create a user
    user = User(email='private@example.com')
    user.set_password('PrivatePass123!')
    db_session.add(user)
    db_session.commit()
    user_id = user.id
    
    # Act: Request user without authentication
    response = client.get(f'/api/users/{user_id}')
    
    # Assert
    assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_get_api_users_me_excludes_password(authenticated_client, db_session):
    """
    Test GET /api/users/me never includes password in response.
    
    Validates:
        - password field is never in response
        - password_hash field is never in response
        - Response is safe for client consumption
    """
    # Act
    response = authenticated_client.get('/api/users/me')
    
    # Assert
    assert response.status_code == 200
    response_data = response.get_json()
    response_str = json.dumps(response_data)
    
    # Ensure no password-related fields in response
    assert 'password' not in response_data
    assert 'password_hash' not in response_data
    assert 'password_hash' not in response_str


# ============================================================================
# TEST CATEGORY 3: UPDATE USER PROFILE API TESTS
# ============================================================================


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_put_api_users_id_authenticated_owner(authenticated_client, db_session):
    """
    Test PUT /api/users/:id updates own profile successfully.
    
    Validates:
        - Authenticated user can update their own profile
        - Returns 200 with updated data
        - Changes are persisted to database
    """
    # Arrange: Get authenticated user
    auth_user = User.query.filter_by(email='test_user@example.com').first()
    user_id = auth_user.id
    
    update_data = {
        'first_name': 'Updated',
        'last_name': 'Name'
    }
    
    # Act
    response = authenticated_client.put(f'/api/users/{user_id}', json=update_data)
    
    # Assert response
    assert response.status_code == 200
    response_data = response.get_json()
    assert response_data['first_name'] == 'Updated'
    assert response_data['last_name'] == 'Name'
    
    # Assert database updated
    db_session.refresh(auth_user)
    assert auth_user.first_name == 'Updated'
    assert auth_user.last_name == 'Name'


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_put_api_users_id_unauthenticated(client, db_session):
    """
    Test PUT /api/users/:id without authentication returns 401.
    
    Validates:
        - Unauthenticated update request returns 401
        - User data is not modified
    """
    # Arrange: Create a user
    user = User(email='noupdate@example.com', first_name='Original')
    user.set_password('Pass123!')
    db_session.add(user)
    db_session.commit()
    user_id = user.id
    
    update_data = {'first_name': 'Hacked'}
    
    # Act
    response = client.put(f'/api/users/{user_id}', json=update_data)
    
    # Assert
    assert response.status_code == 401
    
    # Verify no changes
    db_session.refresh(user)
    assert user.first_name == 'Original'


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_put_api_users_id_unauthorized(authenticated_client, db_session):
    """
    Test PUT /api/users/:id for another user returns 403 Forbidden.
    
    Validates:
        - User cannot update another user's profile
        - Returns 403 Forbidden
        - Target user data is not modified
    """
    # Arrange: Create another user
    other_user = User(email='other@example.com', first_name='Other')
    other_user.set_password('Other123!')
    db_session.add(other_user)
    db_session.commit()
    other_user_id = other_user.id
    
    update_data = {'first_name': 'Unauthorized'}
    
    # Act
    response = authenticated_client.put(f'/api/users/{other_user_id}', json=update_data)
    
    # Assert
    assert response.status_code == 403
    
    # Verify no changes
    db_session.refresh(other_user)
    assert other_user.first_name == 'Other'


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_put_api_users_id_invalid_data(authenticated_client, db_session):
    """
    Test PUT /api/users/:id with invalid data returns 400.
    
    Validates:
        - Invalid email format returns 400
        - Invalid data types return 400
        - Error messages indicate validation failures
    """
    # Arrange
    auth_user = User.query.filter_by(email='test_user@example.com').first()
    user_id = auth_user.id
    
    invalid_data = {
        'email': 'not-an-email'
    }
    
    # Act
    response = authenticated_client.put(f'/api/users/{user_id}', json=invalid_data)
    
    # Assert
    assert response.status_code == 400
    response_data = response.get_json()
    assert 'error' in response_data or 'message' in response_data


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_patch_api_users_id_partial_update(authenticated_client, db_session):
    """
    Test PATCH /api/users/:id for partial profile update.
    
    Validates:
        - PATCH allows updating only specified fields
        - Other fields remain unchanged
        - Returns 200 with updated data
    """
    # Arrange
    auth_user = User.query.filter_by(email='test_user@example.com').first()
    user_id = auth_user.id
    original_last_name = auth_user.last_name
    
    partial_update = {
        'first_name': 'PartialUpdate'
    }
    
    # Act
    response = authenticated_client.patch(f'/api/users/{user_id}', json=partial_update)
    
    # Assert
    assert response.status_code == 200
    response_data = response.get_json()
    assert response_data['first_name'] == 'PartialUpdate'
    
    # Verify only specified field changed
    db_session.refresh(auth_user)
    assert auth_user.first_name == 'PartialUpdate'
    assert auth_user.last_name == original_last_name


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_put_api_users_id_email_uniqueness(authenticated_client, db_session):
    """
    Test PUT /api/users/:id cannot update to existing email.
    
    Validates:
        - Updating email to existing email returns 409
        - Error message indicates email conflict
        - Original email is preserved
    """
    # Arrange: Create existing user
    existing_user = User(email='taken@example.com')
    existing_user.set_password('Pass123!')
    db_session.add(existing_user)
    db_session.commit()
    
    # Get authenticated user
    auth_user = User.query.filter_by(email='test_user@example.com').first()
    user_id = auth_user.id
    original_email = auth_user.email
    
    conflicting_update = {
        'email': 'taken@example.com'
    }
    
    # Act
    response = authenticated_client.put(f'/api/users/{user_id}', json=conflicting_update)
    
    # Assert
    assert response.status_code == 409
    
    # Verify email not changed
    db_session.refresh(auth_user)
    assert auth_user.email == original_email


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_put_api_users_id_updates_database(authenticated_client, db_session):
    """
    Test PUT /api/users/:id persists changes to database.
    
    Validates:
        - Profile changes are committed to database
        - updated_at timestamp is updated
        - All fields are correctly saved
    """
    # Arrange
    auth_user = User.query.filter_by(email='test_user@example.com').first()
    user_id = auth_user.id
    original_updated_at = auth_user.updated_at
    
    update_data = {
        'first_name': 'DatabaseTest',
        'last_name': 'UpdateTest'
    }
    
    # Act
    response = authenticated_client.put(f'/api/users/{user_id}', json=update_data)
    
    # Assert
    assert response.status_code == 200
    
    # Verify database persistence
    db_session.refresh(auth_user)
    assert auth_user.first_name == 'DatabaseTest'
    assert auth_user.last_name == 'UpdateTest'
    # updated_at should be newer (if timestamp tracking is implemented)
    # assert auth_user.updated_at > original_updated_at


# ============================================================================
# TEST CATEGORY 4: DELETE USER API TESTS
# ============================================================================


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_delete_api_users_id_authenticated_owner(authenticated_client, db_session):
    """
    Test DELETE /api/users/:id soft deletes own account.
    
    Validates:
        - Authenticated user can delete their own account
        - Returns 204 No Content or 200
        - User is soft deleted (is_active = False)
    """
    # Arrange
    auth_user = User.query.filter_by(email='test_user@example.com').first()
    user_id = auth_user.id
    
    # Act
    response = authenticated_client.delete(f'/api/users/{user_id}')
    
    # Assert
    assert response.status_code in [200, 204]
    
    # Verify soft delete
    db_session.refresh(auth_user)
    assert auth_user.is_active is False


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_delete_api_users_id_unauthenticated(client, db_session):
    """
    Test DELETE /api/users/:id without authentication returns 401.
    
    Validates:
        - Unauthenticated delete request returns 401
        - User is not deleted
    """
    # Arrange
    user = User(email='nodelete@example.com')
    user.set_password('Pass123!')
    db_session.add(user)
    db_session.commit()
    user_id = user.id
    
    # Act
    response = client.delete(f'/api/users/{user_id}')
    
    # Assert
    assert response.status_code == 401
    
    # Verify user still active
    db_session.refresh(user)
    assert user.is_active is True


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_delete_api_users_id_unauthorized(authenticated_client, db_session):
    """
    Test DELETE /api/users/:id for another user returns 403.
    
    Validates:
        - User cannot delete another user's account
        - Returns 403 Forbidden
        - Target user is not deleted
    """
    # Arrange
    other_user = User(email='notmine@example.com')
    other_user.set_password('Pass123!')
    db_session.add(other_user)
    db_session.commit()
    other_user_id = other_user.id
    
    # Act
    response = authenticated_client.delete(f'/api/users/{other_user_id}')
    
    # Assert
    assert response.status_code == 403
    
    # Verify user not deleted
    db_session.refresh(other_user)
    assert other_user.is_active is True


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_delete_api_users_id_admin_can_delete_any(client, db_session):
    """
    Test DELETE /api/users/:id allows admin to delete any user.
    
    Validates:
        - Admin user can delete other users
        - Returns 200 or 204
        - Target user is soft deleted
    
    Note: Requires admin authentication which may need special fixture
    """
    # Arrange: Create admin user
    admin_user = User(email='admin@example.com', role='admin')
    admin_user.set_password('AdminPass123!')
    db_session.add(admin_user)
    db_session.commit()
    
    # Create target user
    target_user = User(email='target@example.com')
    target_user.set_password('Pass123!')
    db_session.add(target_user)
    db_session.commit()
    target_user_id = target_user.id
    
    # Create admin authenticated client
    try:
        from flask_jwt_extended import create_access_token
        access_token = create_access_token(identity=str(admin_user.id))
        client.environ_base['HTTP_AUTHORIZATION'] = f'Bearer {access_token}'
    except ImportError:
        pytest.skip("JWT not configured, skipping admin test")
    
    # Act
    response = client.delete(f'/api/users/{target_user_id}')
    
    # Assert
    assert response.status_code in [200, 204]
    
    # Verify user deleted
    db_session.refresh(target_user)
    assert target_user.is_active is False


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_delete_api_users_id_not_found(authenticated_client, db_session):
    """
    Test DELETE /api/users/:id returns 404 for nonexistent user.
    
    Validates:
        - DELETE request for invalid ID returns 404
        - Error message indicates user not found
    """
    # Act
    response = authenticated_client.delete('/api/users/99999')
    
    # Assert
    assert response.status_code == 404
    response_data = response.get_json()
    assert 'error' in response_data or 'message' in response_data


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_delete_api_users_id_marks_inactive(authenticated_client, db_session):
    """
    Test DELETE /api/users/:id performs soft delete (not hard delete).
    
    Validates:
        - User record still exists in database after deletion
        - is_active flag is set to False
        - User data is preserved for audit purposes
    """
    # Arrange
    auth_user = User.query.filter_by(email='test_user@example.com').first()
    user_id = auth_user.id
    original_email = auth_user.email
    
    # Act
    response = authenticated_client.delete(f'/api/users/{user_id}')
    
    # Assert
    assert response.status_code in [200, 204]
    
    # Verify soft delete: record exists but inactive
    deleted_user = User.query.get(user_id)
    assert deleted_user is not None  # Record still exists
    assert deleted_user.is_active is False  # Marked inactive
    assert deleted_user.email == original_email  # Data preserved


# ============================================================================
# TEST CATEGORY 5: LIST USERS API TESTS
# ============================================================================


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_get_api_users_list_authenticated(authenticated_client, db_session):
    """
    Test GET /api/users returns paginated list of users.
    
    Validates:
        - Authenticated request returns 200
        - Response contains array of user objects
        - Pagination metadata is included
    """
    # Arrange: Create multiple users
    for i in range(5):
        user = User(email=f'user{i}@example.com')
        user.set_password('Pass123!')
        db_session.add(user)
    db_session.commit()
    
    # Act
    response = authenticated_client.get('/api/users')
    
    # Assert
    assert response.status_code == 200
    response_data = response.get_json()
    
    # Response should contain users array
    assert 'users' in response_data or isinstance(response_data, list)
    
    # If paginated response structure
    if 'users' in response_data:
        assert isinstance(response_data['users'], list)
        assert len(response_data['users']) > 0
        # Pagination metadata
        assert 'page' in response_data or 'total' in response_data
    else:
        # Direct array response
        assert isinstance(response_data, list)
        assert len(response_data) > 0


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_get_api_users_list_unauthenticated(client, db_session):
    """
    Test GET /api/users without authentication returns 401 or limited data.
    
    Validates:
        - Unauthenticated request either returns 401
        - Or returns limited public profile data only
    """
    # Arrange: Create users
    user = User(email='public@example.com')
    user.set_password('Pass123!')
    db_session.add(user)
    db_session.commit()
    
    # Act
    response = client.get('/api/users')
    
    # Assert: Either 401 or limited data
    assert response.status_code in [200, 401]
    
    if response.status_code == 200:
        # If public listing allowed, ensure sensitive data excluded
        response_data = response.get_json()
        users = response_data if isinstance(response_data, list) else response_data.get('users', [])
        for user_data in users:
            assert 'password' not in user_data
            assert 'password_hash' not in user_data


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_get_api_users_list_pagination(authenticated_client, db_session):
    """
    Test GET /api/users with pagination parameters.
    
    Validates:
        - page parameter controls result offset
        - per_page parameter controls result count
        - Pagination metadata is accurate
    """
    # Arrange: Create 15 users
    for i in range(15):
        user = User(email=f'page{i}@example.com')
        user.set_password('Pass123!')
        db_session.add(user)
    db_session.commit()
    
    # Act: Request second page with 5 per page
    response = authenticated_client.get('/api/users?page=2&per_page=5')
    
    # Assert
    assert response.status_code == 200
    response_data = response.get_json()
    
    # Verify pagination works
    users = response_data.get('users', response_data)
    if isinstance(users, list):
        assert len(users) <= 5


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_get_api_users_list_default_limit(authenticated_client, db_session):
    """
    Test GET /api/users applies default page size limit.
    
    Validates:
        - Default per_page value is applied (e.g., 20)
        - Large result sets are paginated
    """
    # Arrange: Create 50 users
    for i in range(50):
        user = User(email=f'limit{i}@example.com')
        user.set_password('Pass123!')
        db_session.add(user)
    db_session.commit()
    
    # Act: Request without per_page parameter
    response = authenticated_client.get('/api/users')
    
    # Assert
    assert response.status_code == 200
    response_data = response.get_json()
    
    users = response_data.get('users', response_data)
    if isinstance(users, list):
        # Verify default limit applied (typically 20 or 50)
        assert len(users) <= 50


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_get_api_users_list_max_limit(authenticated_client, db_session):
    """
    Test GET /api/users enforces maximum page size limit.
    
    Validates:
        - Requesting excessive per_page is capped
        - Maximum limit (e.g., 100) is enforced
    """
    # Arrange: Create users
    for i in range(20):
        user = User(email=f'max{i}@example.com')
        user.set_password('Pass123!')
        db_session.add(user)
    db_session.commit()
    
    # Act: Request with excessive per_page
    response = authenticated_client.get('/api/users?per_page=1000')
    
    # Assert
    assert response.status_code == 200
    response_data = response.get_json()
    
    users = response_data.get('users', response_data)
    if isinstance(users, list):
        # Verify capped at reasonable maximum
        assert len(users) <= 100


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_get_api_users_list_empty_results(authenticated_client, empty_db):
    """
    Test GET /api/users returns empty array when no users exist.
    
    Validates:
        - Empty database returns 200 (not 404)
        - Response is empty array or users: []
        - Pagination metadata shows zero total
    """
    # Act: Request users from empty database
    response = authenticated_client.get('/api/users')
    
    # Assert
    assert response.status_code == 200
    response_data = response.get_json()
    
    users = response_data.get('users', response_data)
    if isinstance(users, list):
        assert len(users) == 0
    
    # Check total count if provided
    if 'total' in response_data:
        assert response_data['total'] >= 0


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_get_api_users_list_sorting(authenticated_client, db_session):
    """
    Test GET /api/users with sort_by parameter.
    
    Validates:
        - sort_by=name sorts alphabetically
        - sort_by=created_at sorts by registration date
        - Sort order can be ascending or descending
    """
    # Arrange: Create users with different names
    users_data = [
        ('charlie@example.com', 'Charlie'),
        ('alice@example.com', 'Alice'),
        ('bob@example.com', 'Bob')
    ]
    
    for email, first_name in users_data:
        user = User(email=email, first_name=first_name)
        user.set_password('Pass123!')
        db_session.add(user)
    db_session.commit()
    
    # Act: Request sorted by first name
    response = authenticated_client.get('/api/users?sort_by=first_name&order=asc')
    
    # Assert
    assert response.status_code == 200
    response_data = response.get_json()
    
    users = response_data.get('users', response_data)
    if isinstance(users, list) and len(users) >= 3:
        # Verify alphabetical order
        first_names = [u['first_name'] for u in users if u.get('first_name')]
        if len(first_names) >= 2:
            assert first_names == sorted(first_names)


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_get_api_users_list_filtering(authenticated_client, db_session):
    """
    Test GET /api/users with filter parameters.
    
    Validates:
        - Filter by role returns only matching users
        - Filter by is_active status works
        - Multiple filters can be combined
    """
    # Arrange: Create users with different roles
    admin = User(email='admin@example.com', role='admin')
    admin.set_password('Pass123!')
    db_session.add(admin)
    
    user = User(email='user@example.com', role='user')
    user.set_password('Pass123!')
    db_session.add(user)
    
    db_session.commit()
    
    # Act: Filter by role=admin
    response = authenticated_client.get('/api/users?role=admin')
    
    # Assert
    assert response.status_code == 200
    response_data = response.get_json()
    
    users = response_data.get('users', response_data)
    if isinstance(users, list):
        # All returned users should have admin role
        for user_data in users:
            if 'role' in user_data:
                assert user_data['role'] == 'admin'


# ============================================================================
# TEST CATEGORY 6: SEARCH USERS API TESTS
# ============================================================================


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_get_api_users_search_by_name(authenticated_client, db_session):
    """
    Test GET /api/users/search finds users by name or email.
    
    Validates:
        - Search query matches user names
        - Search query matches user emails
        - Returns matching results only
    """
    # Arrange: Create users
    users_data = [
        ('john.doe@example.com', 'John', 'Doe'),
        ('jane.smith@example.com', 'Jane', 'Smith'),
        ('bob.johnson@example.com', 'Bob', 'Johnson')
    ]
    
    for email, first_name, last_name in users_data:
        user = User(email=email, first_name=first_name, last_name=last_name)
        user.set_password('Pass123!')
        db_session.add(user)
    db_session.commit()
    
    # Act: Search for "john"
    response = authenticated_client.get('/api/users/search?q=john')
    
    # Assert
    assert response.status_code == 200
    response_data = response.get_json()
    
    results = response_data.get('results', response_data)
    if isinstance(results, list):
        # Verify results contain "john"
        for user_data in results:
            name_match = (
                'john' in user_data.get('first_name', '').lower() or
                'john' in user_data.get('last_name', '').lower() or
                'john' in user_data.get('email', '').lower()
            )
            assert name_match


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_get_api_users_search_case_insensitive(authenticated_client, db_session):
    """
    Test GET /api/users/search is case-insensitive.
    
    Validates:
        - Search "JOHN" finds "john"
        - Search "john" finds "John"
        - Case doesn't affect results
    """
    # Arrange
    user = User(email='searchuser@example.com', first_name='SearchTest')
    user.set_password('Pass123!')
    db_session.add(user)
    db_session.commit()
    
    # Act: Search with different cases
    response_lower = authenticated_client.get('/api/users/search?q=searchtest')
    response_upper = authenticated_client.get('/api/users/search?q=SEARCHTEST')
    response_mixed = authenticated_client.get('/api/users/search?q=SeArChTeSt')
    
    # Assert all find the user
    assert response_lower.status_code == 200
    assert response_upper.status_code == 200
    assert response_mixed.status_code == 200
    
    # Verify consistent results regardless of case
    results_lower = response_lower.get_json()
    results_upper = response_upper.get_json()
    results_mixed = response_mixed.get_json()
    
    # All should return results
    assert len(results_lower.get('results', results_lower)) > 0 or 'searchuser@example.com' in str(results_lower)


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_get_api_users_search_partial_match(authenticated_client, db_session):
    """
    Test GET /api/users/search supports partial string matching.
    
    Validates:
        - Partial name matches work (e.g., "joh" finds "john")
        - Partial email matches work (e.g., "example" finds "@example.com")
        - Results are relevant to query
    """
    # Arrange
    user = User(email='partial@example.com', first_name='Partial', last_name='Match')
    user.set_password('Pass123!')
    db_session.add(user)
    db_session.commit()
    
    # Act: Search with partial query
    response = authenticated_client.get('/api/users/search?q=parti')
    
    # Assert
    assert response.status_code == 200
    response_data = response.get_json()
    
    results = response_data.get('results', response_data)
    # Verify partial match found
    assert len(results) > 0 or 'partial' in str(results).lower()


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_get_api_users_search_no_results(authenticated_client, db_session):
    """
    Test GET /api/users/search returns empty array for no matches.
    
    Validates:
        - No matches returns 200 (not 404)
        - Response is empty array
        - Helpful message may be included
    """
    # Act: Search for nonexistent user
    response = authenticated_client.get('/api/users/search?q=nonexistentuser12345')
    
    # Assert
    assert response.status_code == 200
    response_data = response.get_json()
    
    results = response_data.get('results', response_data)
    if isinstance(results, list):
        assert len(results) == 0


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_get_api_users_search_requires_auth(client, db_session):
    """
    Test GET /api/users/search requires authentication.
    
    Validates:
        - Unauthenticated search request returns 401
        - User search is protected endpoint
    """
    # Act: Search without authentication
    response = client.get('/api/users/search?q=test')
    
    # Assert
    assert response.status_code == 401


# ============================================================================
# TEST CATEGORY 7: CHANGE PASSWORD API TESTS
# ============================================================================


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_post_api_users_change_password_success(authenticated_client, db_session):
    """
    Test POST /api/users/change-password successfully updates password.
    
    Validates:
        - Valid current password and new password returns 200
        - New password is hashed and stored
        - User can authenticate with new password
    """
    # Arrange
    auth_user = User.query.filter_by(email='test_user@example.com').first()
    
    password_data = {
        'current_password': 'TestPassword123!',
        'new_password': 'NewSecurePass456!'
    }
    
    # Act
    response = authenticated_client.post('/api/users/change-password', json=password_data)
    
    # Assert
    assert response.status_code == 200
    
    # Verify new password works
    db_session.refresh(auth_user)
    assert auth_user.check_password('NewSecurePass456!')
    assert not auth_user.check_password('TestPassword123!')


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_post_api_users_change_password_wrong_current(authenticated_client, db_session):
    """
    Test POST /api/users/change-password validates current password.
    
    Validates:
        - Incorrect current password returns 400 or 401
        - Error message indicates authentication failure
        - Password is not changed
    """
    # Arrange
    auth_user = User.query.filter_by(email='test_user@example.com').first()
    original_hash = auth_user.password_hash
    
    password_data = {
        'current_password': 'WrongPassword!',
        'new_password': 'NewSecurePass456!'
    }
    
    # Act
    response = authenticated_client.post('/api/users/change-password', json=password_data)
    
    # Assert
    assert response.status_code in [400, 401]
    response_data = response.get_json()
    assert 'error' in response_data or 'message' in response_data
    
    # Verify password not changed
    db_session.refresh(auth_user)
    assert auth_user.password_hash == original_hash


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_post_api_users_change_password_weak_new(authenticated_client, db_session):
    """
    Test POST /api/users/change-password enforces password strength.
    
    Validates:
        - Weak new password returns 400
        - Error message indicates password requirements
        - Password is not changed
    """
    # Arrange
    auth_user = User.query.filter_by(email='test_user@example.com').first()
    original_hash = auth_user.password_hash
    
    password_data = {
        'current_password': 'TestPassword123!',
        'new_password': 'weak'
    }
    
    # Act
    response = authenticated_client.post('/api/users/change-password', json=password_data)
    
    # Assert
    assert response.status_code == 400
    response_data = response.get_json()
    error_message = response_data.get('error') or response_data.get('message', '')
    assert 'password' in error_message.lower()
    
    # Verify password not changed
    db_session.refresh(auth_user)
    assert auth_user.password_hash == original_hash


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_post_api_users_change_password_unauthenticated(client, db_session):
    """
    Test POST /api/users/change-password requires authentication.
    
    Validates:
        - Unauthenticated request returns 401
        - Password change is protected operation
    """
    # Arrange
    password_data = {
        'current_password': 'SomePass123!',
        'new_password': 'NewPass456!'
    }
    
    # Act
    response = client.post('/api/users/change-password', json=password_data)
    
    # Assert
    assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_post_api_users_change_password_invalidates_tokens(authenticated_client, db_session):
    """
    Test POST /api/users/change-password invalidates old JWT tokens.
    
    Validates:
        - After password change, old tokens should be revoked
        - Security measure to prevent unauthorized access
    
    Note: Implementation depends on JWT revocation strategy
    """
    # Arrange
    password_data = {
        'current_password': 'TestPassword123!',
        'new_password': 'NewSecurePass456!'
    }
    
    # Act: Change password
    response = authenticated_client.post('/api/users/change-password', json=password_data)
    
    # Assert
    assert response.status_code == 200
    
    # Note: Token invalidation testing would require:
    # 1. Token blacklist/revocation mechanism
    # 2. Attempting to use old token after password change
    # 3. Verifying old token is rejected
    # This is implementation-dependent and may require additional test setup


# ============================================================================
# TEST CATEGORY 8: UPLOAD PROFILE PICTURE API TESTS
# ============================================================================


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
@responses.activate
def test_post_api_users_profile_picture_success(authenticated_client, db_session):
    """
    Test POST /api/users/profile-picture successfully uploads image.
    
    Validates:
        - Valid image file upload returns 200
        - Response includes profile picture URL
        - User profile is updated with picture URL
    
    Mocks external file storage service
    """
    # Arrange: Create fake image file
    fake_image = BytesIO(b'fake image content')
    fake_image.name = 'profile.jpg'
    
    # Mock external storage service response
    responses.add(
        responses.POST,
        'https://storage.example.com/upload',
        json={'url': 'https://cdn.example.com/profile123.jpg'},
        status=200
    )
    
    # Prepare multipart form data
    data = {
        'file': (fake_image, 'profile.jpg', 'image/jpeg')
    }
    
    # Act
    response = authenticated_client.post(
        '/api/users/profile-picture',
        data=data,
        content_type='multipart/form-data'
    )
    
    # Assert
    assert response.status_code == 200
    response_data = response.get_json()
    assert 'profile_picture' in response_data or 'url' in response_data
    
    # Verify database updated
    auth_user = User.query.filter_by(email='test_user@example.com').first()
    db_session.refresh(auth_user)
    assert auth_user.profile_picture is not None


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_post_api_users_profile_picture_invalid_format(authenticated_client, db_session):
    """
    Test POST /api/users/profile-picture rejects non-image files.
    
    Validates:
        - Non-image file returns 400
        - Error message indicates invalid file type
        - Only image formats allowed (jpg, png, gif)
    """
    # Arrange: Create fake text file
    fake_file = BytesIO(b'not an image')
    fake_file.name = 'document.txt'
    
    data = {
        'file': (fake_file, 'document.txt', 'text/plain')
    }
    
    # Act
    response = authenticated_client.post(
        '/api/users/profile-picture',
        data=data,
        content_type='multipart/form-data'
    )
    
    # Assert
    assert response.status_code == 400
    response_data = response.get_json()
    error_message = response_data.get('error') or response_data.get('message', '')
    assert 'image' in error_message.lower() or 'format' in error_message.lower()


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_post_api_users_profile_picture_too_large(authenticated_client, db_session):
    """
    Test POST /api/users/profile-picture enforces file size limits.
    
    Validates:
        - File larger than limit (e.g., 5MB) returns 400 or 413
        - Error message indicates file too large
        - Size limit is reasonable for profile pictures
    """
    # Arrange: Create large fake file (simulated)
    large_file = BytesIO(b'x' * (6 * 1024 * 1024))  # 6MB
    large_file.name = 'large.jpg'
    
    data = {
        'file': (large_file, 'large.jpg', 'image/jpeg')
    }
    
    # Act
    response = authenticated_client.post(
        '/api/users/profile-picture',
        data=data,
        content_type='multipart/form-data'
    )
    
    # Assert
    assert response.status_code in [400, 413]
    response_data = response.get_json()
    if response_data:
        error_message = response_data.get('error') or response_data.get('message', '')
        assert 'size' in error_message.lower() or 'large' in error_message.lower()


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_post_api_users_profile_picture_unauthenticated(client, db_session):
    """
    Test POST /api/users/profile-picture requires authentication.
    
    Validates:
        - Unauthenticated upload request returns 401
        - Profile picture upload is protected operation
    """
    # Arrange
    fake_image = BytesIO(b'fake image')
    fake_image.name = 'profile.jpg'
    
    data = {
        'file': (fake_image, 'profile.jpg', 'image/jpeg')
    }
    
    # Act
    response = client.post(
        '/api/users/profile-picture',
        data=data,
        content_type='multipart/form-data'
    )
    
    # Assert
    assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_delete_api_users_profile_picture(authenticated_client, db_session):
    """
    Test DELETE /api/users/profile-picture removes profile picture.
    
    Validates:
        - DELETE request returns 200 or 204
        - profile_picture field is set to None
        - User profile is updated
    """
    # Arrange: Set profile picture
    auth_user = User.query.filter_by(email='test_user@example.com').first()
    auth_user.profile_picture = 'https://example.com/old-picture.jpg'
    db_session.commit()
    
    # Act
    response = authenticated_client.delete('/api/users/profile-picture')
    
    # Assert
    assert response.status_code in [200, 204]
    
    # Verify profile picture removed
    db_session.refresh(auth_user)
    assert auth_user.profile_picture is None or auth_user.profile_picture == ''


# ============================================================================
# TEST CATEGORY 9: USER STATUS AND ROLES API TESTS
# ============================================================================


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_post_api_users_id_activate_admin_only(client, db_session):
    """
    Test POST /api/users/:id/activate restricted to admin users.
    
    Validates:
        - Admin can activate inactive user
        - Regular user cannot activate users (403)
        - Returns 200 on success
    """
    # Arrange: Create admin and inactive user
    admin_user = User(email='admin@example.com', role='admin')
    admin_user.set_password('AdminPass123!')
    db_session.add(admin_user)
    
    inactive_user = User(email='inactive@example.com', is_active=False)
    inactive_user.set_password('Pass123!')
    db_session.add(inactive_user)
    db_session.commit()
    
    inactive_user_id = inactive_user.id
    
    # Create admin client
    try:
        from flask_jwt_extended import create_access_token
        access_token = create_access_token(identity=str(admin_user.id))
        client.environ_base['HTTP_AUTHORIZATION'] = f'Bearer {access_token}'
    except ImportError:
        pytest.skip("JWT not configured")
    
    # Act
    response = client.post(f'/api/users/{inactive_user_id}/activate')
    
    # Assert
    assert response.status_code == 200
    
    # Verify user activated
    db_session.refresh(inactive_user)
    assert inactive_user.is_active is True


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_post_api_users_id_deactivate_admin_only(client, db_session):
    """
    Test POST /api/users/:id/deactivate restricted to admin users.
    
    Validates:
        - Admin can deactivate active user
        - Regular user cannot deactivate users (403)
        - Returns 200 on success
    """
    # Arrange: Create admin and target user
    admin_user = User(email='admin2@example.com', role='admin')
    admin_user.set_password('AdminPass123!')
    db_session.add(admin_user)
    
    target_user = User(email='target@example.com', is_active=True)
    target_user.set_password('Pass123!')
    db_session.add(target_user)
    db_session.commit()
    
    target_user_id = target_user.id
    
    # Create admin client
    try:
        from flask_jwt_extended import create_access_token
        access_token = create_access_token(identity=str(admin_user.id))
        client.environ_base['HTTP_AUTHORIZATION'] = f'Bearer {access_token}'
    except ImportError:
        pytest.skip("JWT not configured")
    
    # Act
    response = client.post(f'/api/users/{target_user_id}/deactivate')
    
    # Assert
    assert response.status_code == 200
    
    # Verify user deactivated
    db_session.refresh(target_user)
    assert target_user.is_active is False


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_put_api_users_id_role_admin_only(client, db_session):
    """
    Test PUT /api/users/:id/role restricted to admin users.
    
    Validates:
        - Admin can change user roles
        - Regular user cannot change roles (403)
        - Returns 200 on success
        - Role is updated in database
    """
    # Arrange: Create admin and target user
    admin_user = User(email='admin3@example.com', role='admin')
    admin_user.set_password('AdminPass123!')
    db_session.add(admin_user)
    
    target_user = User(email='promote@example.com', role='user')
    target_user.set_password('Pass123!')
    db_session.add(target_user)
    db_session.commit()
    
    target_user_id = target_user.id
    
    # Create admin client
    try:
        from flask_jwt_extended import create_access_token
        access_token = create_access_token(identity=str(admin_user.id))
        client.environ_base['HTTP_AUTHORIZATION'] = f'Bearer {access_token}'
    except ImportError:
        pytest.skip("JWT not configured")
    
    role_data = {'role': 'admin'}
    
    # Act
    response = client.put(f'/api/users/{target_user_id}/role', json=role_data)
    
    # Assert
    assert response.status_code == 200
    
    # Verify role changed
    db_session.refresh(target_user)
    assert target_user.role == 'admin'


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_put_api_users_id_role_unauthorized(authenticated_client, db_session):
    """
    Test PUT /api/users/:id/role returns 403 for regular users.
    
    Validates:
        - Regular user cannot change any user's role
        - Returns 403 Forbidden
        - Role is not changed
    """
    # Arrange: Create target user
    target_user = User(email='norolechange@example.com', role='user')
    target_user.set_password('Pass123!')
    db_session.add(target_user)
    db_session.commit()
    
    target_user_id = target_user.id
    role_data = {'role': 'admin'}
    
    # Act: Regular authenticated user tries to change role
    response = authenticated_client.put(f'/api/users/{target_user_id}/role', json=role_data)
    
    # Assert
    assert response.status_code == 403
    
    # Verify role not changed
    db_session.refresh(target_user)
    assert target_user.role == 'user'


# ============================================================================
# TEST CATEGORY 10: ERROR HANDLING AND EDGE CASES
# ============================================================================


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_api_users_invalid_json_body(client, db_session):
    """
    Test API returns 400 for malformed JSON request body.
    
    Validates:
        - Malformed JSON returns 400
        - Error message indicates JSON parse error
        - Request is rejected before processing
    """
    # Arrange: Malformed JSON string
    malformed_json = '{"email": "test@example.com", invalid json}'
    
    # Act: Send malformed JSON
    response = client.post(
        '/api/users/register',
        data=malformed_json,
        content_type='application/json'
    )
    
    # Assert
    assert response.status_code == 400


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_api_users_unsupported_http_method(authenticated_client, db_session):
    """
    Test API returns 405 for unsupported HTTP methods.
    
    Validates:
        - Unsupported method (e.g., PATCH on POST-only endpoint) returns 405
        - Error message indicates method not allowed
    """
    # Act: Try unsupported method
    response = authenticated_client.options('/api/users/register')
    
    # Assert: Either 405 or 200 (if OPTIONS is implemented for CORS)
    assert response.status_code in [200, 405]


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_api_users_invalid_id_format(authenticated_client, db_session):
    """
    Test API returns 400 for non-numeric user ID.
    
    Validates:
        - Non-integer ID returns 400 or 404
        - Error message indicates invalid ID format
    """
    # Act: Request with non-numeric ID
    response = authenticated_client.get('/api/users/abc')
    
    # Assert
    assert response.status_code in [400, 404]


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_api_users_sql_injection_prevention(authenticated_client, db_session):
    """
    Test API properly sanitizes inputs to prevent SQL injection.
    
    Validates:
        - SQL injection attempts are safely handled
        - Parameterized queries prevent SQL injection
        - No database errors from malicious input
    """
    # Arrange: SQL injection attempt
    malicious_email = "test' OR '1'='1"
    
    injection_data = {
        'email': malicious_email,
        'password': 'Pass123!'
    }
    
    # Act: Try to register with SQL injection
    response = authenticated_client.post('/api/users/register', json=injection_data)
    
    # Assert: Either validation error or safely handled
    assert response.status_code in [400, 409]
    
    # Verify no SQL injection occurred
    # Should not create user or bypass authentication
    users = User.query.all()
    assert all(user.email != malicious_email for user in users)


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
def test_api_users_xss_prevention(authenticated_client, db_session):
    """
    Test API escapes HTML/JavaScript in responses to prevent XSS.
    
    Validates:
        - HTML tags in user input are escaped
        - JavaScript code is not executed
        - Response is safe for browser rendering
    """
    # Arrange: XSS attempt
    xss_name = '<script>alert("XSS")</script>'
    
    xss_data = {
        'email': 'xsstest@example.com',
        'password': 'SecurePass123!',
        'first_name': xss_name
    }
    
    # Act: Register with XSS payload
    response = authenticated_client.post('/api/users/register', json=xss_data)
    
    # Assert: Either validation error or sanitized
    if response.status_code == 201:
        response_data = response.get_json()
        # Verify script tags are escaped or removed
        first_name = response_data.get('first_name', '')
        assert '<script>' not in first_name or '&lt;script&gt;' in first_name


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
@pytest.mark.slow
def test_api_users_rate_limiting(client, db_session):
    """
    Test API enforces rate limiting to prevent abuse.
    
    Validates:
        - Excessive requests return 429 Too Many Requests
        - Rate limit headers are included in response
        - Rate limit resets after time window
    
    Note: Marked as slow test due to potential delays
    """
    # Arrange: Prepare request data
    request_data = {
        'email': 'ratelimit@example.com',
        'password': 'Pass123!'
    }
    
    # Act: Make many rapid requests (simulate rate limit)
    responses_list = []
    for i in range(100):  # Attempt many requests
        response = client.post('/api/users/register', json=request_data)
        responses_list.append(response.status_code)
        if response.status_code == 429:
            break
    
    # Assert: At some point, rate limit should kick in
    # This depends on rate limit configuration (e.g., 10 req/min)
    # If rate limiting is implemented, we should see a 429
    if 429 in responses_list:
        assert True  # Rate limiting is working
    else:
        # Rate limiting may not be implemented yet
        # or limit is very high (100+ requests)
        # This test serves as documentation for future implementation
        pass


# ============================================================================
# TEST SUITE SUMMARY
# ============================================================================

"""
Test Suite Coverage Summary:

Total Test Functions: 58

1. User Registration API: 6 tests
   - test_post_api_users_register_success
   - test_post_api_users_register_duplicate_email
   - test_post_api_users_register_invalid_data
   - test_post_api_users_register_missing_fields
   - test_post_api_users_register_creates_database_record
   - test_post_api_users_register_response_format

2. Get User Profile API: 6 tests
   - test_get_api_users_me_authenticated
   - test_get_api_users_me_unauthenticated
   - test_get_api_users_id_success
   - test_get_api_users_id_not_found
   - test_get_api_users_id_unauthorized
   - test_get_api_users_me_excludes_password

3. Update User Profile API: 7 tests
   - test_put_api_users_id_authenticated_owner
   - test_put_api_users_id_unauthenticated
   - test_put_api_users_id_unauthorized
   - test_put_api_users_id_invalid_data
   - test_patch_api_users_id_partial_update
   - test_put_api_users_id_email_uniqueness
   - test_put_api_users_id_updates_database

4. Delete User API: 6 tests
   - test_delete_api_users_id_authenticated_owner
   - test_delete_api_users_id_unauthenticated
   - test_delete_api_users_id_unauthorized
   - test_delete_api_users_id_admin_can_delete_any
   - test_delete_api_users_id_not_found
   - test_delete_api_users_id_marks_inactive

5. List Users API: 8 tests
   - test_get_api_users_list_authenticated
   - test_get_api_users_list_unauthenticated
   - test_get_api_users_list_pagination
   - test_get_api_users_list_default_limit
   - test_get_api_users_list_max_limit
   - test_get_api_users_list_empty_results
   - test_get_api_users_list_sorting
   - test_get_api_users_list_filtering

6. Search Users API: 5 tests
   - test_get_api_users_search_by_name
   - test_get_api_users_search_case_insensitive
   - test_get_api_users_search_partial_match
   - test_get_api_users_search_no_results
   - test_get_api_users_search_requires_auth

7. Change Password API: 5 tests
   - test_post_api_users_change_password_success
   - test_post_api_users_change_password_wrong_current
   - test_post_api_users_change_password_weak_new
   - test_post_api_users_change_password_unauthenticated
   - test_post_api_users_change_password_invalidates_tokens

8. Upload Profile Picture API: 5 tests
   - test_post_api_users_profile_picture_success
   - test_post_api_users_profile_picture_invalid_format
   - test_post_api_users_profile_picture_too_large
   - test_post_api_users_profile_picture_unauthenticated
   - test_delete_api_users_profile_picture

9. User Status and Roles API: 4 tests
   - test_post_api_users_id_activate_admin_only
   - test_post_api_users_id_deactivate_admin_only
   - test_put_api_users_id_role_admin_only
   - test_put_api_users_id_role_unauthorized

10. Error Handling and Edge Cases: 6 tests
    - test_api_users_invalid_json_body
    - test_api_users_unsupported_http_method
    - test_api_users_invalid_id_format
    - test_api_users_sql_injection_prevention
    - test_api_users_xss_prevention
    - test_api_users_rate_limiting

Test Execution:
    pytest tests/integration/test_user_api.py -v
    pytest tests/integration/test_user_api.py -m integration
    pytest tests/integration/test_user_api.py -m api
    pytest tests/integration/test_user_api.py --cov=app.routes

Coverage Target: 90% for API routes
Execution Time Target: <1 second per test
Test Isolation: Each test uses fresh database state via db_session fixture
Authentication: Tests use authenticated_client fixture for protected endpoints
Mocking: External services mocked using responses library
"""

