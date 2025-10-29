"""
Functional Tests Package

This package contains functional (end-to-end) tests for the Flask application, validating
complete user workflows and multi-step business processes across the entire application stack.

Functional tests simulate real user interactions from start to finish, testing that all
components of the system work together correctly to deliver complete features and workflows.

Test Organization
-----------------
Functional test files in this package include:

- test_user_journey.py: Complete user workflow tests
  - User registration → email verification → login → profile management
  - Password management flows (change password, forgot password, reset)
  - Account management (deactivation, deletion, data export)
  - Session management and multi-device scenarios
  - Profile updates and preference management

- test_admin_workflow.py: Administrative workflow tests
  - User management workflows (create, activate, deactivate, delete)
  - Role and permission management
  - Content moderation workflows
  - System configuration and settings
  - Monitoring, reporting, and audit workflows
  - Security and compliance operations

Testing Approach
----------------
Functional tests in this package follow these principles:

1. **End-to-End Validation**: Tests simulate complete user journeys from start to finish
2. **Multi-Step Workflows**: Each test validates a sequence of related actions
3. **Real Interactions**: Uses Flask test_client() to make actual HTTP requests
4. **State Verification**: Validates application state at each step of the workflow
5. **Integration Focus**: Tests how all components work together (routes, services, models, DB)
6. **User Perspective**: Tests from the user's point of view, not individual components

Functional vs Other Test Types
------------------------------
- **Unit Tests** (tests/unit/): Test individual functions/classes in isolation with mocks
- **Integration Tests** (tests/integration/): Test component interactions (2-3 components)
- **Functional Tests** (tests/functional/): Test complete workflows end-to-end (all components)

Example Functional Test Flow:
    1. User registers with valid data → Assert 201 response
    2. Verify user created in database → Assert user exists
    3. Verify email sent (mocked) → Assert email service called
    4. User verifies email via token → Assert email verified
    5. User logs in with credentials → Assert 200 response + JWT token
    6. User accesses protected profile → Assert 200 response + user data
    7. User updates profile → Assert 200 response
    8. Verify profile updated in database → Assert changes persisted
    9. User logs out → Assert session cleared

Coverage Goals
--------------
- Target: Complete coverage of user-facing workflows
- Focus: Critical user journeys and business processes
- Priority: Features most important to end users
- Authentication workflows: 100% (security-critical)
- Core user features: 90%+ coverage
- Admin features: 90%+ coverage (if applicable)

Performance Expectations
------------------------
Functional tests are slower than unit/integration tests due to end-to-end nature:

- Execution time: <5 seconds average per test
- Maximum time: <30 seconds per test (per section 0.10)
- Full functional suite: <15 minutes total
- Tests use real database transactions (not mocked)
- External services are mocked to avoid network delays

Test Isolation
--------------
Each functional test must:
- Create its own test data (users, resources, etc.)
- Clean up after execution (handled by db_session fixture)
- Run independently of other tests
- Be executable in any order
- Not rely on state from previous tests

Usage
-----
Run all functional tests:
    pytest tests/functional/

Run specific functional test file:
    pytest tests/functional/test_user_journey.py

Run specific test scenario:
    pytest tests/functional/test_user_journey.py::test_user_journey_complete_registration_flow

Run functional tests with verbose output:
    pytest tests/functional/ -v

Run functional tests with coverage:
    pytest tests/functional/ --cov=app --cov-report=html

Run functional tests in parallel (faster):
    pytest tests/functional/ -n auto

Skip slow functional tests (for quick feedback):
    pytest tests/functional/ -m "not slow"

Test Markers
------------
Functional tests use pytest markers for categorization:

    @pytest.mark.functional - Mark as functional test (required)
    @pytest.mark.slow - Tests taking >1 second
    @pytest.mark.smoke - Critical smoke tests
    @pytest.mark.admin - Admin-specific workflows

Example:
    @pytest.mark.functional
    @pytest.mark.smoke
    def test_user_journey_complete_registration_flow(client, db_session):
        # Test complete user registration workflow
        pass

Dependencies
------------
Functional tests rely on:

- pytest: Core testing framework
- Flask test_client(): HTTP request simulation
- Database fixtures (from tests/conftest.py):
  - app: Flask application instance
  - client: Flask test client
  - db_session: Database session with automatic rollback
- Test data fixtures (from tests/fixtures/):
  - User fixtures, authentication fixtures
- Mock libraries (for external services):
  - responses: Mock HTTP requests to external APIs
  - pytest-mock: Mock internal services if needed

Best Practices
--------------
1. **Descriptive Test Names**: Use test_<feature>_<scenario>() naming
   Example: test_user_journey_complete_registration_flow()

2. **Clear Documentation**: Add docstrings for complex workflows
   Explain what the test validates and why it matters

3. **Step-by-Step Comments**: Document each step of multi-step workflows
   Makes tests easier to understand and debug

4. **Comprehensive Assertions**: Verify state at each critical step
   Don't just check HTTP status codes - verify data, side effects, state changes

5. **Error Scenarios**: Test both happy paths and error recovery
   What happens when email verification fails? Password reset expires?

6. **Realistic Data**: Use realistic test data that mimics production
   Use Faker for generating realistic names, emails, addresses

7. **Independent Tests**: Each test should be runnable in isolation
   Create all necessary test data within the test

Example Functional Test Structure:
    def test_user_journey_example(client, db_session):
        \"\"\"
        Test complete user registration and first login workflow.
        
        Workflow:
        1. User registers with valid credentials
        2. System sends verification email
        3. User verifies email via token
        4. User logs in with credentials
        5. User accesses protected profile page
        \"\"\"
        # Step 1: Register user
        response = client.post('/api/auth/register', json={
            'email': 'user@example.com',
            'password': 'SecurePass123!'
        })
        assert response.status_code == 201
        
        # Step 2: Verify user in database
        user = User.query.filter_by(email='user@example.com').first()
        assert user is not None
        assert user.is_verified == False
        
        # Step 3: Verify email (simulate clicking link)
        # ... continue with workflow steps ...
        
        # Final: Verify complete workflow success
        assert user.is_verified == True
        assert user.last_login is not None

Debugging Functional Tests
---------------------------
When a functional test fails:

1. Run with verbose output: pytest tests/functional/test_*.py -vv
2. Use debugger on failure: pytest tests/functional/test_*.py --pdb
3. Check database state: Inspect db_session fixture data
4. Review HTTP responses: Print response.json or response.data
5. Check application logs: Verify no unexpected errors

Coordinates With
----------------
- tests/unit/: Unit tests validate individual components used in workflows
- tests/integration/: Integration tests validate component interactions
- tests/conftest.py: Provides shared fixtures (app, client, db_session)
- tests/fixtures/: Provides reusable test data and factories
- pytest.ini: Configures test discovery and markers

See Also
--------
- Agent Action Plan Section 0.7: Test Implementation Design
- Agent Action Plan Section 0.8: Test File Transformation Mapping
- Agent Action Plan Section 0.10: Coverage and Quality Targets
- Agent Action Plan Section 0.12: Execution Parameters

For comprehensive testing documentation, see:
- README.md: Quick start testing guide
- tests/__init__.py: Overall test package documentation
- tests/conftest.py: Shared fixtures documentation
"""

