"""
Mock implementations for cloud storage services (AWS S3, Google Cloud Storage).

This module provides comprehensive mock implementations of cloud storage clients
for testing file upload, download, and deletion functionality without requiring
actual cloud service connections. Includes thread-safe operations and configurable
responses for testing both success and failure scenarios.

Classes:
    MockS3Client: Mock implementation of AWS S3 client
    MockGCSClient: Mock implementation of Google Cloud Storage client
    MockStorageBucket: Generic mock storage bucket implementation

Functions:
    create_mock_s3_response: Helper to create S3 API response structures
    create_mock_gcs_response: Helper to create GCS API response structures
    create_mock_error_response: Helper to create error response structures
    create_mock_multipart_upload: Helper to create multipart upload responses
    mock_s3_client: Pytest fixture for MockS3Client
    mock_gcs_client: Pytest fixture for MockGCSClient
    mock_storage_bucket: Pytest fixture for MockStorageBucket
"""

import base64
import hashlib
import json
import mimetypes
import os
import time
import uuid
from collections import Counter, OrderedDict, defaultdict
from copy import deepcopy
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
from threading import Lock, RLock
from typing import Any, BinaryIO, Callable, Dict, List, Optional, Union
from unittest.mock import MagicMock
from urllib.parse import quote, urlencode, urlparse

import pytest


# Thread-safe storage for mock cloud storage operations
_MOCK_STORAGE_LOCK = RLock()
_MOCK_S3_STORAGE: Dict[str, Dict[str, Dict[str, Any]]] = defaultdict(lambda: defaultdict(dict))
_MOCK_GCS_STORAGE: Dict[str, Dict[str, Dict[str, Any]]] = defaultdict(lambda: defaultdict(dict))


