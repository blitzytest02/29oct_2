"""
Mock Database Operations Module

This module provides comprehensive mock implementations for database operations,
enabling unit tests to isolate database logic without requiring actual database connections.

It includes mock implementations for:
- SQLAlchemy Session operations
- Query building and execution
- Transaction management
- Connection pooling
- Database error scenarios

Usage:
    from tests.mocks.mock_database import MockDatabaseSession, mock_db_session
    
    def test_user_creation(mock_db_session):
        user = User(email='test@example.com')
        mock_db_session.add(user)
        mock_db_session.commit()
        assert mock_db_session.add.called
"""

from typing import List, Dict, Optional, Any, Callable, Union
from unittest.mock import MagicMock
from collections.abc import Iterable
from copy import deepcopy
import pytest

# Import SQLAlchemy exceptions for mocking database errors
try:
    from sqlalchemy.exc import IntegrityError, OperationalError, DataError
except ImportError:
    # Fallback for testing environments where SQLAlchemy might not be installed
    class IntegrityError(Exception):
        """Mock IntegrityError for environments without SQLAlchemy"""
        pass
    
    class OperationalError(Exception):
        """Mock OperationalError for environments without SQLAlchemy"""
        pass
    
    class DataError(Exception):
        """Mock DataError for environments without SQLAlchemy"""
        pass


class MockDatabaseSession:
    """
    Mock implementation of SQLAlchemy Session for unit testing.
    
    Provides all essential session methods with configurable behavior
    to support various testing scenarios including success paths,
    error conditions, and transaction management.
    
    Attributes:
        _objects: List of objects added to the session
        _deleted: List of objects marked for deletion
        _committed: Boolean indicating if commit was called
        _rolled_back: Boolean indicating if rollback was called
        _closed: Boolean indicating if session was closed
        _flushed: Boolean indicating if flush was called
        _transaction: Optional MockTransaction instance
    """
    
    def __init__(self):
        """Initialize a new mock database session."""
        self._objects: List[Any] = []
        self._deleted: List[Any] = []
        self._committed: bool = False
        self._rolled_back: bool = False
        self._closed: bool = False
        self._flushed: bool = False
        self._transaction: Optional['MockTransaction'] = None
        self._expired_objects: List[Any] = []
        self._expunged_objects: List[Any] = []
    
    def add(self, instance: Any) -> None:
        """
        Add an object to the session.
        
        Args:
            instance: The object to add to the session
        """
        if instance not in self._objects:
            self._objects.append(instance)
    
    def commit(self) -> None:
        """
        Commit the current transaction.
        
        Marks the session as committed and clears rollback flag.
        """
        self._committed = True
        self._rolled_back = False
    
    def rollback(self) -> None:
        """
        Rollback the current transaction.
        
        Marks the session as rolled back, clears committed flag,
        and resets objects list.
        """
        self._rolled_back = True
        self._committed = False
        self._objects.clear()
        self._deleted.clear()
    
    def delete(self, instance: Any) -> None:
        """
        Mark an object for deletion.
        
        Args:
            instance: The object to delete
        """
        if instance in self._objects:
            self._objects.remove(instance)
        self._deleted.append(instance)
    
    def query(self, *entities: Any) -> 'MockQuery':
        """
        Create a query object for the given entities.
        
        Args:
            *entities: The model classes or columns to query
            
        Returns:
            MockQuery: A mock query object for chaining
        """
        return MockQuery(entities, session=self)
    
    def flush(self) -> None:
        """
        Flush pending changes to the database.
        
        Marks the session as flushed without committing.
        """
        self._flushed = True
    
    def close(self) -> None:
        """
        Close the session and clean up resources.
        
        Marks the session as closed and resets state.
        """
        self._closed = True
        self._objects.clear()
        self._deleted.clear()
    
    def begin(self) -> 'MockTransaction':
        """
        Begin a new transaction.
        
        Returns:
            MockTransaction: A mock transaction object
        """
        self._transaction = MockTransaction(session=self)
        return self._transaction
    
    def begin_nested(self) -> 'MockTransaction':
        """
        Begin a nested transaction (savepoint).
        
        Returns:
            MockTransaction: A mock nested transaction object
        """
        return MockTransaction(session=self, nested=True)
    
    def expire(self, instance: Any, attribute_names: Optional[List[str]] = None) -> None:
        """
        Mark an instance or specific attributes as expired.
        
        Args:
            instance: The object to expire
            attribute_names: Optional list of specific attributes to expire
        """
        if instance not in self._expired_objects:
            self._expired_objects.append(instance)
    
    def expire_all(self) -> None:
        """
        Expire all objects in the session.
        
        Marks all tracked objects as expired, requiring reload on next access.
        """
        self._expired_objects.extend(self._objects)
    
    def expunge(self, instance: Any) -> None:
        """
        Remove an object from the session.
        
        Args:
            instance: The object to expunge from the session
        """
        if instance in self._objects:
            self._objects.remove(instance)
        self._expunged_objects.append(instance)
    
    def expunge_all(self) -> None:
        """
        Remove all objects from the session.
        
        Clears all tracked objects without affecting the database.
        """
        self._expunged_objects.extend(self._objects)
        self._objects.clear()
    
    def refresh(self, instance: Any, attribute_names: Optional[List[str]] = None) -> None:
        """
        Refresh an instance with the latest data from the database.
        
        Args:
            instance: The object to refresh
            attribute_names: Optional list of specific attributes to refresh
        """
        # In mock implementation, this is a no-op but tracks the call
        if instance not in self._objects:
            self._objects.append(instance)
    
    def merge(self, instance: Any, load: bool = True) -> Any:
        """
        Merge an object into the session.
        
        Args:
            instance: The object to merge
            load: Whether to load the object if not already in session
            
        Returns:
            The merged object (in mock, returns a copy of the instance)
        """
        merged = deepcopy(instance)
        if merged not in self._objects:
            self._objects.append(merged)
        return merged


