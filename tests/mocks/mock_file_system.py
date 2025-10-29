"""
Mock File System Module for Testing

This module provides comprehensive mock implementations for file system operations,
enabling testing of file upload, download, and storage functionality without actual
disk I/O operations. It includes mock file handlers, multipart form data processing,
temporary file management, and file validation utilities.

Mock Components:
- MockFileStorage: Mimics Flask's FileStorage for file uploads
- MockFileSystem: Provides virtual file system operations
- MockTemporaryFile: Handles temporary file operations
- File validation utilities for testing edge cases
- Pytest fixtures for easy test integration

Usage:
    # Using fixtures in tests
    def test_file_upload(mock_file_upload):
        response = client.post('/upload', data={'file': mock_file_upload})
        assert response.status_code == 200
    
    # Creating custom mock files
    mock_file = create_mock_uploaded_file(
        filename='test.pdf',
        content=b'PDF content',
        mimetype='application/pdf'
    )
"""

import pytest
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Callable, BinaryIO
import os
import datetime
import mimetypes
import tempfile
import re
import uuid
from unittest.mock import MagicMock
from copy import deepcopy
from werkzeug.datastructures import FileStorage


class MockFileStorage:
    """
    Mock implementation of Flask's FileStorage class for testing file uploads.
    
    This class mimics the interface of werkzeug.datastructures.FileStorage,
    providing file-like behavior without actual file I/O operations. It supports
    all standard file operations including save, read, seek, and metadata access.
    
    Attributes:
        filename (str): Name of the uploaded file
        mimetype (str): MIME type of the file content
        content_type (str): Alias for mimetype
        content_length (int): Size of file content in bytes
        stream (BytesIO): In-memory binary stream containing file data
        headers (dict): HTTP headers associated with the file upload
    
    Example:
        mock_file = MockFileStorage(
            filename='document.pdf',
            content=b'%PDF-1.4...',
            mimetype='application/pdf'
        )
        mock_file.save('/path/to/destination.pdf')
    """
    
    def __init__(
        self,
        filename: str = 'test.txt',
        content: bytes = b'',
        mimetype: str = 'text/plain',
        headers: Optional[Dict[str, str]] = None
    ):
        """
        Initialize MockFileStorage with file data and metadata.
        
        Args:
            filename: Name of the file including extension
            content: Binary content of the file
            mimetype: MIME type (e.g., 'image/png', 'application/pdf')
            headers: Optional HTTP headers dict
        """
        self.filename = filename
        self.mimetype = mimetype
        self.content_type = mimetype
        self._content = content
        self.stream = BytesIO(content)
        self.content_length = len(content)
        self.headers = headers or {}
        self._position = 0
    
    def save(self, dst: Union[str, Path], buffer_size: int = 16384) -> None:
        """
        Save the file content to a destination path.
        
        Args:
            dst: Destination file path (string or Path object)
            buffer_size: Size of buffer for writing (default: 16384 bytes)
        
        Raises:
            IOError: If the destination cannot be written
        """
        dst_path = Path(dst) if not isinstance(dst, Path) else dst
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.stream.seek(0)
        with open(dst_path, 'wb') as f:
            while True:
                chunk = self.stream.read(buffer_size)
                if not chunk:
                    break
                f.write(chunk)
        self.stream.seek(0)
    
    def read(self, size: int = -1) -> bytes:
        """
        Read bytes from the file stream.
        
        Args:
            size: Number of bytes to read (-1 for all remaining bytes)
        
        Returns:
            bytes: File content read from current position
        """
        return self.stream.read(size)
    
    def seek(self, offset: int, whence: int = 0) -> int:
        """
        Change the stream position to the given offset.
        
        Args:
            offset: Position offset
            whence: Reference point (0=start, 1=current, 2=end)
        
        Returns:
            int: New absolute position
        """
        return self.stream.seek(offset, whence)
    
    def tell(self) -> int:
        """
        Return the current stream position.
        
        Returns:
            int: Current position in bytes from start
        """
        return self.stream.tell()
    
    def close(self) -> None:
        """
        Close the file stream and release resources.
        """
        if self.stream:
            self.stream.close()
    
    def __repr__(self) -> str:
        """String representation of MockFileStorage."""
        return f"<MockFileStorage: {self.filename} ({self.mimetype})>"
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with automatic cleanup."""
        self.close()


class MockFileSystem:
    """
    Virtual file system implementation for testing file operations.
    
    Provides an in-memory file system that supports create, read, delete,
    and list operations without actual disk I/O. Maintains file metadata
    including size, creation time, and MIME type.
    
    Attributes:
        files (Dict): Internal storage mapping file paths to file data
    
    Example:
        fs = MockFileSystem()
        fs.create_file('/uploads/document.pdf', b'PDF content')
        content = fs.read_file('/uploads/document.pdf')
        assert fs.exists('/uploads/document.pdf')
    """
    
    def __init__(self):
        """Initialize an empty virtual file system."""
        self.files: Dict[str, Dict[str, Any]] = {}
    
    def create_file(
        self,
        path: str,
        content: bytes,
        mimetype: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new file in the virtual file system.
        
        Args:
            path: File path within the virtual file system
            content: Binary content of the file
            mimetype: Optional MIME type (auto-detected if not provided)
            metadata: Optional additional metadata dictionary
        
        Returns:
            str: Unique file identifier (UUID)
        
        Raises:
            ValueError: If path is invalid or empty
        """
        if not path:
            raise ValueError("File path cannot be empty")
        
        if mimetype is None:
            mimetype, _ = mimetypes.guess_type(path)
            if mimetype is None:
                mimetype = 'application/octet-stream'
        
        file_id = str(uuid.uuid4())
        now = datetime.datetime.now()
        
        self.files[path] = {
            'id': file_id,
            'content': content,
            'size': len(content),
            'mimetype': mimetype,
            'created_at': now,
            'modified_at': now,
            'accessed_at': now,
            'metadata': metadata or {}
        }
        
        return file_id
    
    def read_file(self, path: str) -> bytes:
        """
        Read file content from the virtual file system.
        
        Args:
            path: File path to read
        
        Returns:
            bytes: File content
        
        Raises:
            FileNotFoundError: If file does not exist
        """
        if path not in self.files:
            raise FileNotFoundError(f"File not found: {path}")
        
        file_data = self.files[path]
        file_data['accessed_at'] = datetime.datetime.now()
        return deepcopy(file_data['content'])
    
    def delete_file(self, path: str) -> bool:
        """
        Delete a file from the virtual file system.
        
        Args:
            path: File path to delete
        
        Returns:
            bool: True if file was deleted, False if it didn't exist
        """
        if path in self.files:
            del self.files[path]
            return True
        return False
    
    def exists(self, path: str) -> bool:
        """
        Check if a file exists in the virtual file system.
        
        Args:
            path: File path to check
        
        Returns:
            bool: True if file exists, False otherwise
        """
        return path in self.files
    
    def list_files(self, prefix: str = '') -> List[str]:
        """
        List all files in the virtual file system, optionally filtered by prefix.
        
        Args:
            prefix: Optional path prefix to filter results
        
        Returns:
            List[str]: List of file paths matching the prefix
        """
        if prefix:
            return [path for path in self.files.keys() if path.startswith(prefix)]
        return list(self.files.keys())
    
    def get_file_metadata(self, path: str) -> Dict[str, Any]:
        """
        Get metadata for a file including size, timestamps, and MIME type.
        
        Args:
            path: File path
        
        Returns:
            Dict[str, Any]: Dictionary containing file metadata
        
        Raises:
            FileNotFoundError: If file does not exist
        """
        if path not in self.files:
            raise FileNotFoundError(f"File not found: {path}")
        
        file_data = self.files[path]
        return {
            'id': file_data['id'],
            'path': path,
            'size': file_data['size'],
            'mimetype': file_data['mimetype'],
            'created_at': file_data['created_at'].isoformat(),
            'modified_at': file_data['modified_at'].isoformat(),
            'accessed_at': file_data['accessed_at'].isoformat(),
            'metadata': deepcopy(file_data['metadata'])
        }
    
    def get_file_size(self, path: str) -> int:
        """
        Get the size of a file in bytes.
        
        Args:
            path: File path
        
        Returns:
            int: File size in bytes
        
        Raises:
            FileNotFoundError: If file does not exist
        """
        if path not in self.files:
            raise FileNotFoundError(f"File not found: {path}")
        return self.files[path]['size']
    
    def clear(self) -> None:
        """
        Remove all files from the virtual file system.
        """
        self.files.clear()
    
    def __repr__(self) -> str:
        """String representation of MockFileSystem."""
        return f"<MockFileSystem: {len(self.files)} files>"


