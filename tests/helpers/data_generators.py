"""
Test Data Generation Utilities

This module provides comprehensive utilities for generating realistic, valid test data
for common entities including users, authentication tokens, email addresses, passwords,
timestamps, and domain-specific objects. Integrates with Faker library for fake data
generation and provides factories for creating test fixtures with customizable attributes.

All functions support customization through optional parameters to enable flexible
test data creation while maintaining realistic and valid data structures.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
import uuid
import random
import string
import secrets

from faker import Faker
import jwt


# Initialize Faker instance for generating realistic fake data
faker = Faker()


def generate_email(domain: Optional[str] = None, username: Optional[str] = None) -> str:
    """
    Generate a valid email address using Faker.
    
    Args:
        domain: Optional custom domain (e.g., 'example.com'). If None, uses Faker default.
        username: Optional custom username. If None, generates random username.
    
    Returns:
        str: Valid email address in format username@domain
    
    Examples:
        >>> email = generate_email()
        >>> '@' in email
        True
        >>> custom_email = generate_email(domain='test.com', username='john')
        >>> custom_email
        'john@test.com'
    """
    if username and domain:
        return f"{username}@{domain}"
    elif domain:
        username = faker.user_name()
        return f"{username}@{domain}"
    else:
        return faker.email()


def generate_password(
    length: int = 12,
    include_uppercase: bool = True,
    include_lowercase: bool = True,
    include_digits: bool = True,
    include_special: bool = True
) -> str:
    """
    Generate a password meeting specified strength requirements.
    
    Args:
        length: Password length (minimum 8 characters)
        include_uppercase: Include uppercase letters (A-Z)
        include_lowercase: Include lowercase letters (a-z)
        include_digits: Include numeric digits (0-9)
        include_special: Include special characters (!@#$%^&*)
    
    Returns:
        str: Generated password meeting requirements
    
    Raises:
        ValueError: If length is less than 8 or no character types selected
    """
    if length < 8:
        raise ValueError("Password length must be at least 8 characters")
    
    if not any([include_uppercase, include_lowercase, include_digits, include_special]):
        raise ValueError("At least one character type must be included")
    
    # Build character set based on requirements
    char_set = ""
    required_chars = []
    
    if include_uppercase:
        char_set += string.ascii_uppercase
        required_chars.append(secrets.choice(string.ascii_uppercase))
    
    if include_lowercase:
        char_set += string.ascii_lowercase
        required_chars.append(secrets.choice(string.ascii_lowercase))
    
    if include_digits:
        char_set += string.digits
        required_chars.append(secrets.choice(string.digits))
    
    if include_special:
        special_chars = "!@#$%^&*"
        char_set += special_chars
        required_chars.append(secrets.choice(special_chars))
    
    # Ensure we have at least one of each required character type
    remaining_length = length - len(required_chars)
    if remaining_length < 0:
        remaining_length = 0
    
    # Generate remaining random characters
    random_chars = [secrets.choice(char_set) for _ in range(remaining_length)]
    
    # Combine required and random characters
    password_chars = required_chars + random_chars
    
    # Shuffle to avoid predictable patterns
    random.shuffle(password_chars)
    
    return ''.join(password_chars)


def generate_uuid() -> str:
    """
    Generate a valid UUID string.
    
    Returns:
        str: UUID string in format xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
    
    Examples:
        >>> uid = generate_uuid()
        >>> len(uid)
        36
        >>> '-' in uid
        True
    """
    return str(uuid.uuid4())


def generate_unique_string(prefix: str = "", length: int = 10) -> str:
    """
    Generate a unique identifier string with optional prefix.
    
    Args:
        prefix: Optional prefix to prepend to unique string
        length: Length of random portion (default 10)
    
    Returns:
        str: Unique string combining prefix and random characters
    
    Examples:
        >>> unique = generate_unique_string(prefix="user_")
        >>> unique.startswith("user_")
        True
    """
    random_part = ''.join(
        secrets.choice(string.ascii_lowercase + string.digits) 
        for _ in range(length)
    )
    
    if prefix:
        return f"{prefix}{random_part}"
    return random_part


def generate_timestamp(
    offset_days: int = 0,
    offset_hours: int = 0,
    offset_minutes: int = 0,
    use_utc: bool = True
) -> str:
    """
    Generate ISO format timestamp string.
    
    Args:
        offset_days: Days to add/subtract from current time (negative for past)
        offset_hours: Hours to add/subtract from current time
        offset_minutes: Minutes to add/subtract from current time
        use_utc: Use UTC time if True, local time if False
    
    Returns:
        str: ISO 8601 formatted timestamp string
    
    Examples:
        >>> timestamp = generate_timestamp()
        >>> 'T' in timestamp
        True
        >>> past_timestamp = generate_timestamp(offset_days=-7)
        >>> past_timestamp < generate_timestamp()
        True
    """
    if use_utc:
        base_time = datetime.utcnow()
    else:
        base_time = datetime.now()
    
    # Apply offsets
    delta = timedelta(days=offset_days, hours=offset_hours, minutes=offset_minutes)
    adjusted_time = base_time + delta
    
    return adjusted_time.isoformat()


def generate_random_int(min_value: int = 0, max_value: int = 100) -> int:
    """
    Generate a random integer within specified range.
    
    Args:
        min_value: Minimum value (inclusive)
        max_value: Maximum value (inclusive)
    
    Returns:
        int: Random integer between min_value and max_value
    
    Raises:
        ValueError: If min_value > max_value
    
    Examples:
        >>> num = generate_random_int(1, 10)
        >>> 1 <= num <= 10
        True
    """
    if min_value > max_value:
        raise ValueError("min_value must be less than or equal to max_value")
    
    return random.randint(min_value, max_value)


def generate_phone_number(country_code: Optional[str] = None) -> str:
    """
    Generate a valid phone number using Faker.
    
    Args:
        country_code: Optional country code to prepend (e.g., '+1' for US)
    
    Returns:
        str: Valid phone number string
    
    Examples:
        >>> phone = generate_phone_number()
        >>> len(phone) > 0
        True
        >>> phone_with_code = generate_phone_number(country_code='+1')
        >>> phone_with_code.startswith('+1')
        True
    """
    base_number = faker.phone_number()
    
    if country_code:
        # Clean existing country code if present
        if base_number.startswith('+'):
            # Remove existing country code
            parts = base_number.split(' ', 1)
            if len(parts) > 1:
                base_number = parts[1]
            else:
                base_number = parts[0][1:]
        
        return f"{country_code} {base_number}"
    
    return base_number


def generate_address(country: Optional[str] = None) -> Dict[str, str]:
    """
    Generate a valid address dictionary with street, city, state, zip, and country.
    
    Args:
        country: Optional country name (defaults to Faker's random country)
    
    Returns:
        Dict[str, str]: Address dictionary with keys: street, city, state, zip, country
    
    Examples:
        >>> address = generate_address()
        >>> 'street' in address and 'city' in address
        True
        >>> address = generate_address(country='USA')
        >>> address['country']
        'USA'
    """
    return {
        'street': faker.street_address(),
        'city': faker.city(),
        'state': faker.state(),
        'zip': faker.zipcode(),
        'country': country if country else faker.country()
    }


def generate_user_data(
    email: Optional[str] = None,
    password: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    phone: Optional[str] = None,
    include_address: bool = False,
    include_timestamps: bool = True
) -> Dict[str, Any]:
    """
    Generate a complete valid user data dictionary.
    
    Args:
        email: Optional custom email (generates random if None)
        password: Optional custom password (generates secure password if None)
        first_name: Optional custom first name (uses Faker if None)
        last_name: Optional custom last name (uses Faker if None)
        phone: Optional custom phone number (generates if None)
        include_address: Include address dictionary in user data
        include_timestamps: Include created_at and updated_at timestamps
    
    Returns:
        Dict[str, Any]: User data dictionary with email, password, name, etc.
    
    Examples:
        >>> user = generate_user_data()
        >>> 'email' in user and 'password' in user
        True
        >>> user_with_address = generate_user_data(include_address=True)
        >>> 'address' in user_with_address
        True
    """
    user_data = {
        'email': email if email else generate_email(),
        'password': password if password else generate_password(),
        'first_name': first_name if first_name else faker.first_name(),
        'last_name': last_name if last_name else faker.last_name(),
        'phone': phone if phone else generate_phone_number(),
        'username': generate_unique_string(prefix="user_", length=8),
        'id': generate_uuid()
    }
    
    if include_address:
        user_data['address'] = generate_address()
    
    if include_timestamps:
        current_time = generate_timestamp()
        user_data['created_at'] = current_time
        user_data['updated_at'] = current_time
    
    return user_data


def generate_auth_token(
    user_id: Optional[str] = None,
    email: Optional[str] = None,
    roles: Optional[List[str]] = None,
    expiry_hours: int = 24,
    secret_key: str = "test-secret-key-not-for-production",
    algorithm: str = "HS256",
    additional_claims: Optional[Dict[str, Any]] = None
) -> str:
    """
    Generate a JWT authentication token for testing.
    
    Args:
        user_id: Optional user ID (generates UUID if None)
        email: Optional email address (generates if None)
        roles: Optional list of user roles (defaults to ['user'])
        expiry_hours: Token expiration in hours (default 24)
        secret_key: Secret key for signing token (default test key)
        algorithm: JWT algorithm (default HS256)
        additional_claims: Optional dictionary of additional JWT claims
    
    Returns:
        str: Encoded JWT token string
    
    Examples:
        >>> token = generate_auth_token()
        >>> len(token) > 0
        True
        >>> token_with_role = generate_auth_token(roles=['admin'])
        >>> len(token_with_role) > 0
        True
    """
    if user_id is None:
        user_id = generate_uuid()
    
    if email is None:
        email = generate_email()
    
    if roles is None:
        roles = ['user']
    
    # Calculate expiration timestamp
    expiry_time = datetime.utcnow() + timedelta(hours=expiry_hours)
    
    # Build JWT payload
    payload = {
        'user_id': user_id,
        'email': email,
        'roles': roles,
        'exp': expiry_time,
        'iat': datetime.utcnow(),
        'nbf': datetime.utcnow()
    }
    
    # Add any additional claims
    if additional_claims:
        payload.update(additional_claims)
    
    # Encode and return token
    token = jwt.encode(payload, secret_key, algorithm=algorithm)
    
    return token


def generate_bulk_users(
    count: int = 10,
    unique_emails: bool = True,
    include_address: bool = False,
    include_timestamps: bool = True
) -> List[Dict[str, Any]]:
    """
    Generate a list of user data dictionaries for bulk testing.
    
    Args:
        count: Number of users to generate
        unique_emails: Ensure all emails are unique
        include_address: Include address for each user
        include_timestamps: Include timestamps for each user
    
    Returns:
        List[Dict[str, Any]]: List of user data dictionaries
    
    Raises:
        ValueError: If count is less than 1
    
    Examples:
        >>> users = generate_bulk_users(count=5)
        >>> len(users)
        5
        >>> all('email' in user for user in users)
        True
    """
    if count < 1:
        raise ValueError("Count must be at least 1")
    
    users = []
    used_emails = set()
    
    for i in range(count):
        # Generate unique email if required
        email = None
        if unique_emails:
            attempts = 0
            while email is None or email in used_emails:
                email = generate_email()
                attempts += 1
                # Prevent infinite loop with unique prefix after 100 attempts
                if attempts > 100:
                    email = generate_email(username=f"user_{i}_{generate_unique_string(length=6)}")
                    break
            used_emails.add(email)
        
        user = generate_user_data(
            email=email,
            include_address=include_address,
            include_timestamps=include_timestamps
        )
        users.append(user)
    
    return users


def generate_invalid_data(data_type: str = "user") -> Dict[str, Any]:
    """
    Generate intentionally invalid data for negative testing.
    
    Args:
        data_type: Type of invalid data to generate ('user', 'email', 'password', 'general')
    
    Returns:
        Dict[str, Any]: Dictionary containing various types of invalid data
    
    Examples:
        >>> invalid = generate_invalid_data('user')
        >>> 'invalid_email' in invalid
        True
        >>> invalid_pwd = generate_invalid_data('password')
        >>> 'too_short' in invalid_pwd
        True
    """
    invalid_data_map = {
        'user': {
            'invalid_email': 'not-an-email',
            'invalid_email_missing_at': 'userexample.com',
            'invalid_email_missing_domain': 'user@',
            'empty_email': '',
            'empty_password': '',
            'short_password': '123',
            'weak_password': 'password',
            'missing_first_name': None,
            'missing_last_name': None,
            'invalid_phone': '123',
            'special_char_injection': "<script>alert('xss')</script>",
            'sql_injection': "'; DROP TABLE users; --",
            'null_values': None,
            'empty_string': '',
            'whitespace_only': '   ',
            'extremely_long_string': 'x' * 10000,
            'unicode_overflow': '\u0000\uffff',
            'negative_id': -1,
            'zero_id': 0,
            'float_as_id': 3.14
        },
        'email': {
            'missing_at': 'userexample.com',
            'missing_domain': 'user@',
            'missing_username': '@example.com',
            'double_at': 'user@@example.com',
            'spaces': 'user name@example.com',
            'special_chars': 'user!#$%@example.com',
            'empty': '',
            'null': None,
            'too_long': 'x' * 100 + '@example.com'
        },
        'password': {
            'too_short': '123',
            'empty': '',
            'null': None,
            'only_letters': 'abcdefgh',
            'only_numbers': '12345678',
            'no_uppercase': 'password123!',
            'no_lowercase': 'PASSWORD123!',
            'no_numbers': 'Password!!!',
            'no_special': 'Password123',
            'whitespace_only': '        ',
            'common_password': 'password',
            'sequential': '12345678',
            'repeated': 'aaaaaaaa'
        },
        'general': {
            'null': None,
            'empty_string': '',
            'whitespace': '   ',
            'zero': 0,
            'negative': -1,
            'huge_number': 999999999999999,
            'special_chars': '!@#$%^&*()',
            'sql_injection': "'; DROP TABLE users; --",
            'xss_script': "<script>alert('xss')</script>",
            'path_traversal': '../../../etc/passwd',
            'unicode_null': '\u0000',
            'boolean_string': 'true',
            'array': ['item1', 'item2'],
            'object': {'key': 'value'}
        }
    }
    
    return invalid_data_map.get(data_type, invalid_data_map['general'])
