"""
Database Helper Utilities for Testing

This module provides comprehensive database helper functions for test data management,
database seeding, transaction handling, and test isolation. These utilities simplify
database testing by providing reusable functions for common database operations.

The helpers support:
- Database table creation and cleanup
- Bulk data insertion for performance
- Fixture data loading from JSON/YAML files
- Database state backup and restoration
- Transaction management for test isolation
- Database verification and validation

Usage:
    from tests.helpers.db_helpers import (
        seed_database,
        clear_database,
        create_test_tables,
        bulk_insert_users
    )
    
    def test_user_operations(app):
        with app.app_context():
            create_test_tables()
            seed_database()
            # Test code here
            clear_database()

All functions work with SQLAlchemy ORM and support in-memory SQLite for fast testing.
"""

from typing import Optional, Dict, List, Any, Type, Union, Callable
import json
from pathlib import Path
from contextlib import contextmanager
import copy
try:
    import yaml
except ImportError:
    yaml = None  # YAML support is optional

from app.extensions import db
from app.models import User


def seed_database(user_count: int = 10, **kwargs: Any) -> Dict[str, List[Any]]:
    """
    Seeds database with initial test data.
    
    Creates a specified number of test users and other test data as needed for
    testing. This function is useful for integration tests that require populated
    database state.
    
    Args:
        user_count: Number of users to create (default: 10)
        **kwargs: Additional seed data configuration options
    
    Returns:
        Dictionary containing lists of created records by model type:
        {
            'users': [<User>, <User>, ...],
            ...
        }
    
    Example:
        >>> seed_data = seed_database(user_count=5)
        >>> assert len(seed_data['users']) == 5
    """
    created_records: Dict[str, List[Any]] = {'users': []}
    
    try:
        # Create test users with unique emails
        users = []
        for i in range(user_count):
            user = User(
                email=f'testuser{i}@example.com',
                password_hash=f'hashed_password_{i}',  # Mock hash
                first_name=f'TestFirst{i}',
                last_name=f'TestLast{i}',
                is_active=True
            )
            users.append(user)
        
        db.session.add_all(users)
        db.session.commit()
        created_records['users'] = users
        
    except Exception as e:
        db.session.rollback()
        raise RuntimeError(f"Failed to seed database: {str(e)}") from e
    
    return created_records


def clear_database() -> None:
    """
    Removes all data from database tables.
    
    Deletes all records from all tables in the database while preserving table
    structure. This is useful for cleaning up after tests to ensure test isolation.
    
    Note: This function deletes data but does not drop tables. Use drop_test_tables()
    to remove table structures.
    
    Example:
        >>> clear_database()
        >>> assert User.query.count() == 0
    """
    try:
        # Get all table names from metadata
        meta = db.metadata
        
        # Disable foreign key constraints temporarily (for SQLite)
        if db.engine.name == 'sqlite':
            db.session.execute(db.text('PRAGMA foreign_keys = OFF'))
        
        # Delete data from all tables
        for table in reversed(meta.sorted_tables):
            db.session.execute(table.delete())
        
        db.session.commit()
        
        # Re-enable foreign key constraints
        if db.engine.name == 'sqlite':
            db.session.execute(db.text('PRAGMA foreign_keys = ON'))
            db.session.commit()
            
    except Exception as e:
        db.session.rollback()
        raise RuntimeError(f"Failed to clear database: {str(e)}") from e


def create_test_tables() -> None:
    """
    Creates database tables for testing.
    
    Creates all tables defined in SQLAlchemy models. This is typically called at the
    beginning of test sessions or test cases that require a fresh database schema.
    
    Example:
        >>> create_test_tables()
        >>> # Tables are now created and ready for testing
    """
    try:
        db.create_all()
    except Exception as e:
        raise RuntimeError(f"Failed to create test tables: {str(e)}") from e


def drop_test_tables() -> None:
    """
    Drops all test tables.
    
    Removes all tables from the database including their structure and data. This is
    useful for complete cleanup after test runs or when resetting database schema
    between test sessions.
    
    Example:
        >>> drop_test_tables()
        >>> # All tables are removed from database
    """
    try:
        db.drop_all()
    except Exception as e:
        raise RuntimeError(f"Failed to drop test tables: {str(e)}") from e


