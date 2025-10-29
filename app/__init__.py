"""
Flask Application Factory Module

This module implements the Flask application factory pattern, providing the create_app
function that creates and configures Flask application instances. This pattern enables:

- Multiple app instances with different configurations (development, testing, production)
- Easier testing by allowing test-specific configurations
- Cleaner separation of concerns and avoiding circular imports
- Support for multiple Flask apps in the same process

The create_app function:
1. Creates a Flask application instance
2. Loads environment-specific configuration
3. Initializes Flask extensions (database, migrations, CORS, JWT)
4. Registers API blueprints dynamically
5. Configures error handlers for consistent error responses
6. Sets up application logging
7. Returns the fully configured application instance

Usage:
    from app import create_app
    
    # Create app with default (development) configuration
    app = create_app()
    
    # Create app with test configuration
    test_app = create_app('testing')
    
    # Create app with production configuration
    prod_app = create_app('production')

Extensions Used:
    - SQLAlchemy (db): Database ORM and session management
    - Flask-Migrate (migrate): Database migration support using Alembic
    - Flask-CORS (cors): Cross-origin resource sharing for API access
    - Flask-JWT-Extended (jwt): JWT token authentication and authorization
"""

import os
import logging
import importlib
from pathlib import Path
from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException


# Configure module logger
logger = logging.getLogger(__name__)


def create_app(config_name=None):
    """
    Application factory function that creates and configures a Flask application.
    
    This function implements the application factory pattern, creating a new Flask
    application instance with the specified configuration. It initializes all
    extensions, registers blueprints, and configures error handlers.
    
    Args:
        config_name (str, optional): Configuration environment name.
            Valid values: 'development', 'testing', 'production'
            If None, defaults to value from FLASK_ENV environment variable,
            or 'development' if not set.
    
    Returns:
        Flask: Fully configured Flask application instance ready to run.
    
    Raises:
        ImportError: If configuration class cannot be imported.
        ValueError: If invalid config_name is provided.
    
    Example:
        >>> from app import create_app
        >>> app = create_app('testing')
        >>> with app.test_client() as client:
        ...     response = client.get('/api/health')
        ...     assert response.status_code == 200
    """
    # Create Flask application instance
    app = Flask(__name__)
    
    # Determine configuration environment
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')
    
    # Validate configuration name
    valid_configs = ['development', 'testing', 'production']
    if config_name not in valid_configs:
        logger.warning(
            f"Invalid config_name '{config_name}'. Defaulting to 'development'. "
            f"Valid options: {valid_configs}"
        )
        config_name = 'development'
    
    # Load configuration
    _load_configuration(app, config_name)
    
    # Initialize Flask extensions
    _initialize_extensions(app)
    
    # Register blueprints
    _register_blueprints(app)
    
    # Configure error handlers
    _register_error_handlers(app)
    
    # Configure logging
    _configure_logging(app)
    
    # Log application startup
    logger.info(
        f"Flask application created successfully with {config_name} configuration"
    )
    
    return app


def _load_configuration(app, config_name):
    """
    Load configuration settings into the Flask app based on environment.
    
    Imports and applies the appropriate configuration class for the specified
    environment. Falls back to safe defaults if configuration cannot be loaded.
    
    Args:
        app (Flask): Flask application instance to configure.
        config_name (str): Configuration environment name.
    
    Raises:
        ImportError: If configuration module cannot be imported.
    """
    try:
        if config_name == 'testing':
            from config.test_config import TestConfig
            app.config.from_object(TestConfig)
            logger.debug("Loaded TestConfig configuration")
        elif config_name == 'production':
            try:
                from config import ProductionConfig
                app.config.from_object(ProductionConfig)
                logger.debug("Loaded ProductionConfig configuration")
            except ImportError:
                logger.warning(
                    "ProductionConfig not found, falling back to base Config"
                )
                from config import Config
                app.config.from_object(Config)
        else:  # development
            try:
                from config import DevelopmentConfig
                app.config.from_object(DevelopmentConfig)
                logger.debug("Loaded DevelopmentConfig configuration")
            except ImportError:
                logger.warning(
                    "DevelopmentConfig not found, falling back to base Config"
                )
                from config import Config
                app.config.from_object(Config)
    except ImportError as e:
        logger.error(f"Failed to load configuration: {e}")
        # Set minimal safe defaults for testing/development
        app.config['TESTING'] = (config_name == 'testing')
        app.config['DEBUG'] = (config_name == 'development')
        app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
        logger.warning("Using minimal default configuration due to import error")


