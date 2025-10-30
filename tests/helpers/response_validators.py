"""
API Response Validation Helpers

This module provides comprehensive utilities to verify HTTP response correctness
including status code validation, JSON schema validation, response header checks,
pagination metadata verification, error response format validation, and content-type
verification with descriptive error messages for test failures.

All validation functions raise AssertionError with detailed messages on validation
failure to provide clear test feedback.
"""

import json
import re
from typing import Optional, Dict, Any, List, Union, Callable

from werkzeug.wrappers import Response
import jsonschema
from jsonschema import ValidationError as JSONSchemaValidationError


def validate_response_status(
    response: Response,
    expected_status: int,
    message: Optional[str] = None
) -> None:
    """
    Validates HTTP status code with descriptive errors.
    
    Args:
        response: Flask test client response object
        expected_status: Expected HTTP status code
        message: Optional custom error message
        
    Raises:
        AssertionError: If status code doesn't match expected value
        
    Example:
        validate_response_status(response, 200)
        validate_response_status(response, 404, "User should not be found")
    """
    actual_status = response.status_code
    
    if actual_status != expected_status:
        error_msg = (
            f"Expected status code {expected_status}, but got {actual_status}. "
            f"Response data: {response.get_data(as_text=True)[:200]}"
        )
        if message:
            error_msg = f"{message}. {error_msg}"
        raise AssertionError(error_msg)


def validate_json_response(response: Response) -> Dict[str, Any]:
    """
    Validates response is valid JSON and returns parsed data.
    
    Args:
        response: Flask test client response object
        
    Returns:
        Parsed JSON data as dictionary
        
    Raises:
        AssertionError: If response is not valid JSON
        
    Example:
        data = validate_json_response(response)
        assert data['id'] == 1
    """
    try:
        data = response.get_json()
        if data is None:
            # Try to parse manually for better error messages
            response_text = response.get_data(as_text=True)
            if not response_text:
                raise AssertionError(
                    f"Response is empty. Status: {response.status_code}"
                )
            data = json.loads(response_text)
        return data
    except json.JSONDecodeError as e:
        response_text = response.get_data(as_text=True)
        raise AssertionError(
            f"Response is not valid JSON. Error: {str(e)}. "
            f"Response data: {response_text[:200]}"
        )
    except Exception as e:
        raise AssertionError(
            f"Failed to parse JSON response: {str(e)}. "
            f"Status: {response.status_code}"
        )


def validate_response_schema(
    response: Response,
    schema: Dict[str, Any],
    message: Optional[str] = None
) -> Dict[str, Any]:
    """
    Validates response against JSON schema.
    
    Args:
        response: Flask test client response object
        schema: JSON schema dictionary to validate against
        message: Optional custom error message
        
    Returns:
        Parsed and validated JSON data
        
    Raises:
        AssertionError: If response doesn't conform to schema
        
    Example:
        schema = {
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
                "email": {"type": "string", "format": "email"}
            },
            "required": ["id", "email"]
        }
        data = validate_response_schema(response, schema)
    """
    data = validate_json_response(response)
    
    try:
        jsonschema.validate(instance=data, schema=schema)
        return data
    except JSONSchemaValidationError as e:
        error_msg = (
            f"Response does not conform to schema. "
            f"Validation error: {e.message}. "
            f"Failed path: {'.'.join(str(p) for p in e.path) if e.path else 'root'}. "
            f"Response data: {json.dumps(data, indent=2)[:300]}"
        )
        if message:
            error_msg = f"{message}. {error_msg}"
        raise AssertionError(error_msg)


def validate_success_response(
    response: Response,
    expected_status: Optional[int] = None
) -> Dict[str, Any]:
    """
    Validates 2xx success response format.
    
    Args:
        response: Flask test client response object
        expected_status: Optional specific 2xx status code to check (defaults to any 2xx)
        
    Returns:
        Parsed JSON data if response contains JSON
        
    Raises:
        AssertionError: If response is not a 2xx success status
        
    Example:
        data = validate_success_response(response)
        data = validate_success_response(response, 200)
    """
    actual_status = response.status_code
    
    if expected_status is not None:
        if actual_status != expected_status:
            raise AssertionError(
                f"Expected success status {expected_status}, but got {actual_status}. "
                f"Response: {response.get_data(as_text=True)[:200]}"
            )
    else:
        if not (200 <= actual_status < 300):
            raise AssertionError(
                f"Expected 2xx success status, but got {actual_status}. "
                f"Response: {response.get_data(as_text=True)[:200]}"
            )
    
    # Return parsed JSON if content type is JSON
    content_type = response.headers.get('Content-Type', '')
    if 'application/json' in content_type:
        return validate_json_response(response)
    
    return {}


