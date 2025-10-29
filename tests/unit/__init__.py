"""
Unit Tests Package

This package contains all unit tests for isolated component testing of the Flask
application. Unit tests focus on testing individual functions, methods, and classes
in isolation with mocked external dependencies.

Test Subdirectories
------------------
- routes/: API route handler unit tests
- services/: Business logic service unit tests  
- models/: Data model and ORM unit tests
- utils/: Utility function unit tests
- middleware/: Middleware component unit tests

Testing Approach
----------------
Unit tests in this package follow these principles:
- Test isolation: Each test runs independently with no shared state
- Mock external dependencies: Database, external APIs, and file systems are mocked
- Fast execution: Unit tests should complete in <100ms per test
- High coverage: Target 85-95% code coverage for business logic

Usage
-----
Run all unit tests:
    pytest tests/unit/

Run specific subdirectory tests:
    pytest tests/unit/services/
    pytest tests/unit/routes/

Run with coverage:
    pytest tests/unit/ --cov=app --cov-report=term-missing
"""
