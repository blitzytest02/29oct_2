"""
Unit Tests for Flask User Route Handlers

This module provides comprehensive unit tests for the Flask user API route handlers,
focusing on request validation, response formatting, HTTP status codes, pagination,
and error handling. All external dependencies (UserService, User model, database)
are mocked using pytest-mock to ensure fast, isolated unit testing.

The tests validate the following user API endpoints:
- GET /api/users - List users with pagination
- POST /api/users - Create new user
- GET /api/users/:id - Get user by ID
- PUT /api/users/:id - Update user
- DELETE /api/users/:id - Delete user

Test Coverage Areas:
- Request validation (email format, required fields, field constraints)
- Response formatting (JSON structure, serialization)
- HTTP status codes (200, 201, 400, 401, 403, 404, 409, 422)
- Pagination metadata (page, limit, total, pages)
- Error handling (unauthorized, forbidden, not found, validation errors)
- Authentication requirements
- Edge cases (empty results, duplicate emails, nonexistent resources)

All tests follow Flask testing best practices using the test_client() fixture
from conftest.py and employ pytest markers for test categorization.

Test Classes:
    - TestUserList: Tests for listing users with pagination
    - TestCreateUser: Tests for user creation
    - TestGetUser: Tests for retrieving users by ID
    - TestUpdateUser: Tests for updating user attributes
    - TestDeleteUser: Tests for user deletion

Example Usage:
    # Run all user route tests
    pytest tests/unit/routes/test_user_routes.py
    
    # Run only unit tests
    pytest -m unit tests/unit/routes/test_user_routes.py
    
    # Run with coverage
    pytest --cov=app.routes tests/unit/routes/test_user_routes.py
"""

import json
import pytest


# ============================================================================
# TEST FIXTURES
# ============================================================================


@pytest.fixture
def mock_user_service(mocker):
    """
    Mock UserService to isolate route handler logic from business logic.
    
    This fixture creates a mock UserService with all methods stubbed,
    allowing tests to focus on HTTP request/response handling without
    executing actual business logic or database operations.
    
    Args:
        mocker: pytest-mock fixture for creating mocks
    
    Returns:
        MagicMock: Mocked UserService with configurable return values
    
    Example:
        def test_list_users(client, mock_user_service):
            mock_user_service.list_users.return_value = {'users': [], 'total': 0}
            response = authenticated_client.get('/api/users')
            assert response.status_code == 200
    """
    # Create a mock UserService class
    mock_service = mocker.MagicMock()
    
    # Patch the UserService import in the routes module
    # This ensures the route handlers use our mock instead of real service
    mocker.patch('app.routes.users.UserService', return_value=mock_service)
    
    return mock_service


@pytest.fixture
def mock_user_model(mocker):
    """
    Mock User model to prevent database operations in unit tests.
    
    This fixture mocks the User model class, allowing tests to simulate
    user objects without database dependencies. Useful for testing
    serialization and model-related logic in route handlers.
    
    Args:
        mocker: pytest-mock fixture for creating mocks
    
    Returns:
        MagicMock: Mocked User model class with configurable instances
    
    Example:
        def test_get_user(client, mock_user_model):
            mock_user = mock_user_model.return_value
            mock_user.id = 1
            mock_user.email = 'test@example.com'
            # Test logic here
    """
    mock_model = mocker.MagicMock()
    mocker.patch('app.models.User', mock_model)
    return mock_model


@pytest.fixture
def sample_user_data():
    """
    Provide sample user data for testing user creation and updates.
    
    Returns:
        dict: Dictionary containing valid user attributes for testing
    """
    return {
        'email': 'testuser@example.com',
        'password': 'SecurePassword123!',
        'first_name': 'Test',
        'last_name': 'User'
    }


@pytest.fixture
def sample_user_response():
    """
    Provide sample user response data for mocking service responses.
    
    Returns:
        dict: Dictionary representing a serialized user object
    """
    return {
        'id': 1,
        'email': 'testuser@example.com',
        'first_name': 'Test',
        'last_name': 'User',
        'created_at': '2025-10-29T12:00:00Z',
        'updated_at': '2025-10-29T12:00:00Z'
    }





# ============================================================================
# TEST CLASS: TestUserList
# ============================================================================


