"""
Pytest Configuration and Shared Fixtures
Generated for Node.js to Flask migration project

This module contains pytest configuration and shared fixtures
that are available to all test files.
"""

import os
import pytest
from dotenv import load_dotenv

# Load test environment variables
load_dotenv('.env.test')

# Register fixtures plugin
pytest_plugins = ['tests.fixtures.db_fixtures']


@pytest.fixture(scope='session')
def app():
    """
    Create and configure a Flask application instance for testing.
    
    This fixture is session-scoped, meaning it's created once per test session.
    It creates a Flask application configured for testing with an in-memory
    SQLite database and proper test configuration.
    
    Returns:
        Flask: A configured Flask application instance for testing
    """
    from app import create_app
    
    # Create Flask app with testing configuration
    app = create_app('testing')
    
    return app


@pytest.fixture(scope='function')
def client(app):
    """
    Create a test client for the Flask application.
    
    This fixture provides a test client that can be used to make
    requests to the application without running a server.
    
    Args:
        app: The Flask application fixture
        
    Returns:
        FlaskClient: A test client for the Flask application
    """
    if app is None:
        return None
    
    with app.test_client() as client:
        yield client





@pytest.fixture(scope='function')
def runner(app):
    """
    Create a CLI test runner for the Flask application.
    
    This fixture provides a test runner for testing Flask CLI commands.
    
    Args:
        app: The Flask application fixture
        
    Returns:
        FlaskCliRunner: A test runner for CLI commands
    """
    if app is None:
        return None
    
    return app.test_cli_runner()