class MockTemporaryFile:
    """
    Mock implementation of temporary file operations for testing.
    
    Provides a file-like object that behaves like a temporary file with
    automatic cleanup support. Compatible with context managers and
    standard file operations.
    
    Attributes:
        name (str): Path to the temporary file
    
    Example:
        with MockTemporaryFile() as temp_file:
            temp_file.write(b'temporary data')
            temp_file.seek(0)
            content = temp_file.read()
    """
    
    def __init__(
        self,
        mode: str = 'w+b',
        suffix: str = '',
        prefix: str = 'tmp',
        dir: Optional[str] = None,
        delete: bool = True
    ):
        """
        Initialize a mock temporary file.
        
        Args:
            mode: File mode (default: 'w+b' for binary read/write)
            suffix: File suffix/extension
            prefix: File prefix
            dir: Directory for temporary file (uses system temp if None)
            delete: Whether to delete file on close (default: True)
        """
        self._mode = mode
        self._suffix = suffix
        self._prefix = prefix
        self._dir = dir or tempfile.gettempdir()
        self._delete = delete
        self._stream = BytesIO()
        self._closed = False
        
        # Generate unique filename
        unique_id = uuid.uuid4().hex[:8]
        self.name = os.path.join(
            self._dir,
            f"{prefix}{unique_id}{suffix}"
        )
    
    def read(self, size: int = -1) -> bytes:
        """
        Read bytes from the temporary file.
        
        Args:
            size: Number of bytes to read (-1 for all)
        
        Returns:
            bytes: Content read from file
        """
        if self._closed:
            raise ValueError("I/O operation on closed file")
        return self._stream.read(size)
    
    def write(self, data: bytes) -> int:
        """
        Write bytes to the temporary file.
        
        Args:
            data: Bytes to write
        
        Returns:
            int: Number of bytes written
        """
        if self._closed:
            raise ValueError("I/O operation on closed file")
        return self._stream.write(data)
    
    def seek(self, offset: int, whence: int = 0) -> int:
        """
        Change the stream position.
        
        Args:
            offset: Position offset
            whence: Reference point (0=start, 1=current, 2=end)
        
        Returns:
            int: New absolute position
        """
        if self._closed:
            raise ValueError("I/O operation on closed file")
        return self._stream.seek(offset, whence)
    
    def tell(self) -> int:
        """
        Return the current stream position.
        
        Returns:
            int: Current position in bytes
        """
        if self._closed:
            raise ValueError("I/O operation on closed file")
        return self._stream.tell()
    
    def close(self) -> None:
        """
        Close the temporary file and clean up resources.
        """
        if not self._closed:
            self._stream.close()
            self._closed = True
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with automatic cleanup."""
        self.close()
    
    def __repr__(self) -> str:
        """String representation of MockTemporaryFile."""
        status = "closed" if self._closed else "open"
        return f"<MockTemporaryFile: {self.name} ({status})>"


def create_mock_uploaded_file(
    filename: str = 'test.txt',
    content: bytes = b'test content',
    mimetype: Optional[str] = None,
    headers: Optional[Dict[str, str]] = None
) -> MockFileStorage:
    """
    Create a mock uploaded file for testing file upload functionality.
    
    This function generates a MockFileStorage object that mimics a file
    uploaded through a Flask multipart/form-data request. MIME type is
    automatically detected from the filename if not provided.
    
    Args:
        filename: Name of the uploaded file with extension
        content: Binary content of the file
        mimetype: MIME type (auto-detected if None)
        headers: Optional HTTP headers dictionary
    
    Returns:
        MockFileStorage: Mock file upload object compatible with Flask
    
    Example:
        mock_pdf = create_mock_uploaded_file(
            filename='report.pdf',
            content=b'%PDF-1.4...',
            mimetype='application/pdf'
        )
        
        # Test edge cases
        empty_file = create_mock_uploaded_file(filename='empty.txt', content=b'')
        large_file = create_mock_uploaded_file(
            filename='large.bin',
            content=b'x' * (10 * 1024 * 1024)  # 10MB file
        )
    """
    if mimetype is None:
        mimetype, _ = mimetypes.guess_type(filename)
        if mimetype is None:
            mimetype = 'application/octet-stream'
    
    return MockFileStorage(
        filename=filename,
        content=content,
        mimetype=mimetype,
        headers=headers
    )


def create_mock_multipart_data(
    files: Optional[Dict[str, MockFileStorage]] = None,
    fields: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Create mock multipart/form-data for testing file upload endpoints.
    
    Generates a dictionary suitable for use with Flask test client's
    `data` parameter when testing endpoints that accept both file uploads
    and regular form fields.
    
    Args:
        files: Dictionary mapping field names to MockFileStorage objects
        fields: Dictionary mapping field names to string values
    
    Returns:
        Dict[str, Any]: Combined dictionary with files and fields
    
    Example:
        data = create_mock_multipart_data(
            files={
                'document': create_mock_uploaded_file('doc.pdf', b'PDF data'),
                'image': create_mock_uploaded_file('photo.jpg', b'JPEG data')
            },
            fields={
                'title': 'My Document',
                'description': 'Test upload',
                'category': 'reports'
            }
        )
        
        response = client.post('/upload', data=data, content_type='multipart/form-data')
    """
    result = {}
    
    if fields:
        result.update(fields)
    
    if files:
        result.update(files)
    
    return result