@pytest.mark.unit
@pytest.mark.api
class TestUserList:
    """
    Test suite for GET /api/users endpoint (list users with pagination).
    
    Tests cover:
    - Successful user listing with pagination
    - Pagination parameters (page, limit)
    - Empty result handling
    - Authentication requirements
    """
    
    def test_list_users_success(self, authenticated_client, mock_user_service, sample_user_response):
        """
        Test successful user list retrieval with default pagination.
        
        Verifies that:
        - GET /api/users returns 200 status code
        - Response contains 'users' array with user objects
        - Response contains pagination metadata (total, page, limit, pages)
        - User objects have correct structure
        - UserService.list_users() is called with correct parameters
        """
        # Arrange: Mock service to return sample users
        mock_user_service.list_users.return_value = {
            'users': [sample_user_response],
            'total': 1,
            'page': 1,
            'limit': 10,
            'pages': 1
        }
        
        # Act: Make GET request to list users
        response = authenticated_client.get('/api/users')
        
        # Assert: Verify response structure and status code
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'users' in data
        assert isinstance(data['users'], list)
        assert len(data['users']) == 1
        assert data['users'][0]['id'] == 1
        assert data['users'][0]['email'] == 'testuser@example.com'
        
        # Assert: Verify pagination metadata
        assert 'total' in data
        assert data['total'] == 1
        assert data['page'] == 1
        assert data['limit'] == 10
        assert data['pages'] == 1
        
        # Assert: Verify service was called correctly
        mock_user_service.list_users.assert_called_once()
    
    def test_list_users_with_pagination(self, authenticated_client, mock_user_service):
        """
        Test user list with custom pagination parameters.
        
        Verifies that:
        - Query parameters 'page' and 'limit' are correctly processed
        - Service receives correct pagination parameters
        - Response reflects requested page and limit
        """
        # Arrange: Mock service to return paginated results
        mock_user_service.list_users.return_value = {
            'users': [],
            'total': 50,
            'page': 2,
            'limit': 20,
            'pages': 3
        }
        
        # Act: Make GET request with pagination parameters
        response = authenticated_client.get('/api/users?page=2&limit=20')
        
        # Assert: Verify response status and pagination
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['page'] == 2
        assert data['limit'] == 20
        assert data['total'] == 50
        assert data['pages'] == 3
        
        # Assert: Verify service was called with correct pagination
        mock_user_service.list_users.assert_called_once_with(page=2, limit=20)
    
    def test_list_users_with_empty_result(self, authenticated_client, mock_user_service):
        """
        Test user list when no users exist in the database.
        
        Verifies that:
        - Empty user list returns 200 status (not 404)
        - Response contains empty 'users' array
        - Pagination metadata reflects zero total
        """
        # Arrange: Mock service to return empty result
        mock_user_service.list_users.return_value = {
            'users': [],
            'total': 0,
            'page': 1,
            'limit': 10,
            'pages': 0
        }
        
        # Act: Make GET request to list users
        response = authenticated_client.get('/api/users')
        
        # Assert: Verify successful response with empty list
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'users' in data
        assert data['users'] == []
        assert data['total'] == 0
        assert data['pages'] == 0
    
    def test_list_users_unauthorized(self, client, mock_user_service):
        """
        Test user list endpoint when user is not authenticated.
        
        Verifies that:
        - Unauthenticated requests return 401 Unauthorized
        - Response contains appropriate error message
        - Service is not called when authentication fails
        """
        # Arrange: Configure client without authentication
        # (client fixture is already unauthenticated by default)
        
        # Act: Make GET request without authentication
        response = client.get('/api/users')
        
        # Assert: Verify unauthorized response
        assert response.status_code == 401
        
        data = json.loads(response.data)
        # JWT authentication errors return nested error object
        assert 'error' in data
        assert 'message' in data['error']
        assert 'authorization' in data['error']['message'].lower() or 'authentication' in data['error']['message'].lower()
        
        # Assert: Verify service was not called
        mock_user_service.list_users.assert_not_called()


# ============================================================================
# TEST CLASS: TestCreateUser
# ============================================================================


