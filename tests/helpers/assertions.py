"""
Custom Assertion Helper Functions for Flask Testing

This module provides reusable, expressive assertion functions for complex validation
scenarios in Flask tests. All functions provide clear, descriptive failure messages
to aid in debugging test failures.

Functions:
    - assert_json_structure: Validates JSON response matches expected structure
    - assert_status_code: Enhanced status code assertion with descriptive messages
    - assert_response_contains: Checks if response contains expected keys/values
    - assert_response_excludes: Verifies response does not contain sensitive data
    - assert_valid_datetime: Validates datetime string formats
    - assert_valid_uuid: Validates UUID format strings
    - assert_error_response: Validates error response format
    - assert_pagination: Validates pagination metadata in responses
    - assert_list_length: Validates list length with descriptive messages
    - assert_nested_value: Validates nested dictionary values with path notation
"""

from typing import Optional, Dict, Any, List, Union, Callable
from datetime import datetime
from uuid import UUID
import re
import json
from functools import reduce


def assert_json_structure(
    data: Any,
    expected_structure: Dict[str, Any],
    strict: bool = False,
    path: str = ""
) -> None:
    """
    Validates that a JSON data structure matches the expected structure.
    
    Args:
        data: The actual data structure to validate
        expected_structure: A dictionary defining the expected structure where:
            - Keys are field names
            - Values can be:
                * type objects (int, str, list, dict, etc.)
                * nested dictionaries for nested structures
                * callable validators
        strict: If True, disallows extra keys not in expected_structure
        path: Current path in nested structure (for error messages)
    
    Raises:
        AssertionError: If the structure doesn't match expectations
    
    Example:
        expected = {
            'id': int,
            'name': str,
            'email': str,
            'created_at': str,
            'profile': {
                'age': int,
                'city': str
            }
        }
        assert_json_structure(response_data, expected)
    """
    if not isinstance(expected_structure, dict):
        raise ValueError("expected_structure must be a dictionary")
    
    if not isinstance(data, dict):
        location = f" at {path}" if path else ""
        raise AssertionError(
            f"Expected dict{location}, got {type(data).__name__}: {data}"
        )
    
    # Check for missing required keys
    missing_keys = set(expected_structure.keys()) - set(data.keys())
    if missing_keys:
        location = f" at {path}" if path else ""
        raise AssertionError(
            f"Missing required keys{location}: {sorted(missing_keys)}"
        )
    
    # Check for extra keys in strict mode
    if strict:
        extra_keys = set(data.keys()) - set(expected_structure.keys())
        if extra_keys:
            location = f" at {path}" if path else ""
            raise AssertionError(
                f"Unexpected extra keys{location}: {sorted(extra_keys)}"
            )
    
    # Validate each field
    for key, expected_type in expected_structure.items():
        current_path = f"{path}.{key}" if path else key
        value = data[key]
        
        # Handle callable validators
        if callable(expected_type) and not isinstance(expected_type, type):
            try:
                result = expected_type(value)
                if result is False:
                    raise AssertionError(
                        f"Validator failed for {current_path}: {value}"
                    )
            except Exception as e:
                raise AssertionError(
                    f"Validator error at {current_path}: {str(e)}"
                )
        # Handle nested dictionaries
        elif isinstance(expected_type, dict):
            assert_json_structure(value, expected_type, strict, current_path)
        # Handle type checking
        elif isinstance(expected_type, type):
            if not isinstance(value, expected_type):
                raise AssertionError(
                    f"Type mismatch at {current_path}: "
                    f"expected {expected_type.__name__}, "
                    f"got {type(value).__name__} ({value})"
                )
        else:
            raise ValueError(
                f"Invalid expected_type at {current_path}: {expected_type}"
            )