def validate_error_response(
    response: Response,
    expected_status: int,
    expected_message: Optional[str] = None,
    expected_code: Optional[str] = None
) -> Dict[str, Any]:
    """
    Validates error response structure (status, message, code).
    
    Args:
        response: Flask test client response object
        expected_status: Expected HTTP error status code
        expected_message: Optional expected error message (can be substring)
        expected_code: Optional expected error code
        
    Returns:
        Parsed error response data
        
    Raises:
        AssertionError: If error response doesn't match expected format
        
    Example:
        validate_error_response(response, 400, "Invalid email format")
        validate_error_response(response, 401, expected_code="UNAUTHORIZED")
    """
    validate_response_status(response, expected_status)
    data = validate_json_response(response)
    
    # Check for common error response fields
    if 'message' not in data and 'error' not in data:
        raise AssertionError(
            f"Error response missing 'message' or 'error' field. "
            f"Response data: {json.dumps(data, indent=2)}"
        )
    
    actual_message = data.get('message') or data.get('error', '')
    
    if expected_message is not None:
        if expected_message not in actual_message:
            raise AssertionError(
                f"Expected error message to contain '{expected_message}', "
                f"but got '{actual_message}'"
            )
    
    if expected_code is not None:
        actual_code = data.get('code') or data.get('error_code')
        if actual_code != expected_code:
            raise AssertionError(
                f"Expected error code '{expected_code}', but got '{actual_code}'"
            )
    
    return data


def validate_created_response(
    response: Response,
    expected_location: Optional[str] = None,
    location_pattern: Optional[str] = None
) -> Dict[str, Any]:
    r"""
    Validates 201 Created response with Location header.
    
    Args:
        response: Flask test client response object
        expected_location: Optional exact Location header value to check
        location_pattern: Optional regex pattern for Location header
        
    Returns:
        Parsed JSON data from response body
        
    Raises:
        AssertionError: If response is not 201 or Location header is invalid
        
    Example:
        data = validate_created_response(response)
        data = validate_created_response(response, location_pattern=r'/api/users/\d+')
    """
    validate_response_status(response, 201, "Expected 201 Created status")
    
    location = response.headers.get('Location')
    
    if expected_location is not None:
        if location != expected_location:
            raise AssertionError(
                f"Expected Location header '{expected_location}', "
                f"but got '{location}'"
            )
    elif location_pattern is not None:
        if not location:
            raise AssertionError("Location header is missing in 201 Created response")
        if not re.match(location_pattern, location):
            raise AssertionError(
                f"Location header '{location}' does not match pattern '{location_pattern}'"
            )
    
    # Return JSON data if present
    content_type = response.headers.get('Content-Type', '')
    if 'application/json' in content_type and response.get_data():
        return validate_json_response(response)
    
    return {}


def validate_no_content_response(response: Response) -> None:
    """
    Validates 204 No Content response.
    
    Args:
        response: Flask test client response object
        
    Raises:
        AssertionError: If response is not 204 or contains content
        
    Example:
        validate_no_content_response(response)
    """
    validate_response_status(response, 204, "Expected 204 No Content status")
    
    response_data = response.get_data()
    if response_data:
        raise AssertionError(
            f"204 No Content response should not contain body data, "
            f"but got: {response.get_data(as_text=True)[:200]}"
        )


