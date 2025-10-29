"""
Utility input validation functions for Flask application.

This module provides comprehensive validation functions for common input types including
email addresses, passwords, URLs, phone numbers, and generic data validators.

All validators follow consistent patterns:
- Return boolean True for valid inputs, False for invalid
- Handle None and empty values gracefully
- Provide detailed validation logic for edge cases
- Support international formats where applicable

Designed to support Node.js to Flask migration with functional equivalence.
"""

import html
import re
import string
from datetime import datetime
from typing import Any, List, Optional, Union
from urllib import parse


# ==============================================================================
# EMAIL VALIDATION
# ==============================================================================

def validate_email(email: Optional[str]) -> bool:
    """
    Validate email address format.
    
    Checks for:
    - Proper structure: local@domain.tld
    - Valid characters in local and domain parts
    - Presence of @ symbol and domain extension
    - Rejects whitespace and invalid formats
    
    Args:
        email: Email address string to validate
        
    Returns:
        bool: True if email is valid, False otherwise
        
    Examples:
        >>> validate_email("user@example.com")
        True
        >>> validate_email("invalid@")
        False
    """
    if not email or not isinstance(email, str):
        return False
    
    # Trim whitespace
    email = email.strip()
    
    # Check for empty after strip
    if not email:
        return False
    
    # Standard email regex pattern
    # Allows: alphanumeric, dots, underscores, percent, plus, hyphen in local part
    # Allows: alphanumeric, dots, hyphen in domain
    # Requires: at least 2 letter TLD
    email_pattern = re.compile(
        r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    )
    
    return email_pattern.match(email) is not None


def normalize_email(email: str) -> str:
    """
    Normalize email address to lowercase for consistent comparison.
    
    Args:
        email: Email address to normalize
        
    Returns:
        str: Lowercase email address
    """
    if not email:
        return ""
    return email.lower().strip()


# ==============================================================================
# PASSWORD VALIDATION
# ==============================================================================

def validate_password_strength(password: Optional[str], min_length: int = 8, max_length: int = 128) -> bool:
    """
    Validate password meets strength requirements.
    
    Requirements:
    - Minimum length (default 8 characters)
    - Maximum length (default 128 characters)
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character
    
    Args:
        password: Password string to validate
        min_length: Minimum password length (default 8)
        max_length: Maximum password length (default 128)
        
    Returns:
        bool: True if password meets all requirements, False otherwise
        
    Examples:
        >>> validate_password_strength("Passw0rd!")
        True
        >>> validate_password_strength("weak")
        False
    """
    if not password or not isinstance(password, str):
        return False
    
    # Check length constraints
    if len(password) < min_length or len(password) > max_length:
        return False
    
    # Check for required character types
    has_upper = any(c in string.ascii_uppercase for c in password)
    has_lower = any(c in string.ascii_lowercase for c in password)
    has_digit = any(c in string.digits for c in password)
    has_special = any(c in string.punctuation for c in password)
    
    return all([has_upper, has_lower, has_digit, has_special])


def check_password_pattern_weakness(password: str) -> bool:
    """
    Check if password contains common weak patterns.
    
    Detects:
    - Sequential characters (abc, 123)
    - Repeated characters (aaa, 111)
    - Common dictionary words (password, admin, welcome)
    - Keyboard patterns (qwerty)
    
    Args:
        password: Password to check
        
    Returns:
        bool: True if weak pattern detected, False if no weak patterns
    """
    if not password:
        return True
    
    password_lower = password.lower()
    
    # Common dictionary words
    common_words = ["password", "welcome", "admin", "user", "test", "login", "master"]
    if any(word in password_lower for word in common_words):
        return True
    
    # Sequential patterns
    if any(seq in password_lower for seq in ["abc", "123", "qwerty"]):
        return True
    
    # Repeated characters (3 or more)
    if re.search(r'(.)\1{2,}', password):
        return True
    
    return False


# ==============================================================================
# URL VALIDATION
# ==============================================================================

