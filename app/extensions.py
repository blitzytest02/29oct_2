"""
Flask Extensions Initialization Module

This module initializes Flask extensions using the application factory pattern with
lazy initialization. Extension instances are created here without being bound to a
specific Flask app instance, allowing them to be initialized later with init_app()
in the create_app function.

This pattern enables:
- Testing with multiple app configurations
- Avoiding circular import issues
- Clean separation of concerns
- Multiple Flask app instances in the same process

Extensions initialized:
- SQLAlchemy (db): Database ORM for data persistence
- Migrate (migrate): Database migration management
- CORS (cors): Cross-Origin Resource Sharing configuration
- JWTManager (jwt): JSON Web Token authentication

Usage:
    from app.extensions import db, migrate, cors, jwt
    
    def create_app():
        app = Flask(__name__)
        
        # Initialize extensions with app instance
        db.init_app(app)
        migrate.init_app(app, db)
        cors.init_app(app)
        jwt.init_app(app)
        
        return app
"""

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from flask_jwt_extended import JWTManager


# SQLAlchemy database ORM instance
# Provides database session management and ORM functionality
# Members: create_all(), drop_all(), session, session.commit(), session.rollback(),
#          session.add(), session.delete(), session.query(), init_app()
db = SQLAlchemy()


# Flask-Migrate database migration manager
# Handles database schema migrations using Alembic
# Members: init_app()
migrate = Migrate()


# Flask-CORS cross-origin resource sharing handler
# Manages CORS headers for API endpoints accessible from different origins
# Members: init_app()
cors = CORS()


# Flask-JWT-Extended JSON Web Token manager
# Handles JWT token creation, validation, and authentication
# Members: init_app()
jwt = JWTManager()
