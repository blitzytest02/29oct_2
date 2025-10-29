"""
Flask application package.
Provides application factory for creating Flask app instances.
"""

import logging
from flask import Flask

# Create a logger for the app
logger = logging.getLogger(__name__)


def create_app(config_name='development'):
    """
    Application factory for creating Flask app instances.
    
    This function creates and configures a Flask application instance using
    the application factory pattern. It supports different configurations
    for development, testing, and production environments.
    
    Args:
        config_name (str): Configuration name ('development', 'testing', 'production')
    
    Returns:
        Flask: Configured Flask application instance
    
    Example:
        app = create_app('testing')
        app.run()
    """
    from app.extensions import db, migrate, cors, jwt
    
    app = Flask(__name__)
    
    # Load configuration based on config_name
    if config_name == 'testing':
        from config.test_config import TestConfig
        app.config.from_object(TestConfig)
    elif config_name == 'production':
        from config import Config
        app.config.from_object(Config)
    else:  # development
        from config import Config
        app.config.from_object(Config)
    
    # Initialize Flask extensions
    db.init_app(app)
    migrate.init_app(app, db)
    cors.init_app(app)
    jwt.init_app(app)
    
    return app