def validate_pagination_response(
    response: Response,
    expected_page: Optional[int] = None,
    expected_per_page: Optional[int] = None,
    min_total: Optional[int] = None,
    max_total: Optional[int] = None
) -> Dict[str, Any]:
    """
    Validates pagination metadata (page, per_page, total, items).
    
    Args:
        response: Flask test client response object
        expected_page: Optional expected current page number
        expected_per_page: Optional expected items per page
        min_total: Optional minimum total items
        max_total: Optional maximum total items
        
    Returns:
        Parsed response data with pagination metadata
        
    Raises:
        AssertionError: If pagination metadata is missing or invalid
        
    Example:
        data = validate_pagination_response(response, expected_page=1, expected_per_page=10)
    """
    validate_success_response(response)
    data = validate_json_response(response)
    
    # Check for pagination fields (support multiple common formats)
    page = data.get('page') or data.get('current_page')
    per_page = data.get('per_page') or data.get('page_size') or data.get('limit')
    total = data.get('total') or data.get('total_items') or data.get('count')
    items = data.get('items') or data.get('data') or data.get('results')
    
    if page is None:
        raise AssertionError(
            "Pagination response missing 'page' or 'current_page' field. "
            f"Response data: {json.dumps(data, indent=2)[:300]}"
        )
    
    if per_page is None:
        raise AssertionError(
            "Pagination response missing 'per_page', 'page_size', or 'limit' field. "
            f"Response data: {json.dumps(data, indent=2)[:300]}"
        )
    
    if total is None:
        raise AssertionError(
            "Pagination response missing 'total', 'total_items', or 'count' field. "
            f"Response data: {json.dumps(data, indent=2)[:300]}"
        )
    
    if items is None:
        raise AssertionError(
            "Pagination response missing 'items', 'data', or 'results' field. "
            f"Response data: {json.dumps(data, indent=2)[:300]}"
        )
    
    if not isinstance(items, list):
        raise AssertionError(
            f"Pagination items field must be a list, got {type(items).__name__}"
        )
    
    # Validate expected values
    if expected_page is not None and page != expected_page:
        raise AssertionError(
            f"Expected page {expected_page}, but got {page}"
        )
    
    if expected_per_page is not None and per_page != expected_per_page:
        raise AssertionError(
            f"Expected per_page {expected_per_page}, but got {per_page}"
        )
    
    if min_total is not None and total < min_total:
        raise AssertionError(
            f"Expected at least {min_total} total items, but got {total}"
        )
    
    if max_total is not None and total > max_total:
        raise AssertionError(
            f"Expected at most {max_total} total items, but got {total}"
        )
    
    # Validate items count doesn't exceed per_page
    if len(items) > per_page:
        raise AssertionError(
            f"Items count {len(items)} exceeds per_page limit {per_page}"
        )
    
    return data


