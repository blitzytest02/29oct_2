"""
Tests Package for Flask Application Migration

This package contains the comprehensive test suite for the Flask/Python implementation
of the migrated Node.js server application. The test infrastructure follows pytest
best practices and industry standards for test organization and execution.

Test Organization
-----------------
The test suite is organized into the following categories:

- **unit/**: Unit tests for isolated component testing
  - routes/: API route handler tests
  - services/: Business logic service tests
  - models/: Data model and ORM tests
  - utils/: Utility function tests
  - middleware/: Middleware component tests

- **integration/**: Integration tests for component interactions
  - API endpoint workflows (request → route → service → model → response)
  - Database operations with actual database transactions
  - Authentication and authorization flows
  - External service integrations (with mocking)

- **functional/**: Functional tests for end-to-end workflows
  - Complete user journeys
  - Multi-step business processes
  - Full application workflows

- **fixtures/**: Shared test data and fixtures
  - Reusable test data factories
  - Common fixture definitions
  - Sample data sets

- **mocks/**: Mock implementations
  - External API mocks
  - Database mocks for unit tests
  - Service mocks

Test Execution
--------------
Run tests using pytest from the repository root:

    # Run all tests
    pytest

    # Run specific test category
    pytest tests/unit/
    pytest tests/integration/
    pytest tests/functional/

    # Run with coverage
    pytest --cov=app --cov-report=html

    # Run in parallel
    pytest -n auto

    # Run specific test file
    pytest tests/unit/services/test_user_service.py

Coverage Targets
----------------
- Overall Line Coverage: >= 85%
- Branch Coverage: >= 80%
- Function Coverage: >= 90%
- Critical Components (auth, security): 100%

Testing Standards
-----------------
All tests in this package follow these standards:

1. **Test Isolation**: Each test runs independently with proper setup/teardown
2. **Descriptive Naming**: test_<action>_<expected_result> naming convention
3. **AAA Pattern**: Arrange-Act-Assert structure for clarity
4. **Comprehensive Coverage**: Happy path, edge cases, and error scenarios
5. **Performance**: Unit tests < 100ms, Integration tests < 1s
6. **Documentation**: Complex test scenarios include docstrings

Test Configuration
------------------
- pytest.ini: Pytest configuration and markers
- conftest.py: Shared fixtures and test configuration
- .coveragerc: Coverage measurement settings

Dependencies
------------
Testing framework and utilities:
- pytest: Core testing framework
- pytest-cov: Code coverage measurement
- pytest-mock: Mocking utilities
- pytest-flask: Flask-specific test helpers
- factory-boy: Test data factories
- faker: Fake data generation
- freezegun: Time mocking
- responses: HTTP request mocking

For detailed testing documentation, see:
- README.md: Quick start guide
- docs/testing/: Comprehensive testing documentation
"""

__version__ = "1.0.0"
__author__ = "Blitzy Platform"
__all__ = []

# Package metadata
PACKAGE_NAME = "tests"
PACKAGE_DESCRIPTION = "Comprehensive test suite for Flask application migration"

# Test configuration constants
DEFAULT_TEST_TIMEOUT = 30  # seconds
UNIT_TEST_TIMEOUT = 1  # seconds
INTEGRATION_TEST_TIMEOUT = 5  # seconds
FUNCTIONAL_TEST_TIMEOUT = 30  # seconds

# Coverage targets (percentages)
COVERAGE_TARGET_OVERALL = 85
COVERAGE_TARGET_BRANCH = 80
COVERAGE_TARGET_FUNCTION = 90
COVERAGE_TARGET_CRITICAL = 100  # For authentication, authorization, security

# Test markers (defined in pytest.ini)
# - unit: Unit tests (fast, isolated)
# - integration: Integration tests (slower, database)
# - functional: Functional tests (end-to-end workflows)
# - slow: Tests that take >1 second
# - smoke: Critical smoke tests
# - api: API endpoint tests
# - database: Tests requiring database
# - external: Tests involving external services (mocked)