def bulk_insert_users(user_data_list: List[Dict[str, Any]]) -> List[User]:
    """
    Inserts multiple users efficiently.
    
    Creates and inserts multiple User records in a single transaction for improved
    performance. This is useful for tests that require many user records.
    
    Args:
        user_data_list: List of dictionaries containing user data fields:
            - email (required): User email address
            - password_hash: Hashed password
            - first_name: User first name
            - last_name: User last name
            - Additional User model fields as needed
    
    Returns:
        List of created User instances with database-assigned IDs
    
    Example:
        >>> users_data = [
        ...     {'email': 'user1@example.com', 'password_hash': 'hash1'},
        ...     {'email': 'user2@example.com', 'password_hash': 'hash2'}
        ... ]
        >>> users = bulk_insert_users(users_data)
        >>> assert len(users) == 2
    """
    if not user_data_list:
        return []
    
    try:
        users = []
        for user_data in user_data_list:
            user = User(**user_data)
            users.append(user)
        
        db.session.add_all(users)
        db.session.commit()
        
        return users
        
    except Exception as e:
        db.session.rollback()
        raise RuntimeError(f"Failed to bulk insert users: {str(e)}") from e


def bulk_insert_records(model_class: Type[db.Model], records_data: List[Dict[str, Any]]) -> List[Any]:
    """
    Generic bulk insert for any model.
    
    Creates and inserts multiple records of any SQLAlchemy model type in a single
    transaction. This is a generic version of bulk_insert_users that works with
    any model class.
    
    Args:
        model_class: SQLAlchemy model class to instantiate
        records_data: List of dictionaries containing field data for the model
    
    Returns:
        List of created model instances with database-assigned IDs
    
    Example:
        >>> from app.models import User
        >>> data = [{'email': 'test@example.com', 'password_hash': 'hash'}]
        >>> records = bulk_insert_records(User, data)
        >>> assert len(records) == 1
    """
    if not records_data:
        return []
    
    try:
        records = []
        for record_data in records_data:
            record = model_class(**record_data)
            records.append(record)
        
        db.session.add_all(records)
        db.session.commit()
        
        return records
        
    except Exception as e:
        db.session.rollback()
        raise RuntimeError(
            f"Failed to bulk insert {model_class.__name__} records: {str(e)}"
        ) from e


