"""
Database Testing Fixtures

This module provides pytest fixtures for database testing with comprehensive transaction
management, session handling, and database state control. These fixtures ensure complete
test isolation by managing database lifecycle and transaction boundaries.

Fixtures provided:
- db_session: Function-scoped fixture providing fresh database with automatic rollback
- db_transaction: Explicit transaction control for testing rollback scenarios
- clean_database: Utility fixture to clear all tables while preserving schema
- database_engine: Session-scoped database engine for connection pooling tests

Key features:
- Complete test isolation with automatic database cleanup
- Support for both in-memory SQLite (fast unit tests) and PostgreSQL (integration tests)
- Transaction management with nested transaction support
- Connection pooling test support
- Flask application context integration

Usage:
    def test_user_creation(db_session):
        user = User(email='test@example.com', password='secure123')
        db_session.add(user)
        db_session.commit()
        
        assert user.id is not None
        assert User.query.count() == 1
    
    def test_transaction_rollback(db_transaction):
        user = User(email='test@example.com')
        db_transaction.add(user)
        db_transaction.flush()
        
        # Simulate error and rollback
        db_transaction.rollback()
        
        assert User.query.count() == 0

Design principles:
- Each test gets a clean database state (no shared state between tests)
- Automatic teardown prevents test pollution
- Fixtures compose well with other fixtures
- Supports multiple database backends transparently
"""

import pytest
from app.extensions import db


@pytest.fixture(scope='function')
def db_session(app):
    """
    Provides a fresh database session for each test with automatic cleanup.
    
    This fixture creates a complete database schema before each test and destroys
    it after the test completes, ensuring complete test isolation. It uses
    function scope so every test gets its own clean database state.
    
    Lifecycle:
    1. Setup: Creates all database tables using db.create_all()
    2. Test execution: Yields db.session for test to use
    3. Teardown: Rolls back any uncommitted changes and drops all tables
    
    Args:
        app: Flask application instance fixture (from conftest.py)
    
    Yields:
        db.session: SQLAlchemy session object for database operations
    
    Usage:
        def test_create_user(db_session):
            user = User(email='test@example.com')
            db_session.add(user)
            db_session.commit()
            
            assert user.id is not None
    
    Note:
        - Uses in-memory SQLite by default for fast test execution
        - Can be configured to use PostgreSQL for integration tests
        - Automatically handles Flask application context
        - All changes are rolled back even if test fails
    """
    with app.app_context():
        # Create all database tables with current schema
        db.create_all()
        
        try:
            # Yield the session for test to use
            yield db.session
        finally:
            # Ensure cleanup happens even if test fails
            # First, roll back any uncommitted transactions
            db.session.rollback()
            
            # Remove the session to clean up connections
            db.session.remove()
            
            # Drop all tables to ensure clean state for next test
            db.drop_all()


@pytest.fixture
def db_transaction(db_session):
    """
    Provides explicit transaction control for testing transaction behaviors.
    
    This fixture builds on db_session and provides a nested transaction using
    SAVEPOINT functionality. This allows tests to explicitly test transaction
    commit and rollback scenarios, including error handling and database
    constraint violations.
    
    The nested transaction pattern enables:
    - Testing rollback scenarios without affecting the outer transaction
    - Simulating database errors and recovery
    - Testing transaction isolation levels
    - Verifying constraint violation handling
    
    Args:
        db_session: Database session fixture providing base session
    
    Yields:
        db.session: SQLAlchemy session with nested transaction active
    
    Usage:
        def test_rollback_on_error(db_transaction):
            # Create user in nested transaction
            user = User(email='test@example.com')
            db_transaction.add(user)
            db_transaction.flush()  # Force SQL execution
            
            # Verify user exists in transaction
            assert User.query.filter_by(email='test@example.com').first() is not None
            
            # Simulate error and rollback
            db_transaction.rollback()
            
            # Verify user was rolled back
            assert User.query.filter_by(email='test@example.com').first() is None
        
        def test_commit_nested_transaction(db_transaction):
            user = User(email='test@example.com')
            db_transaction.add(user)
            
            # Commit nested transaction
            db_transaction.commit()
            
            # Verify changes persisted within test scope
            assert User.query.count() == 1
    
    Note:
        - Uses SAVEPOINT for nested transactions (supported by PostgreSQL, MySQL, SQLite 3.6.8+)
        - Nested transaction is automatically rolled back after test
        - Allows testing both successful commits and rollback scenarios
        - Changes committed in nested transaction are visible to the test
    """
    # Begin a nested transaction using SAVEPOINT
    nested_transaction = db_session.begin_nested()
    
    try:
        # Yield the session for test to use with nested transaction
        yield db_session
    finally:
        # Ensure nested transaction cleanup
        # If test didn't explicitly rollback or commit, we rollback
        if nested_transaction.is_active:
            nested_transaction.rollback()


