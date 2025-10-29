"""
Unit tests package for utility and helper functions.

This package initialization file makes tests/unit/utils a Python package,
enabling pytest test discovery of all utility test modules including:
- test_validators.py: Input validation function tests
- test_helpers.py: Utility and helper function tests
- Additional utility test modules as they are created

Following pytest best practices, this __init__.py serves as a minimal package
marker that enables:
1. Test discovery via 'pytest tests/unit/utils/' command
2. Proper test organization and namespace isolation
3. Relative imports between utility test modules if needed
4. Future extension with shared utility test fixtures

This supports the Flask migration testing objective (Agent Action Plan Section 0.1)
of ensuring functional equivalence during Node.js to Python/Flask migration.

Test Organization:
- Unit tests focus on isolated utility functions
- Each test module corresponds to a source utility module
- Fixtures can be added here for shared utility test setup
- Mock objects for utility dependencies can be defined here

Usage:
    Run all utility tests:
        $ pytest tests/unit/utils/
    
    Run specific utility test module:
        $ pytest tests/unit/utils/test_validators.py
    
    Run with coverage:
        $ pytest --cov=app.utils tests/unit/utils/
"""

# This file intentionally left minimal per pytest best practices.
# Shared fixtures and imports can be added here as the test suite grows.
