"""Base factory class for factory_boy test data factories.

This module provides the BaseFactory class that serves as the foundation for all
factory_boy factories in the test suite. It extends SQLAlchemyModelFactory with
shared configuration, database session management, and common factory patterns.

All model factories (UserFactory, PostFactory, ProductFactory, etc.) should inherit
from BaseFactory to ensure consistent database session handling and factory behavior.
"""

import factory
from factory.alchemy import SQLAlchemyModelFactory


class BaseFactory(SQLAlchemyModelFactory):
    """Base factory class for all model factories with SQLAlchemy integration.
    
    This base class provides:
    - SQLAlchemy session management integrated with Flask-SQLAlchemy
    - Automatic database session handling for factory operations
    - Common configuration shared across all model factories
    - Session cleanup and transaction management
    - Dynamic session configuration via class methods
    
    All model factories (UserFactory, PostFactory, etc.) should inherit from this class
    to leverage shared session management and configuration.
    
    Usage Example:
        ```python
        # Define a model factory
        class UserFactory(BaseFactory):
            class Meta:
                model = User
            
            email = factory.Sequence(lambda n: f'user{n}@example.com')
            username = factory.Sequence(lambda n: f'user{n}')
        
        # Configure session in test fixture
        @pytest.fixture(autouse=True)
        def setup_factories(db_session):
            BaseFactory.set_session(db_session)
            yield
            BaseFactory.set_session(None)
        
        # Use in tests
        def test_example(setup_factories):
            user = UserFactory()
            assert user.id is not None
        ```
    
    Attributes:
        Meta.abstract: Marks this as an abstract factory (no direct instantiation)
        Meta.sqlalchemy_session: Database session for factory operations
        Meta.sqlalchemy_session_persistence: Persistence strategy ('commit' or 'flush')
    """
    
    class Meta:
        """Factory metadata configuration.
        
        Attributes:
            abstract: True to prevent direct instantiation of BaseFactory
            sqlalchemy_session: Database session instance (set dynamically via set_session())
            sqlalchemy_session_persistence: Strategy for persisting objects to database
                - 'commit': Commit objects to database (default, ensures data is saved)
                - 'flush': Flush to database without commit (faster for tests)
        """
        abstract = True  # This is an abstract factory, not tied to a specific model
        sqlalchemy_session = None  # Will be set dynamically from pytest fixtures
        sqlalchemy_session_persistence = 'commit'  # Commit objects to database
    
    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """Override _create to ensure proper session handling.
        
        This method is called by factory_boy to create instances. It ensures that
        the database session is properly configured before attempting to create
        model instances.
        
        Args:
            model_class: The SQLAlchemy model class to instantiate
            *args: Positional arguments passed to model constructor
            **kwargs: Keyword arguments passed to model constructor
        
        Returns:
            Instance of model_class persisted to the database
        
        Raises:
            RuntimeError: If database session is not configured via set_session()
        
        Note:
            This method should not be called directly. Use the factory class
            directly (e.g., UserFactory()) which will invoke this method internally.
        """
        # Get session from meta if not already set
        if cls._meta.sqlalchemy_session is None:
            # Session must be set by pytest fixtures via set_session()
            raise RuntimeError(
                f"Database session not configured for {cls.__name__}. "
                "Call BaseFactory.set_session(db.session) in your test fixture "
                "before using factories. "
                "\n\nExample fixture:\n"
                "    @pytest.fixture(autouse=True)\n"
                "    def setup_factory_session(db_session):\n"
                "        BaseFactory.set_session(db_session)\n"
                "        yield\n"
                "        BaseFactory.set_session(None)"
            )
        
        # Call parent _create with validated session
        return super()._create(model_class, *args, **kwargs)
    
    @classmethod
    def set_session(cls, session):
        """Set the SQLAlchemy session for all factories.
        
        This method should be called in pytest fixtures to configure the database
        session used by all factory_boy factories. It sets the session for BaseFactory
        and automatically propagates it to all subclass factories (UserFactory,
        PostFactory, etc.).
        
        Args:
            session: SQLAlchemy session instance from Flask-SQLAlchemy (db.session)
                     or None to clear the session
        
        Example:
            ```python
            # In tests/conftest.py
            @pytest.fixture(autouse=True)
            def setup_factory_session(db_session):
                '''Configure factory_boy factories with database session.'''
                BaseFactory.set_session(db_session)
                yield
                BaseFactory.set_session(None)  # Cleanup after tests
            ```
        
        Note:
            - This should be called once per test session in a pytest fixture
            - Setting session to None clears the configuration (useful for cleanup)
            - All existing subclass factories will automatically use the new session
            - Safe to call multiple times (replaces previous session configuration)
        """
        # Set session on BaseFactory
        cls._meta.sqlalchemy_session = session
        
        # Propagate session to all subclasses
        # This ensures UserFactory, PostFactory, etc. all use the same session
        for subclass in cls.__subclasses__():
            if hasattr(subclass._meta, 'sqlalchemy_session'):
                subclass._meta.sqlalchemy_session = session
            
            # Recursively update nested subclasses
            # (e.g., if factories inherit from intermediate base classes)
            _update_subclass_sessions(subclass, session)


def _update_subclass_sessions(factory_class, session):
    """Recursively update session for all subclasses of a factory.
    
    Helper function to ensure deeply nested factory class hierarchies
    all receive the updated database session.
    
    Args:
        factory_class: Factory class to update subclasses for
        session: SQLAlchemy session to set
    """
    for subclass in factory_class.__subclasses__():
        if hasattr(subclass._meta, 'sqlalchemy_session'):
            subclass._meta.sqlalchemy_session = session
        
        # Recursive call for nested hierarchies
        _update_subclass_sessions(subclass, session)