def validate_file_type(
    filename: str,
    allowed_types: List[str],
    use_mimetype: bool = False
) -> bool:
    """
    Validate that a file has an allowed type/extension.
    
    Can validate either by file extension or by MIME type detection.
    Useful for testing file upload validation logic.
    
    Args:
        filename: Name of the file to validate
        allowed_types: List of allowed extensions (e.g., ['.pdf', '.doc']) 
                      or MIME types (e.g., ['application/pdf'])
        use_mimetype: If True, validate by MIME type; if False, by extension
    
    Returns:
        bool: True if file type is allowed, False otherwise
    
    Example:
        # Extension validation
        assert validate_file_type('document.pdf', ['.pdf', '.doc'])
        assert not validate_file_type('script.exe', ['.pdf', '.doc'])
        
        # MIME type validation
        assert validate_file_type(
            'document.pdf',
            ['application/pdf', 'application/msword'],
            use_mimetype=True
        )
    """
    if use_mimetype:
        detected_mimetype, _ = mimetypes.guess_type(filename)
        if detected_mimetype is None:
            return False
        return detected_mimetype in allowed_types
    else:
        file_extension = os.path.splitext(filename)[1].lower()
        normalized_allowed = [ext.lower() for ext in allowed_types]
        return file_extension in normalized_allowed