def validate_url(url: Optional[str]) -> bool:
    """
    Validate URL format.
    
    Checks for:
    - Valid scheme (http or https)
    - Valid domain/netloc
    - Proper URL structure
    
    Args:
        url: URL string to validate
        
    Returns:
        bool: True if URL is valid, False otherwise
        
    Examples:
        >>> validate_url("https://example.com")
        True
        >>> validate_url("example.com")
        False
    """
    if not url or not isinstance(url, str):
        return False
    
    # Trim whitespace
    url = url.strip()
    
    if not url:
        return False
    
    try:
        parsed = parse.urlparse(url)
        
        # Must have valid scheme (http or https)
        if parsed.scheme not in ['http', 'https']:
            return False
        
        # Must have non-empty netloc (domain)
        if not parsed.netloc:
            return False
        
        # URL must contain '//' after scheme
        if '//' not in url:
            return False
        
        return True
    except Exception:
        return False


# ==============================================================================
# PHONE NUMBER VALIDATION
# ==============================================================================

def validate_phone_number(phone: Optional[str], min_digits: int = 10, max_digits: int = 15) -> bool:
    """
    Validate phone number format.
    
    Accepts various formats:
    - US: (555) 123-4567, 555-123-4567, 5551234567
    - International: +1-555-123-4567, +44 20 7123 4567
    
    Checks:
    - Contains sufficient digits (10-15 typical range)
    - No letters (except extension markers: ext, extension, x)
    - Valid formatting characters only
    
    Args:
        phone: Phone number string to validate
        min_digits: Minimum number of digits required (default 10)
        max_digits: Maximum number of digits allowed (default 15)
        
    Returns:
        bool: True if phone number is valid, False otherwise
        
    Examples:
        >>> validate_phone_number("555-123-4567")
        True
        >>> validate_phone_number("123")
        False
    """
    if not phone or not isinstance(phone, str):
        return False
    
    # Remove extension markers before digit validation
    phone_no_ext = re.sub(r'\s*(ext|extension|x)\s*\d+', '', phone, flags=re.IGNORECASE)
    
    # Extract only digits
    digits = re.sub(r'\D', '', phone_no_ext)
    
    # Check digit count
    if len(digits) < min_digits or len(digits) > max_digits:
        return False
    
    # Check for invalid letters (excluding extension markers)
    # Remove all valid phone formatting characters and digits
    cleaned = re.sub(r'[\d\s\-\(\)\+\.\[\]]', '', phone_no_ext)
    # Remove valid extension markers
    cleaned = re.sub(r'(ext|extension|x)', '', cleaned, flags=re.IGNORECASE)
    
    # If anything remains, it's invalid
    if cleaned.strip():
        return False
    
    # Check for obviously invalid patterns
    if digits.startswith('000') or digits.startswith('111') or digits.startswith('0'):
        return False
    
    return True


def normalize_phone_number(phone: str) -> str:
    """
    Normalize phone number to digits only.
    
    Args:
        phone: Phone number to normalize
        
    Returns:
        str: Phone number with only digits
        
    Examples:
        >>> normalize_phone_number("+1 (555) 123-4567")
        "15551234567"
    """
    if not phone:
        return ""
    return re.sub(r'\D', '', phone)


def format_phone_number(phone: str, format_type: str = "US") -> str:
    """
    Format phone number to standard format.
    
    Args:
        phone: Phone number string (digits only or formatted)
        format_type: Format type ("US" for XXX-XXX-XXXX)
        
    Returns:
        str: Formatted phone number
    """
    digits = normalize_phone_number(phone)
    
    if format_type == "US" and len(digits) == 10:
        return f"{digits[0:3]}-{digits[3:6]}-{digits[6:10]}"
    elif format_type == "US" and len(digits) == 11 and digits.startswith('1'):
        return f"+1-{digits[1:4]}-{digits[4:7]}-{digits[7:11]}"
    
    return digits


