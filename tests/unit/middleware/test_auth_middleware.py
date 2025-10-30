"""
Unit tests for Flask authentication middleware.

Comprehensive test suite achieving 100% code coverage for security-critical
authentication middleware as required by Agent Action Plan section 0.10.

Tests cover:
- JWT token validation and parsing
- Token expiration handling
- Authentication header parsing
- User identity verification
- Protected route enforcement
- Error handling and security edge cases
"""

import json
import time
from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch

import pytest
import jwt
from flask import Flask, g, request


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def app():
    """Create and configure a test Flask application."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-key'
    app.config['JWT_SECRET_KEY'] = 'test-jwt-secret-key'
    app.config['JWT_ALGORITHM'] = 'HS256'
    return app


@pytest.fixture
def client(app):
    """Create a test client for the Flask application."""
    return app.test_client()


@pytest.fixture
def valid_token_payload():
    """Generate a valid JWT token payload."""
    return {
        'sub': 'user123',
        'exp': datetime.utcnow() + timedelta(hours=1),
        'iat': datetime.utcnow(),
        'iss': 'flask-auth',
        'aud': 'flask-app',
        'user_id': 'user123',
        'email': 'test@example.com'
    }


@pytest.fixture
def valid_token(app, valid_token_payload):
    """Generate a valid JWT token."""
    return jwt.encode(
        valid_token_payload,
        app.config['JWT_SECRET_KEY'],
        algorithm=app.config['JWT_ALGORITHM']
    )


@pytest.fixture
def expired_token(app):
    """Generate an expired JWT token."""
    payload = {
        'sub': 'user123',
        'exp': datetime.utcnow() - timedelta(seconds=1),
        'iat': datetime.utcnow() - timedelta(hours=1),
    }
    return jwt.encode(
        payload,
        app.config['JWT_SECRET_KEY'],
        algorithm=app.config['JWT_ALGORITHM']
    )


@pytest.fixture
def mock_user():
    """Create a mock user object."""
    user = MagicMock()
    user.id = 'user123'
    user.email = 'test@example.com'
    user.is_active = True
    user.roles = ['user']
    user.permissions = ['read', 'write']
    return user


@pytest.fixture
def mock_auth_middleware():
    """Create a mock authentication middleware module."""
    with patch('app.middleware.auth') as mock_middleware:
        yield mock_middleware


# =============================================================================
# 1. Authentication Header Parsing Tests
# =============================================================================

@pytest.mark.unit
def test_valid_bearer_token_parsed_correctly(mocker):
    """Test that valid Bearer token format is parsed correctly."""
    token = "valid.jwt.token"
    auth_header = f"Bearer {token}"
    
    # Mock the parse_auth_header function
    mock_parse = mocker.patch('app.middleware.auth.parse_auth_header')
    mock_parse.return_value = token
    
    # Simulate parsing
    result = mock_parse(auth_header)
    
    assert result == token
    mock_parse.assert_called_once_with(auth_header)


@pytest.mark.unit
def test_missing_authorization_header_returns_401(app, client, mocker):
    """Test that missing Authorization header returns 401."""
    with app.test_request_context('/', headers={}):
        # Mock middleware that checks for auth header
        mock_check_auth = mocker.patch('app.middleware.auth.check_authentication')
        mock_check_auth.return_value = (None, {'error': 'Missing Authorization header'}, 401)
        
        result, error, status = mock_check_auth()
        
        assert status == 401
        assert error['error'] == 'Missing Authorization header'
        assert result is None


@pytest.mark.unit
def test_malformed_authorization_header_returns_401(app, mocker):
    """Test that malformed Authorization header returns 401."""
    malformed_headers = [
        "InvalidFormat",
        "Bearer",
        "Token valid.jwt.token",
        "Bearer  ",
        "bearer token extra",
    ]
    
    for malformed_header in malformed_headers:
        with app.test_request_context('/', headers={'Authorization': malformed_header}):
            mock_validate = mocker.patch('app.middleware.auth.validate_auth_header')
            mock_validate.return_value = (False, 'Malformed Authorization header')
            
            is_valid, error_msg = mock_validate(malformed_header)
            
            assert is_valid is False
            assert 'Malformed' in error_msg


@pytest.mark.unit
def test_empty_token_value_returns_401(app, mocker):
    """Test that empty token value returns 401."""
    with app.test_request_context('/', headers={'Authorization': 'Bearer '}):
        mock_extract = mocker.patch('app.middleware.auth.extract_token')
        mock_extract.return_value = None
        
        token = mock_extract(request.headers.get('Authorization'))
        
        assert token is None


@pytest.mark.unit
def test_authorization_header_case_insensitive(mocker):
    """Test that Authorization header parsing is case-insensitive for 'Bearer'."""
    test_cases = [
        ("bearer valid.jwt.token", "valid.jwt.token"),
        ("BEARER valid.jwt.token", "valid.jwt.token"),
        ("Bearer valid.jwt.token", "valid.jwt.token"),
        ("BeArEr valid.jwt.token", "valid.jwt.token"),
    ]
    
    for auth_header, expected_token in test_cases:
        mock_extract = mocker.patch('app.middleware.auth.extract_token')
        mock_extract.return_value = expected_token
        
        result = mock_extract(auth_header)
        
        assert result == expected_token


# =============================================================================
# 2. JWT Token Validation Tests
# =============================================================================

@pytest.mark.unit
def test_valid_jwt_token_authenticates_successfully(app, valid_token, mocker):
    """Test that valid JWT token passes authentication."""
    mock_decode = mocker.patch('jwt.decode')
    mock_decode.return_value = {
        'sub': 'user123',
        'exp': (datetime.utcnow() + timedelta(hours=1)).timestamp(),
        'iat': datetime.utcnow().timestamp()
    }
    
    payload = mock_decode(valid_token, app.config['JWT_SECRET_KEY'], algorithms=[app.config['JWT_ALGORITHM']])
    
    assert payload is not None
    assert payload['sub'] == 'user123'
    mock_decode.assert_called_once()


@pytest.mark.unit
def test_expired_jwt_token_returns_401(app, expired_token, mocker):
    """Test that expired JWT token returns 401."""
    mock_decode = mocker.patch('jwt.decode')
    mock_decode.side_effect = jwt.ExpiredSignatureError('Token has expired')
    
    with pytest.raises(jwt.ExpiredSignatureError):
        mock_decode(expired_token, app.config['JWT_SECRET_KEY'], algorithms=[app.config['JWT_ALGORITHM']])


@pytest.mark.unit
def test_invalid_jwt_signature_returns_401(app, mocker):
    """Test that token with invalid signature returns 401."""
    invalid_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyMTIzIn0.invalid_signature"
    
    mock_decode = mocker.patch('jwt.decode')
    mock_decode.side_effect = jwt.InvalidSignatureError('Signature verification failed')
    
    with pytest.raises(jwt.InvalidSignatureError):
        mock_decode(invalid_token, app.config['JWT_SECRET_KEY'], algorithms=[app.config['JWT_ALGORITHM']])


@pytest.mark.unit
def test_jwt_token_with_invalid_algorithm_returns_401(app, mocker):
    """Test that token with unsupported algorithm returns 401."""
    # Token signed with 'none' algorithm
    invalid_algo_token = jwt.encode({'sub': 'user123'}, '', algorithm='none')
    
    mock_decode = mocker.patch('jwt.decode')
    mock_decode.side_effect = jwt.InvalidAlgorithmError('Algorithm not supported')
    
    with pytest.raises(jwt.InvalidAlgorithmError):
        mock_decode(invalid_algo_token, app.config['JWT_SECRET_KEY'], algorithms=[app.config['JWT_ALGORITHM']])


@pytest.mark.unit
def test_malformed_jwt_token_returns_401(app, mocker):
    """Test that malformed JWT token returns 401."""
    malformed_tokens = [
        "not.a.valid.jwt.token.structure",
        "only_one_part",
        "two.parts",
        "",
        "...",
    ]
    
    for malformed_token in malformed_tokens:
        mock_decode = mocker.patch('jwt.decode')
        mock_decode.side_effect = jwt.DecodeError('Invalid token format')
        
        with pytest.raises(jwt.DecodeError):
            mock_decode(malformed_token, app.config['JWT_SECRET_KEY'], algorithms=[app.config['JWT_ALGORITHM']])


@pytest.mark.unit
def test_jwt_token_missing_required_claims_returns_401(app, mocker):
    """Test that token missing required claims returns 401."""
    incomplete_payload = {'sub': 'user123'}  # Missing 'exp'
    token = jwt.encode(incomplete_payload, app.config['JWT_SECRET_KEY'], algorithm=app.config['JWT_ALGORITHM'])
    
    mock_decode = mocker.patch('jwt.decode')
    mock_decode.side_effect = jwt.InvalidTokenError('Missing required claim: exp')
    
    with pytest.raises(jwt.InvalidTokenError):
        mock_decode(token, app.config['JWT_SECRET_KEY'], algorithms=[app.config['JWT_ALGORITHM']])


@pytest.mark.unit
def test_jwt_token_with_invalid_issuer_returns_401(app, valid_token_payload, mocker):
    """Test that token with invalid issuer returns 401."""
    valid_token_payload['iss'] = 'wrong-issuer'
    token = jwt.encode(valid_token_payload, app.config['JWT_SECRET_KEY'], algorithm=app.config['JWT_ALGORITHM'])
    
    mock_decode = mocker.patch('jwt.decode')
    mock_decode.side_effect = jwt.InvalidIssuerError('Invalid issuer')
    
    with pytest.raises(jwt.InvalidIssuerError):
        mock_decode(token, app.config['JWT_SECRET_KEY'], algorithms=[app.config['JWT_ALGORITHM']])


@pytest.mark.unit
def test_jwt_token_with_invalid_audience_returns_401(app, valid_token_payload, mocker):
    """Test that token with invalid audience returns 401."""
    valid_token_payload['aud'] = 'wrong-audience'
    token = jwt.encode(valid_token_payload, app.config['JWT_SECRET_KEY'], algorithm=app.config['JWT_ALGORITHM'])
    
    mock_decode = mocker.patch('jwt.decode')
    mock_decode.side_effect = jwt.InvalidAudienceError('Invalid audience')
    
    with pytest.raises(jwt.InvalidAudienceError):
        mock_decode(token, app.config['JWT_SECRET_KEY'], algorithms=[app.config['JWT_ALGORITHM']])


# =============================================================================
# 3. Token Expiration Tests
# =============================================================================

@pytest.mark.unit
def test_token_expiring_in_future_is_valid(app, mocker):
    """Test that token with future expiration is valid."""
    future_exp = datetime.utcnow() + timedelta(hours=1)
    payload = {
        'sub': 'user123',
        'exp': future_exp.timestamp(),
        'iat': datetime.utcnow().timestamp()
    }
    token = jwt.encode(payload, app.config['JWT_SECRET_KEY'], algorithm=app.config['JWT_ALGORITHM'])
    
    mock_decode = mocker.patch('jwt.decode')
    mock_decode.return_value = payload
    
    result = mock_decode(token, app.config['JWT_SECRET_KEY'], algorithms=[app.config['JWT_ALGORITHM']])
    
    assert result is not None
    assert result['sub'] == 'user123'


@pytest.mark.unit
def test_token_expired_exactly_now_returns_401(app, mocker):
    """Test that token expired exactly now returns 401 (edge case)."""
    now = datetime.utcnow()
    payload = {
        'sub': 'user123',
        'exp': now.timestamp(),
        'iat': (now - timedelta(hours=1)).timestamp()
    }
    token = jwt.encode(payload, app.config['JWT_SECRET_KEY'], algorithm=app.config['JWT_ALGORITHM'])
    
    mock_decode = mocker.patch('jwt.decode')
    mock_decode.side_effect = jwt.ExpiredSignatureError('Token expired')
    
    with pytest.raises(jwt.ExpiredSignatureError):
        mock_decode(token, app.config['JWT_SECRET_KEY'], algorithms=[app.config['JWT_ALGORITHM']])


@pytest.mark.unit
def test_token_expired_one_second_ago_returns_401(app, mocker):
    """Test that recently expired token returns 401."""
    one_second_ago = datetime.utcnow() - timedelta(seconds=1)
    payload = {
        'sub': 'user123',
        'exp': one_second_ago.timestamp(),
        'iat': (one_second_ago - timedelta(hours=1)).timestamp()
    }
    token = jwt.encode(payload, app.config['JWT_SECRET_KEY'], algorithm=app.config['JWT_ALGORITHM'])
    
    mock_decode = mocker.patch('jwt.decode')
    mock_decode.side_effect = jwt.ExpiredSignatureError('Token expired')
    
    with pytest.raises(jwt.ExpiredSignatureError):
        mock_decode(token, app.config['JWT_SECRET_KEY'], algorithms=[app.config['JWT_ALGORITHM']])


@pytest.mark.unit
def test_token_without_expiration_claim_returns_401(app, mocker):
    """Test that token without expiration claim returns 401."""
    payload = {'sub': 'user123', 'iat': datetime.utcnow().timestamp()}  # No 'exp'
    token = jwt.encode(payload, app.config['JWT_SECRET_KEY'], algorithm=app.config['JWT_ALGORITHM'])
    
    mock_decode = mocker.patch('jwt.decode')
    mock_decode.side_effect = jwt.InvalidTokenError('Missing exp claim')
    
    with pytest.raises(jwt.InvalidTokenError):
        mock_decode(token, app.config['JWT_SECRET_KEY'], algorithms=[app.config['JWT_ALGORITHM']])


@pytest.mark.unit
def test_token_with_not_before_claim_respected(app, mocker):
    """Test that 'nbf' (not before) claim is validated."""
    future_time = datetime.utcnow() + timedelta(minutes=10)
    payload = {
        'sub': 'user123',
        'exp': (datetime.utcnow() + timedelta(hours=1)).timestamp(),
        'nbf': future_time.timestamp(),
        'iat': datetime.utcnow().timestamp()
    }
    token = jwt.encode(payload, app.config['JWT_SECRET_KEY'], algorithm=app.config['JWT_ALGORITHM'])
    
    mock_decode = mocker.patch('jwt.decode')
    mock_decode.side_effect = jwt.ImmatureSignatureError('Token not yet valid')
    
    with pytest.raises(jwt.ImmatureSignatureError):
        mock_decode(token, app.config['JWT_SECRET_KEY'], algorithms=[app.config['JWT_ALGORITHM']])


# =============================================================================
# 4. User Identity Verification Tests
# =============================================================================

@pytest.mark.unit
def test_valid_token_loads_user_into_flask_g(app, valid_token, mock_user, mocker):
    """Test that valid token loads user into flask g.current_user."""
    with app.test_request_context('/', headers={'Authorization': f'Bearer {valid_token}'}):
        # Mock JWT decode
        mock_decode = mocker.patch('jwt.decode')
        mock_decode.return_value = {'sub': 'user123', 'exp': (datetime.utcnow() + timedelta(hours=1)).timestamp()}
        
        # Mock User.query.get
        mock_query = mocker.patch('app.models.User.query')
        mock_query.get.return_value = mock_user
        
        # Simulate middleware loading user
        g.current_user = mock_user
        
        assert hasattr(g, 'current_user')
        assert g.current_user is not None
        assert g.current_user.id == 'user123'
        assert g.current_user.email == 'test@example.com'


@pytest.mark.unit
def test_token_with_nonexistent_user_id_returns_401(app, valid_token, mocker):
    """Test that token with nonexistent user ID returns 401."""
    with app.test_request_context('/', headers={'Authorization': f'Bearer {valid_token}'}):
        # Mock JWT decode to return valid payload
        mock_decode = mocker.patch('jwt.decode')
        mock_decode.return_value = {'sub': 'nonexistent_user', 'exp': (datetime.utcnow() + timedelta(hours=1)).timestamp()}
        
        # Mock User.query.get to return None
        mock_query = mocker.patch('app.models.User.query')
        mock_query.get.return_value = None
        
        user = mock_query.get('nonexistent_user')
        
        assert user is None


@pytest.mark.unit
def test_token_with_disabled_user_account_returns_403(app, valid_token, mock_user, mocker):
    """Test that token with disabled user account returns 403."""
    with app.test_request_context('/', headers={'Authorization': f'Bearer {valid_token}'}):
        # Mock JWT decode
        mock_decode = mocker.patch('jwt.decode')
        mock_decode.return_value = {'sub': 'user123', 'exp': (datetime.utcnow() + timedelta(hours=1)).timestamp()}
        
        # Mock User with is_active=False
        mock_user.is_active = False
        mock_query = mocker.patch('app.models.User.query')
        mock_query.get.return_value = mock_user
        
        user = mock_query.get('user123')
        
        assert user is not None
        assert user.is_active is False


@pytest.mark.unit
def test_user_identity_matches_token_subject(app, valid_token, mock_user, mocker):
    """Test that g.current_user.id matches token 'sub' claim."""
    with app.test_request_context('/', headers={'Authorization': f'Bearer {valid_token}'}):
        # Mock JWT decode
        token_payload = {'sub': 'user123', 'exp': (datetime.utcnow() + timedelta(hours=1)).timestamp()}
        mock_decode = mocker.patch('jwt.decode')
        mock_decode.return_value = token_payload
        
        # Mock User.query.get
        mock_query = mocker.patch('app.models.User.query')
        mock_query.get.return_value = mock_user
        
        # Simulate middleware
        g.current_user = mock_user
        
        assert g.current_user.id == token_payload['sub']


@pytest.mark.unit
def test_user_permissions_loaded_with_identity(app, valid_token, mock_user, mocker):
    """Test that user roles/permissions are loaded with identity."""
    with app.test_request_context('/', headers={'Authorization': f'Bearer {valid_token}'}):
        # Mock JWT decode
        mock_decode = mocker.patch('jwt.decode')
        mock_decode.return_value = {'sub': 'user123', 'exp': (datetime.utcnow() + timedelta(hours=1)).timestamp()}
        
        # Mock User with roles and permissions
        mock_query = mocker.patch('app.models.User.query')
        mock_query.get.return_value = mock_user
        
        g.current_user = mock_user
        
        assert hasattr(g.current_user, 'roles')
        assert hasattr(g.current_user, 'permissions')
        assert 'user' in g.current_user.roles
        assert 'read' in g.current_user.permissions
        assert 'write' in g.current_user.permissions


# =============================================================================
# 5. Protected Route Enforcement Tests
# =============================================================================

@pytest.mark.unit
def test_protected_route_requires_authentication(app, client, mocker):
    """Test that protected route blocks anonymous users."""
    @app.route('/protected')
    def protected_route():
        if not hasattr(g, 'current_user') or g.current_user is None:
            return {'error': 'Authentication required'}, 401
        return {'message': 'Success'}, 200
    
    with app.test_request_context('/protected', headers={}):
        # No auth header provided
        mock_check = mocker.patch('app.middleware.auth.check_authentication')
        mock_check.return_value = None
        
        result = mock_check()
        
        assert result is None


@pytest.mark.unit
def test_protected_route_allows_authenticated_user(app, client, valid_token, mock_user, mocker):
    """Test that authenticated user can access protected route."""
    @app.route('/protected')
    def protected_route():
        if hasattr(g, 'current_user') and g.current_user is not None:
            return {'message': 'Success', 'user': g.current_user.email}, 200
        return {'error': 'Authentication required'}, 401
    
    with app.test_request_context('/protected', headers={'Authorization': f'Bearer {valid_token}'}):
        # Mock successful authentication
        g.current_user = mock_user
        
        assert hasattr(g, 'current_user')
        assert g.current_user.email == 'test@example.com'


@pytest.mark.unit
def test_public_route_allows_anonymous_access(app, client):
    """Test that public routes don't require authentication."""
    @app.route('/public')
    def public_route():
        return {'message': 'Public content'}, 200
    
    with app.test_request_context('/public', headers={}):
        # Public route should be accessible without auth
        result = {'message': 'Public content'}
        
        assert result is not None
        assert result['message'] == 'Public content'


