"""
Unit tests for service layer business logic.

This package contains unit tests for Flask service layer components,
testing business logic in isolation with mocked external dependencies.

Test files in this package follow the naming pattern: test_*_service.py

Expected test modules (to be created once Flask services are implemented):
- test_user_service.py: User service business logic tests
- test_auth_service.py: Authentication service tests
- test_email_service.py: Email service tests
- Additional service test modules as needed

Shared service test fixtures and utilities can be added here as the
testing infrastructure evolves to support mocking of databases, external
APIs, and other service dependencies using pytest-mock.

Coverage target for service layer: 85-95% per Agent Action Plan section 0.10
"""