__version__ = "1.0.0"
__author__ = "Blitzy Platform"
__all__ = []

# Package metadata
PACKAGE_NAME = "tests.functional"
PACKAGE_DESCRIPTION = "Functional end-to-end tests for complete user workflows and business processes"

# Functional test configuration constants
FUNCTIONAL_TEST_TIMEOUT = 30  # Maximum seconds per functional test
FUNCTIONAL_TEST_AVERAGE_TIME = 5  # Target average seconds per test
MAX_WORKFLOW_STEPS = 20  # Maximum steps in a single workflow test

# Test markers specific to functional tests
FUNCTIONAL_MARKERS = [
    "functional",  # All functional tests must have this marker
    "slow",  # Tests taking >1 second
    "smoke",  # Critical smoke tests for deployment validation
    "admin",  # Admin-specific workflow tests
]

# Workflow categories for functional tests
WORKFLOW_CATEGORIES = [
    "user_registration",  # User signup and verification workflows
    "authentication",  # Login, logout, session management
    "profile_management",  # Profile updates, settings, preferences
    "password_management",  # Change password, forgot password, reset
    "account_management",  # Deactivation, deletion, data export
    "admin_workflows",  # Administrative operations and management
    "security_workflows",  # 2FA, suspicious activity, API tokens
    "compliance_workflows",  # GDPR, data requests, anonymization
]