class MockQuery:
    """
    Mock implementation of SQLAlchemy Query for unit testing.
    
    Provides chainable query methods that can be configured to return
    specific test data or raise database errors for testing error handling.
    
    Attributes:
        _entities: The model classes being queried
        _filters: List of filter conditions applied
        _results: Configured result set to return
        _session: Optional reference to the mock session
    """
    
    def __init__(self, entities: tuple, session: Optional[MockDatabaseSession] = None,
                 results: Optional[List[Any]] = None):
        """
        Initialize a new mock query.
        
        Args:
            entities: Tuple of model classes or columns
            session: Optional mock session reference
            results: Optional pre-configured results
        """
        self._entities = entities
        self._session = session
        self._results = results or []
        self._filters: List[Dict[str, Any]] = []
        self._order: List[str] = []
        self._limit_value: Optional[int] = None
        self._offset_value: int = 0
        self._joins: List[Any] = []
        self._groups: List[str] = []
        self._having_clause: Optional[Any] = None
        self._distinct_flag: bool = False
    
    def filter(self, *criterion: Any) -> 'MockQuery':
        """
        Apply filter criteria to the query.
        
        Args:
            *criterion: Filter expressions to apply
            
        Returns:
            MockQuery: Self for method chaining
        """
        for crit in criterion:
            self._filters.append({'type': 'filter', 'criterion': crit})
        return self
    
    def filter_by(self, **kwargs: Any) -> 'MockQuery':
        """
        Apply filter criteria using keyword arguments.
        
        Args:
            **kwargs: Column=value pairs for filtering
            
        Returns:
            MockQuery: Self for method chaining
        """
        self._filters.append({'type': 'filter_by', 'kwargs': kwargs})
        return self
    
    def first(self) -> Optional[Any]:
        """
        Return the first result or None if no results.
        
        Returns:
            Optional[Any]: First result or None
        """
        return self._results[0] if self._results else None
    
    def all(self) -> List[Any]:
        """
        Return all results as a list.
        
        Returns:
            List[Any]: All query results
        """
        results = self._results.copy()
        
        # Apply limit and offset
        if self._offset_value:
            results = results[self._offset_value:]
        if self._limit_value is not None:
            results = results[:self._limit_value]
        
        return results
    
    def one(self) -> Any:
        """
        Return exactly one result or raise an error.
        
        Returns:
            Any: The single result
            
        Raises:
            ValueError: If no results or multiple results found
        """
        if len(self._results) == 0:
            raise ValueError("No results found")
        if len(self._results) > 1:
            raise ValueError("Multiple results found")
        return self._results[0]
    
    def one_or_none(self) -> Optional[Any]:
        """
        Return one result, None, or raise error if multiple results.
        
        Returns:
            Optional[Any]: Single result or None
            
        Raises:
            ValueError: If multiple results found
        """
        if len(self._results) == 0:
            return None
        if len(self._results) > 1:
            raise ValueError("Multiple results found")
        return self._results[0]
    
    def count(self) -> int:
        """
        Return the count of results.
        
        Returns:
            int: Number of results
        """
        return len(self._results)
    
    def join(self, *props: Any, **kwargs: Any) -> 'MockQuery':
        """
        Add a JOIN clause to the query.
        
        Args:
            *props: Properties or models to join
            **kwargs: Additional join parameters
            
        Returns:
            MockQuery: Self for method chaining
        """
        self._joins.extend(props)
        return self
    
    def order_by(self, *criterion: Any) -> 'MockQuery':
        """
        Add ORDER BY clauses to the query.
        
        Args:
            *criterion: Order by expressions
            
        Returns:
            MockQuery: Self for method chaining
        """
        self._order.extend([str(c) for c in criterion])
        return self
    
    def limit(self, limit: int) -> 'MockQuery':
        """
        Limit the number of results returned.
        
        Args:
            limit: Maximum number of results
            
        Returns:
            MockQuery: Self for method chaining
        """
        self._limit_value = limit
        return self
    
    def offset(self, offset: int) -> 'MockQuery':
        """
        Skip a number of results from the beginning.
        
        Args:
            offset: Number of results to skip
            
        Returns:
            MockQuery: Self for method chaining
        """
        self._offset_value = offset
        return self
    
    def group_by(self, *criterion: Any) -> 'MockQuery':
        """
        Add GROUP BY clauses to the query.
        
        Args:
            *criterion: Columns or expressions to group by
            
        Returns:
            MockQuery: Self for method chaining
        """
        self._groups.extend([str(c) for c in criterion])
        return self
    
    def having(self, criterion: Any) -> 'MockQuery':
        """
        Add a HAVING clause to the query.
        
        Args:
            criterion: Having condition expression
            
        Returns:
            MockQuery: Self for method chaining
        """
        self._having_clause = criterion
        return self
    
    def distinct(self, *expr: Any) -> 'MockQuery':
        """
        Apply a DISTINCT clause to the query.
        
        Args:
            *expr: Optional expressions for DISTINCT ON
            
        Returns:
            MockQuery: Self for method chaining
        """
        self._distinct_flag = True
        return self
    
    def scalar(self) -> Optional[Any]:
        """
        Return a scalar result (first column of first row).
        
        Returns:
            Optional[Any]: Scalar value or None
        """
        result = self.first()
        if result is None:
            return None
        # If result is a tuple or has attributes, return first element/attribute
        if isinstance(result, (tuple, list)):
            return result[0] if result else None
        return result
    
    def get(self, ident: Any) -> Optional[Any]:
        """
        Get an object by its primary key identifier.
        
        Args:
            ident: Primary key value
            
        Returns:
            Optional[Any]: Object with matching primary key or None
        """
        # Search through results for matching id
        for result in self._results:
            if hasattr(result, 'id') and result.id == ident:
                return result
        return None
    
    def __iter__(self):
        """
        Make the query iterable.
        
        Returns:
            Iterator over query results
        """
        return iter(self.all())
    
    def __len__(self):
        """
        Return the count of results.
        
        Returns:
            int: Number of results
        """
        return self.count()