def assert_status_code(
    response: Any,
    expected_status: int,
    message: Optional[str] = None
) -> None:
    """
    Enhanced status code assertion with descriptive error messages.
    
    Args:
        response: Flask test client response object or dict with 'status_code' key
        expected_status: Expected HTTP status code
        message: Optional custom error message
    
    Raises:
        AssertionError: If status code doesn't match
    
    Example:
        assert_status_code(response, 200, "User creation should succeed")
        assert_status_code(response, 404, "Non-existent user should return 404")
    """
    # Extract status code from response object
    if hasattr(response, 'status_code'):
        actual_status = response.status_code
    elif isinstance(response, dict) and 'status_code' in response:
        actual_status = response['status_code']
    else:
        raise ValueError(
            f"Response object must have 'status_code' attribute or key, "
            f"got {type(response).__name__}"
        )
    
    if actual_status != expected_status:
        # Build descriptive error message
        status_names = {
            200: "OK",
            201: "Created",
            204: "No Content",
            400: "Bad Request",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found",
            409: "Conflict",
            422: "Unprocessable Entity",
            500: "Internal Server Error"
        }
        
        expected_name = status_names.get(expected_status, "Unknown")
        actual_name = status_names.get(actual_status, "Unknown")
        
        error_msg = (
            f"Status code mismatch: "
            f"expected {expected_status} ({expected_name}), "
            f"got {actual_status} ({actual_name})"
        )
        
        if message:
            error_msg = f"{message}: {error_msg}"
        
        # Add response body if available for debugging
        if hasattr(response, 'data'):
            try:
                body = response.get_json() if hasattr(response, 'get_json') else response.data
                if body:
                    error_msg += f"\nResponse body: {body}"
            except Exception:
                pass
        
        raise AssertionError(error_msg)


def assert_response_contains(
    response_data: Dict[str, Any],
    expected_keys: Union[List[str], Dict[str, Any]],
    check_values: bool = False
) -> None:
    """
    Checks if response contains expected keys and optionally validates values.
    
    Args:
        response_data: Response data dictionary
        expected_keys: List of keys that must exist, or dict of key-value pairs
        check_values: If True and expected_keys is dict, validates values match
    
    Raises:
        AssertionError: If expected keys are missing or values don't match
    
    Example:
        # Check keys exist
        assert_response_contains(response.json, ['id', 'name', 'email'])
        
        # Check keys and values
        assert_response_contains(
            response.json,
            {'status': 'success', 'id': 123},
            check_values=True
        )
    """
    if not isinstance(response_data, dict):
        raise AssertionError(
            f"Response data must be a dictionary, got {type(response_data).__name__}"
        )
    
    if isinstance(expected_keys, list):
        missing_keys = [key for key in expected_keys if key not in response_data]
        if missing_keys:
            raise AssertionError(
                f"Response missing expected keys: {missing_keys}\n"
                f"Available keys: {list(response_data.keys())}"
            )
    
    elif isinstance(expected_keys, dict):
        missing_keys = [key for key in expected_keys.keys() if key not in response_data]
        if missing_keys:
            raise AssertionError(
                f"Response missing expected keys: {missing_keys}\n"
                f"Available keys: {list(response_data.keys())}"
            )
        
        if check_values:
            mismatches = []
            for key, expected_value in expected_keys.items():
                actual_value = response_data.get(key)
                if actual_value != expected_value:
                    mismatches.append(
                        f"  {key}: expected {expected_value!r}, got {actual_value!r}"
                    )
            
            if mismatches:
                raise AssertionError(
                    f"Response value mismatches:\n" + "\n".join(mismatches)
                )
    else:
        raise ValueError(
            f"expected_keys must be list or dict, got {type(expected_keys).__name__}"
        )