def create_mock_s3_response(
    bucket: str,
    key: str,
    content: bytes,
    metadata: Optional[Dict[str, Any]] = None,
    version_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a mock S3 API response structure.
    
    Args:
        bucket: S3 bucket name
        key: Object key
        content: File content bytes
        metadata: Optional custom metadata
        version_id: Optional version ID for versioned objects
    
    Returns:
        Dictionary matching S3 API response format
    """
    content_md5 = hashlib.md5(content).hexdigest()
    etag = f'"{content_md5}"'
    content_type, _ = mimetypes.guess_type(key)
    
    response = {
        'ResponseMetadata': {
            'RequestId': str(uuid.uuid4()),
            'HTTPStatusCode': 200,
            'HTTPHeaders': {
                'content-type': content_type or 'application/octet-stream',
                'content-length': str(len(content)),
                'etag': etag,
                'x-amz-request-id': str(uuid.uuid4()),
                'date': datetime.now().isoformat()
            }
        },
        'ETag': etag,
        'Bucket': bucket,
        'Key': key,
        'ContentLength': len(content),
        'ContentType': content_type or 'application/octet-stream',
        'LastModified': datetime.now(),
        'Metadata': metadata or {},
        'VersionId': version_id or str(uuid.uuid4())
    }
    return response


def create_mock_gcs_response(
    bucket: str,
    blob_name: str,
    content: bytes,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create a mock Google Cloud Storage API response structure.
    
    Args:
        bucket: GCS bucket name
        blob_name: Blob name (object key)
        content: File content bytes
        metadata: Optional custom metadata
    
    Returns:
        Dictionary matching GCS API response format
    """
    content_md5 = base64.b64encode(hashlib.md5(content).digest()).decode()
    content_type, _ = mimetypes.guess_type(blob_name)
    
    response = {
        'kind': 'storage#object',
        'id': f'{bucket}/{blob_name}/{uuid.uuid4()}',
        'selfLink': f'https://www.googleapis.com/storage/v1/b/{bucket}/o/{quote(blob_name)}',
        'name': blob_name,
        'bucket': bucket,
        'generation': str(int(time.time() * 1000)),
        'metageneration': '1',
        'contentType': content_type or 'application/octet-stream',
        'timeCreated': datetime.now().isoformat() + 'Z',
        'updated': datetime.now().isoformat() + 'Z',
        'storageClass': 'STANDARD',
        'size': str(len(content)),
        'md5Hash': content_md5,
        'mediaLink': f'https://storage.googleapis.com/download/storage/v1/b/{bucket}/o/{quote(blob_name)}?alt=media',
        'metadata': metadata or {},
        'crc32c': base64.b64encode(hashlib.sha256(content).digest()[:4]).decode()
    }
    return response


def create_mock_error_response(
    error_code: str,
    message: str,
    status_code: int = 400,
    service: str = 's3'
) -> Dict[str, Any]:
    """
    Create a mock error response for testing failure scenarios.
    
    Args:
        error_code: Error code (e.g., 'NoSuchKey', 'AccessDenied')
        message: Error message
        status_code: HTTP status code
        service: Service type ('s3' or 'gcs')
    
    Returns:
        Dictionary with error response structure
    """
    if service == 's3':
        return {
            'Error': {
                'Code': error_code,
                'Message': message,
                'Type': 'Sender'
            },
            'ResponseMetadata': {
                'RequestId': str(uuid.uuid4()),
                'HTTPStatusCode': status_code,
                'HTTPHeaders': {}
            }
        }
    else:  # gcs
        return {
            'error': {
                'code': status_code,
                'message': message,
                'errors': [{
                    'domain': 'global',
                    'reason': error_code,
                    'message': message
                }]
            }
        }


def create_mock_multipart_upload(
    bucket: str,
    key: str,
    upload_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a mock multipart upload initiation response.
    
    Args:
        bucket: S3 bucket name
        key: Object key
        upload_id: Optional upload ID (generated if not provided)
    
    Returns:
        Dictionary with multipart upload response structure
    """
    return {
        'Bucket': bucket,
        'Key': key,
        'UploadId': upload_id or str(uuid.uuid4()),
        'ResponseMetadata': {
            'RequestId': str(uuid.uuid4()),
            'HTTPStatusCode': 200,
            'HTTPHeaders': {}
        }
    }


class MockS3Client:
    """
    Mock implementation of AWS S3 client for testing.
    
    Provides thread-safe mock operations for S3 including upload, download,
    delete, list, and metadata operations. Supports presigned URLs and
    multipart uploads.
    
    Attributes:
        storage: Thread-safe storage dictionary for uploaded objects
        lock: Thread lock for atomic operations
        buckets: Set of created bucket names
    """
    
    def __init__(self):
        """Initialize MockS3Client with empty storage."""
        self.storage: Dict[str, Dict[str, Dict[str, Any]]] = defaultdict(lambda: defaultdict(dict))
        self.lock = RLock()
        self.buckets: set = set()
        self.multipart_uploads: Dict[str, Dict[str, Any]] = {}
    
    def upload_file(
        self,
        filename: str,
        bucket: str,
        key: str,
        extra_args: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Upload a file to mock S3 storage.
        
        Args:
            filename: Local file path to upload
            bucket: S3 bucket name
            key: Object key (destination path in S3)
            extra_args: Optional additional arguments (metadata, ACL, etc.)
        
        Returns:
            Mock S3 response dictionary
        
        Raises:
            FileNotFoundError: If local file doesn't exist
            PermissionError: If simulating permission denied scenario
        """
        if not os.path.exists(filename):
            raise FileNotFoundError(f"File not found: {filename}")
        
        with open(filename, 'rb') as f:
            content = f.read()
        
        metadata = extra_args.get('Metadata', {}) if extra_args else {}
        
        with self.lock:
            self.buckets.add(bucket)
            self.storage[bucket][key] = {
                'content': content,
                'metadata': metadata,
                'etag': hashlib.md5(content).hexdigest(),
                'size': len(content),
                'last_modified': datetime.now(),
                'content_type': mimetypes.guess_type(filename)[0] or 'application/octet-stream',
                'version_id': str(uuid.uuid4())
            }
        
        return create_mock_s3_response(bucket, key, content, metadata)
    
    def download_file(
        self,
        bucket: str,
        key: str,
        filename: str
    ) -> Dict[str, Any]:
        """
        Download a file from mock S3 storage.
        
        Args:
            bucket: S3 bucket name
            key: Object key to download
            filename: Local file path to save downloaded content
        
        Returns:
            Mock S3 response dictionary
        
        Raises:
            KeyError: If object doesn't exist (simulates NoSuchKey error)
        """
        with self.lock:
            if bucket not in self.storage or key not in self.storage[bucket]:
                raise KeyError(f"Object not found: s3://{bucket}/{key}")
            
            obj_data = deepcopy(self.storage[bucket][key])
            content = obj_data['content']
        
        # Write content to file
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, 'wb') as f:
            f.write(content)
        
        return create_mock_s3_response(
            bucket, key, content,
            obj_data.get('metadata'),
            obj_data.get('version_id')
        )
    
    def delete_object(
        self,
        bucket: str,
        key: str
    ) -> Dict[str, Any]:
        """
        Delete an object from mock S3 storage.
        
        Args:
            bucket: S3 bucket name
            key: Object key to delete
        
        Returns:
            Mock S3 delete response dictionary
        """
        with self.lock:
            if bucket in self.storage and key in self.storage[bucket]:
                del self.storage[bucket][key]
        
        return {
            'ResponseMetadata': {
                'RequestId': str(uuid.uuid4()),
                'HTTPStatusCode': 204,
                'HTTPHeaders': {}
            },
            'DeleteMarker': False,
            'VersionId': str(uuid.uuid4())
        }
    
    def list_objects(
        self,
        bucket: str,
        prefix: str = '',
        max_keys: int = 1000,
        delimiter: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List objects in mock S3 bucket.
        
        Args:
            bucket: S3 bucket name
            prefix: Filter objects by prefix
            max_keys: Maximum number of objects to return
            delimiter: Delimiter for grouping keys
        
        Returns:
            Mock S3 list objects response dictionary
        """
        with self.lock:
            if bucket not in self.storage:
                return {
                    'ResponseMetadata': {
                        'RequestId': str(uuid.uuid4()),
                        'HTTPStatusCode': 200
                    },
                    'Contents': [],
                    'Name': bucket,
                    'Prefix': prefix,
                    'MaxKeys': max_keys,
                    'IsTruncated': False
                }
            
            objects = []
            for key, obj_data in self.storage[bucket].items():
                if key.startswith(prefix):
                    objects.append({
                        'Key': key,
                        'LastModified': obj_data.get('last_modified', datetime.now()),
                        'ETag': f'"{obj_data["etag"]}"',
                        'Size': obj_data['size'],
                        'StorageClass': 'STANDARD'
                    })
            
            objects = objects[:max_keys]
        
        return {
            'ResponseMetadata': {
                'RequestId': str(uuid.uuid4()),
                'HTTPStatusCode': 200
            },
            'Contents': objects,
            'Name': bucket,
            'Prefix': prefix,
            'MaxKeys': max_keys,
            'IsTruncated': len(objects) >= max_keys
        }
    
    def get_object(
        self,
        bucket: str,
        key: str
    ) -> Dict[str, Any]:
        """
        Get object data from mock S3 storage.
        
        Args:
            bucket: S3 bucket name
            key: Object key
        
        Returns:
            Mock S3 get object response with Body stream
        
        Raises:
            KeyError: If object doesn't exist
        """
        with self.lock:
            if bucket not in self.storage or key not in self.storage[bucket]:
                raise KeyError(f"Object not found: s3://{bucket}/{key}")
            
            obj_data = deepcopy(self.storage[bucket][key])
        
        response = create_mock_s3_response(
            bucket, key, obj_data['content'],
            obj_data.get('metadata'),
            obj_data.get('version_id')
        )
        response['Body'] = BytesIO(obj_data['content'])
        
        return response
    
    def put_object(
        self,
        bucket: str,
        key: str,
        body: Union[bytes, BinaryIO],
        metadata: Optional[Dict[str, Any]] = None,
        content_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Put object into mock S3 storage.
        
        Args:
            bucket: S3 bucket name
            key: Object key
            body: Object content (bytes or file-like object)
            metadata: Optional custom metadata
            content_type: Optional content type
        
        Returns:
            Mock S3 put object response dictionary
        """
        if isinstance(body, bytes):
            content = body
        else:
            content = body.read()
        
        with self.lock:
            self.buckets.add(bucket)
            self.storage[bucket][key] = {
                'content': content,
                'metadata': metadata or {},
                'etag': hashlib.md5(content).hexdigest(),
                'size': len(content),
                'last_modified': datetime.now(),
                'content_type': content_type or mimetypes.guess_type(key)[0] or 'application/octet-stream',
                'version_id': str(uuid.uuid4())
            }
        
        return create_mock_s3_response(bucket, key, content, metadata)
    
    def copy_object(
        self,
        copy_source: Dict[str, str],
        bucket: str,
        key: str
    ) -> Dict[str, Any]:
        """
        Copy object within mock S3 storage.
        
        Args:
            copy_source: Dictionary with 'Bucket' and 'Key' of source object
            bucket: Destination bucket name
            key: Destination object key
        
        Returns:
            Mock S3 copy object response dictionary
        
        Raises:
            KeyError: If source object doesn't exist
        """
        source_bucket = copy_source['Bucket']
        source_key = copy_source['Key']
        
        with self.lock:
            if source_bucket not in self.storage or source_key not in self.storage[source_bucket]:
                raise KeyError(f"Source object not found: s3://{source_bucket}/{source_key}")
            
            source_data = deepcopy(self.storage[source_bucket][source_key])
            self.buckets.add(bucket)
            self.storage[bucket][key] = {
                **source_data,
                'last_modified': datetime.now(),
                'version_id': str(uuid.uuid4())
            }
        
        return {
            'ResponseMetadata': {
                'RequestId': str(uuid.uuid4()),
                'HTTPStatusCode': 200
            },
            'CopyObjectResult': {
                'ETag': f'"{source_data["etag"]}"',
                'LastModified': datetime.now()
            }
        }
    
    def generate_presigned_url(
        self,
        client_method: str,
        params: Dict[str, Any],
        expires_in: int = 3600
    ) -> str:
        """
        Generate a mock presigned URL for S3 operations.
        
        Args:
            client_method: S3 client method name (e.g., 'get_object')
            params: Parameters for the operation
            expires_in: URL expiration time in seconds
        
        Returns:
            Mock presigned URL string
        """
        bucket = params.get('Bucket', 'mock-bucket')
        key = params.get('Key', 'mock-key')
        expiration = int(time.time()) + expires_in
        
        query_params = {
            'X-Amz-Algorithm': 'AWS4-HMAC-SHA256',
            'X-Amz-Credential': 'mock-credentials',
            'X-Amz-Date': datetime.now().strftime('%Y%m%dT%H%M%SZ'),
            'X-Amz-Expires': str(expires_in),
            'X-Amz-SignedHeaders': 'host',
            'X-Amz-Signature': hashlib.sha256(f'{bucket}{key}{expiration}'.encode()).hexdigest()
        }
        
        return f'https://{bucket}.s3.amazonaws.com/{quote(key)}?{urlencode(query_params)}'
    
    def head_object(
        self,
        bucket: str,
        key: str
    ) -> Dict[str, Any]:
        """
        Get object metadata without downloading content.
        
        Args:
            bucket: S3 bucket name
            key: Object key
        
        Returns:
            Mock S3 head object response with metadata
        
        Raises:
            KeyError: If object doesn't exist
        """
        with self.lock:
            if bucket not in self.storage or key not in self.storage[bucket]:
                raise KeyError(f"Object not found: s3://{bucket}/{key}")
            
            obj_data = self.storage[bucket][key]
        
        return {
            'ResponseMetadata': {
                'RequestId': str(uuid.uuid4()),
                'HTTPStatusCode': 200
            },
            'ETag': f'"{obj_data["etag"]}"',
            'ContentLength': obj_data['size'],
            'ContentType': obj_data.get('content_type', 'application/octet-stream'),
            'LastModified': obj_data.get('last_modified', datetime.now()),
            'Metadata': obj_data.get('metadata', {}),
            'VersionId': obj_data.get('version_id')
        }
    
    def get_object_metadata(
        self,
        bucket: str,
        key: str
    ) -> Dict[str, Any]:
        """
        Get custom metadata for an object.
        
        Args:
            bucket: S3 bucket name
            key: Object key
        
        Returns:
            Dictionary of custom metadata
        
        Raises:
            KeyError: If object doesn't exist
        """
        with self.lock:
            if bucket not in self.storage or key not in self.storage[bucket]:
                raise KeyError(f"Object not found: s3://{bucket}/{key}")
            
            return deepcopy(self.storage[bucket][key].get('metadata', {}))
    
    def set_object_metadata(
        self,
        bucket: str,
        key: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Set custom metadata for an object.
        
        Args:
            bucket: S3 bucket name
            key: Object key
            metadata: Dictionary of metadata to set
        
        Returns:
            Mock S3 response dictionary
        
        Raises:
            KeyError: If object doesn't exist
        """
        with self.lock:
            if bucket not in self.storage or key not in self.storage[bucket]:
                raise KeyError(f"Object not found: s3://{bucket}/{key}")
            
            self.storage[bucket][key]['metadata'] = metadata
        
        return {
            'ResponseMetadata': {
                'RequestId': str(uuid.uuid4()),
                'HTTPStatusCode': 200
            }
        }
    
    def list_buckets(self) -> Dict[str, Any]:
        """
        List all mock S3 buckets.
        
        Returns:
            Mock S3 list buckets response dictionary
        """
        with self.lock:
            buckets_list = [
                {
                    'Name': bucket,
                    'CreationDate': datetime.now()
                }
                for bucket in self.buckets
            ]
        
        return {
            'ResponseMetadata': {
                'RequestId': str(uuid.uuid4()),
                'HTTPStatusCode': 200
            },
            'Buckets': buckets_list,
            'Owner': {
                'DisplayName': 'mock-owner',
                'ID': str(uuid.uuid4())
            }
        }
    
    def create_bucket(
        self,
        bucket: str,
        location: str = 'us-east-1'
    ) -> Dict[str, Any]:
        """
        Create a mock S3 bucket.
        
        Args:
            bucket: Bucket name
            location: AWS region location
        
        Returns:
            Mock S3 create bucket response dictionary
        """
        with self.lock:
            self.buckets.add(bucket)
            if bucket not in self.storage:
                self.storage[bucket] = {}
        
        return {
            'ResponseMetadata': {
                'RequestId': str(uuid.uuid4()),
                'HTTPStatusCode': 200
            },
            'Location': f'/{bucket}'
        }
    
    def delete_bucket(
        self,
        bucket: str
    ) -> Dict[str, Any]:
        """
        Delete a mock S3 bucket.
        
        Args:
            bucket: Bucket name
        
        Returns:
            Mock S3 delete bucket response dictionary
        
        Raises:
            ValueError: If bucket contains objects
        """
        with self.lock:
            if bucket in self.storage and len(self.storage[bucket]) > 0:
                raise ValueError(f"Bucket not empty: {bucket}")
            
            if bucket in self.storage:
                del self.storage[bucket]
            self.buckets.discard(bucket)
        
        return {
            'ResponseMetadata': {
                'RequestId': str(uuid.uuid4()),
                'HTTPStatusCode': 204
            }
        }
    
    def get_bucket_location(
        self,
        bucket: str
    ) -> Dict[str, Any]:
        """
        Get mock S3 bucket location.
        
        Args:
            bucket: Bucket name
        
        Returns:
            Mock S3 get bucket location response dictionary
        """
        return {
            'ResponseMetadata': {
                'RequestId': str(uuid.uuid4()),
                'HTTPStatusCode': 200
            },
            'LocationConstraint': 'us-east-1'
        }
    
    def clear_storage(self) -> None:
        """Clear all mock S3 storage data."""
        with self.lock:
            self.storage.clear()
            self.buckets.clear()
            self.multipart_uploads.clear()


class MockGCSClient:
    """
    Mock implementation of Google Cloud Storage client for testing.
    
    Provides thread-safe mock operations for GCS including blob upload,
    download, delete, list, and metadata operations. Supports signed URLs.
    
    Attributes:
        storage: Thread-safe storage dictionary for uploaded blobs
        lock: Thread lock for atomic operations
        buckets: Set of created bucket names
    """
    
    def __init__(self):
        """Initialize MockGCSClient with empty storage."""
        self.storage: Dict[str, Dict[str, Dict[str, Any]]] = defaultdict(lambda: defaultdict(dict))
        self.lock = RLock()
        self.buckets: set = set()
        self._mock_buckets: Dict[str, 'MockStorageBucket'] = {}
    
    def upload_blob(
        self,
        bucket_name: str,
        blob_name: str,
        source_file: Union[str, BinaryIO],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Upload a blob to mock GCS storage.
        
        Args:
            bucket_name: GCS bucket name
            blob_name: Blob name (object key)
            source_file: Source file path or file-like object
            metadata: Optional custom metadata
        
        Returns:
            Mock GCS response dictionary
        
        Raises:
            FileNotFoundError: If source file doesn't exist
        """
        if isinstance(source_file, str):
            if not os.path.exists(source_file):
                raise FileNotFoundError(f"File not found: {source_file}")
            with open(source_file, 'rb') as f:
                content = f.read()
        else:
            content = source_file.read()
        
        with self.lock:
            self.buckets.add(bucket_name)
            self.storage[bucket_name][blob_name] = {
                'content': content,
                'metadata': metadata or {},
                'md5_hash': base64.b64encode(hashlib.md5(content).digest()).decode(),
                'size': len(content),
                'time_created': datetime.now(),
                'updated': datetime.now(),
                'content_type': mimetypes.guess_type(blob_name)[0] or 'application/octet-stream',
                'generation': str(int(time.time() * 1000))
            }
        
        return create_mock_gcs_response(bucket_name, blob_name, content, metadata)
    
    def download_blob(
        self,
        bucket_name: str,
        blob_name: str,
        destination_file: str
    ) -> Dict[str, Any]:
        """
        Download a blob from mock GCS storage.
        
        Args:
            bucket_name: GCS bucket name
            blob_name: Blob name to download
            destination_file: Local file path to save content
        
        Returns:
            Mock GCS response dictionary
        
        Raises:
            KeyError: If blob doesn't exist
        """
        with self.lock:
            if bucket_name not in self.storage or blob_name not in self.storage[bucket_name]:
                raise KeyError(f"Blob not found: gs://{bucket_name}/{blob_name}")
            
            blob_data = deepcopy(self.storage[bucket_name][blob_name])
            content = blob_data['content']
        
        os.makedirs(os.path.dirname(destination_file), exist_ok=True)
        with open(destination_file, 'wb') as f:
            f.write(content)
        
        return create_mock_gcs_response(
            bucket_name, blob_name, content,
            blob_data.get('metadata')
        )
    
    def delete_blob(
        self,
        bucket_name: str,
        blob_name: str
    ) -> Dict[str, Any]:
        """
        Delete a blob from mock GCS storage.
        
        Args:
            bucket_name: GCS bucket name
            blob_name: Blob name to delete
        
        Returns:
            Mock GCS delete response dictionary
        """
        with self.lock:
            if bucket_name in self.storage and blob_name in self.storage[bucket_name]:
                del self.storage[bucket_name][blob_name]
        
        return {
            'kind': 'storage#object',
            'id': f'{bucket_name}/{blob_name}',
            'deleted': True
        }
    
    def list_blobs(
        self,
        bucket_name: str,
        prefix: str = '',
        max_results: int = 1000
    ) -> Dict[str, Any]:
        """
        List blobs in mock GCS bucket.
        
        Args:
            bucket_name: GCS bucket name
            prefix: Filter blobs by prefix
            max_results: Maximum number of blobs to return
        
        Returns:
            Mock GCS list blobs response dictionary
        """
        with self.lock:
            if bucket_name not in self.storage:
                return {
                    'kind': 'storage#objects',
                    'items': []
                }
            
            items = []
            for blob_name, blob_data in self.storage[bucket_name].items():
                if blob_name.startswith(prefix):
                    items.append({
                        'kind': 'storage#object',
                        'id': f'{bucket_name}/{blob_name}',
                        'name': blob_name,
                        'bucket': bucket_name,
                        'size': str(blob_data['size']),
                        'contentType': blob_data.get('content_type', 'application/octet-stream'),
                        'timeCreated': blob_data.get('time_created', datetime.now()).isoformat() + 'Z',
                        'updated': blob_data.get('updated', datetime.now()).isoformat() + 'Z',
                        'md5Hash': blob_data['md5_hash'],
                        'generation': blob_data.get('generation', '1')
                    })
            
            items = items[:max_results]
        
        return {
            'kind': 'storage#objects',
            'items': items
        }
    
    def get_blob(
        self,
        bucket_name: str,
        blob_name: str
    ) -> Dict[str, Any]:
        """
        Get blob data from mock GCS storage.
        
        Args:
            bucket_name: GCS bucket name
            blob_name: Blob name
        
        Returns:
            Mock GCS get blob response with content
        
        Raises:
            KeyError: If blob doesn't exist
        """
        with self.lock:
            if bucket_name not in self.storage or blob_name not in self.storage[bucket_name]:
                raise KeyError(f"Blob not found: gs://{bucket_name}/{blob_name}")
            
            blob_data = deepcopy(self.storage[bucket_name][blob_name])
        
        response = create_mock_gcs_response(
            bucket_name, blob_name, blob_data['content'],
            blob_data.get('metadata')
        )
        response['content'] = blob_data['content']
        
        return response
    
    def copy_blob(
        self,
        source_bucket: str,
        source_blob: str,
        destination_bucket: str,
        destination_blob: str
    ) -> Dict[str, Any]:
        """
        Copy blob within mock GCS storage.
        
        Args:
            source_bucket: Source bucket name
            source_blob: Source blob name
            destination_bucket: Destination bucket name
            destination_blob: Destination blob name
        
        Returns:
            Mock GCS copy blob response dictionary
        
        Raises:
            KeyError: If source blob doesn't exist
        """
        with self.lock:
            if source_bucket not in self.storage or source_blob not in self.storage[source_bucket]:
                raise KeyError(f"Source blob not found: gs://{source_bucket}/{source_blob}")
            
            source_data = deepcopy(self.storage[source_bucket][source_blob])
            self.buckets.add(destination_bucket)
            self.storage[destination_bucket][destination_blob] = {
                **source_data,
                'time_created': datetime.now(),
                'updated': datetime.now(),
                'generation': str(int(time.time() * 1000))
            }
        
        return create_mock_gcs_response(
            destination_bucket, destination_blob,
            source_data['content'],
            source_data.get('metadata')
        )
    
    def get_blob_metadata(
        self,
        bucket_name: str,
        blob_name: str
    ) -> Dict[str, Any]:
        """
        Get custom metadata for a blob.
        
        Args:
            bucket_name: GCS bucket name
            blob_name: Blob name
        
        Returns:
            Dictionary of custom metadata
        
        Raises:
            KeyError: If blob doesn't exist
        """
        with self.lock:
            if bucket_name not in self.storage or blob_name not in self.storage[bucket_name]:
                raise KeyError(f"Blob not found: gs://{bucket_name}/{blob_name}")
            
            return deepcopy(self.storage[bucket_name][blob_name].get('metadata', {}))
    
    def set_blob_metadata(
        self,
        bucket_name: str,
        blob_name: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Set custom metadata for a blob.
        
        Args:
            bucket_name: GCS bucket name
            blob_name: Blob name
            metadata: Dictionary of metadata to set
        
        Returns:
            Mock GCS response dictionary
        
        Raises:
            KeyError: If blob doesn't exist
        """
        with self.lock:
            if bucket_name not in self.storage or blob_name not in self.storage[bucket_name]:
                raise KeyError(f"Blob not found: gs://{bucket_name}/{blob_name}")
            
            self.storage[bucket_name][blob_name]['metadata'] = metadata
        
        return {
            'kind': 'storage#object',
            'id': f'{bucket_name}/{blob_name}',
            'metadata': metadata
        }
    
    def generate_signed_url(
        self,
        bucket_name: str,
        blob_name: str,
        expiration: int = 3600,
        method: str = 'GET'
    ) -> str:
        """
        Generate a mock signed URL for GCS operations.
        
        Args:
            bucket_name: GCS bucket name
            blob_name: Blob name
            expiration: URL expiration time in seconds
            method: HTTP method (GET, PUT, etc.)
        
        Returns:
            Mock signed URL string
        """
        expiration_time = int(time.time()) + expiration
        signature = hashlib.sha256(f'{bucket_name}{blob_name}{expiration_time}'.encode()).hexdigest()
        
        query_params = {
            'GoogleAccessId': 'mock-service-account',
            'Expires': str(expiration_time),
            'Signature': signature
        }
        
        return f'https://storage.googleapis.com/{bucket_name}/{quote(blob_name)}?{urlencode(query_params)}'
    
    def bucket(self, bucket_name: str) -> 'MockStorageBucket':
        """
        Get a mock storage bucket object.
        
        Args:
            bucket_name: Bucket name
        
        Returns:
            MockStorageBucket instance
        """
        if bucket_name not in self._mock_buckets:
            self._mock_buckets[bucket_name] = MockStorageBucket(bucket_name, self)
        return self._mock_buckets[bucket_name]
    
    def list_buckets(self) -> Dict[str, Any]:
        """
        List all mock GCS buckets.
        
        Returns:
            Mock GCS list buckets response dictionary
        """
        with self.lock:
            items = [
                {
                    'kind': 'storage#bucket',
                    'id': bucket,
                    'name': bucket,
                    'timeCreated': datetime.now().isoformat() + 'Z',
                    'location': 'US',
                    'storageClass': 'STANDARD'
                }
                for bucket in self.buckets
            ]
        
        return {
            'kind': 'storage#buckets',
            'items': items
        }
    
    def create_bucket(
        self,
        bucket_name: str,
        location: str = 'US'
    ) -> Dict[str, Any]:
        """
        Create a mock GCS bucket.
        
        Args:
            bucket_name: Bucket name
            location: GCS location
        
        Returns:
            Mock GCS create bucket response dictionary
        """
        with self.lock:
            self.buckets.add(bucket_name)
            if bucket_name not in self.storage:
                self.storage[bucket_name] = {}
        
        return {
            'kind': 'storage#bucket',
            'id': bucket_name,
            'name': bucket_name,
            'location': location,
            'timeCreated': datetime.now().isoformat() + 'Z'
        }
    
    def delete_bucket(
        self,
        bucket_name: str
    ) -> Dict[str, Any]:
        """
        Delete a mock GCS bucket.
        
        Args:
            bucket_name: Bucket name
        
        Returns:
            Mock GCS delete bucket response dictionary
        
        Raises:
            ValueError: If bucket contains blobs
        """
        with self.lock:
            if bucket_name in self.storage and len(self.storage[bucket_name]) > 0:
                raise ValueError(f"Bucket not empty: {bucket_name}")
            
            if bucket_name in self.storage:
                del self.storage[bucket_name]
            self.buckets.discard(bucket_name)
        
        return {
            'kind': 'storage#bucket',
            'id': bucket_name,
            'deleted': True
        }
    
    def clear_storage(self) -> None:
        """Clear all mock GCS storage data."""
        with self.lock:
            self.storage.clear()
            self.buckets.clear()
            self._mock_buckets.clear()


class MockStorageBucket:
    """
    Generic mock storage bucket implementation.
    
    Provides a unified interface for testing storage bucket operations
    across different cloud providers. Supports upload, download, delete,
    list, and metadata operations.
    
    Attributes:
        name: Bucket name
        location: Bucket location
        client: Parent storage client
        storage: Thread-safe storage dictionary
        lock: Thread lock for atomic operations
    """
    
    def __init__(self, name: str, client: Optional[MockGCSClient] = None, location: str = 'US'):
        """
        Initialize MockStorageBucket.
        
        Args:
            name: Bucket name
            client: Optional parent GCS client
            location: Bucket location
        """
        self.name = name
        self.location = location
        self._client = client
        self._storage: Dict[str, Dict[str, Any]] = {}
        self._lock = RLock()
        self._metadata: Dict[str, Any] = {}
        self._exists = True
    
    def upload(
        self,
        object_key: str,
        content: Union[bytes, BinaryIO],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Upload an object to the mock bucket.
        
        Args:
            object_key: Object key/name
            content: Object content (bytes or file-like object)
            metadata: Optional custom metadata
        
        Returns:
            Mock upload response dictionary
        """
        if isinstance(content, bytes):
            data = content
        else:
            data = content.read()
        
        with self._lock:
            self._storage[object_key] = {
                'content': data,
                'metadata': metadata or {},
                'size': len(data),
                'etag': hashlib.md5(data).hexdigest(),
                'last_modified': datetime.now(),
                'content_type': mimetypes.guess_type(object_key)[0] or 'application/octet-stream'
            }
        
        return {
            'key': object_key,
            'size': len(data),
            'etag': hashlib.md5(data).hexdigest(),
            'bucket': self.name
        }
    
    def download(
        self,
        object_key: str
    ) -> bytes:
        """
        Download an object from the mock bucket.
        
        Args:
            object_key: Object key/name
        
        Returns:
            Object content as bytes
        
        Raises:
            KeyError: If object doesn't exist
        """
        with self._lock:
            if object_key not in self._storage:
                raise KeyError(f"Object not found: {object_key}")
            
            return deepcopy(self._storage[object_key]['content'])
    
    def delete(
        self,
        object_key: str
    ) -> bool:
        """
        Delete an object from the mock bucket.
        
        Args:
            object_key: Object key/name
        
        Returns:
            True if deleted, False if object didn't exist
        """
        with self._lock:
            if object_key in self._storage:
                del self._storage[object_key]
                return True
            return False
    
    def list_objects(
        self,
        prefix: str = '',
        max_keys: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        List objects in the mock bucket.
        
        Args:
            prefix: Filter objects by prefix
            max_keys: Maximum number of objects to return
        
        Returns:
            List of object metadata dictionaries
        """
        with self._lock:
            objects = []
            for key, obj_data in self._storage.items():
                if key.startswith(prefix):
                    objects.append({
                        'key': key,
                        'size': obj_data['size'],
                        'etag': obj_data['etag'],
                        'last_modified': obj_data['last_modified'],
                        'content_type': obj_data['content_type']
                    })
            
            return objects[:max_keys]
    
    def get_object(
        self,
        object_key: str
    ) -> Dict[str, Any]:
        """
        Get object metadata and content.
        
        Args:
            object_key: Object key/name
        
        Returns:
            Dictionary with object metadata and content
        
        Raises:
            KeyError: If object doesn't exist
        """
        with self._lock:
            if object_key not in self._storage:
                raise KeyError(f"Object not found: {object_key}")
            
            return deepcopy(self._storage[object_key])
    
    def exists(self, object_key: Optional[str] = None) -> bool:
        """
        Check if bucket or object exists.
        
        Args:
            object_key: Optional object key to check (if None, checks bucket)
        
        Returns:
            True if exists, False otherwise
        """
        if object_key is None:
            return self._exists
        
        with self._lock:
            return object_key in self._storage
    
    def create(self) -> Dict[str, Any]:
        """
        Create the mock bucket.
        
        Returns:
            Mock bucket creation response dictionary
        """
        self._exists = True
        return {
            'name': self.name,
            'location': self.location,
            'created': datetime.now().isoformat()
        }
    
    def clear(self) -> None:
        """Clear all objects from the mock bucket."""
        with self._lock:
            self._storage.clear()
    
    def get_metadata(self) -> Dict[str, Any]:
        """
        Get bucket metadata.
        
        Returns:
            Dictionary of bucket metadata
        """
        with self._lock:
            return deepcopy(self._metadata)
    
    def set_metadata(
        self,
        metadata: Dict[str, Any]
    ) -> None:
        """
        Set bucket metadata.
        
        Args:
            metadata: Dictionary of metadata to set
        """
        with self._lock:
            self._metadata = metadata
    
    def get_size(self) -> int:
        """
        Get total size of all objects in bucket.
        
        Returns:
            Total size in bytes
        """
        with self._lock:
            return sum(obj['size'] for obj in self._storage.values())
    
    def get_object_count(self) -> int:
        """
        Get count of objects in bucket.
        
        Returns:
            Number of objects
        """
        with self._lock:
            return len(self._storage)


# Pytest fixtures for easy test usage

@pytest.fixture
def mock_s3_client():
    """
    Pytest fixture providing a MockS3Client instance.
    
    Yields:
        MockS3Client: Fresh mock S3 client for testing
    """
    client = MockS3Client()
    yield client
    client.clear_storage()


@pytest.fixture
def mock_gcs_client():
    """
    Pytest fixture providing a MockGCSClient instance.
    
    Yields:
        MockGCSClient: Fresh mock GCS client for testing
    """
    client = MockGCSClient()
    yield client
    client.clear_storage()


@pytest.fixture
def mock_storage_bucket():
    """
    Pytest fixture providing a MockStorageBucket instance.
    
    Yields:
        MockStorageBucket: Fresh mock storage bucket for testing
    """
    bucket = MockStorageBucket('test-bucket')
    yield bucket
    bucket.clear()