def load_fixture_data(fixture_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Loads data from JSON/YAML fixture files.
    
    Reads test fixture data from JSON or YAML files and returns it as a Python
    dictionary. The file format is auto-detected based on file extension.
    
    Args:
        fixture_path: Path to fixture file (.json or .yaml/.yml)
    
    Returns:
        Dictionary containing the loaded fixture data
    
    Raises:
        FileNotFoundError: If fixture file does not exist
        ValueError: If file format is unsupported or data is invalid
    
    Example:
        >>> data = load_fixture_data('tests/fixtures/users.json')
        >>> users = bulk_insert_records(User, data['users'])
    """
    fixture_path = Path(fixture_path)
    
    if not fixture_path.exists():
        raise FileNotFoundError(f"Fixture file not found: {fixture_path}")
    
    try:
        file_content = fixture_path.read_text(encoding='utf-8')
        
        # Determine file format from extension
        if fixture_path.suffix.lower() == '.json':
            return json.loads(file_content)
        elif fixture_path.suffix.lower() in ['.yaml', '.yml']:
            if yaml is None:
                raise ImportError(
                    "PyYAML is required for YAML fixtures. "
                    "Install with: pip install pyyaml"
                )
            return yaml.safe_load(file_content)
        else:
            raise ValueError(
                f"Unsupported fixture format: {fixture_path.suffix}. "
                "Supported formats: .json, .yaml, .yml"
            )
            
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in fixture file: {str(e)}") from e
    except Exception as e:
        # Handle YAML errors or other parsing errors
        if yaml and isinstance(e, yaml.YAMLError):
            raise ValueError(f"Invalid YAML in fixture file: {str(e)}") from e
        if not isinstance(e, (ValueError, FileNotFoundError, ImportError)):
            raise RuntimeError(f"Failed to load fixture data: {str(e)}") from e
        raise


def create_database_backup() -> Dict[str, List[Dict[str, Any]]]:
    """
    Creates snapshot of database state.
    
    Captures the current state of all records in all tables and returns them as a
    dictionary. This can be used with restore_database_backup() to restore database
    state later.
    
    Returns:
        Dictionary mapping table names to lists of record dictionaries
    
    Example:
        >>> backup = create_database_backup()
        >>> # Make changes to database
        >>> restore_database_backup(backup)
    """
    backup: Dict[str, List[Dict[str, Any]]] = {}
    
    try:
        # Iterate through all tables
        meta = db.metadata
        for table in meta.sorted_tables:
            table_name = table.name
            
            # Query all records from table
            records = db.session.execute(db.select(table)).fetchall()
            
            # Convert records to dictionaries
            backup[table_name] = []
            for record in records:
                # Convert row to dictionary
                record_dict = dict(record._mapping)
                backup[table_name].append(copy.deepcopy(record_dict))
        
        return backup
        
    except Exception as e:
        raise RuntimeError(f"Failed to create database backup: {str(e)}") from e


def restore_database_backup(backup: Dict[str, List[Dict[str, Any]]]) -> None:
    """
    Restores database to saved state.
    
    Clears the current database and restores it to a previously saved state created
    by create_database_backup(). This is useful for test isolation when you need to
    reset database state between tests.
    
    Args:
        backup: Database backup dictionary from create_database_backup()
    
    Example:
        >>> backup = create_database_backup()
        >>> # Make changes
        >>> restore_database_backup(backup)
        >>> # Database is now in original state
    """
    try:
        # Clear existing data
        clear_database()
        
        # Restore data for each table
        meta = db.metadata
        for table in meta.sorted_tables:
            table_name = table.name
            if table_name in backup and backup[table_name]:
                # Insert records back into table
                db.session.execute(table.insert(), backup[table_name])
        
        db.session.commit()
        
    except Exception as e:
        db.session.rollback()
        raise RuntimeError(f"Failed to restore database backup: {str(e)}") from e


def get_record_count(model_class: Type[db.Model]) -> int:
    """
    Returns count of records in table.
    
    Queries the database to count the number of records for a given model class.
    This is useful for verifying test data creation and cleanup.
    
    Args:
        model_class: SQLAlchemy model class to count
    
    Returns:
        Number of records in the model's table
    
    Example:
        >>> count = get_record_count(User)
        >>> assert count == 0  # Verify database is empty
    """
    try:
        return db.session.query(model_class).count()
    except Exception as e:
        raise RuntimeError(
            f"Failed to get record count for {model_class.__name__}: {str(e)}"
        ) from e


def verify_database_empty() -> None:
    """
    Asserts database has no test data.
    
    Verifies that all tables in the database are empty. Raises an AssertionError if
    any table contains data. This is useful for verifying database cleanup in test
    teardown.
    
    Raises:
        AssertionError: If any table contains data
    
    Example:
        >>> clear_database()
        >>> verify_database_empty()  # Passes
    """
    try:
        meta = db.metadata
        non_empty_tables = []
        
        for table in meta.sorted_tables:
            result = db.session.execute(
                db.select(db.func.count()).select_from(table)
            ).scalar()
            
            if result > 0:
                non_empty_tables.append(f"{table.name} ({result} records)")
        
        if non_empty_tables:
            raise AssertionError(
                f"Database is not empty. Tables with data: {', '.join(non_empty_tables)}"
            )
            
    except AssertionError:
        raise
    except Exception as e:
        raise RuntimeError(f"Failed to verify database empty: {str(e)}") from e


@contextmanager
def create_test_transaction():
    """
    Creates transaction context for rollback testing.
    
    Provides a context manager that begins a database transaction and automatically
    rolls it back when the context exits. This ensures test isolation by preventing
    test changes from persisting to the database.
    
    Usage:
        >>> with create_test_transaction():
        ...     user = User(email='test@example.com')
        ...     db.session.add(user)
        ...     db.session.flush()  # Use flush instead of commit
        ...     # Transaction is rolled back on exit
        >>> assert User.query.count() == 0
    
    Yields:
        Database session with active transaction
    
    Note:
        Use db.session.flush() instead of db.session.commit() inside the context
        to avoid committing the transaction prematurely.
    """
    # Begin nested transaction using SAVEPOINT
    connection = db.engine.connect()
    transaction = connection.begin()
    
    # Create a new session bound to the connection
    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=connection)
    test_session = Session()
    
    # Save original session
    original_session = db.session
    
    try:
        # Replace the db.session with our test session
        db.session = test_session
        yield test_session
    finally:
        # Rollback the transaction
        test_session.close()
        transaction.rollback()
        connection.close()
        
        # Restore original session
        db.session = original_session


def rollback_transaction() -> None:
    """
    Rolls back test transaction.
    
    Explicitly rolls back the current database transaction. This is useful for
    cleaning up after tests that modify the database or for testing rollback
    behavior itself.
    
    Example:
        >>> user = User(email='test@example.com')
        >>> db.session.add(user)
        >>> rollback_transaction()
        >>> assert User.query.count() == 0
    """
    try:
        db.session.rollback()
    except Exception as e:
        raise RuntimeError(f"Failed to rollback transaction: {str(e)}") from e