def _initialize_extensions(app):
    """
    Initialize Flask extensions with the application instance.
    
    This function initializes all Flask extensions using the init_app pattern,
    which allows extensions to be configured with the app instance after creation.
    This is essential for the application factory pattern.
    
    Extensions initialized:
        - db (SQLAlchemy): Database ORM for data persistence
        - migrate (Flask-Migrate): Database migration management
        - cors (CORS): Cross-origin resource sharing configuration
        - jwt (JWTManager): JWT token authentication
    
    Args:
        app (Flask): Flask application instance to initialize extensions with.
    """
    from app.extensions import db, migrate, cors, jwt
    
    try:
        # Ensure DATABASE_URI is set before initializing SQLAlchemy
        # If None or empty, provide a safe fallback for testing/development
        if not app.config.get('SQLALCHEMY_DATABASE_URI'):
            logger.warning(
                "SQLALCHEMY_DATABASE_URI not set. Using default SQLite database. "
                "Set DATABASE_URL environment variable for production."
            )
            app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///default.db'
        
        # Initialize SQLAlchemy database ORM
        db.init_app(app)
        logger.debug("Initialized SQLAlchemy database extension")
        
        # Initialize Flask-Migrate for database migrations
        # Pass both app and db instance for migration support
        migrate.init_app(app, db)
        logger.debug("Initialized Flask-Migrate extension")
        
        # Initialize CORS for cross-origin requests
        cors.init_app(app)
        logger.debug("Initialized Flask-CORS extension")
        
        # Initialize JWT Manager for authentication
        jwt.init_app(app)
        logger.debug("Initialized Flask-JWT-Extended extension")
        
    except Exception as e:
        logger.error(f"Error initializing extensions: {e}")
        raise


def _register_blueprints(app):
    """
    Dynamically discover and register Flask blueprints.
    
    This function attempts to import and register blueprints from the app.routes
    module. It handles missing blueprint modules gracefully, allowing the
    application to start even if no routes are defined yet.
    
    Blueprint Discovery:
        - Looks for route modules in app/routes/ directory
        - Each route module should export a Blueprint instance
        - Blueprints are registered with optional URL prefix
    
    Args:
        app (Flask): Flask application instance to register blueprints with.
    
    Note:
        This function will not raise errors if no blueprints are found,
        allowing the app to function during initial development or testing.
    """
    # Check if routes module exists
    routes_path = Path(__file__).parent / 'routes'
    
    if not routes_path.exists():
        logger.debug(
            "No routes directory found. Application will start without blueprints."
        )
        return
    
    # Attempt to discover and register blueprints
    try:
        # Try importing common blueprint modules
        blueprint_modules = [
            ('app.routes.auth', 'auth_bp', '/api/auth'),
            ('app.routes.users', 'users_bp', '/api/users'),
            ('app.routes.main', 'main_bp', '/api'),
        ]
        
        registered_count = 0
        for module_name, blueprint_name, url_prefix in blueprint_modules:
            try:
                # Attempt to import the blueprint module
                module = importlib.import_module(module_name)
                
                # Get the blueprint instance from the module
                if hasattr(module, blueprint_name):
                    blueprint = getattr(module, blueprint_name)
                    app.register_blueprint(blueprint, url_prefix=url_prefix)
                    logger.info(
                        f"Registered blueprint '{blueprint_name}' at '{url_prefix}'"
                    )
                    registered_count += 1
                    
            except (ImportError, AttributeError) as e:
                # Blueprint doesn't exist yet, continue silently
                logger.debug(f"Blueprint {module_name}.{blueprint_name} not found: {e}")
                continue
        
        if registered_count == 0:
            logger.debug("No blueprints registered. Routes may not be defined yet.")
        else:
            logger.info(f"Successfully registered {registered_count} blueprint(s)")
            
    except Exception as e:
        logger.error(f"Error during blueprint registration: {e}")
        # Don't raise - allow app to start without blueprints for testing


