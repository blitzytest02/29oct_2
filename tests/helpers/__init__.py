"""
Test Helper Utilities Package

This package provides comprehensive helper utilities for Flask application testing,
including custom assertions, data generation, request building, response validation,
authentication helpers, database operations, and test client wrappers.

All helpers are designed to reduce code duplication in tests and provide consistent,
expressive patterns for common testing operations. The package follows pytest
best practices and integrates seamlessly with Flask's test_client().

Modules:
    assertions: Custom assertion functions for complex validations
    data_generators: Utilities for generating realistic test data
    request_builders: HTTP request construction helpers
    response_validators: API response validation functions
    auth_helpers: Authentication and authorization testing utilities
    db_helpers: Database seeding, cleanup, and transaction management
    client_wrappers: Enhanced test client wrappers with additional functionality

Usage:
    # Import everything needed for testing in one line
    from tests.helpers import (
        assert_json_structure,
        generate_user_data,
        build_get_request,
        validate_response_status,
        create_test_user,
        seed_database,
        AuthenticatedClient
    )
    
    # Or import all helpers at once
    from tests.helpers import *

Architecture Notes:
    This __init__.py serves as the package's public API, providing convenient
    access to all helper utilities through centralized imports. It follows the
    pattern of selective re-exporting to maintain a clean namespace while
    ensuring all necessary functionality is accessible.
"""

# ============================================================================
# ASSERTIONS MODULE - Custom assertion functions for test validation
# ============================================================================

from tests.helpers.assertions import (
    assert_json_structure,
    assert_status_code,
    assert_response_contains,
    assert_response_excludes,
    assert_valid_datetime,
    assert_valid_uuid,
    assert_error_response,
    assert_pagination,
    assert_list_length,
    assert_nested_value,
)

# ============================================================================
# DATA GENERATORS MODULE - Test data creation utilities
# ============================================================================

from tests.helpers.data_generators import (
    generate_email,
    generate_password,
    generate_uuid,
    generate_unique_string,
    generate_timestamp,
    generate_random_int,
    generate_phone_number,
    generate_address,
    generate_user_data,
    generate_auth_token,
    generate_bulk_users,
    generate_invalid_data,
)

# ============================================================================
# REQUEST BUILDERS MODULE - HTTP request construction helpers
# ============================================================================

from tests.helpers.request_builders import (
    build_get_request,
    build_post_request,
    build_put_request,
    build_delete_request,
    build_patch_request,
    build_authenticated_request,
    build_multipart_request,
    build_request_with_query_params,
    build_request_with_headers,
    build_request_with_cookies,
    RequestBuilder,
)

# ============================================================================
# RESPONSE VALIDATORS MODULE - API response validation functions
# ============================================================================

from tests.helpers.response_validators import (
    validate_response_status,
    validate_json_response,
    validate_response_schema,
    validate_success_response,
    validate_error_response,
    validate_created_response,
    validate_no_content_response,
    validate_pagination_response,
    validate_list_response,
    validate_response_headers,
    validate_content_type,
    validate_authentication_required,
    validate_forbidden_response,
    validate_not_found_response,
)

# ============================================================================
# AUTH HELPERS MODULE - Authentication and authorization testing utilities
# ============================================================================

from tests.helpers.auth_helpers import (
    create_test_user,
    create_admin_user,
    create_user_with_role,
    login_user,
    register_user,
    logout_user,
    generate_jwt_token,
    generate_expired_token,
    generate_invalid_token,
    create_auth_headers,
    create_authenticated_client,
    verify_token,
)

# ============================================================================
# DATABASE HELPERS MODULE - Database operations and transaction management
# ============================================================================

from tests.helpers.db_helpers import (
    seed_database,
    clear_database,
    create_test_tables,
    drop_test_tables,
    bulk_insert_users,
    bulk_insert_records,
    load_fixture_data,
    create_database_backup,
    restore_database_backup,
    get_record_count,
    verify_database_empty,
    create_test_transaction,
    rollback_transaction,
)

# ============================================================================
# CLIENT WRAPPERS MODULE - Enhanced test client classes
# ============================================================================

from tests.helpers.client_wrappers import (
    AuthenticatedClient,
    APITestClient,
    MultipartClient,
    WebSocketTestClient,
)

# ============================================================================
# PUBLIC API - Explicit exports for import * usage
# ============================================================================

__all__ = [
    # Assertions
    'assert_json_structure',
    'assert_status_code',
    'assert_response_contains',
    'assert_response_excludes',
    'assert_valid_datetime',
    'assert_valid_uuid',
    'assert_error_response',
    'assert_pagination',
    'assert_list_length',
    'assert_nested_value',
    
    # Data Generators
    'generate_email',
    'generate_password',
    'generate_uuid',
    'generate_unique_string',
    'generate_timestamp',
    'generate_random_int',
    'generate_phone_number',
    'generate_address',
    'generate_user_data',
    'generate_auth_token',
    'generate_bulk_users',
    'generate_invalid_data',
    
    # Request Builders
    'build_get_request',
    'build_post_request',
    'build_put_request',
    'build_delete_request',
    'build_patch_request',
    'build_authenticated_request',
    'build_multipart_request',
    'build_request_with_query_params',
    'build_request_with_headers',
    'build_request_with_cookies',
    'RequestBuilder',
    
    # Response Validators
    'validate_response_status',
    'validate_json_response',
    'validate_response_schema',
    'validate_success_response',
    'validate_error_response',
    'validate_created_response',
    'validate_no_content_response',
    'validate_pagination_response',
    'validate_list_response',
    'validate_response_headers',
    'validate_content_type',
    'validate_authentication_required',
    'validate_forbidden_response',
    'validate_not_found_response',
    
    # Auth Helpers
    'create_test_user',
    'create_admin_user',
    'create_user_with_role',
    'login_user',
    'register_user',
    'logout_user',
    'generate_jwt_token',
    'generate_expired_token',
    'generate_invalid_token',
    'create_auth_headers',
    'create_authenticated_client',
    'verify_token',
    
    # Database Helpers
    'seed_database',
    'clear_database',
    'create_test_tables',
    'drop_test_tables',
    'bulk_insert_users',
    'bulk_insert_records',
    'load_fixture_data',
    'create_database_backup',
    'restore_database_backup',
    'get_record_count',
    'verify_database_empty',
    'create_test_transaction',
    'rollback_transaction',
    
    # Client Wrappers
    'AuthenticatedClient',
    'APITestClient',
    'MultipartClient',
    'WebSocketTestClient',
]
