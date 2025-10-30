"""
Integration Tests Package

This package contains integration tests for the Flask application, validating the interaction
between multiple components and their integration points.

Integration tests in this package focus on:
- API endpoint workflows (request → route → service → model → response)
- Database operations with actual database transactions
- Authentication and authorization flows
- File upload/download operations
- Cache interactions with actual cache systems (or mocked external services)
- Component interactions across layers of the application

Unlike unit tests which isolate individual components, integration tests verify that
multiple components work together correctly as a system.

Test Organization:
- test_*_api.py: API endpoint integration tests
- test_*_workflow.py: Complex multi-step workflow tests
- test_*_db.py: Database integration and transaction tests
- test_auth*.py: Authentication and authorization flow tests

Coverage Goals:
- 80-90% coverage of integration points
- Focus on critical user workflows
- Validate data flow between components
- Ensure proper error handling across component boundaries

Execution:
    Run all integration tests:
        pytest tests/integration/

    Run specific integration test file:
        pytest tests/integration/test_user_api.py

    Run integration tests with coverage:
        pytest tests/integration/ --cov=app --cov-report=term-missing

Performance:
- Integration tests typically take 100ms-1s per test
- Use test database with transactions for isolation
- Mock only external services, use real internal components

Test Markers:
    Use @pytest.mark.integration decorator to mark integration tests:
        @pytest.mark.integration
        def test_user_creation_workflow(client, db_session):
            pass

Dependencies:
- pytest: Testing framework
- Flask test client: HTTP testing
- Database fixtures: From tests/conftest.py
- Shared fixtures: From tests/fixtures/

See Also:
- tests/unit/: Unit tests for isolated component testing
- tests/functional/: End-to-end functional tests
- tests/conftest.py: Shared fixtures and pytest configuration
"""