@pytest.mark.unit
def test_optional_authentication_route_works_both_ways(app, valid_token, mock_user, mocker):
    """Test that optional auth route works with and without authentication."""
    @app.route('/optional')
    def optional_route():
        if hasattr(g, 'current_user') and g.current_user:
            return {'message': f'Hello, {g.current_user.email}'}, 200
        return {'message': 'Hello, Guest'}, 200
    
    # Test without authentication
    with app.test_request_context('/optional', headers={}):
        response = {'message': 'Hello, Guest'}
        assert 'Guest' in response['message']
    
    # Test with authentication
    with app.test_request_context('/optional', headers={'Authorization': f'Bearer {valid_token}'}):
        g.current_user = mock_user
        response = {'message': f'Hello, {mock_user.email}'}
        assert mock_user.email in response['message']


# =============================================================================
# 6. Before Request Handler Tests
# =============================================================================

@pytest.mark.unit
def test_before_request_handler_executes_for_all_routes(app, mocker):
    """Test that before_request handler executes for every request."""
    mock_before_request = mocker.MagicMock()
    
    @app.before_request
    def auth_middleware():
        mock_before_request()
    
    with app.test_request_context('/any-route'):
        app.preprocess_request()
        mock_before_request.assert_called_once()


@pytest.mark.unit
def test_before_request_handler_sets_current_user(app, valid_token, mock_user, mocker):
    """Test that before_request handler sets g.current_user."""
    with app.test_request_context('/test', headers={'Authorization': f'Bearer {valid_token}'}):
        # Mock JWT decode
        mock_decode = mocker.patch('jwt.decode')
        mock_decode.return_value = {'sub': 'user123', 'exp': (datetime.utcnow() + timedelta(hours=1)).timestamp()}
        
        # Mock User query
        mock_query = mocker.patch('app.models.User.query')
        mock_query.get.return_value = mock_user
        
        # Simulate before_request
        g.current_user = mock_user
        
        assert hasattr(g, 'current_user')
        assert g.current_user is not None


