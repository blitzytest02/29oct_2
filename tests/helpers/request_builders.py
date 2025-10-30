"""
HTTP Request Builder Utilities for Flask Test Client

This module provides comprehensive helper functions and a fluent builder class
for constructing properly formatted HTTP requests for Flask's test_client().
These utilities simplify test code by handling common request patterns including
JSON serialization, header management, authentication, query parameters, and
multipart file uploads.

Usage:
    # Simple GET request with query params
    response = client.get(**build_get_request('/api/users', {'page': 1}))
    
    # POST request with JSON and authentication
    response = client.post(**build_authenticated_request(
        build_post_request('/api/users', {'name': 'John'}),
        'my-jwt-token'
    ))
    
    # Fluent builder for complex requests
    response = client.post(**RequestBuilder()
        .with_url('/api/users')
        .with_method('POST')
        .with_json({'name': 'John'})
        .with_headers({'X-Custom': 'value'})
        .with_query_params({'source': 'test'})
        .build()
    )
"""

from typing import Optional, Dict, Any, Union, List, Tuple
from urllib.parse import urlencode, parse_qs, parse_qsl, urlparse, urlunparse
from io import BytesIO
from werkzeug.datastructures import FileStorage
from copy import deepcopy


def build_get_request(
    url: str,
    query_params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    cookies: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Constructs a GET request with query parameters and headers.
    
    This function builds a properly formatted request dictionary for Flask's
    test_client().get() method, handling query parameter encoding and header
    management.
    
    Args:
        url: The request URL path (e.g., '/api/users')
        query_params: Optional dictionary of query parameters to append to URL
        headers: Optional dictionary of HTTP headers
        cookies: Optional dictionary of cookies to include in request
    
    Returns:
        Dictionary containing 'path' and optionally 'headers' and 'cookies'
        ready to be unpacked into client.get(**result)
    
    Example:
        >>> request = build_get_request('/api/users', {'page': 1, 'limit': 10})
        >>> response = client.get(**request)
    """
    # Start with the base URL
    request_url = url
    
    # Add query parameters if provided
    if query_params:
        request_url = build_request_with_query_params(url, query_params)
    
    # Build the request dictionary
    request_dict: Dict[str, Any] = {'path': request_url}
    
    # Add headers if provided
    if headers:
        request_dict['headers'] = deepcopy(headers)
    
    # Add cookies if provided
    if cookies:
        # Flask test client expects cookies as a list of tuples or dict
        request_dict['cookies'] = deepcopy(cookies)
    
    return request_dict


def build_post_request(
    url: str,
    json_data: Optional[Dict[str, Any]] = None,
    data: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    query_params: Optional[Dict[str, Any]] = None,
    cookies: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Constructs a POST request with JSON body and headers.
    
    Builds a request dictionary for Flask's test_client().post() method with
    automatic JSON serialization and Content-Type header management.
    
    Args:
        url: The request URL path
        json_data: Optional dictionary to be sent as JSON body
        data: Optional dictionary for form data (mutually exclusive with json_data)
        headers: Optional dictionary of HTTP headers
        query_params: Optional dictionary of query parameters
        cookies: Optional dictionary of cookies
    
    Returns:
        Dictionary ready to be unpacked into client.post(**result)
    
    Example:
        >>> request = build_post_request('/api/users', {'name': 'John', 'email': 'john@example.com'})
        >>> response = client.post(**request)
    """
    # Start with the base URL
    request_url = url
    
    # Add query parameters if provided
    if query_params:
        request_url = build_request_with_query_params(url, query_params)
    
    # Build the request dictionary
    request_dict: Dict[str, Any] = {'path': request_url}
    
    # Add JSON data if provided
    if json_data is not None:
        request_dict['json'] = deepcopy(json_data)
        # Flask test client automatically sets Content-Type for json parameter
    
    # Add form data if provided (mutually exclusive with json_data)
    if data is not None and json_data is None:
        request_dict['data'] = deepcopy(data)
    
    # Add headers if provided
    if headers:
        request_dict['headers'] = deepcopy(headers)
    
    # Add cookies if provided
    if cookies:
        request_dict['cookies'] = deepcopy(cookies)
    
    return request_dict


def build_put_request(
    url: str,
    json_data: Optional[Dict[str, Any]] = None,
    data: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    query_params: Optional[Dict[str, Any]] = None,
    cookies: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Constructs a PUT request with JSON body.
    
    Builds a request dictionary for Flask's test_client().put() method with
    automatic JSON serialization, typically used for full resource updates.
    
    Args:
        url: The request URL path
        json_data: Optional dictionary to be sent as JSON body
        data: Optional dictionary for form data
        headers: Optional dictionary of HTTP headers
        query_params: Optional dictionary of query parameters
        cookies: Optional dictionary of cookies
    
    Returns:
        Dictionary ready to be unpacked into client.put(**result)
    
    Example:
        >>> request = build_put_request('/api/users/1', {'name': 'Jane', 'email': 'jane@example.com'})
        >>> response = client.put(**request)
    """
    # Start with the base URL
    request_url = url
    
    # Add query parameters if provided
    if query_params:
        request_url = build_request_with_query_params(url, query_params)
    
    # Build the request dictionary
    request_dict: Dict[str, Any] = {'path': request_url}
    
    # Add JSON data if provided
    if json_data is not None:
        request_dict['json'] = deepcopy(json_data)
    
    # Add form data if provided
    if data is not None and json_data is None:
        request_dict['data'] = deepcopy(data)
    
    # Add headers if provided
    if headers:
        request_dict['headers'] = deepcopy(headers)
    
    # Add cookies if provided
    if cookies:
        request_dict['cookies'] = deepcopy(cookies)
    
    return request_dict


def build_delete_request(
    url: str,
    headers: Optional[Dict[str, str]] = None,
    query_params: Optional[Dict[str, Any]] = None,
    cookies: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Constructs a DELETE request.
    
    Builds a request dictionary for Flask's test_client().delete() method.
    DELETE requests typically don't have a body but may include headers
    and query parameters.
    
    Args:
        url: The request URL path
        headers: Optional dictionary of HTTP headers
        query_params: Optional dictionary of query parameters
        cookies: Optional dictionary of cookies
    
    Returns:
        Dictionary ready to be unpacked into client.delete(**result)
    
    Example:
        >>> request = build_delete_request('/api/users/1')
        >>> response = client.delete(**request)
    """
    # Start with the base URL
    request_url = url
    
    # Add query parameters if provided
    if query_params:
        request_url = build_request_with_query_params(url, query_params)
    
    # Build the request dictionary
    request_dict: Dict[str, Any] = {'path': request_url}
    
    # Add headers if provided
    if headers:
        request_dict['headers'] = deepcopy(headers)
    
    # Add cookies if provided
    if cookies:
        request_dict['cookies'] = deepcopy(cookies)
    
    return request_dict


def build_patch_request(
    url: str,
    json_data: Optional[Dict[str, Any]] = None,
    data: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    query_params: Optional[Dict[str, Any]] = None,
    cookies: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Constructs a PATCH request with partial updates.
    
    Builds a request dictionary for Flask's test_client().patch() method,
    typically used for partial resource updates where only modified fields
    are sent.
    
    Args:
        url: The request URL path
        json_data: Optional dictionary with partial update data
        data: Optional dictionary for form data
        headers: Optional dictionary of HTTP headers
        query_params: Optional dictionary of query parameters
        cookies: Optional dictionary of cookies
    
    Returns:
        Dictionary ready to be unpacked into client.patch(**result)
    
    Example:
        >>> request = build_patch_request('/api/users/1', {'email': 'newemail@example.com'})
        >>> response = client.patch(**request)
    """
    # Start with the base URL
    request_url = url
    
    # Add query parameters if provided
    if query_params:
        request_url = build_request_with_query_params(url, query_params)
    
    # Build the request dictionary
    request_dict: Dict[str, Any] = {'path': request_url}
    
    # Add JSON data if provided
    if json_data is not None:
        request_dict['json'] = deepcopy(json_data)
    
    # Add form data if provided
    if data is not None and json_data is None:
        request_dict['data'] = deepcopy(data)
    
    # Add headers if provided
    if headers:
        request_dict['headers'] = deepcopy(headers)
    
    # Add cookies if provided
    if cookies:
        request_dict['cookies'] = deepcopy(cookies)
    
    return request_dict


def build_authenticated_request(
    request_dict: Dict[str, Any],
    token: str,
    token_type: str = 'Bearer'
) -> Dict[str, Any]:
    """
    Adds authentication headers (Bearer token) to an existing request.
    
    Takes a request dictionary built by any of the build_*_request functions
    and adds an Authorization header with the provided token.
    
    Args:
        request_dict: Existing request dictionary from build_*_request functions
        token: The authentication token (JWT, API key, etc.)
        token_type: The authentication scheme (default: 'Bearer')
    
    Returns:
        Updated request dictionary with Authorization header
    
    Example:
        >>> request = build_post_request('/api/users', {'name': 'John'})
        >>> auth_request = build_authenticated_request(request, 'my-jwt-token')
        >>> response = client.post(**auth_request)
    """
    # Create a deep copy to avoid mutating the original
    authenticated_request = deepcopy(request_dict)
    
    # Initialize headers if not present
    if 'headers' not in authenticated_request:
        authenticated_request['headers'] = {}
    
    # Add the Authorization header
    authenticated_request['headers']['Authorization'] = f'{token_type} {token}'
    
    return authenticated_request


def build_multipart_request(
    url: str,
    files: Dict[str, Union[Tuple[str, BytesIO], Tuple[str, BytesIO, str]]],
    data: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    query_params: Optional[Dict[str, Any]] = None,
    cookies: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Constructs multipart/form-data request for file uploads.
    
    Builds a request dictionary for Flask's test_client() with file uploads.
    Creates FileStorage objects that Flask expects for handling uploaded files.
    
    Args:
        url: The request URL path
        files: Dictionary mapping field names to file tuples:
               - (filename, file_content) or
               - (filename, file_content, content_type)
               where file_content is BytesIO object
        data: Optional dictionary of additional form fields
        headers: Optional dictionary of HTTP headers
        query_params: Optional dictionary of query parameters
        cookies: Optional dictionary of cookies
    
    Returns:
        Dictionary ready to be unpacked into client.post(**result)
    
    Example:
        >>> file_content = BytesIO(b'file content here')
        >>> files = {'document': ('test.pdf', file_content, 'application/pdf')}
        >>> request = build_multipart_request('/api/upload', files, {'description': 'Test file'})
        >>> response = client.post(**request)
    """
    # Start with the base URL
    request_url = url
    
    # Add query parameters if provided
    if query_params:
        request_url = build_request_with_query_params(url, query_params)
    
    # Build the request dictionary
    request_dict: Dict[str, Any] = {'path': request_url}
    
    # Process files into FileStorage objects
    file_storage_dict: Dict[str, FileStorage] = {}
    for field_name, file_tuple in files.items():
        if len(file_tuple) == 2:
            # (filename, content)
            filename, content = file_tuple
            content_type = 'application/octet-stream'
        elif len(file_tuple) == 3:
            # (filename, content, content_type)
            filename, content, content_type = file_tuple
        else:
            raise ValueError(
                f"Invalid file tuple for field '{field_name}'. "
                f"Expected (filename, content) or (filename, content, content_type)"
            )
        
        # Create FileStorage object
        file_storage_dict[field_name] = FileStorage(
            stream=content,
            filename=filename,
            content_type=content_type
        )
    
    # Build the data dictionary combining files and form data
    request_data: Dict[str, Any] = {}
    
    # Add regular form data if provided
    if data:
        request_data.update(deepcopy(data))
    
    # Add file storage objects
    request_data.update(file_storage_dict)
    
    # Set the data in request
    request_dict['data'] = request_data
    
    # Set content type to multipart/form-data
    # Flask test client will handle the boundary parameter automatically
    if headers:
        request_dict['headers'] = deepcopy(headers)
    else:
        request_dict['headers'] = {}
    
    # Don't set Content-Type manually - let Flask test client handle it
    # to get the correct boundary parameter
    
    # Add cookies if provided
    if cookies:
        request_dict['cookies'] = deepcopy(cookies)
    
    return request_dict


def build_request_with_query_params(
    url: str,
    query_params: Dict[str, Any]
) -> str:
    """
    Adds query parameters to a URL.
    
    Properly encodes query parameters and appends them to the URL,
    handling both URLs with and without existing query strings.
    
    Args:
        url: The base URL (may already contain query parameters)
        query_params: Dictionary of query parameters to add/merge
    
    Returns:
        URL string with encoded query parameters
    
    Example:
        >>> url = build_request_with_query_params('/api/users', {'page': 1, 'limit': 10})
        >>> print(url)
        '/api/users?page=1&limit=10'
    """
    # Parse the existing URL
    parsed_url = urlparse(url)
    
    # Parse existing query parameters
    existing_params = dict(parse_qsl(parsed_url.query))
    
    # Merge with new query parameters (new params override existing)
    merged_params = {**existing_params, **query_params}
    
    # Encode the query parameters
    encoded_query = urlencode(merged_params, doseq=True)
    
    # Rebuild the URL with the new query string
    new_url = urlunparse((
        parsed_url.scheme,
        parsed_url.netloc,
        parsed_url.path,
        parsed_url.params,
        encoded_query,
        parsed_url.fragment
    ))
    
    return new_url


def build_request_with_headers(
    request_dict: Dict[str, Any],
    headers: Dict[str, str]
) -> Dict[str, Any]:
    """
    Adds custom headers to an existing request.
    
    Merges additional headers into a request dictionary, preserving
    existing headers and allowing overrides.
    
    Args:
        request_dict: Existing request dictionary from build_*_request functions
        headers: Dictionary of headers to add or override
    
    Returns:
        Updated request dictionary with merged headers
    
    Example:
        >>> request = build_get_request('/api/users')
        >>> request = build_request_with_headers(request, {'X-Custom-Header': 'value'})
        >>> response = client.get(**request)
    """
    # Create a deep copy to avoid mutating the original
    updated_request = deepcopy(request_dict)
    
    # Initialize headers if not present
    if 'headers' not in updated_request:
        updated_request['headers'] = {}
    
    # Merge headers (new headers override existing)
    updated_request['headers'].update(deepcopy(headers))
    
    return updated_request


def build_request_with_cookies(
    request_dict: Dict[str, Any],
    cookies: Dict[str, str]
) -> Dict[str, Any]:
    """
    Adds cookies to an existing request.
    
    Merges cookies into a request dictionary, preserving existing cookies
    and allowing overrides.
    
    Args:
        request_dict: Existing request dictionary from build_*_request functions
        cookies: Dictionary of cookies to add or override
    
    Returns:
        Updated request dictionary with merged cookies
    
    Example:
        >>> request = build_get_request('/api/users')
        >>> request = build_request_with_cookies(request, {'session_id': 'abc123'})
        >>> response = client.get(**request)
    """
    # Create a deep copy to avoid mutating the original
    updated_request = deepcopy(request_dict)
    
    # Initialize cookies if not present
    if 'cookies' not in updated_request:
        updated_request['cookies'] = {}
    
    # Merge cookies (new cookies override existing)
    updated_request['cookies'].update(deepcopy(cookies))
    
    return updated_request


class RequestBuilder:
    """
    Fluent interface for building complex HTTP requests.
    
    Provides a chainable API for constructing HTTP requests with all options,
    making test code more readable and maintainable for complex scenarios.
    
    Example:
        >>> response = client.post(**RequestBuilder()
        ...     .with_url('/api/users')
        ...     .with_method('POST')
        ...     .with_json({'name': 'John', 'email': 'john@example.com'})
        ...     .with_headers({'X-Request-ID': 'test-123'})
        ...     .with_query_params({'source': 'test'})
        ...     .with_authentication('my-jwt-token')
        ...     .build()
        ... )
    """
    
    def __init__(self) -> None:
        """Initialize a new RequestBuilder with empty state."""
        self._url: Optional[str] = None
        self._method: str = 'GET'
        self._json_data: Optional[Dict[str, Any]] = None
        self._form_data: Optional[Dict[str, Any]] = None
        self._headers: Dict[str, str] = {}
        self._query_params: Dict[str, Any] = {}
        self._cookies: Dict[str, str] = {}
        self._files: Optional[Dict[str, Union[Tuple[str, BytesIO], Tuple[str, BytesIO, str]]]] = None
    
    def with_method(self, method: str) -> 'RequestBuilder':
        """
        Set the HTTP method for the request.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE, PATCH, etc.)
        
        Returns:
            Self for method chaining
        """
        self._method = method.upper()
        return self
    
    def with_url(self, url: str) -> 'RequestBuilder':
        """
        Set the URL path for the request.
        
        Args:
            url: The request URL path
        
        Returns:
            Self for method chaining
        """
        self._url = url
        return self
    
    def with_json(self, json_data: Dict[str, Any]) -> 'RequestBuilder':
        """
        Set JSON data for the request body.
        
        Args:
            json_data: Dictionary to be sent as JSON
        
        Returns:
            Self for method chaining
        """
        self._json_data = deepcopy(json_data)
        self._form_data = None  # Clear form data if JSON is set
        return self
    
    def with_data(self, form_data: Dict[str, Any]) -> 'RequestBuilder':
        """
        Set form data for the request body.
        
        Args:
            form_data: Dictionary for form-encoded data
        
        Returns:
            Self for method chaining
        """
        self._form_data = deepcopy(form_data)
        self._json_data = None  # Clear JSON if form data is set
        return self
    
    def with_headers(self, headers: Dict[str, str]) -> 'RequestBuilder':
        """
        Add or merge headers for the request.
        
        Args:
            headers: Dictionary of HTTP headers
        
        Returns:
            Self for method chaining
        """
        self._headers.update(deepcopy(headers))
        return self
    
    def with_query_params(self, query_params: Dict[str, Any]) -> 'RequestBuilder':
        """
        Add or merge query parameters for the request.
        
        Args:
            query_params: Dictionary of query parameters
        
        Returns:
            Self for method chaining
        """
        self._query_params.update(deepcopy(query_params))
        return self
    
    def with_cookies(self, cookies: Dict[str, str]) -> 'RequestBuilder':
        """
        Add or merge cookies for the request.
        
        Args:
            cookies: Dictionary of cookies
        
        Returns:
            Self for method chaining
        """
        self._cookies.update(deepcopy(cookies))
        return self
    
    def with_authentication(
        self,
        token: str,
        token_type: str = 'Bearer'
    ) -> 'RequestBuilder':
        """
        Add authentication header to the request.
        
        Args:
            token: The authentication token
            token_type: The authentication scheme (default: 'Bearer')
        
        Returns:
            Self for method chaining
        """
        self._headers['Authorization'] = f'{token_type} {token}'
        return self
    
    def with_files(
        self,
        files: Dict[str, Union[Tuple[str, BytesIO], Tuple[str, BytesIO, str]]]
    ) -> 'RequestBuilder':
        """
        Add files for multipart upload.
        
        Args:
            files: Dictionary mapping field names to file tuples
        
        Returns:
            Self for method chaining
        """
        self._files = deepcopy(files)
        return self
    
    def build(self) -> Dict[str, Any]:
        """
        Build and return the complete request dictionary.
        
        Returns:
            Dictionary ready to be unpacked into Flask test client methods
        
        Raises:
            ValueError: If URL is not set or configuration is invalid
        """
        if self._url is None:
            raise ValueError("URL must be set before building request")
        
        # If files are present, use multipart builder
        if self._files:
            return build_multipart_request(
                url=self._url,
                files=self._files,
                data=self._form_data,
                headers=self._headers if self._headers else None,
                query_params=self._query_params if self._query_params else None,
                cookies=self._cookies if self._cookies else None
            )
        
        # Choose the appropriate builder based on method
        if self._method == 'GET':
            return build_get_request(
                url=self._url,
                query_params=self._query_params if self._query_params else None,
                headers=self._headers if self._headers else None,
                cookies=self._cookies if self._cookies else None
            )
        elif self._method == 'POST':
            return build_post_request(
                url=self._url,
                json_data=self._json_data,
                data=self._form_data,
                headers=self._headers if self._headers else None,
                query_params=self._query_params if self._query_params else None,
                cookies=self._cookies if self._cookies else None
            )
        elif self._method == 'PUT':
            return build_put_request(
                url=self._url,
                json_data=self._json_data,
                data=self._form_data,
                headers=self._headers if self._headers else None,
                query_params=self._query_params if self._query_params else None,
                cookies=self._cookies if self._cookies else None
            )
        elif self._method == 'DELETE':
            return build_delete_request(
                url=self._url,
                headers=self._headers if self._headers else None,
                query_params=self._query_params if self._query_params else None,
                cookies=self._cookies if self._cookies else None
            )
        elif self._method == 'PATCH':
            return build_patch_request(
                url=self._url,
                json_data=self._json_data,
                data=self._form_data,
                headers=self._headers if self._headers else None,
                query_params=self._query_params if self._query_params else None,
                cookies=self._cookies if self._cookies else None
            )
        else:
            # For other methods, build a generic request
            request_url = self._url
            if self._query_params:
                request_url = build_request_with_query_params(self._url, self._query_params)
            
            request_dict: Dict[str, Any] = {'path': request_url}
            
            if self._json_data is not None:
                request_dict['json'] = self._json_data
            elif self._form_data is not None:
                request_dict['data'] = self._form_data
            
            if self._headers:
                request_dict['headers'] = self._headers
            
            if self._cookies:
                request_dict['cookies'] = self._cookies
            
            return request_dict