def _register_error_handlers(app):
    """
    Register error handlers for consistent error responses across the application.
    
    This function configures custom error handlers for common HTTP errors and
    exceptions, ensuring that all errors return properly formatted JSON responses
    with appropriate status codes and error messages.
    
    Error Handlers Registered:
        - 400 Bad Request: Invalid client request data
        - 401 Unauthorized: Authentication required or failed
        - 403 Forbidden: Insufficient permissions
        - 404 Not Found: Resource not found
        - 405 Method Not Allowed: HTTP method not supported
        - 500 Internal Server Error: Unexpected server errors
        - Generic HTTPException: Catch-all for Werkzeug HTTP exceptions
        - Generic Exception: Catch-all for unhandled exceptions
    
    Args:
        app (Flask): Flask application instance to register error handlers with.
    
    Response Format:
        All error responses follow this JSON structure:
        {
            "error": {
                "status": <HTTP status code>,
                "message": "<Error message>",
                "type": "<Error type>"
            }
        }
    """
    
    @app.errorhandler(400)
    def bad_request_error(error):
        """Handle 400 Bad Request errors."""
        # Preserve custom error description if provided
        message = error.description if hasattr(error, 'description') and error.description != 'Bad Request' else 'Bad request. The request data is invalid or malformed.'
        return jsonify({
            'error': {
                'status': 400,
                'message': message,
                'type': 'BadRequest'
            }
        }), 400
    
    @app.errorhandler(401)
    def unauthorized_error(error):
        """Handle 401 Unauthorized errors."""
        # Preserve custom error description if provided
        message = error.description if hasattr(error, 'description') and error.description != 'Unauthorized' else 'Unauthorized. Authentication is required.'
        return jsonify({
            'error': {
                'status': 401,
                'message': message,
                'type': 'Unauthorized'
            }
        }), 401
    
    @app.errorhandler(403)
    def forbidden_error(error):
        """Handle 403 Forbidden errors."""
        return jsonify({
            'error': {
                'status': 403,
                'message': 'Forbidden. You do not have permission to access this resource.',
                'type': 'Forbidden'
            }
        }), 403
    
    @app.errorhandler(404)
    def not_found_error(error):
        """Handle 404 Not Found errors."""
        return jsonify({
            'error': {
                'status': 404,
                'message': 'Resource not found.',
                'type': 'NotFound'
            }
        }), 404
    
    @app.errorhandler(405)
    def method_not_allowed_error(error):
        """Handle 405 Method Not Allowed errors."""
        return jsonify({
            'error': {
                'status': 405,
                'message': 'Method not allowed for this endpoint.',
                'type': 'MethodNotAllowed'
            }
        }), 405
    
    @app.errorhandler(500)
    def internal_server_error(error):
        """Handle 500 Internal Server Error."""
        logger.error(f"Internal server error: {error}")
        return jsonify({
            'error': {
                'status': 500,
                'message': 'Internal server error. Please try again later.',
                'type': 'InternalServerError'
            }
        }), 500
    
    @app.errorhandler(HTTPException)
    def handle_http_exception(error):
        """Handle all Werkzeug HTTP exceptions."""
        return jsonify({
            'error': {
                'status': error.code,
                'message': error.description,
                'type': error.name
            }
        }), error.code
    
    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        """Handle all unexpected exceptions."""
        logger.exception(f"Unexpected error: {error}")
        
        # In production, don't expose internal error details
        if app.config.get('DEBUG'):
            error_message = str(error)
        else:
            error_message = 'An unexpected error occurred. Please contact support.'
        
        return jsonify({
            'error': {
                'status': 500,
                'message': error_message,
                'type': 'UnexpectedError'
            }
        }), 500
    
    logger.debug("Registered error handlers for consistent error responses")


def _configure_logging(app):
    """
    Configure application logging based on environment and configuration.
    
    Sets up logging handlers, formatters, and log levels appropriate for the
    application's configuration. Ensures proper logging for debugging in
    development and appropriate log levels in production.
    
    Args:
        app (Flask): Flask application instance to configure logging for.
    """
    # Get log level from config or default to INFO
    log_level_name = app.config.get('LOG_LEVEL', 'INFO')
    log_level = getattr(logging, log_level_name.upper(), logging.INFO)
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Set Flask app logger level
    app.logger.setLevel(log_level)
    
    # Log configuration details
    app.logger.info(f"Logging configured with level: {log_level_name}")
    app.logger.debug(f"Debug mode: {app.config.get('DEBUG', False)}")
    app.logger.debug(f"Testing mode: {app.config.get('TESTING', False)}")