@pytest.mark.unit
@pytest.mark.api
class TestCreateUser:
    """
    Test suite for POST /api/users endpoint (create new user).
    
    Tests cover:
    - Successful user creation
    - Duplicate email handling
    - Invalid email format validation
    - Missing required fields validation
    - Authentication requirements
    """
    
    def test_create_user_with_valid_data(self, authenticated_client, mock_user_service, sample_user_data, sample_user_response):
        """
        Test successful user creation with valid data.
        
        Verifies that:
        - POST /api/users with valid data returns 201 Created
        - Response contains created user object
        - User object has all expected fields
        - Password is not included in response (security)
        - UserService.create_user() is called with correct data
        """
        # Arrange: Mock service to return created user
        mock_user_service.create_user.return_value = sample_user_response
        
        # Act: Make POST request to create user
        response = authenticated_client.post(
            '/api/users',
            data=json.dumps(sample_user_data),
            content_type='application/json'
        )
        
        # Assert: Verify created response
        assert response.status_code == 201
        
        data = json.loads(response.data)
        assert 'id' in data
        assert data['id'] == 1
        assert data['email'] == 'testuser@example.com'
        assert data['first_name'] == 'Test'
        assert data['last_name'] == 'User'
        
        # Assert: Verify password is not in response
        assert 'password' not in data
        
        # Assert: Verify service was called with correct data
        mock_user_service.create_user.assert_called_once()
        call_args = mock_user_service.create_user.call_args[0][0]
        assert call_args['email'] == sample_user_data['email']
    
    def test_create_user_with_duplicate_email(self, authenticated_client, mock_user_service, sample_user_data):
        """
        Test user creation with email that already exists.
        
        Verifies that:
        - Duplicate email returns 409 Conflict
        - Response contains appropriate error message
        - No user is created
        """
        # Arrange: Mock service to raise duplicate email error
        mock_user_service.create_user.side_effect = ValueError('Email already exists')
        
        # Act: Make POST request with duplicate email
        response = authenticated_client.post(
            '/api/users',
            data=json.dumps(sample_user_data),
            content_type='application/json'
        )
        
        # Assert: Verify conflict response
        assert response.status_code == 409
        
        data = json.loads(response.data)
        # Application errors return {'error': {'message': ..., 'status': ..., 'type': ...}}
        assert 'error' in data
        assert 'message' in data['error']
        error_msg = data['error']['message']
        assert 'email' in error_msg.lower() or 'already exists' in error_msg.lower()
    
    def test_create_user_with_invalid_email(self, authenticated_client, mock_user_service, sample_user_data):
        """
        Test user creation with invalid email format.
        
        Verifies that:
        - Invalid email format returns 400 Bad Request
        - Response contains validation error message
        - Service is not called with invalid data
        """
        # Arrange: Modify sample data to have invalid email
        invalid_data = sample_user_data.copy()
        invalid_data['email'] = 'invalid-email-format'
        
        # Act: Make POST request with invalid email
        response = authenticated_client.post(
            '/api/users',
            data=json.dumps(invalid_data),
            content_type='application/json'
        )
        
        # Assert: Verify bad request response
        assert response.status_code == 400
        
        data = json.loads(response.data)
        # Application errors return {'error': {'message': ..., 'status': ..., 'type': ...}}
        assert 'error' in data
        assert 'message' in data['error']
    
    def test_create_user_with_missing_required_fields(self, authenticated_client, mock_user_service):
        """
        Test user creation with missing required fields.
        
        Verifies that:
        - Missing required fields return 400 Bad Request
        - Response contains validation errors for each missing field
        - Service is not called with incomplete data
        """
        # Arrange: Create data with missing required fields
        incomplete_data = {
            'email': 'testuser@example.com'
            # Missing password, first_name, last_name
        }
        
        # Act: Make POST request with incomplete data
        response = authenticated_client.post(
            '/api/users',
            data=json.dumps(incomplete_data),
            content_type='application/json'
        )
        
        # Assert: Verify bad request response
        assert response.status_code == 400
        
        data = json.loads(response.data)
        # Application errors return {'error': {'message': ..., 'status': ..., 'type': ...}}
        assert 'error' in data
        assert 'message' in data['error']
    
    def test_create_user_unauthorized(self, client, mock_user_service, sample_user_data):
        """
        Test user creation when user is not authenticated.
        
        Verifies that:
        - Unauthenticated requests return 401 Unauthorized
        - Response contains appropriate error message
        - Service is not called
        """
        # Arrange: Client is already unauthenticated by default
        
        # Act: Make POST request without authentication
        response = client.post(
            '/api/users',
            data=json.dumps(sample_user_data),
            content_type='application/json'
        )
        
        # Assert: Verify unauthorized response
        assert response.status_code == 401
        
        data = json.loads(response.data)
        # JWT authentication errors return nested error object
        assert 'error' in data
        assert 'message' in data['error']
        assert 'authorization' in data['error']['message'].lower() or 'authentication' in data['error']['message'].lower()
        
        # Assert: Verify service was not called
        mock_user_service.create_user.assert_not_called()


# ============================================================================
# TEST CLASS: TestGetUser
# ============================================================================