def validate_list_response(
    response: Response,
    min_items: Optional[int] = None,
    max_items: Optional[int] = None,
    expected_count: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Validates list response structure.
    
    Args:
        response: Flask test client response object
        min_items: Optional minimum number of items expected
        max_items: Optional maximum number of items expected
        expected_count: Optional exact number of items expected
        
    Returns:
        List of items from response
        
    Raises:
        AssertionError: If response is not a valid list or count doesn't match
        
    Example:
        items = validate_list_response(response, min_items=1)
        items = validate_list_response(response, expected_count=5)
    """
    validate_success_response(response)
    data = validate_json_response(response)
    
    # Support different list response formats
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        items = data.get('items') or data.get('data') or data.get('results')
        if items is None:
            raise AssertionError(
                "Response is a dict but missing 'items', 'data', or 'results' field. "
                f"Response data: {json.dumps(data, indent=2)[:300]}"
            )
    else:
        raise AssertionError(
            f"Expected list response, but got {type(data).__name__}"
        )
    
    if not isinstance(items, list):
        raise AssertionError(
            f"Items must be a list, got {type(items).__name__}"
        )
    
    actual_count = len(items)
    
    if expected_count is not None and actual_count != expected_count:
        raise AssertionError(
            f"Expected {expected_count} items, but got {actual_count}"
        )
    
    if min_items is not None and actual_count < min_items:
        raise AssertionError(
            f"Expected at least {min_items} items, but got {actual_count}"
        )
    
    if max_items is not None and actual_count > max_items:
        raise AssertionError(
            f"Expected at most {max_items} items, but got {actual_count}"
        )
    
    return items


def validate_response_headers(
    response: Response,
    required_headers: Dict[str, Optional[str]] = None,
    forbidden_headers: Optional[List[str]] = None
) -> None:
    """
    Validates required headers present and optionally checks values.
    
    Args:
        response: Flask test client response object
        required_headers: Dict of header names to expected values (None for any value)
        forbidden_headers: Optional list of headers that should not be present
        
    Raises:
        AssertionError: If required headers are missing or forbidden headers are present
        
    Example:
        validate_response_headers(response, {
            'Content-Type': 'application/json',
            'X-Request-ID': None  # Just check it exists
        })
        validate_response_headers(response, forbidden_headers=['X-Debug-Info'])
    """
    if required_headers:
        for header_name, expected_value in required_headers.items():
            actual_value = response.headers.get(header_name)
            
            if actual_value is None:
                raise AssertionError(
                    f"Required header '{header_name}' is missing. "
                    f"Available headers: {list(response.headers.keys())}"
                )
            
            if expected_value is not None and actual_value != expected_value:
                raise AssertionError(
                    f"Header '{header_name}' expected value '{expected_value}', "
                    f"but got '{actual_value}'"
                )
    
    if forbidden_headers:
        for header_name in forbidden_headers:
            if header_name in response.headers:
                raise AssertionError(
                    f"Forbidden header '{header_name}' is present in response with value "
                    f"'{response.headers[header_name]}'"
                )


def validate_content_type(
    response: Response,
    expected_type: str = 'application/json',
    allow_charset: bool = True
) -> None:
    """
    Validates Content-Type header.
    
    Args:
        response: Flask test client response object
        expected_type: Expected content type (default: 'application/json')
        allow_charset: Whether to allow charset suffix (e.g., '; charset=utf-8')
        
    Raises:
        AssertionError: If Content-Type doesn't match expected value
        
    Example:
        validate_content_type(response)
        validate_content_type(response, 'text/html')
        validate_content_type(response, 'application/json', allow_charset=False)
    """
    content_type = response.headers.get('Content-Type', '')
    
    if not content_type:
        raise AssertionError(
            f"Content-Type header is missing. Expected '{expected_type}'"
        )
    
    if allow_charset:
        # Check if expected type is in content type (handles charset suffix)
        if expected_type not in content_type:
            raise AssertionError(
                f"Expected Content-Type '{expected_type}', but got '{content_type}'"
            )
    else:
        # Exact match required
        if content_type != expected_type:
            raise AssertionError(
                f"Expected Content-Type '{expected_type}', but got '{content_type}'"
            )


def validate_authentication_required(
    response: Response,
    expected_message: Optional[str] = None
) -> Dict[str, Any]:
    """
    Validates 401 response when unauthenticated.
    
    Args:
        response: Flask test client response object
        expected_message: Optional expected error message substring
        
    Returns:
        Parsed error response data
        
    Raises:
        AssertionError: If response is not 401 or doesn't have proper auth error format
        
    Example:
        validate_authentication_required(response)
        validate_authentication_required(response, "Authentication required")
    """
    validate_response_status(response, 401, "Expected 401 Unauthorized status")
    
    # Check for WWW-Authenticate header (standard for 401 responses)
    www_authenticate = response.headers.get('WWW-Authenticate')
    if not www_authenticate:
        # Not strictly required, but common practice
        pass
    
    data = validate_json_response(response)
    
    if expected_message:
        actual_message = data.get('message') or data.get('error', '')
        if expected_message not in actual_message:
            raise AssertionError(
                f"Expected authentication error message to contain '{expected_message}', "
                f"but got '{actual_message}'"
            )
    
    return data


def validate_forbidden_response(
    response: Response,
    expected_message: Optional[str] = None
) -> Dict[str, Any]:
    """
    Validates 403 response when unauthorized (lacks permissions).
    
    Args:
        response: Flask test client response object
        expected_message: Optional expected error message substring
        
    Returns:
        Parsed error response data
        
    Raises:
        AssertionError: If response is not 403 or doesn't have proper forbidden format
        
    Example:
        validate_forbidden_response(response)
        validate_forbidden_response(response, "Insufficient permissions")
    """
    validate_response_status(response, 403, "Expected 403 Forbidden status")
    data = validate_json_response(response)
    
    if expected_message:
        actual_message = data.get('message') or data.get('error', '')
        if expected_message not in actual_message:
            raise AssertionError(
                f"Expected forbidden error message to contain '{expected_message}', "
                f"but got '{actual_message}'"
            )
    
    return data


def validate_not_found_response(
    response: Response,
    expected_message: Optional[str] = None,
    resource_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Validates 404 response format.
    
    Args:
        response: Flask test client response object
        expected_message: Optional expected error message substring
        resource_type: Optional resource type that was not found (e.g., 'User', 'Post')
        
    Returns:
        Parsed error response data
        
    Raises:
        AssertionError: If response is not 404 or doesn't have proper not found format
        
    Example:
        validate_not_found_response(response)
        validate_not_found_response(response, resource_type='User')
        validate_not_found_response(response, expected_message="User not found")
    """
    validate_response_status(response, 404, "Expected 404 Not Found status")
    data = validate_json_response(response)
    
    actual_message = data.get('message') or data.get('error', '')
    
    if not actual_message:
        raise AssertionError(
            "404 response missing error message. "
            f"Response data: {json.dumps(data, indent=2)}"
        )
    
    if expected_message:
        if expected_message not in actual_message:
            raise AssertionError(
                f"Expected not found error message to contain '{expected_message}', "
                f"but got '{actual_message}'"
            )
    
    if resource_type:
        if resource_type.lower() not in actual_message.lower():
            raise AssertionError(
                f"Expected not found error to mention resource type '{resource_type}', "
                f"but got '{actual_message}'"
            )
    
    return data