def validate_file_size(
    content: bytes,
    max_size_bytes: int,
    min_size_bytes: int = 0
) -> bool:
    """
    Validate that file content is within acceptable size limits.
    
    Checks if file size falls within the specified minimum and maximum
    byte limits. Useful for testing file size validation.
    
    Args:
        content: Binary file content to validate
        max_size_bytes: Maximum allowed file size in bytes
        min_size_bytes: Minimum allowed file size in bytes (default: 0)
    
    Returns:
        bool: True if file size is valid, False otherwise
    
    Example:
        # Test normal file
        assert validate_file_size(b'x' * 1000, max_size_bytes=5000)
        
        # Test oversized file
        assert not validate_file_size(b'x' * 10000, max_size_bytes=5000)
        
        # Test empty file
        assert not validate_file_size(b'', max_size_bytes=5000, min_size_bytes=1)
        
        # Test size range
        MB = 1024 * 1024
        content = b'x' * (2 * MB)
        assert validate_file_size(content, max_size_bytes=10*MB, min_size_bytes=1*MB)
    """
    file_size = len(content)
    return min_size_bytes <= file_size <= max_size_bytes


def validate_filename(
    filename: str,
    allow_path_chars: bool = False,
    max_length: int = 255
) -> bool:
    """
    Validate filename for security and safety.
    
    Checks for malicious patterns including path traversal attempts,
    special characters, and excessive length. Essential for testing
    file upload security.
    
    Args:
        filename: Filename to validate
        allow_path_chars: If True, allow forward slashes (default: False)
        max_length: Maximum allowed filename length (default: 255)
    
    Returns:
        bool: True if filename is safe, False if it contains malicious patterns
    
    Example:
        # Valid filenames
        assert validate_filename('document.pdf')
        assert validate_filename('my-file_v2.txt')
        
        # Path traversal attacks
        assert not validate_filename('../../../etc/passwd')
        assert not validate_filename('..\\..\\windows\\system32')
        
        # Special characters
        assert not validate_filename('file<script>.txt')
        assert not validate_filename('file|pipe.txt')
        
        # Length validation
        assert not validate_filename('x' * 300)
    """
    if not filename or len(filename) > max_length:
        return False
    
    # Check for path traversal patterns
    if re.search(r'\.\.[/\\]', filename):
        return False
    
    # Check for absolute paths
    if filename.startswith('/') or (len(filename) > 1 and filename[1] == ':'):
        return False
    
    # Check for null bytes
    if '\x00' in filename:
        return False
    
    # Define dangerous characters
    dangerous_chars = r'[<>:"|?*\x00-\x1f]'
    if not allow_path_chars:
        dangerous_chars = r'[<>:"|?*\\/\x00-\x1f]'
    
    if re.search(dangerous_chars, filename):
        return False
    
    # Check for Windows reserved names
    reserved_names = [
        'CON', 'PRN', 'AUX', 'NUL',
        'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
        'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
    ]
    
    base_name = os.path.splitext(filename)[0].upper()
    if base_name in reserved_names:
        return False
    
    return True