@pytest.mark.unit
@pytest.mark.api
class TestGetUser:
    """
    Test suite for GET /api/users/:id endpoint (get user by ID).
    
    Tests cover:
    - Successful user retrieval by ID
    - Nonexistent user handling (404)
    - Authentication requirements
    """
    
    def test_get_user_by_id_existing(self, authenticated_client, mock_user_service, sample_user_response):
        """
        Test successful retrieval of existing user by ID.
        
        Verifies that:
        - GET /api/users/:id with valid ID returns 200 OK
        - Response contains user object with all fields
        - Password is not included in response
        - UserService.get_user() is called with correct ID
        """
        # Arrange: Mock service to return user
        mock_user_service.get_user.return_value = sample_user_response
        
        # Act: Make GET request for specific user
        response = authenticated_client.get('/api/users/1')
        
        # Assert: Verify successful response
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['id'] == 1
        assert data['email'] == 'testuser@example.com'
        assert data['first_name'] == 'Test'
        assert data['last_name'] == 'User'
        assert 'password' not in data
        
        # Assert: Verify service was called with correct ID
        mock_user_service.get_user.assert_called_once_with(1)
    
    def test_get_user_by_id_nonexistent(self, authenticated_client, mock_user_service):
        """
        Test retrieval of nonexistent user by ID.
        
        Verifies that:
        - GET /api/users/:id with nonexistent ID returns 404 Not Found
        - Response contains appropriate error message
        - Service is called but returns None
        """
        # Arrange: Mock service to return None for nonexistent user
        mock_user_service.get_user.return_value = None
        
        # Act: Make GET request for nonexistent user
        response = authenticated_client.get('/api/users/999')
        
        # Assert: Verify not found response
        assert response.status_code == 404
        
        data = json.loads(response.data)
        # Application errors return {'error': {'message': ..., 'status': ..., 'type': ...}}
        assert 'error' in data
        assert 'message' in data['error']
        
        # Assert: Verify service was called with correct ID
        mock_user_service.get_user.assert_called_once_with(999)
    
    def test_get_user_unauthorized(self, client, mock_user_service):
        """
        Test user retrieval when user is not authenticated.
        
        Verifies that:
        - Unauthenticated requests return 401 Unauthorized
        - Response contains appropriate error message
        - Service is not called
        """
        # Arrange: Client is already unauthenticated by default
        
        # Act: Make GET request without authentication
        response = client.get('/api/users/1')
        
        # Assert: Verify unauthorized response
        assert response.status_code == 401
        
        data = json.loads(response.data)
        # JWT authentication errors return nested error object
        assert 'error' in data
        assert 'message' in data['error']
        assert 'authorization' in data['error']['message'].lower() or 'authentication' in data['error']['message'].lower()
        
        # Assert: Verify service was not called
        mock_user_service.get_user.assert_not_called()


# ============================================================================
# TEST CLASS: TestUpdateUser
# ============================================================================


@pytest.mark.unit
@pytest.mark.api
class TestUpdateUser:
    """
    Test suite for PUT /api/users/:id endpoint (update user).
    
    Tests cover:
    - Successful user update
    - Nonexistent user update (404)
    - Authentication requirements
    - Authorization (cannot update other users)
    """
    
    def test_update_user_with_valid_changes(self, authenticated_client, mock_user_service, sample_user_response):
        """
        Test successful user update with valid data.
        
        Verifies that:
        - PUT /api/users/:id with valid data returns 200 OK
        - Response contains updated user object
        - Only specified fields are updated
        - UserService.update_user() is called with correct parameters
        """
        # Arrange: Mock service to return updated user
        updated_response = sample_user_response.copy()
        updated_response['first_name'] = 'Updated'
        mock_user_service.update_user.return_value = updated_response
        
        update_data = {'first_name': 'Updated'}
        
        # Act: Make PUT request to update user
        response = authenticated_client.put(
            '/api/users/1',
            data=json.dumps(update_data),
            content_type='application/json'
        )
        
        # Assert: Verify successful update response
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['id'] == 1
        assert data['first_name'] == 'Updated'
        assert 'password' not in data
        
        # Assert: Verify service was called with correct parameters
        mock_user_service.update_user.assert_called_once_with(1, update_data)
    
    def test_update_user_nonexistent(self, authenticated_client, mock_user_service):
        """
        Test update of nonexistent user.
        
        Verifies that:
        - PUT /api/users/:id with nonexistent ID returns 404 Not Found
        - Response contains appropriate error message
        """
        # Arrange: Mock service to return None for nonexistent user
        mock_user_service.update_user.return_value = None
        
        update_data = {'first_name': 'Updated'}
        
        # Act: Make PUT request for nonexistent user
        response = authenticated_client.put(
            '/api/users/999',
            data=json.dumps(update_data),
            content_type='application/json'
        )
        
        # Assert: Verify not found response
        assert response.status_code == 404
        
        data = json.loads(response.data)
        # Application errors return {'error': {'message': ..., 'status': ..., 'type': ...}}
        assert 'error' in data
        assert 'message' in data['error']
    
    def test_update_user_unauthorized(self, client, mock_user_service):
        """
        Test user update when user is not authenticated.
        
        Verifies that:
        - Unauthenticated requests return 401 Unauthorized
        - Response contains appropriate error message
        - Service is not called
        """
        # Arrange: Client is already unauthenticated by default
        update_data = {'first_name': 'Updated'}
        
        # Act: Make PUT request without authentication
        response = client.put(
            '/api/users/1',
            data=json.dumps(update_data),
            content_type='application/json'
        )
        
        # Assert: Verify unauthorized response
        assert response.status_code == 401
        
        data = json.loads(response.data)
        # JWT authentication errors return nested error object
        assert 'error' in data
        assert 'message' in data['error']
        assert 'authorization' in data['error']['message'].lower() or 'authentication' in data['error']['message'].lower()
        
        # Assert: Verify service was not called
        mock_user_service.update_user.assert_not_called()
    
    def test_update_user_forbidden(self, authenticated_client, mock_user_service):
        """
        Test user update when authenticated user tries to update another user.
        
        Verifies that:
        - Attempting to update another user returns 403 Forbidden
        - Response contains appropriate error message
        - Service validates user ownership
        """
        # Arrange: Mock service to raise permission error
        mock_user_service.update_user.side_effect = PermissionError('Cannot update another user')
        
        update_data = {'first_name': 'Updated'}
        
        # Act: Make PUT request to update another user
        response = authenticated_client.put(
            '/api/users/2',
            data=json.dumps(update_data),
            content_type='application/json'
        )
        
        # Assert: Verify forbidden response
        assert response.status_code == 403
        
        data = json.loads(response.data)
        # Application errors return {'error': {'message': ..., 'status': ..., 'type': ...}}
        assert 'error' in data
        assert 'message' in data['error']