class MockTransaction:
    """
    Mock implementation of SQLAlchemy Transaction for unit testing.
    
    Supports context manager protocol for testing transaction blocks.
    
    Attributes:
        _session: Reference to the mock session
        _nested: Whether this is a nested transaction (savepoint)
        _active: Whether the transaction is currently active
        _committed: Whether the transaction was committed
        _rolled_back: Whether the transaction was rolled back
    """
    
    def __init__(self, session: Optional[MockDatabaseSession] = None, nested: bool = False):
        """
        Initialize a new mock transaction.
        
        Args:
            session: Optional mock session reference
            nested: Whether this is a nested transaction
        """
        self._session = session
        self._nested = nested
        self._active = False
        self._committed = False
        self._rolled_back = False
    
    def begin(self) -> 'MockTransaction':
        """
        Begin the transaction.
        
        Returns:
            MockTransaction: Self for chaining
        """
        self._active = True
        return self
    
    def commit(self) -> None:
        """
        Commit the transaction.
        
        Marks transaction as committed and inactive.
        """
        self._committed = True
        self._active = False
        if self._session:
            self._session.commit()
    
    def rollback(self) -> None:
        """
        Rollback the transaction.
        
        Marks transaction as rolled back and inactive.
        """
        self._rolled_back = True
        self._active = False
        if self._session:
            self._session.rollback()
    
    def close(self) -> None:
        """
        Close the transaction.
        
        Marks transaction as inactive.
        """
        self._active = False
    
    def __enter__(self) -> 'MockTransaction':
        """
        Enter the transaction context.
        
        Returns:
            MockTransaction: Self
        """
        self._active = True
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Exit the transaction context.
        
        Commits if no exception, rolls back otherwise.
        
        Args:
            exc_type: Exception type if raised
            exc_val: Exception value if raised
            exc_tb: Exception traceback if raised
        """
        if exc_type is not None:
            self.rollback()
        else:
            self.commit()
        return False  # Don't suppress exceptions


class MockConnectionPool:
    """
    Mock implementation of database connection pool for unit testing.
    
    Simulates connection pool behavior including connection management,
    pool sizing, and connection lifecycle.
    
    Attributes:
        _size: Maximum pool size
        _checked_out: Number of connections currently in use
        _disposed: Whether the pool has been disposed
    """
    
    def __init__(self, pool_size: int = 5):
        """
        Initialize a new mock connection pool.
        
        Args:
            pool_size: Maximum number of connections in the pool
        """
        self._size = pool_size
        self._checked_out = 0
        self._disposed = False
        self._connections: List[MagicMock] = []
    
    def connect(self) -> MagicMock:
        """
        Get a connection from the pool.
        
        Returns:
            MagicMock: A mock database connection
            
        Raises:
            OperationalError: If pool is disposed or exhausted
        """
        if self._disposed:
            raise OperationalError("Connection pool has been disposed", None, None)
        
        if self._checked_out >= self._size:
            raise OperationalError("Connection pool exhausted", None, None)
        
        connection = MagicMock()
        connection.closed = False
        self._connections.append(connection)
        self._checked_out += 1
        return connection
    
    def dispose(self) -> None:
        """
        Dispose of the connection pool and close all connections.
        
        Marks the pool as disposed and clears all connections.
        """
        self._disposed = True
        for conn in self._connections:
            conn.closed = True
        self._connections.clear()
        self._checked_out = 0
    
    def recreate(self) -> 'MockConnectionPool':
        """
        Recreate the connection pool.
        
        Returns a new pool with the same configuration.
        
        Returns:
            MockConnectionPool: A new connection pool instance
        """
        self.dispose()
        return MockConnectionPool(pool_size=self._size)
    
    def status(self) -> Dict[str, Any]:
        """
        Get the current status of the connection pool.
        
        Returns:
            Dict[str, Any]: Pool status information
        """
        return {
            'pool_size': self._size,
            'checked_out': self._checked_out,
            'available': self._size - self._checked_out,
            'disposed': self._disposed,
            'total_connections': len(self._connections)
        }
    
    def size(self) -> int:
        """
        Get the maximum size of the connection pool.
        
        Returns:
            int: Maximum pool size
        """
        return self._size
    
    def checked_in_connections(self) -> int:
        """
        Get the number of connections currently in the pool (not in use).
        
        Returns:
            int: Number of available connections
        """
        return max(0, self._size - self._checked_out)
    
    def checked_out_connections(self) -> int:
        """
        Get the number of connections currently in use.
        
        Returns:
            int: Number of checked out connections
        """
        return self._checked_out


# Helper Functions

def create_mock_query_result(data: List[Any], 
                             deep_copy: bool = True) -> List[Any]:
    """
    Create a mock query result from test data.
    
    Optionally creates deep copies to ensure test isolation and prevent
    test pollution when objects are modified during testing.
    
    Args:
        data: List of objects to use as query results
        deep_copy: Whether to create deep copies of the data (default: True)
        
    Returns:
        List[Any]: Query result list suitable for MockQuery
        
    Example:
        users = [User(id=1, email='test@example.com')]
        mock_results = create_mock_query_result(users)
        mock_query._results = mock_results
    """
    if deep_copy:
        return [deepcopy(item) for item in data]
    return list(data)


def mock_database_error(error_type: str = 'integrity',
                       message: str = 'Database error',
                       orig_error: Optional[Exception] = None) -> Exception:
    """
    Create a mock database error for testing error handling.
    
    Supports various SQLAlchemy exception types to test different
    error scenarios including constraint violations, operational errors,
    and data errors.
    
    Args:
        error_type: Type of error ('integrity', 'operational', 'data')
        message: Error message
        orig_error: Original exception that caused the error
        
    Returns:
        Exception: Appropriate SQLAlchemy exception instance
        
    Example:
        # Test handling of integrity constraint violation
        error = mock_database_error('integrity', 'Duplicate key violation')
        mock_session.commit.side_effect = error
    """
    if error_type == 'integrity':
        return IntegrityError(message, None, orig_error)
    elif error_type == 'operational':
        return OperationalError(message, None, orig_error)
    elif error_type == 'data':
        return DataError(message, None, orig_error)
    else:
        return Exception(f"Unknown error type: {error_type}")


def mock_constraint_violation(constraint_name: str = 'unique_constraint',
                              column_name: Optional[str] = None,
                              value: Optional[Any] = None) -> IntegrityError:
    """
    Create a mock constraint violation error for testing.
    
    Simulates database constraint violations such as unique constraints,
    foreign key violations, and check constraint failures.
    
    Args:
        constraint_name: Name of the violated constraint
        column_name: Optional column name involved in the violation
        value: Optional value that caused the violation
        
    Returns:
        IntegrityError: Mock integrity error with constraint details
        
    Example:
        # Test duplicate email handling
        error = mock_constraint_violation('users_email_key', 'email', 'test@example.com')
        mock_session.commit.side_effect = error
    """
    detail_parts = [f"Constraint {constraint_name} violated"]
    if column_name:
        detail_parts.append(f"on column '{column_name}'")
    if value:
        detail_parts.append(f"with value '{value}'")
    
    message = " ".join(detail_parts)
    return IntegrityError(message, None, None)


# Pytest Fixtures

@pytest.fixture
def mock_db_session() -> MockDatabaseSession:
    """
    Pytest fixture providing a mock database session.
    
    Creates a fresh MockDatabaseSession instance for each test,
    ensuring test isolation and preventing state leakage between tests.
    
    Returns:
        MockDatabaseSession: A new mock session instance
        
    Example:
        def test_user_creation(mock_db_session):
            user = User(email='test@example.com')
            mock_db_session.add(user)
            mock_db_session.commit()
            assert mock_db_session._committed
    """
    return MockDatabaseSession()


@pytest.fixture
def mock_query() -> MockQuery:
    """
    Pytest fixture providing a mock query object.
    
    Creates a fresh MockQuery instance for each test with an empty
    result set that can be configured as needed.
    
    Returns:
        MockQuery: A new mock query instance
        
    Example:
        def test_user_filtering(mock_query):
            mock_query._results = [User(id=1)]
            result = mock_query.filter_by(id=1).first()
            assert result.id == 1
    """
    return MockQuery(entities=(), results=[])


@pytest.fixture
def mock_transaction() -> MockTransaction:
    """
    Pytest fixture providing a mock transaction object.
    
    Creates a fresh MockTransaction instance for each test to enable
    testing of transaction management and context manager behavior.
    
    Returns:
        MockTransaction: A new mock transaction instance
        
    Example:
        def test_transaction_rollback(mock_transaction):
            with mock_transaction:
                raise Exception("Test error")
            assert mock_transaction._rolled_back
    """
    return MockTransaction()