def assert_response_excludes(
    response_data: Dict[str, Any],
    excluded_keys: List[str],
    recursive: bool = False
) -> None:
    """
    Verifies response does not contain sensitive or unwanted data.
    
    Args:
        response_data: Response data dictionary
        excluded_keys: List of keys that must NOT exist
        recursive: If True, checks nested dictionaries as well
    
    Raises:
        AssertionError: If any excluded keys are found
    
    Example:
        # Ensure password not in response
        assert_response_excludes(response.json, ['password', 'password_hash'])
        
        # Recursively check nested objects
        assert_response_excludes(
            response.json,
            ['password', 'secret_key', 'api_token'],
            recursive=True
        )
    """
    if not isinstance(response_data, dict):
        raise AssertionError(
            f"Response data must be a dictionary, got {type(response_data).__name__}"
        )
    
    def find_excluded_keys(data: Any, path: str = "") -> List[str]:
        """Recursively find excluded keys in data structure."""
        found = []
        
        if isinstance(data, dict):
            for key, value in data.items():
                current_path = f"{path}.{key}" if path else key
                
                if key in excluded_keys:
                    found.append(current_path)
                
                if recursive:
                    found.extend(find_excluded_keys(value, current_path))
        
        elif isinstance(data, list) and recursive:
            for i, item in enumerate(data):
                current_path = f"{path}[{i}]"
                found.extend(find_excluded_keys(item, current_path))
        
        return found
    
    found_keys = find_excluded_keys(response_data)
    
    if found_keys:
        raise AssertionError(
            f"Response contains excluded keys: {found_keys}\n"
            f"These sensitive fields should not be exposed"
        )


def assert_valid_datetime(
    datetime_string: str,
    format_pattern: Optional[str] = None,
    allow_timezone: bool = True
) -> None:
    """
    Validates datetime string formats.
    
    Args:
        datetime_string: String to validate as datetime
        format_pattern: Optional strftime format pattern (e.g., '%Y-%m-%d %H:%M:%S')
                       If None, tries ISO format
        allow_timezone: Whether timezone info is allowed/required
    
    Raises:
        AssertionError: If string is not a valid datetime
    
    Example:
        assert_valid_datetime('2023-10-15T14:30:00')
        assert_valid_datetime('2023-10-15 14:30:00', format_pattern='%Y-%m-%d %H:%M:%S')
        assert_valid_datetime('2023-10-15T14:30:00Z', allow_timezone=True)
    """
    if not isinstance(datetime_string, str):
        raise AssertionError(
            f"Expected string, got {type(datetime_string).__name__}: {datetime_string}"
        )
    
    if not datetime_string.strip():
        raise AssertionError("Datetime string is empty")
    
    try:
        if format_pattern:
            # Use specific format
            parsed_dt = datetime.strptime(datetime_string, format_pattern)
        else:
            # Try ISO format first
            try:
                parsed_dt = datetime.fromisoformat(datetime_string.replace('Z', '+00:00'))
            except ValueError:
                # Try common formats
                common_formats = [
                    '%Y-%m-%dT%H:%M:%S',
                    '%Y-%m-%d %H:%M:%S',
                    '%Y-%m-%d',
                    '%Y/%m/%d %H:%M:%S',
                    '%d/%m/%Y %H:%M:%S',
                    '%m/%d/%Y %H:%M:%S'
                ]
                
                parsed_dt = None
                for fmt in common_formats:
                    try:
                        parsed_dt = datetime.strptime(datetime_string, fmt)
                        break
                    except ValueError:
                        continue
                
                if parsed_dt is None:
                    raise ValueError(
                        f"Could not parse datetime with any common format"
                    )
        
        # Validate that it's a reasonable date (not too far in past/future)
        year = parsed_dt.year
        if year < 1900 or year > 2100:
            raise AssertionError(
                f"Datetime year {year} is outside reasonable range (1900-2100)"
            )
        
    except ValueError as e:
        error_msg = f"Invalid datetime string: '{datetime_string}'"
        if format_pattern:
            error_msg += f" (expected format: {format_pattern})"
        error_msg += f"\nError: {str(e)}"
        raise AssertionError(error_msg)