@pytest.fixture
def clean_database(app):
    """
    Utility fixture to clear all database tables while preserving schema.
    
    This fixture is useful for integration tests that need to reset the database
    to a clean state without destroying and recreating the schema. It deletes
    all data from all tables but preserves the table structure, which is faster
    than dropping and recreating tables.
    
    Use cases:
    - Integration test setup requiring clean state
    - Test suites that share database across multiple tests
    - Clearing test data between test classes
    - Resetting database for specific test scenarios
    
    Args:
        app: Flask application instance fixture
    
    Yields:
        callable: Function that clears all database tables when called
    
    Usage:
        def test_with_clean_state(clean_database):
            # Start with clean database
            clean_database()
            
            # Perform test operations
            user1 = User(email='user1@example.com')
            user2 = User(email='user2@example.com')
            db.session.add_all([user1, user2])
            db.session.commit()
            
            assert User.query.count() == 2
            
            # Clean database mid-test if needed
            clean_database()
            
            assert User.query.count() == 0
        
        @pytest.fixture
        def populated_database(clean_database, db_session):
            # Clear any existing data
            clean_database()
            
            # Populate with test data
            users = [User(email=f'user{i}@example.com') for i in range(10)]
            db_session.add_all(users)
            db_session.commit()
            
            return db_session
    
    Note:
        - Faster than dropping and recreating tables
        - Preserves database schema and indexes
        - Handles foreign key constraints properly
        - Requires Flask application context
    """
    def _clean_database():
        """
        Internal function to perform database cleanup.
        
        Clears all data from all tables in the correct order to handle
        foreign key constraints. Uses SQLAlchemy metadata to discover
        all tables and truncates them efficiently.
        """
        with app.app_context():
            # Get all table names from metadata
            # Reverse order handles foreign key dependencies
            for table in reversed(db.metadata.sorted_tables):
                # Delete all rows from table
                db.session.execute(table.delete())
            
            # Commit the deletions
            db.session.commit()
    
    yield _clean_database


@pytest.fixture(scope='session')
def database_engine(app):
    """
    Provides session-scoped database engine for connection pooling tests.
    
    This fixture provides access to the underlying SQLAlchemy engine for tests
    that need to verify connection pooling behavior, connection lifecycle, or
    low-level database operations. It persists for the entire test session,
    making it suitable for performance tests and connection management validation.
    
    Use cases:
    - Testing database connection pooling configuration
    - Verifying connection acquisition and release
    - Performance testing with connection reuse
    - Testing connection timeout and error handling
    - Raw SQL execution for complex test scenarios
    
    Args:
        app: Flask application instance fixture
    
    Yields:
        Engine: SQLAlchemy engine instance
    
    Usage:
        def test_connection_pooling(database_engine):
            # Get pool statistics
            pool = database_engine.pool
            
            # Verify pool configuration
            assert pool.size() >= 0
            assert pool.timeout() == 30
            
            # Test connection acquisition
            connection = database_engine.connect()
            assert connection is not None
            
            # Verify connection is from pool
            assert pool.checkedout() > 0
            
            # Release connection back to pool
            connection.close()
            assert pool.checkedout() == 0
        
        def test_concurrent_connections(database_engine):
            # Test multiple simultaneous connections
            connections = []
            for i in range(5):
                conn = database_engine.connect()
                connections.append(conn)
            
            # Verify all connections acquired
            assert len(connections) == 5
            assert database_engine.pool.checkedout() == 5
            
            # Close all connections
            for conn in connections:
                conn.close()
            
            # Verify all returned to pool
            assert database_engine.pool.checkedout() == 0
        
        def test_raw_sql_execution(database_engine):
            # Execute raw SQL for complex test setup
            with database_engine.connect() as connection:
                result = connection.execute(
                    "SELECT COUNT(*) as count FROM users"
                )
                count = result.fetchone()['count']
                assert count >= 0
    
    Note:
        - Session scope persists engine for entire test run
        - Useful for connection pool behavior testing
        - Provides lower-level database access than db.session
        - Requires manual connection management
        - Connection pool statistics available via engine.pool
    """
    with app.app_context():
        # Get the database engine from the db extension
        engine = db.engine
        
        yield engine
        
        # Session-scoped fixture doesn't need per-test cleanup
        # Engine will be properly closed when test session ends