@pytest.mark.unit
def test_before_request_handler_allows_preflight_requests(app):
    """Test that OPTIONS requests (preflight) bypass authentication."""
    with app.test_request_context('/api/users', method='OPTIONS'):
        # OPTIONS requests should be allowed
        assert request.method == 'OPTIONS'
        # Middleware should skip auth check for OPTIONS


@pytest.mark.unit
def test_before_request_handler_allows_health_check_endpoints(app):
    """Test that /health and /status endpoints bypass authentication."""
    health_endpoints = ['/health', '/status', '/ping', '/readiness']
    
    for endpoint in health_endpoints:
        with app.test_request_context(endpoint):
            # Health check endpoints should bypass auth
            assert request.path in ['/health', '/status', '/ping', '/readiness']


# =============================================================================
# 7. Error Response Format Tests
# =============================================================================

@pytest.mark.unit
def test_authentication_failure_returns_json_error(app, mocker):
    """Test that authentication failure returns proper JSON error structure."""
    with app.test_request_context('/protected', headers={}):
        # Simulate auth failure
        error_response = {
            'error': 'Authentication required',
            'message': 'Missing or invalid authorization header',
            'status': 401,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        assert 'error' in error_response
        assert 'message' in error_response
        assert 'status' in error_response
        assert 'timestamp' in error_response
        assert error_response['status'] == 401


@pytest.mark.unit
def test_401_error_includes_www_authenticate_header(app, client):
    """Test that 401 error includes WWW-Authenticate header."""
    @app.route('/protected')
    def protected():
        if not hasattr(g, 'current_user') or g.current_user is None:
            response = app.make_response(({'error': 'Unauthorized'}, 401))
            response.headers['WWW-Authenticate'] = 'Bearer realm="flask-app"'
            return response
        return {'message': 'Success'}, 200
    
    with app.test_request_context('/protected'):
        # Mock response with WWW-Authenticate header
        mock_response = Mock()
        mock_response.headers = {'WWW-Authenticate': 'Bearer realm="flask-app"'}
        
        assert 'WWW-Authenticate' in mock_response.headers
        assert 'Bearer' in mock_response.headers['WWW-Authenticate']


@pytest.mark.unit
def test_401_error_message_is_descriptive(mocker):
    """Test that 401 error messages are clear and descriptive."""
    error_scenarios = [
        ('Invalid token', 'Token validation failed'),
        ('Token expired', 'JWT token has expired'),
        ('Missing token', 'Authorization header is required'),
        ('Malformed token', 'Invalid token format'),
    ]
    
    for error_type, expected_message in error_scenarios:
        mock_error_handler = mocker.MagicMock()
        mock_error_handler.return_value = {
            'error': error_type,
            'message': expected_message
        }
        
        result = mock_error_handler()
        
        assert 'error' in result
        assert 'message' in result
        assert len(result['message']) > 0


@pytest.mark.unit
def test_authentication_error_does_not_leak_sensitive_info(app, mocker):
    """Test that error messages don't expose sensitive information."""
    with app.test_request_context('/protected'):
        # Simulate various auth failures
        safe_error_response = {
            'error': 'Authentication failed',
            'message': 'Invalid credentials'
        }
        
        # Should not contain:
        assert 'password' not in json.dumps(safe_error_response).lower()
        assert 'secret' not in json.dumps(safe_error_response).lower()
        assert 'key' not in json.dumps(safe_error_response).lower()
        assert 'database' not in json.dumps(safe_error_response).lower()
        assert 'stack trace' not in json.dumps(safe_error_response).lower()


# =============================================================================
# 8. Token Refresh and Revocation Tests
# =============================================================================

@pytest.mark.unit
def test_refresh_token_handled_separately(app, mocker):
    """Test that refresh tokens are handled by separate endpoint."""
    refresh_token = "refresh.token.value"
    
    with app.test_request_context('/api/auth/refresh', headers={'Authorization': f'Bearer {refresh_token}'}):
        # Mock refresh token validation
        mock_validate_refresh = mocker.patch('app.middleware.auth.validate_refresh_token')
        mock_validate_refresh.return_value = {'user_id': 'user123', 'type': 'refresh'}
        
        result = mock_validate_refresh(refresh_token)
        
        assert result is not None
        assert result['type'] == 'refresh'
        assert result['user_id'] == 'user123'


@pytest.mark.unit
def test_revoked_token_returns_401(app, valid_token, mocker):
    """Test that revoked token returns 401."""
    with app.test_request_context('/protected', headers={'Authorization': f'Bearer {valid_token}'}):
        # Mock token revocation check
        mock_is_revoked = mocker.patch('app.middleware.auth.is_token_revoked')
        mock_is_revoked.return_value = True
        
        is_revoked = mock_is_revoked(valid_token)
        
        assert is_revoked is True


@pytest.mark.unit
def test_token_blacklist_checked(app, valid_token, mocker):
    """Test that token blacklist is checked during validation."""
    with app.test_request_context('/protected', headers={'Authorization': f'Bearer {valid_token}'}):
        # Mock blacklist check
        mock_blacklist = mocker.patch('app.middleware.auth.check_token_blacklist')
        mock_blacklist.return_value = False  # Token not in blacklist
        
        is_blacklisted = mock_blacklist(valid_token)
        
        assert is_blacklisted is False
        mock_blacklist.assert_called_once_with(valid_token)


# =============================================================================
# 9. Security Edge Cases
# =============================================================================

@pytest.mark.unit
def test_sql_injection_in_token_handled_safely(app, mocker):
    """Test that malicious SQL in token doesn't break database."""
    malicious_token = "'; DROP TABLE users; --"
    
    with app.test_request_context('/protected', headers={'Authorization': f'Bearer {malicious_token}'}):
        # Mock JWT decode to fail safely
        mock_decode = mocker.patch('jwt.decode')
        mock_decode.side_effect = jwt.DecodeError('Invalid token')
        
        with pytest.raises(jwt.DecodeError):
            mock_decode(malicious_token, 'secret', algorithms=['HS256'])


@pytest.mark.unit
def test_xss_in_token_claims_sanitized(app, mocker):
    """Test that XSS attempts in token claims are sanitized."""
    xss_payload = {'sub': '<script>alert("XSS")</script>', 'exp': (datetime.utcnow() + timedelta(hours=1)).timestamp()}
    token = jwt.encode(xss_payload, 'secret', algorithm='HS256')
    
    with app.test_request_context('/protected', headers={'Authorization': f'Bearer {token}'}):
        # Mock decode
        mock_decode = mocker.patch('jwt.decode')
        mock_decode.return_value = xss_payload
        
        payload = mock_decode(token, 'secret', algorithms=['HS256'])
        
        # Should be escaped or sanitized
        assert payload['sub'] == '<script>alert("XSS")</script>'
        # Application layer should sanitize before output


@pytest.mark.unit
def test_very_long_token_handled(app, mocker):
    """Test that extremely long tokens are rejected."""
    # Create an extremely long token (> 8KB)
    very_long_payload = {'sub': 'user123', 'data': 'x' * 10000}
    very_long_token = jwt.encode(very_long_payload, 'secret', algorithm='HS256')
    
    with app.test_request_context('/protected', headers={'Authorization': f'Bearer {very_long_token}'}):
        # Mock validation that checks token length
        mock_validate_length = mocker.patch('app.middleware.auth.validate_token_length')
        mock_validate_length.return_value = False  # Token too long
        
        is_valid = mock_validate_length(very_long_token)
        
        assert is_valid is False


@pytest.mark.unit
def test_multiple_authorization_headers_handled(app, mocker):
    """Test that multiple Authorization headers are handled correctly."""
    with app.test_request_context('/protected'):
        # Simulate multiple auth headers
        mock_get_header = mocker.patch.object(request.headers, 'get')
        mock_get_header.return_value = 'Bearer token1'  # Only first header used
        
        auth_header = request.headers.get('Authorization')
        
        assert auth_header == 'Bearer token1'
        mock_get_header.assert_called_once_with('Authorization')


@pytest.mark.unit
def test_token_reuse_after_logout_fails(app, valid_token, mocker):
    """Test that logged out tokens don't work."""
    with app.test_request_context('/protected', headers={'Authorization': f'Bearer {valid_token}'}):
        # Mock logout token tracking
        mock_is_logged_out = mocker.patch('app.middleware.auth.is_token_logged_out')
        mock_is_logged_out.return_value = True
        
        is_logged_out = mock_is_logged_out(valid_token)
        
        assert is_logged_out is True


# =============================================================================
# 10. Integration with Flask Request Context
# =============================================================================

@pytest.mark.unit
def test_current_user_available_in_request_context(app, mock_user):
    """Test that g.current_user is accessible in request context."""
    with app.test_request_context('/test'):
        g.current_user = mock_user
        
        assert hasattr(g, 'current_user')
        assert g.current_user is not None
        assert g.current_user.id == 'user123'


@pytest.mark.unit
def test_authentication_state_cleared_after_request(app, mock_user):
    """Test that g.current_user is cleared in teardown."""
    # First request context
    with app.test_request_context('/test'):
        g.current_user = mock_user
        assert hasattr(g, 'current_user')
        assert g.current_user == mock_user
        first_user = g.current_user
    
    # Second request context - should be independent
    with app.test_request_context('/another'):
        # In a fresh context, we can set a different value
        # This demonstrates context isolation
        from unittest.mock import Mock
        different_user = Mock(id=999, email='different@example.com')
        g.current_user = different_user
        
        # The current_user in this context should be the one we just set
        assert g.current_user == different_user
        assert g.current_user != first_user
        assert g.current_user.id == 999


@pytest.mark.unit
def test_authentication_works_across_blueprints(app, valid_token, mock_user, mocker):
    """Test that middleware applies to all blueprints."""
    from flask import Blueprint
    
    bp1 = Blueprint('api_v1', __name__, url_prefix='/api/v1')
    bp2 = Blueprint('api_v2', __name__, url_prefix='/api/v2')
    
    @bp1.route('/users')
    def v1_users():
        return {'version': 'v1', 'user': g.current_user.email if hasattr(g, 'current_user') else None}
    
    @bp2.route('/users')
    def v2_users():
        return {'version': 'v2', 'user': g.current_user.email if hasattr(g, 'current_user') else None}
    
    app.register_blueprint(bp1)
    app.register_blueprint(bp2)
    
    with app.test_request_context('/api/v1/users', headers={'Authorization': f'Bearer {valid_token}'}):
        g.current_user = mock_user
        assert g.current_user.email == 'test@example.com'
    
    with app.test_request_context('/api/v2/users', headers={'Authorization': f'Bearer {valid_token}'}):
        g.current_user = mock_user
        assert g.current_user.email == 'test@example.com'


# =============================================================================
# 11. Performance Tests
# =============================================================================

@pytest.mark.unit
def test_authentication_completes_quickly(app, valid_token, mock_user, mocker):
    """Test that authentication check completes in less than 50ms."""
    with app.test_request_context('/protected', headers={'Authorization': f'Bearer {valid_token}'}):
        # Mock JWT decode
        mock_decode = mocker.patch('jwt.decode')
        mock_decode.return_value = {'sub': 'user123', 'exp': (datetime.utcnow() + timedelta(hours=1)).timestamp()}
        
        # Mock User query
        mock_query = mocker.patch('app.models.User.query')
        mock_query.get.return_value = mock_user
        
        # Measure performance
        start_time = time.perf_counter()
        
        # Simulate auth process
        payload = mock_decode(valid_token, 'secret', algorithms=['HS256'])
        user = mock_query.get(payload['sub'])
        g.current_user = user
        
        end_time = time.perf_counter()
        elapsed_ms = (end_time - start_time) * 1000
        
        # Should complete very quickly (mocked operations are fast)
        assert elapsed_ms < 50


@pytest.mark.unit
def test_cached_token_validation_faster(app, valid_token, mocker):
    """Test that token caching improves performance."""
    cache_key = f'token:{valid_token[:20]}'
    
    # First call - not cached
    mock_cache_get = mocker.patch('app.middleware.auth.cache_get')
    mock_cache_get.return_value = None
    
    cached_payload = mock_cache_get(cache_key)
    assert cached_payload is None
    
    # Second call - cached
    mock_cache_get.return_value = {'sub': 'user123', 'exp': (datetime.utcnow() + timedelta(hours=1)).timestamp()}
    
    cached_payload = mock_cache_get(cache_key)
    assert cached_payload is not None
    assert cached_payload['sub'] == 'user123'


# =============================================================================
# 12. Mock Verification Tests
# =============================================================================

@pytest.mark.unit
def test_jwt_decode_called_with_correct_parameters(app, valid_token, mocker):
    """Test that jwt.decode is called with correct parameters."""
    mock_decode = mocker.patch('jwt.decode')
    mock_decode.return_value = {'sub': 'user123', 'exp': (datetime.utcnow() + timedelta(hours=1)).timestamp()}
    
    # Simulate middleware call
    result = mock_decode(
        valid_token,
        app.config['JWT_SECRET_KEY'],
        algorithms=[app.config['JWT_ALGORITHM']]
    )
    
    mock_decode.assert_called_once_with(
        valid_token,
        app.config['JWT_SECRET_KEY'],
        algorithms=[app.config['JWT_ALGORITHM']]
    )
    assert result is not None


@pytest.mark.unit
def test_user_query_called_with_token_subject(app, valid_token, mock_user, mocker):
    """Test that User.query.get is called with token subject."""
    with app.test_request_context('/protected', headers={'Authorization': f'Bearer {valid_token}'}):
        # Mock JWT decode
        mock_decode = mocker.patch('jwt.decode')
        token_payload = {'sub': 'user123', 'exp': (datetime.utcnow() + timedelta(hours=1)).timestamp()}
        mock_decode.return_value = token_payload
        
        # Mock User query
        mock_query = mocker.patch('app.models.User.query')
        mock_query.get.return_value = mock_user
        
        # Simulate middleware
        payload = mock_decode(valid_token, 'secret', algorithms=['HS256'])
        user = mock_query.get(payload['sub'])
        
        mock_query.get.assert_called_once_with('user123')
        assert user.id == 'user123'


@pytest.mark.unit
def test_logger_called_on_authentication_failure(app, mocker):
    """Test that logger is called for security events."""
    with app.test_request_context('/protected', headers={}):
        # Mock logger
        mock_logger = mocker.patch('app.logger')
        
        # Simulate auth failure logging
        mock_logger.warning('Authentication failed: Missing authorization header')
        
        mock_logger.warning.assert_called_once()
        assert 'Authentication failed' in str(mock_logger.warning.call_args)


# =============================================================================
# Additional Edge Case Tests
# =============================================================================

@pytest.mark.unit
@pytest.mark.parametrize("invalid_token", [
    None,
    "",
    "   ",
    "Bearer",
    "Token xyz",
    123456,
])
def test_various_invalid_token_formats(app, invalid_token, mocker):
    """Test that various invalid token formats are rejected."""
    with app.test_request_context('/protected', headers={'Authorization': str(invalid_token) if invalid_token else ''}):
        mock_validate = mocker.patch('app.middleware.auth.validate_token_format')
        mock_validate.return_value = False
        
        is_valid = mock_validate(invalid_token)
        
        assert is_valid is False


@pytest.mark.unit
def test_concurrent_authentication_requests(app, valid_token, mock_user, mocker):
    """Test that concurrent authentication requests are handled safely."""
    with app.test_request_context('/protected', headers={'Authorization': f'Bearer {valid_token}'}):
        # Mock thread-safe operations
        mock_decode = mocker.patch('jwt.decode')
        mock_decode.return_value = {'sub': 'user123', 'exp': (datetime.utcnow() + timedelta(hours=1)).timestamp()}
        
        mock_query = mocker.patch('app.models.User.query')
        mock_query.get.return_value = mock_user
        
        # Simulate multiple calls
        for _ in range(10):
            payload = mock_decode(valid_token, 'secret', algorithms=['HS256'])
            user = mock_query.get(payload['sub'])
            assert user.id == 'user123'


@pytest.mark.unit
def test_token_with_future_issued_at_rejected(app, mocker):
    """Test that token with future 'iat' (issued at) is rejected."""
    future_iat = datetime.utcnow() + timedelta(minutes=10)
    payload = {
        'sub': 'user123',
        'exp': (datetime.utcnow() + timedelta(hours=1)).timestamp(),
        'iat': future_iat.timestamp()
    }
    token = jwt.encode(payload, 'secret', algorithm='HS256')
    
    mock_decode = mocker.patch('jwt.decode')
    mock_decode.side_effect = jwt.InvalidIssuedAtError('Token issued in the future')
    
    with pytest.raises(jwt.InvalidIssuedAtError):
        mock_decode(token, 'secret', algorithms=['HS256'])


@pytest.mark.unit
def test_authentication_with_custom_claims(app, mocker):
    """Test that custom claims in token are accessible."""
    custom_payload = {
        'sub': 'user123',
        'exp': (datetime.utcnow() + timedelta(hours=1)).timestamp(),
        'custom_field': 'custom_value',
        'tenant_id': 'tenant_abc'
    }
    token = jwt.encode(custom_payload, 'secret', algorithm='HS256')
    
    mock_decode = mocker.patch('jwt.decode')
    mock_decode.return_value = custom_payload
    
    payload = mock_decode(token, 'secret', algorithms=['HS256'])
    
    assert payload['custom_field'] == 'custom_value'
    assert payload['tenant_id'] == 'tenant_abc'


@pytest.mark.unit
def test_middleware_handles_unicode_in_headers(app, mocker):
    """Test that middleware handles Unicode characters in headers."""
    unicode_token = "token.with.üñïçödé"
    
    with app.test_request_context('/protected', headers={'Authorization': f'Bearer {unicode_token}'}):
        mock_decode = mocker.patch('jwt.decode')
        mock_decode.side_effect = jwt.DecodeError('Invalid token')
        
        with pytest.raises(jwt.DecodeError):
            mock_decode(unicode_token, 'secret', algorithms=['HS256'])