# Pytest Fixtures

@pytest.fixture
def mock_file_upload() -> MockFileStorage:
    """
    Pytest fixture providing a mock uploaded file for testing.
    
    Creates a basic text file upload that can be used in tests requiring
    file upload functionality. The file contains sample text content and
    uses text/plain MIME type.
    
    Yields:
        MockFileStorage: Mock uploaded file ready for testing
    
    Example:
        def test_file_upload_endpoint(client, mock_file_upload):
            response = client.post(
                '/api/upload',
                data={'file': mock_file_upload},
                content_type='multipart/form-data'
            )
            assert response.status_code == 200
            assert 'file_id' in response.json
    """
    return create_mock_uploaded_file(
        filename='test_upload.txt',
        content=b'This is a test file for upload testing.',
        mimetype='text/plain'
    )


@pytest.fixture
def mock_file_system() -> MockFileSystem:
    """
    Pytest fixture providing a clean mock file system for each test.
    
    Creates a new MockFileSystem instance that provides isolated virtual
    file storage for testing file operations without disk I/O. Automatically
    cleaned up after each test.
    
    Yields:
        MockFileSystem: Empty virtual file system for testing
    
    Example:
        def test_file_operations(mock_file_system):
            # Create a file
            file_id = mock_file_system.create_file(
                '/uploads/test.txt',
                b'content'
            )
            
            # Verify it exists
            assert mock_file_system.exists('/uploads/test.txt')
            
            # Read it back
            content = mock_file_system.read_file('/uploads/test.txt')
            assert content == b'content'
            
            # Delete it
            assert mock_file_system.delete_file('/uploads/test.txt')
            assert not mock_file_system.exists('/uploads/test.txt')
    """
    fs = MockFileSystem()
    yield fs
    fs.clear()