def assert_valid_uuid(
    uuid_string: str,
    version: Optional[int] = None
) -> None:
    """
    Validates UUID format strings.
    
    Args:
        uuid_string: String to validate as UUID
        version: Optional UUID version to enforce (1, 3, 4, or 5)
    
    Raises:
        AssertionError: If string is not a valid UUID
    
    Example:
        assert_valid_uuid('550e8400-e29b-41d4-a716-446655440000')
        assert_valid_uuid('550e8400-e29b-41d4-a716-446655440000', version=4)
    """
    if not isinstance(uuid_string, str):
        raise AssertionError(
            f"Expected string, got {type(uuid_string).__name__}: {uuid_string}"
        )
    
    if not uuid_string.strip():
        raise AssertionError("UUID string is empty")
    
    # Basic UUID regex pattern
    uuid_pattern = re.compile(
        r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
        re.IGNORECASE
    )
    
    if not uuid_pattern.match(uuid_string):
        raise AssertionError(
            f"Invalid UUID format: '{uuid_string}'\n"
            f"Expected format: 8-4-4-4-12 hexadecimal digits with hyphens"
        )
    
    try:
        parsed_uuid = UUID(uuid_string)
        
        # Validate version if specified
        if version is not None:
            if parsed_uuid.version != version:
                raise AssertionError(
                    f"UUID version mismatch: expected version {version}, "
                    f"got version {parsed_uuid.version} for UUID: {uuid_string}"
                )
    
    except ValueError as e:
        raise AssertionError(
            f"Invalid UUID: '{uuid_string}'\nError: {str(e)}"
        )


def assert_error_response(
    response_data: Dict[str, Any],
    expected_status: Optional[int] = None,
    expected_message_pattern: Optional[str] = None,
    expected_code: Optional[str] = None
) -> None:
    """
    Validates error response format (status, message, code).
    
    Args:
        response_data: Error response data dictionary
        expected_status: Expected HTTP status code in response
        expected_message_pattern: Regex pattern to match error message
        expected_code: Expected error code (e.g., 'VALIDATION_ERROR')
    
    Raises:
        AssertionError: If error response doesn't match expected format
    
    Example:
        assert_error_response(
            response.json,
            expected_status=400,
            expected_message_pattern=r'Invalid email',
            expected_code='VALIDATION_ERROR'
        )
    """
    if not isinstance(response_data, dict):
        raise AssertionError(
            f"Error response must be a dictionary, got {type(response_data).__name__}"
        )
    
    # Check for common error response fields
    error_field_found = False
    error_content = None
    
    # Try different common error response structures
    if 'error' in response_data:
        error_content = response_data['error']
        error_field_found = True
    elif 'message' in response_data:
        error_content = response_data['message']
        error_field_found = True
    elif 'detail' in response_data:
        error_content = response_data['detail']
        error_field_found = True
    
    if not error_field_found:
        raise AssertionError(
            f"Response missing error field. Expected one of: 'error', 'message', 'detail'\n"
            f"Available keys: {list(response_data.keys())}"
        )
    
    # Validate status if provided
    if expected_status is not None:
        if 'status' in response_data:
            actual_status = response_data['status']
            if actual_status != expected_status:
                raise AssertionError(
                    f"Error status mismatch: expected {expected_status}, "
                    f"got {actual_status}"
                )
        elif 'status_code' in response_data:
            actual_status = response_data['status_code']
            if actual_status != expected_status:
                raise AssertionError(
                    f"Error status code mismatch: expected {expected_status}, "
                    f"got {actual_status}"
                )
    
    # Validate message pattern if provided
    if expected_message_pattern is not None:
        message_str = str(error_content)
        if not re.search(expected_message_pattern, message_str, re.IGNORECASE):
            raise AssertionError(
                f"Error message doesn't match pattern.\n"
                f"Pattern: {expected_message_pattern}\n"
                f"Message: {message_str}"
            )
    
    # Validate error code if provided
    if expected_code is not None:
        if 'code' in response_data:
            actual_code = response_data['code']
            if actual_code != expected_code:
                raise AssertionError(
                    f"Error code mismatch: expected '{expected_code}', "
                    f"got '{actual_code}'"
                )
        elif 'error_code' in response_data:
            actual_code = response_data['error_code']
            if actual_code != expected_code:
                raise AssertionError(
                    f"Error code mismatch: expected '{expected_code}', "
                    f"got '{actual_code}'"
                )
        else:
            raise AssertionError(
                f"Error response missing 'code' or 'error_code' field\n"
                f"Available keys: {list(response_data.keys())}"
            )