# ==============================================================================
# GENERIC VALIDATORS
# ==============================================================================

def is_empty(value: Any) -> bool:
    """
    Check if value is empty or None.
    
    Considers empty: None, "", empty whitespace, empty collections
    
    Args:
        value: Value to check
        
    Returns:
        bool: True if value is empty, False otherwise
    """
    if value is None:
        return True
    
    if isinstance(value, str):
        return not value.strip()
    
    if isinstance(value, (list, dict, tuple, set)):
        return len(value) == 0
    
    return False


def validate_string_length(value: Optional[str], min_length: int, max_length: int) -> bool:
    """
    Validate string length is within specified range.
    
    Args:
        value: String to validate
        min_length: Minimum length (inclusive)
        max_length: Maximum length (inclusive)
        
    Returns:
        bool: True if length is valid, False otherwise
    """
    if not isinstance(value, str):
        return False
    
    return min_length <= len(value) <= max_length


def validate_against_pattern(value: Optional[str], pattern: str) -> bool:
    """
    Validate string matches regex pattern.
    
    Args:
        value: String to validate
        pattern: Regex pattern string
        
    Returns:
        bool: True if value matches pattern, False otherwise
    """
    if not isinstance(value, str) or not pattern:
        return False
    
    try:
        compiled_pattern = re.compile(pattern)
        return compiled_pattern.match(value) is not None
    except re.error:
        return False


def validate_in_list(value: Any, allowed_values: List[Any]) -> bool:
    """
    Validate value is in allowed values list.
    
    Args:
        value: Value to check
        allowed_values: List of allowed values
        
    Returns:
        bool: True if value is in list, False otherwise
    """
    return value in allowed_values


def validate_numeric_range(value: Union[int, float], min_value: Union[int, float], max_value: Union[int, float]) -> bool:
    """
    Validate numeric value is within specified range.
    
    Args:
        value: Numeric value to validate
        min_value: Minimum value (inclusive)
        max_value: Maximum value (inclusive)
        
    Returns:
        bool: True if value is in range, False otherwise
    """
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    
    return min_value <= value <= max_value


def validate_date_in_future(date: datetime) -> bool:
    """
    Validate date is in the future.
    
    Args:
        date: datetime object to validate
        
    Returns:
        bool: True if date is in future, False otherwise
    """
    if not isinstance(date, datetime):
        return False
    
    return date > datetime.now()


def validate_username(username: Optional[str]) -> bool:
    """
    Validate username format.
    
    Requirements:
    - 3-20 characters
    - Alphanumeric and underscore only
    
    Args:
        username: Username to validate
        
    Returns:
        bool: True if valid username, False otherwise
    """
    if not username or not isinstance(username, str):
        return False
    
    username_pattern = re.compile(r'^[a-zA-Z0-9_]{3,20}$')
    return username_pattern.match(username) is not None


# ==============================================================================
# TYPE VALIDATORS
# ==============================================================================

def validate_type_string(value: Any) -> bool:
    """Validate value is a string."""
    return isinstance(value, str)


def validate_type_integer(value: Any) -> bool:
    """Validate value is an integer (not boolean)."""
    return isinstance(value, int) and not isinstance(value, bool)