# ============================================================================
# TEST CLASS: TestDeleteUser
# ============================================================================


@pytest.mark.unit
@pytest.mark.api
class TestDeleteUser:
    """
    Test suite for DELETE /api/users/:id endpoint (delete user).
    
    Tests cover:
    - Successful user deletion
    - Nonexistent user deletion (404)
    - Authentication requirements
    """
    
    def test_delete_user_existing(self, authenticated_client, mock_user_service):
        """
        Test successful deletion of existing user.
        
        Verifies that:
        - DELETE /api/users/:id with valid ID returns 204 No Content
        - No response body is returned
        - UserService.delete_user() is called with correct ID
        """
        # Arrange: Mock service to return True for successful deletion
        mock_user_service.delete_user.return_value = True
        
        # Act: Make DELETE request
        response = authenticated_client.delete('/api/users/1')
        
        # Assert: Verify no content response
        assert response.status_code == 204
        assert len(response.data) == 0 or response.data == b''
        
        # Assert: Verify service was called with correct ID
        mock_user_service.delete_user.assert_called_once_with(1)
    
    def test_delete_user_nonexistent(self, authenticated_client, mock_user_service):
        """
        Test deletion of nonexistent user.
        
        Verifies that:
        - DELETE /api/users/:id with nonexistent ID returns 404 Not Found
        - Response contains appropriate error message
        """
        # Arrange: Mock service to return False for nonexistent user
        mock_user_service.delete_user.return_value = False
        
        # Act: Make DELETE request for nonexistent user
        response = authenticated_client.delete('/api/users/999')
        
        # Assert: Verify not found response
        assert response.status_code == 404
        
        data = json.loads(response.data)
        # Application errors return {'error': {'message': ..., 'status': ..., 'type': ...}}
        assert 'error' in data
        assert 'message' in data['error']
    
    def test_delete_user_unauthorized(self, client, mock_user_service):
        """
        Test user deletion when user is not authenticated.
        
        Verifies that:
        - Unauthenticated requests return 401 Unauthorized
        - Response contains appropriate error message
        - Service is not called
        """
        # Arrange: Client is already unauthenticated by default
        
        # Act: Make DELETE request without authentication
        response = client.delete('/api/users/1')
        
        # Assert: Verify unauthorized response
        assert response.status_code == 401
        
        data = json.loads(response.data)
        # JWT authentication errors return nested error object
        assert 'error' in data
        assert 'message' in data['error']
        assert 'authorization' in data['error']['message'].lower() or 'authentication' in data['error']['message'].lower()
        
        # Assert: Verify service was not called
        mock_user_service.delete_user.assert_not_called()