@pytest.fixture
def temp_file(tmp_path: Path) -> Callable[[str, bytes], Path]:
    """
    Pytest fixture for creating temporary files in tests.
    
    Provides a factory function that creates temporary files in pytest's
    tmp_path directory. Files are automatically cleaned up after the test.
    Works with pytest's built-in tmp_path fixture for actual filesystem
    operations when needed.
    
    Args:
        tmp_path: Pytest's tmp_path fixture (automatically injected)
    
    Yields:
        Callable: Factory function that creates temporary files
    
    Example:
        def test_file_processing(temp_file):
            # Create a temporary PDF file
            pdf_path = temp_file('document.pdf', b'%PDF-1.4...')
            
            # Use the file in your test
            with open(pdf_path, 'rb') as f:
                content = f.read()
            
            assert pdf_path.exists()
            # File automatically cleaned up after test
        
        def test_multiple_temp_files(temp_file):
            file1 = temp_file('data.json', b'{"key": "value"}')
            file2 = temp_file('image.png', b'\\x89PNG...')
            
            assert file1.exists() and file2.exists()
    """
    created_files = []
    
    def _create_temp_file(filename: str, content: bytes) -> Path:
        """
        Create a temporary file with specified content.
        
        Args:
            filename: Name for the temporary file
            content: Binary content to write
        
        Returns:
            Path: Path object pointing to the created file
        """
        file_path = tmp_path / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(content)
        created_files.append(file_path)
        return file_path
    
    yield _create_temp_file
    
    # Cleanup: Remove all created files
    for file_path in created_files:
        if file_path.exists():
            file_path.unlink()


# Additional utility functions for edge case testing

def create_empty_file() -> MockFileStorage:
    """
    Create a mock empty file for testing edge cases.
    
    Returns:
        MockFileStorage: Empty file with no content
    
    Example:
        empty = create_empty_file()
        assert empty.content_length == 0
    """
    return create_mock_uploaded_file(
        filename='empty.txt',
        content=b'',
        mimetype='text/plain'
    )


def create_oversized_file(size_mb: int = 100) -> MockFileStorage:
    """
    Create a mock oversized file for testing file size limits.
    
    Args:
        size_mb: Size of file in megabytes (default: 100MB)
    
    Returns:
        MockFileStorage: Large file for size limit testing
    
    Example:
        large_file = create_oversized_file(size_mb=50)
        assert not validate_file_size(
            large_file._content,
            max_size_bytes=10 * 1024 * 1024  # 10MB limit
        )
    """
    content = b'x' * (size_mb * 1024 * 1024)
    return create_mock_uploaded_file(
        filename=f'large_file_{size_mb}mb.bin',
        content=content,
        mimetype='application/octet-stream'
    )


def create_malicious_filename_file() -> MockFileStorage:
    """
    Create a mock file with a malicious filename for security testing.
    
    Returns:
        MockFileStorage: File with path traversal attempt in filename
    
    Example:
        malicious = create_malicious_filename_file()
        assert not validate_filename(malicious.filename)
    """
    return create_mock_uploaded_file(
        filename='../../../etc/passwd',
        content=b'malicious content',
        mimetype='text/plain'
    )


def create_invalid_type_file() -> MockFileStorage:
    """
    Create a mock file with an executable extension for type validation testing.
    
    Returns:
        MockFileStorage: File with .exe extension
    
    Example:
        exe_file = create_invalid_type_file()
        assert not validate_file_type(
            exe_file.filename,
            allowed_types=['.pdf', '.doc', '.txt']
        )
    """
    return create_mock_uploaded_file(
        filename='malware.exe',
        content=b'MZ\x90\x00',  # PE executable header
        mimetype='application/x-msdownload'
    )