def validate_type_float(value: Any) -> bool:
    """Validate value is a float or int."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def validate_type_boolean(value: Any) -> bool:
    """Validate value is a boolean."""
    return isinstance(value, bool)


def validate_type_list(value: Any) -> bool:
    """Validate value is a list."""
    return isinstance(value, list)


def validate_type_dict(value: Any) -> bool:
    """Validate value is a dictionary."""
    return isinstance(value, dict)


# ==============================================================================
# ADDITIONAL VALIDATION FUNCTIONS
# ==============================================================================

def is_common_password(password: Optional[str]) -> bool:
    """
    Check if password is a commonly used weak password.
    
    This is an alias for check_password_pattern_weakness for API compatibility.
    
    Args:
        password: Password to check
        
    Returns:
        bool: True if password is common/weak, False otherwise
    """
    return check_password_pattern_weakness(password)


def normalize_url(url: str) -> str:
    """
    Normalize URL to standard format.
    
    Args:
        url: URL to normalize
        
    Returns:
        str: Normalized URL
    """
    if not url:
        return ""
    
    # Parse and reconstruct URL to normalize it
    parsed = parse.urlparse(url)
    
    # Ensure scheme is lowercase
    scheme = parsed.scheme.lower() if parsed.scheme else ""
    
    # Ensure netloc is lowercase
    netloc = parsed.netloc.lower() if parsed.netloc else ""
    
    # Reconstruct normalized URL
    normalized = parse.urlunparse((
        scheme,
        netloc,
        parsed.path,
        parsed.params,
        parsed.query,
        parsed.fragment
    ))
    
    return normalized


def validate_not_empty(value: Any) -> bool:
    """
    Validate that a value is not empty.
    
    This is an alias for the inverse of is_empty for API compatibility.
    
    Args:
        value: Value to check
        
    Returns:
        bool: True if not empty, False if empty
    """
    return not is_empty(value)


def validate_type(value: Any, expected_type: type) -> bool:
    """
    Validate that value matches expected type.
    
    Args:
        value: Value to validate
        expected_type: Expected Python type
        
    Returns:
        bool: True if value is of expected type, False otherwise
    """
    return isinstance(value, expected_type)


def validate_length(value: Optional[str], min_length: int = 0, max_length: int = None) -> bool:
    """
    Validate string length is within specified bounds.
    
    This is an alias for validate_string_length for API compatibility.
    
    Args:
        value: String to validate
        min_length: Minimum length (inclusive)
        max_length: Maximum length (inclusive), None for no max
        
    Returns:
        bool: True if length is valid, False otherwise
    """
    if value is None:
        return False
    
    if not isinstance(value, str):
        return False
    
    if len(value) < min_length:
        return False
    
    if max_length is not None and len(value) > max_length:
        return False
    
    return True


def validate_range(value: Union[int, float], min_value: Union[int, float] = None, max_value: Union[int, float] = None) -> bool:
    """
    Validate numeric value is within specified range.
    
    This is an alias for validate_numeric_range for API compatibility.
    
    Args:
        value: Numeric value to validate
        min_value: Minimum value (inclusive), None for no min
        max_value: Maximum value (inclusive), None for no max
        
    Returns:
        bool: True if value is in range, False otherwise
    """
    if not isinstance(value, (int, float)):
        return False
    
    if min_value is not None and value < min_value:
        return False
    
    if max_value is not None and value > max_value:
        return False
    
    return True


def validate_pattern(value: Optional[str], pattern: str) -> bool:
    """
    Validate string matches regex pattern.
    
    This is an alias for validate_against_pattern for API compatibility.
    
    Args:
        value: String to validate
        pattern: Regular expression pattern
        
    Returns:
        bool: True if value matches pattern, False otherwise
    """
    return validate_against_pattern(value, pattern)


# ==============================================================================
# XSS PREVENTION
# ==============================================================================

def sanitize_html(value: Optional[str]) -> Optional[str]:
    """
    Sanitize HTML/JavaScript to prevent XSS attacks.
    
    Escapes HTML special characters (<, >, &, ", ') to prevent
    injection of malicious scripts.
    
    Args:
        value: String that may contain HTML/JavaScript
        
    Returns:
        str: Sanitized string with HTML entities escaped, or None if input is None
        
    Examples:
        >>> sanitize_html('<script>alert("XSS")</script>')
        '&lt;script&gt;alert(&quot;XSS&quot;)&lt;/script&gt;'
        >>> sanitize_html('Normal text')
        'Normal text'
    """
    if value is None:
        return None
    
    if not isinstance(value, str):
        return value
    
    # Use html.escape to convert special characters to HTML entities
    return html.escape(value, quote=True)