def assert_pagination(
    response_data: Dict[str, Any],
    expected_page: Optional[int] = None,
    expected_per_page: Optional[int] = None,
    expected_total: Optional[int] = None,
    min_items: Optional[int] = None,
    max_items: Optional[int] = None
) -> None:
    """
    Validates pagination metadata in responses.
    
    Args:
        response_data: Response data containing pagination info
        expected_page: Expected current page number
        expected_per_page: Expected items per page
        expected_total: Expected total item count
        min_items: Minimum number of items expected
        max_items: Maximum number of items expected
    
    Raises:
        AssertionError: If pagination metadata is invalid
    
    Example:
        assert_pagination(
            response.json,
            expected_page=1,
            expected_per_page=10,
            min_items=1,
            max_items=10
        )
    """
    if not isinstance(response_data, dict):
        raise AssertionError(
            f"Response data must be a dictionary, got {type(response_data).__name__}"
        )
    
    # Check for pagination metadata
    pagination_keys = ['pagination', 'meta', 'paging']
    pagination_data = None
    
    for key in pagination_keys:
        if key in response_data:
            pagination_data = response_data[key]
            break
    
    if pagination_data is None:
        # Check if pagination fields are at root level
        if 'page' in response_data or 'total' in response_data:
            pagination_data = response_data
        else:
            raise AssertionError(
                f"Response missing pagination metadata. "
                f"Expected one of: {pagination_keys} or pagination fields at root level"
            )
    
    # Validate page number
    if expected_page is not None:
        page_keys = ['page', 'current_page', 'page_number']
        page_value = None
        
        for key in page_keys:
            if key in pagination_data:
                page_value = pagination_data[key]
                break
        
        if page_value is None:
            raise AssertionError(
                f"Pagination missing page number field. Expected one of: {page_keys}"
            )
        
        if page_value != expected_page:
            raise AssertionError(
                f"Page number mismatch: expected {expected_page}, got {page_value}"
            )
    
    # Validate per_page
    if expected_per_page is not None:
        per_page_keys = ['per_page', 'page_size', 'limit']
        per_page_value = None
        
        for key in per_page_keys:
            if key in pagination_data:
                per_page_value = pagination_data[key]
                break
        
        if per_page_value is None:
            raise AssertionError(
                f"Pagination missing per_page field. Expected one of: {per_page_keys}"
            )
        
        if per_page_value != expected_per_page:
            raise AssertionError(
                f"Per page mismatch: expected {expected_per_page}, got {per_page_value}"
            )
    
    # Validate total
    if expected_total is not None:
        total_keys = ['total', 'total_count', 'total_items']
        total_value = None
        
        for key in total_keys:
            if key in pagination_data:
                total_value = pagination_data[key]
                break
        
        if total_value is None:
            raise AssertionError(
                f"Pagination missing total field. Expected one of: {total_keys}"
            )
        
        if total_value != expected_total:
            raise AssertionError(
                f"Total count mismatch: expected {expected_total}, got {total_value}"
            )
    
    # Validate item count bounds
    items_keys = ['items', 'data', 'results']
    items = None
    
    for key in items_keys:
        if key in response_data:
            items = response_data[key]
            break
    
    if items is not None and isinstance(items, list):
        item_count = len(items)
        
        if min_items is not None and item_count < min_items:
            raise AssertionError(
                f"Item count below minimum: expected at least {min_items}, got {item_count}"
            )
        
        if max_items is not None and item_count > max_items:
            raise AssertionError(
                f"Item count above maximum: expected at most {max_items}, got {item_count}"
            )


