"""
Test Client Wrapper Classes for Enhanced Flask Testing

This module provides wrapper classes around Flask's test client to simplify
HTTP testing and reduce boilerplate code across test modules. Each wrapper
class provides specialized functionality for different testing scenarios.

Classes:
    AuthenticatedClient: Pre-configured client with automatic authentication
    APITestClient: Enhanced client for API testing with JSON support
    MultipartClient: Specialized client for file upload testing
    WebSocketTestClient: Client for WebSocket connection testing
"""

import json
from typing import Optional, Dict, Any, Union, List, Callable
from io import BytesIO

from werkzeug.datastructures import FileStorage
from werkzeug.test import TestResponse
from flask.testing import FlaskClient
from flask import Response


class AuthenticatedClient:
    """
    Wrapper around Flask test_client with pre-configured authentication.
    
    This class automatically injects authentication tokens into all requests,
    simplifying testing of protected endpoints. It supports all standard HTTP
    methods and provides automatic JSON encoding/decoding.
    
    Attributes:
        client: The underlying Flask test client
        token: The authentication token (Bearer token format)
        token_type: The type of token (default: 'Bearer')
    """
    
    def __init__(self, client: FlaskClient, token: Optional[str] = None, token_type: str = 'Bearer'):
        """
        Initialize authenticated client wrapper.
        
        Args:
            client: Flask test client instance
            token: Optional authentication token to pre-configure
            token_type: Type of authentication token (default: 'Bearer')
        """
        self.client = client
        self.token = token
        self.token_type = token_type
    
    def set_token(self, token: str, token_type: str = 'Bearer') -> None:
        """
        Set or update the authentication token.
        
        Args:
            token: Authentication token string
            token_type: Type of authentication token (default: 'Bearer')
        """
        self.token = token
        self.token_type = token_type
    
    def clear_token(self) -> None:
        """
        Clear the authentication token.
        
        This removes authentication from subsequent requests until
        a new token is set.
        """
        self.token = None
    
    def _prepare_headers(self, headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """
        Prepare request headers with authentication token.
        
        Args:
            headers: Optional additional headers to include
            
        Returns:
            Dictionary of headers including authentication
        """
        request_headers = headers.copy() if headers else {}
        
        if self.token:
            auth_header = f'{self.token_type} {self.token}'
            request_headers['Authorization'] = auth_header
        
        return request_headers
    
    def get(self, 
            path: str, 
            headers: Optional[Dict[str, str]] = None,
            query_string: Optional[Dict[str, Any]] = None,
            **kwargs) -> TestResponse:
        """
        Perform authenticated GET request.
        
        Args:
            path: URL path to request
            headers: Optional additional headers
            query_string: Optional query parameters
            **kwargs: Additional arguments passed to test client
            
        Returns:
            TestResponse object from Flask test client
        """
        request_headers = self._prepare_headers(headers)
        return self.client.get(
            path,
            headers=request_headers,
            query_string=query_string,
            **kwargs
        )
    
    def post(self,
             path: str,
             data: Optional[Union[Dict[str, Any], str]] = None,
             json_data: Optional[Dict[str, Any]] = None,
             headers: Optional[Dict[str, str]] = None,
             **kwargs) -> TestResponse:
        """
        Perform authenticated POST request with automatic JSON encoding.
        
        Args:
            path: URL path to request
            data: Optional form data or string body
            json_data: Optional JSON data (automatically encoded)
            headers: Optional additional headers
            **kwargs: Additional arguments passed to test client
            
        Returns:
            TestResponse object from Flask test client
        """
        request_headers = self._prepare_headers(headers)
        
        if json_data is not None:
            request_headers['Content-Type'] = 'application/json'
            return self.client.post(
                path,
                data=json.dumps(json_data),
                headers=request_headers,
                **kwargs
            )
        
        return self.client.post(
            path,
            data=data,
            headers=request_headers,
            **kwargs
        )
    
    def put(self,
            path: str,
            data: Optional[Union[Dict[str, Any], str]] = None,
            json_data: Optional[Dict[str, Any]] = None,
            headers: Optional[Dict[str, str]] = None,
            **kwargs) -> TestResponse:
        """
        Perform authenticated PUT request with automatic JSON encoding.
        
        Args:
            path: URL path to request
            data: Optional form data or string body
            json_data: Optional JSON data (automatically encoded)
            headers: Optional additional headers
            **kwargs: Additional arguments passed to test client
            
        Returns:
            TestResponse object from Flask test client
        """
        request_headers = self._prepare_headers(headers)
        
        if json_data is not None:
            request_headers['Content-Type'] = 'application/json'
            return self.client.put(
                path,
                data=json.dumps(json_data),
                headers=request_headers,
                **kwargs
            )
        
        return self.client.put(
            path,
            data=data,
            headers=request_headers,
            **kwargs
        )
    
    def delete(self,
               path: str,
               headers: Optional[Dict[str, str]] = None,
               **kwargs) -> TestResponse:
        """
        Perform authenticated DELETE request.
        
        Args:
            path: URL path to request
            headers: Optional additional headers
            **kwargs: Additional arguments passed to test client
            
        Returns:
            TestResponse object from Flask test client
        """
        request_headers = self._prepare_headers(headers)
        return self.client.delete(
            path,
            headers=request_headers,
            **kwargs
        )
    
    def patch(self,
              path: str,
              data: Optional[Union[Dict[str, Any], str]] = None,
              json_data: Optional[Dict[str, Any]] = None,
              headers: Optional[Dict[str, str]] = None,
              **kwargs) -> TestResponse:
        """
        Perform authenticated PATCH request with automatic JSON encoding.
        
        Args:
            path: URL path to request
            data: Optional form data or string body
            json_data: Optional JSON data (automatically encoded)
            headers: Optional additional headers
            **kwargs: Additional arguments passed to test client
            
        Returns:
            TestResponse object from Flask test client
        """
        request_headers = self._prepare_headers(headers)
        
        if json_data is not None:
            request_headers['Content-Type'] = 'application/json'
            return self.client.patch(
                path,
                data=json.dumps(json_data),
                headers=request_headers,
                **kwargs
            )
        
        return self.client.patch(
            path,
            data=data,
            headers=request_headers,
            **kwargs
        )


class APITestClient:
    """
    Enhanced test client for API testing with automatic JSON handling.
    
    This class provides convenient methods for testing RESTful APIs with
    automatic JSON content-type headers, response status assertions, and
    JSON response parsing utilities.
    
    Attributes:
        client: The underlying Flask test client
    """
    
    def __init__(self, client: FlaskClient):
        """
        Initialize API test client wrapper.
        
        Args:
            client: Flask test client instance
        """
        self.client = client
    
    def _prepare_json_headers(self, headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """
        Prepare headers with JSON content-type.
        
        Args:
            headers: Optional additional headers
            
        Returns:
            Dictionary of headers including JSON content-type
        """
        request_headers = headers.copy() if headers else {}
        request_headers.setdefault('Content-Type', 'application/json')
        request_headers.setdefault('Accept', 'application/json')
        return request_headers
    
    def get(self,
            path: str,
            headers: Optional[Dict[str, str]] = None,
            query_string: Optional[Dict[str, Any]] = None,
            **kwargs) -> TestResponse:
        """
        Perform GET request with JSON headers.
        
        Args:
            path: URL path to request
            headers: Optional additional headers
            query_string: Optional query parameters
            **kwargs: Additional arguments passed to test client
            
        Returns:
            TestResponse object from Flask test client
        """
        request_headers = self._prepare_json_headers(headers)
        return self.client.get(
            path,
            headers=request_headers,
            query_string=query_string,
            **kwargs
        )
    
    def post(self,
             path: str,
             json_data: Optional[Dict[str, Any]] = None,
             headers: Optional[Dict[str, str]] = None,
             **kwargs) -> TestResponse:
        """
        Perform POST request with JSON data.
        
        Args:
            path: URL path to request
            json_data: Optional JSON data (automatically encoded)
            headers: Optional additional headers
            **kwargs: Additional arguments passed to test client
            
        Returns:
            TestResponse object from Flask test client
        """
        request_headers = self._prepare_json_headers(headers)
        data = json.dumps(json_data) if json_data is not None else None
        return self.client.post(
            path,
            data=data,
            headers=request_headers,
            **kwargs
        )
    
    def put(self,
            path: str,
            json_data: Optional[Dict[str, Any]] = None,
            headers: Optional[Dict[str, str]] = None,
            **kwargs) -> TestResponse:
        """
        Perform PUT request with JSON data.
        
        Args:
            path: URL path to request
            json_data: Optional JSON data (automatically encoded)
            headers: Optional additional headers
            **kwargs: Additional arguments passed to test client
            
        Returns:
            TestResponse object from Flask test client
        """
        request_headers = self._prepare_json_headers(headers)
        data = json.dumps(json_data) if json_data is not None else None
        return self.client.put(
            path,
            data=data,
            headers=request_headers,
            **kwargs
        )
    
    def delete(self,
               path: str,
               headers: Optional[Dict[str, str]] = None,
               **kwargs) -> TestResponse:
        """
        Perform DELETE request with JSON headers.
        
        Args:
            path: URL path to request
            headers: Optional additional headers
            **kwargs: Additional arguments passed to test client
            
        Returns:
            TestResponse object from Flask test client
        """
        request_headers = self._prepare_json_headers(headers)
        return self.client.delete(
            path,
            headers=request_headers,
            **kwargs
        )
    
    def patch(self,
              path: str,
              json_data: Optional[Dict[str, Any]] = None,
              headers: Optional[Dict[str, str]] = None,
              **kwargs) -> TestResponse:
        """
        Perform PATCH request with JSON data.
        
        Args:
            path: URL path to request
            json_data: Optional JSON data (automatically encoded)
            headers: Optional additional headers
            **kwargs: Additional arguments passed to test client
            
        Returns:
            TestResponse object from Flask test client
        """
        request_headers = self._prepare_json_headers(headers)
        data = json.dumps(json_data) if json_data is not None else None
        return self.client.patch(
            path,
            data=data,
            headers=request_headers,
            **kwargs
        )
    
    def options(self,
                path: str,
                headers: Optional[Dict[str, str]] = None,
                **kwargs) -> TestResponse:
        """
        Perform OPTIONS request.
        
        Args:
            path: URL path to request
            headers: Optional additional headers
            **kwargs: Additional arguments passed to test client
            
        Returns:
            TestResponse object from Flask test client
        """
        request_headers = headers.copy() if headers else {}
        return self.client.options(
            path,
            headers=request_headers,
            **kwargs
        )
    
    def head(self,
             path: str,
             headers: Optional[Dict[str, str]] = None,
             **kwargs) -> TestResponse:
        """
        Perform HEAD request.
        
        Args:
            path: URL path to request
            headers: Optional additional headers
            **kwargs: Additional arguments passed to test client
            
        Returns:
            TestResponse object from Flask test client
        """
        request_headers = headers.copy() if headers else {}
        return self.client.head(
            path,
            headers=request_headers,
            **kwargs
        )
    
    def assert_status(self, response: TestResponse, expected_status: int) -> None:
        """
        Assert response has expected status code.
        
        Args:
            response: TestResponse object to check
            expected_status: Expected HTTP status code
            
        Raises:
            AssertionError: If status code doesn't match
        """
        assert response.status_code == expected_status, (
            f"Expected status {expected_status}, got {response.status_code}. "
            f"Response: {response.get_data(as_text=True)}"
        )
    
    def assert_json(self, response: TestResponse, expected_data: Dict[str, Any]) -> None:
        """
        Assert response JSON matches expected data.
        
        Args:
            response: TestResponse object to check
            expected_data: Expected JSON data structure
            
        Raises:
            AssertionError: If JSON doesn't match
        """
        response_json = self.get_json(response)
        assert response_json == expected_data, (
            f"Expected JSON: {expected_data}, got: {response_json}"
        )
    
    def get_json(self, response: TestResponse) -> Optional[Dict[str, Any]]:
        """
        Parse and return JSON from response.
        
        Args:
            response: TestResponse object to parse
            
        Returns:
            Parsed JSON data or None if no JSON content
            
        Raises:
            ValueError: If response contains invalid JSON
        """
        if not response.data:
            return None
        
        try:
            return json.loads(response.get_data(as_text=True))
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in response: {e}")


class MultipartClient:
    """
    Specialized test client for file upload testing with multipart/form-data support.
    
    This class provides convenient methods for testing file upload endpoints,
    supporting both file-only and mixed content (files + JSON) uploads.
    
    Attributes:
        client: The underlying Flask test client
    """
    
    def __init__(self, client: FlaskClient):
        """
        Initialize multipart test client wrapper.
        
        Args:
            client: Flask test client instance
        """
        self.client = client
    
    def create_file_storage(self,
                            content: Union[str, bytes],
                            filename: str,
                            content_type: str = 'application/octet-stream') -> FileStorage:
        """
        Create a FileStorage object for file upload testing.
        
        Args:
            content: File content as string or bytes
            filename: Name of the file
            content_type: MIME type of the file
            
        Returns:
            FileStorage object ready for upload
        """
        if isinstance(content, str):
            content = content.encode('utf-8')
        
        file_stream = BytesIO(content)
        return FileStorage(
            stream=file_stream,
            filename=filename,
            content_type=content_type
        )
    
    def add_file_attachment(self,
                           data: Dict[str, Any],
                           field_name: str,
                           file_content: Union[str, bytes],
                           filename: str,
                           content_type: str = 'application/octet-stream') -> Dict[str, Any]:
        """
        Add file attachment to form data dictionary.
        
        Args:
            data: Existing form data dictionary
            field_name: Form field name for the file
            file_content: File content as string or bytes
            filename: Name of the file
            content_type: MIME type of the file
            
        Returns:
            Updated data dictionary with file attachment
        """
        file_storage = self.create_file_storage(file_content, filename, content_type)
        data[field_name] = file_storage
        return data
    
    def post_with_file(self,
                       path: str,
                       file_field: str,
                       file_content: Union[str, bytes],
                       filename: str,
                       content_type: str = 'application/octet-stream',
                       additional_data: Optional[Dict[str, Any]] = None,
                       headers: Optional[Dict[str, str]] = None,
                       **kwargs) -> TestResponse:
        """
        Perform POST request with file upload.
        
        Args:
            path: URL path to request
            file_field: Form field name for the file
            file_content: File content as string or bytes
            filename: Name of the file
            content_type: MIME type of the file
            additional_data: Optional additional form fields
            headers: Optional additional headers
            **kwargs: Additional arguments passed to test client
            
        Returns:
            TestResponse object from Flask test client
        """
        data = additional_data.copy() if additional_data else {}
        file_storage = self.create_file_storage(file_content, filename, content_type)
        data[file_field] = file_storage
        
        request_headers = headers.copy() if headers else {}
        
        return self.client.post(
            path,
            data=data,
            headers=request_headers,
            content_type='multipart/form-data',
            **kwargs
        )
    
    def put_with_file(self,
                      path: str,
                      file_field: str,
                      file_content: Union[str, bytes],
                      filename: str,
                      content_type: str = 'application/octet-stream',
                      additional_data: Optional[Dict[str, Any]] = None,
                      headers: Optional[Dict[str, str]] = None,
                      **kwargs) -> TestResponse:
        """
        Perform PUT request with file upload.
        
        Args:
            path: URL path to request
            file_field: Form field name for the file
            file_content: File content as string or bytes
            filename: Name of the file
            content_type: MIME type of the file
            additional_data: Optional additional form fields
            headers: Optional additional headers
            **kwargs: Additional arguments passed to test client
            
        Returns:
            TestResponse object from Flask test client
        """
        data = additional_data.copy() if additional_data else {}
        file_storage = self.create_file_storage(file_content, filename, content_type)
        data[file_field] = file_storage
        
        request_headers = headers.copy() if headers else {}
        
        return self.client.put(
            path,
            data=data,
            headers=request_headers,
            content_type='multipart/form-data',
            **kwargs
        )
    
    def post_multipart(self,
                       path: str,
                       files: Dict[str, tuple],
                       form_data: Optional[Dict[str, Any]] = None,
                       headers: Optional[Dict[str, str]] = None,
                       **kwargs) -> TestResponse:
        """
        Perform POST request with multiple files and form data.
        
        Args:
            path: URL path to request
            files: Dictionary mapping field names to (filename, content, content_type) tuples
            form_data: Optional additional form fields
            headers: Optional additional headers
            **kwargs: Additional arguments passed to test client
            
        Returns:
            TestResponse object from Flask test client
        """
        data = form_data.copy() if form_data else {}
        
        for field_name, file_info in files.items():
            if len(file_info) == 2:
                filename, content = file_info
                content_type = 'application/octet-stream'
            elif len(file_info) == 3:
                filename, content, content_type = file_info
            else:
                raise ValueError(f"Invalid file_info format for field {field_name}")
            
            file_storage = self.create_file_storage(content, filename, content_type)
            data[field_name] = file_storage
        
        request_headers = headers.copy() if headers else {}
        
        return self.client.post(
            path,
            data=data,
            headers=request_headers,
            content_type='multipart/form-data',
            **kwargs
        )
    
    def put_multipart(self,
                      path: str,
                      files: Dict[str, tuple],
                      form_data: Optional[Dict[str, Any]] = None,
                      headers: Optional[Dict[str, str]] = None,
                      **kwargs) -> TestResponse:
        """
        Perform PUT request with multiple files and form data.
        
        Args:
            path: URL path to request
            files: Dictionary mapping field names to (filename, content, content_type) tuples
            form_data: Optional additional form fields
            headers: Optional additional headers
            **kwargs: Additional arguments passed to test client
            
        Returns:
            TestResponse object from Flask test client
        """
        data = form_data.copy() if form_data else {}
        
        for field_name, file_info in files.items():
            if len(file_info) == 2:
                filename, content = file_info
                content_type = 'application/octet-stream'
            elif len(file_info) == 3:
                filename, content, content_type = file_info
            else:
                raise ValueError(f"Invalid file_info format for field {field_name}")
            
            file_storage = self.create_file_storage(content, filename, content_type)
            data[field_name] = file_storage
        
        request_headers = headers.copy() if headers else {}
        
        return self.client.put(
            path,
            data=data,
            headers=request_headers,
            content_type='multipart/form-data',
            **kwargs
        )


class WebSocketTestClient:
    """
    Test client for WebSocket connection testing.
    
    This class provides a simplified interface for testing WebSocket-like
    functionality. It maintains connection state and message queues for
    simulating bidirectional communication in tests.
    
    Note: This is a mock implementation for testing purposes. For full
    WebSocket testing with real protocols, consider using libraries like
    flask-socketio with their test client implementations.
    
    Attributes:
        client: The underlying Flask test client
        connected: Connection state flag
        message_queue: Queue of received messages
        connection_path: Current connection path
    """
    
    def __init__(self, client: FlaskClient):
        """
        Initialize WebSocket test client wrapper.
        
        Args:
            client: Flask test client instance
        """
        self.client = client
        self.connected = False
        self.message_queue: List[Any] = []
        self.connection_path: Optional[str] = None
    
    def connect(self,
                path: str,
                headers: Optional[Dict[str, str]] = None,
                query_string: Optional[Dict[str, Any]] = None,
                **kwargs) -> bool:
        """
        Establish WebSocket connection to specified path.
        
        Args:
            path: WebSocket endpoint path
            headers: Optional connection headers
            query_string: Optional query parameters
            **kwargs: Additional connection parameters
            
        Returns:
            True if connection successful, False otherwise
        """
        if self.connected:
            raise RuntimeError("Already connected. Disconnect first before reconnecting.")
        
        try:
            # Simulate WebSocket handshake with GET request
            # Note: Flask's test client doesn't support real WebSocket protocol upgrades
            # (Upgrade/Connection headers cause 400 Bad Request). We use a custom header
            # for testing purposes to simulate WebSocket connections.
            request_headers = headers.copy() if headers else {}
            request_headers['X-WebSocket-Handshake'] = 'mock'
            
            response = self.client.get(
                path,
                headers=request_headers,
                query_string=query_string,
                **kwargs
            )
            
            # Check for successful WebSocket handshake (101 Switching Protocols)
            # or successful connection (200 OK for testing purposes)
            if response.status_code in (101, 200):
                self.connected = True
                self.connection_path = path
                self.message_queue = []
                return True
            
            return False
            
        except Exception:
            self.connected = False
            return False
    
    def disconnect(self) -> None:
        """
        Close WebSocket connection.
        
        Clears connection state and message queue.
        """
        if not self.connected:
            return
        
        self.connected = False
        self.connection_path = None
        self.message_queue = []
    
    def send_message(self,
                     message: str,
                     message_type: str = 'text') -> bool:
        """
        Send text or binary message through WebSocket.
        
        Args:
            message: Message content to send
            message_type: Type of message ('text' or 'binary')
            
        Returns:
            True if message sent successfully, False otherwise
            
        Raises:
            RuntimeError: If not connected
        """
        if not self.connected:
            raise RuntimeError("Not connected. Call connect() first.")
        
        try:
            # Simulate sending message via POST to connection path
            headers = {
                'Content-Type': 'text/plain' if message_type == 'text' else 'application/octet-stream'
            }
            
            response = self.client.post(
                self.connection_path,
                data=message,
                headers=headers
            )
            
            # Store any response in message queue
            if response.data:
                self.message_queue.append(response.get_data(as_text=True))
            
            return response.status_code in (200, 201, 204)
            
        except Exception:
            return False
    
    def receive_message(self, timeout: Optional[float] = None) -> Optional[str]:
        """
        Receive message from WebSocket.
        
        Args:
            timeout: Optional timeout in seconds (not implemented in mock)
            
        Returns:
            Received message or None if no messages available
            
        Raises:
            RuntimeError: If not connected
        """
        if not self.connected:
            raise RuntimeError("Not connected. Call connect() first.")
        
        if self.message_queue:
            return self.message_queue.pop(0)
        
        return None
    
    def send_json(self, data: Dict[str, Any]) -> bool:
        """
        Send JSON message through WebSocket.
        
        Args:
            data: Dictionary to send as JSON
            
        Returns:
            True if message sent successfully, False otherwise
            
        Raises:
            RuntimeError: If not connected
        """
        if not self.connected:
            raise RuntimeError("Not connected. Call connect() first.")
        
        try:
            json_message = json.dumps(data)
            
            headers = {
                'Content-Type': 'application/json'
            }
            
            response = self.client.post(
                self.connection_path,
                data=json_message,
                headers=headers
            )
            
            # Store any response in message queue
            if response.data:
                try:
                    response_json = json.loads(response.get_data(as_text=True))
                    self.message_queue.append(response_json)
                except json.JSONDecodeError:
                    self.message_queue.append(response.get_data(as_text=True))
            
            return response.status_code in (200, 201, 204)
            
        except Exception:
            return False
    
    def receive_json(self, timeout: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """
        Receive and parse JSON message from WebSocket.
        
        Args:
            timeout: Optional timeout in seconds (not implemented in mock)
            
        Returns:
            Parsed JSON message or None if no messages available
            
        Raises:
            RuntimeError: If not connected
            ValueError: If received message is not valid JSON
        """
        if not self.connected:
            raise RuntimeError("Not connected. Call connect() first.")
        
        message = self.receive_message(timeout)
        
        if message is None:
            return None
        
        # If message is already a dict (from send_json response), return it
        if isinstance(message, dict):
            return message
        
        # Otherwise parse as JSON string
        try:
            return json.loads(message)
        except json.JSONDecodeError as e:
            raise ValueError(f"Received message is not valid JSON: {e}")
    
    def is_connected(self) -> bool:
        """
        Check if WebSocket connection is active.
        
        Returns:
            True if connected, False otherwise
        """
        return self.connected