def assert_list_length(
    data: List[Any],
    expected_length: Optional[int] = None,
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
    context: str = "List"
) -> None:
    """
    Validates list length with descriptive messages.
    
    Args:
        data: List to validate
        expected_length: Exact expected length
        min_length: Minimum allowed length
        max_length: Maximum allowed length
        context: Description for error messages
    
    Raises:
        AssertionError: If list length doesn't meet criteria
    
    Example:
        assert_list_length(users, expected_length=5, context="Users list")
        assert_list_length(items, min_length=1, max_length=100, context="Items")
    """
    if not isinstance(data, list):
        raise AssertionError(
            f"{context} must be a list, got {type(data).__name__}"
        )
    
    actual_length = len(data)
    
    if expected_length is not None:
        if actual_length != expected_length:
            raise AssertionError(
                f"{context} length mismatch: expected {expected_length}, "
                f"got {actual_length}"
            )
    
    if min_length is not None:
        if actual_length < min_length:
            raise AssertionError(
                f"{context} too short: expected at least {min_length} items, "
                f"got {actual_length}"
            )
    
    if max_length is not None:
        if actual_length > max_length:
            raise AssertionError(
                f"{context} too long: expected at most {max_length} items, "
                f"got {actual_length}"
            )


def assert_nested_value(
    data: Dict[str, Any],
    path: str,
    expected_value: Any = None,
    value_type: Optional[type] = None,
    validator: Optional[Callable] = None
) -> Any:
    """
    Validates nested dictionary values with dot notation path.
    
    Args:
        data: Dictionary to traverse
        path: Dot-notation path (e.g., 'user.profile.address.city')
        expected_value: Expected value at path (if provided, validates equality)
        value_type: Expected type of value at path
        validator: Optional callable to validate the value
    
    Returns:
        The value at the specified path
    
    Raises:
        AssertionError: If path doesn't exist or validation fails
    
    Example:
        # Check nested value exists and get it
        city = assert_nested_value(data, 'user.profile.address.city')
        
        # Check nested value equals expected
        assert_nested_value(data, 'user.status', expected_value='active')
        
        # Check nested value type
        assert_nested_value(data, 'user.age', value_type=int)
        
        # Custom validation
        assert_nested_value(
            data,
            'user.email',
            validator=lambda x: '@' in x
        )
    """
    if not isinstance(data, dict):
        raise AssertionError(
            f"Data must be a dictionary, got {type(data).__name__}"
        )
    
    if not path:
        raise ValueError("Path cannot be empty")
    
    keys = path.split('.')
    current_value = data
    traversed_path = []
    
    # Traverse the nested structure
    try:
        for key in keys:
            traversed_path.append(key)
            
            if not isinstance(current_value, dict):
                raise AssertionError(
                    f"Cannot traverse non-dict at path '{'.'.join(traversed_path[:-1])}': "
                    f"got {type(current_value).__name__}"
                )
            
            if key not in current_value:
                raise AssertionError(
                    f"Key '{key}' not found at path '{'.'.join(traversed_path[:-1])}'\n"
                    f"Available keys: {list(current_value.keys())}"
                )
            
            current_value = current_value[key]
    
    except (KeyError, TypeError) as e:
        raise AssertionError(
            f"Failed to traverse path '{path}' at '{'.'.join(traversed_path)}': {str(e)}"
        )
    
    # Validate expected value
    if expected_value is not None:
        if current_value != expected_value:
            raise AssertionError(
                f"Value mismatch at path '{path}': "
                f"expected {expected_value!r}, got {current_value!r}"
            )
    
    # Validate type
    if value_type is not None:
        if not isinstance(current_value, value_type):
            raise AssertionError(
                f"Type mismatch at path '{path}': "
                f"expected {value_type.__name__}, got {type(current_value).__name__}"
            )
    
    # Run custom validator
    if validator is not None:
        if not callable(validator):
            raise ValueError("Validator must be callable")
        
        try:
            result = validator(current_value)
            if result is False:
                raise AssertionError(
                    f"Validator failed at path '{path}' for value: {current_value!r}"
                )
        except AssertionError:
            raise
        except Exception as e:
            raise AssertionError(
                f"Validator error at path '{path}': {str(e)}"
            )
    
    return current_value

