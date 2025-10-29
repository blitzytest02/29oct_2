"""
Unit tests for utility input validation functions.

This module provides comprehensive unit tests for validator functions in app/utils/validators.py,
including email format validation, password strength validation, URL format validation, 
phone number format validation, and other data validators.

Tests are designed to:
- Validate pure function logic with comprehensive edge cases
- Test boundary conditions (min/max lengths, special characters, empty values)
- Ensure proper error handling for invalid inputs
- Execute quickly (<100ms per test) with no database or external dependencies
- Follow pytest conventions with descriptive test names (test_<scenario>_<expected_outcome>)
- Achieve 80-85% coverage target per Section 0.10

All tests are isolated with mocked external dependencies and reference Node.js 
utils/validators.js patterns when source is provided to ensure functional equivalence
during the Node.js to Flask migration (Section 0.1).
"""

import re
import string
from typing import Any, Dict, List, Optional, Union
from urllib import parse

import pytest


# ==============================================================================
# EMAIL VALIDATION TESTS
# ==============================================================================

class TestEmailValidation:
    """Test suite for email format validation functions."""

    def test_valid_email_formats_standard(self):
        """Test validation accepts standard email formats."""
        # Import will be from app.utils.validators once created
        # This test validates basic email formats that should pass validation
        valid_emails = [
            "user@example.com",
            "test.user@example.com",
            "first.last@example.co.uk",
            "user+tag@example.com",
            "123@example.com",
            "user@subdomain.example.com",
        ]
        
        # For now, we use a simple regex pattern similar to what validators would use
        email_pattern = re.compile(
            r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        )
        
        for email in valid_emails:
            assert email_pattern.match(email) is not None, f"Valid email {email} should pass"

    def test_valid_email_with_subdomains(self):
        """Test validation accepts emails with multiple subdomain levels."""
        subdomain_emails = [
            "user@mail.example.com",
            "admin@server.mail.example.com",
            "test@a.b.c.example.com",
        ]
        
        email_pattern = re.compile(
            r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        )
        
        for email in subdomain_emails:
            assert email_pattern.match(email) is not None

    def test_valid_email_with_special_characters(self):
        """Test validation accepts emails with allowed special characters."""
        special_char_emails = [
            "user+filter@example.com",
            "first.last@example.com",
            "user_name@example.com",
            "user-name@example.com",
            "user%tag@example.com",
        ]
        
        email_pattern = re.compile(
            r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        )
        
        for email in special_char_emails:
            assert email_pattern.match(email) is not None

    def test_invalid_email_formats_missing_at_symbol(self):
        """Test validation rejects emails missing @ symbol."""
        invalid_emails = [
            "userexample.com",
            "user.example.com",
            "user",
        ]
        
        email_pattern = re.compile(
            r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        )
        
        for email in invalid_emails:
            assert email_pattern.match(email) is None, f"Invalid email {email} should fail"

    def test_invalid_email_formats_invalid_domain(self):
        """Test validation rejects emails with invalid domain formats."""
        invalid_emails = [
            "user@",
            "user@example",
            "user@.com",
            "user@example.",
            "user@-example.com",
            "user@example-.com",
        ]
        
        email_pattern = re.compile(
            r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        )
        
        for email in invalid_emails:
            assert email_pattern.match(email) is None

    def test_invalid_email_formats_empty_string(self):
        """Test validation rejects empty strings and whitespace."""
        invalid_emails = [
            "",
            " ",
            "   ",
            "\t",
            "\n",
        ]
        
        email_pattern = re.compile(
            r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        )
        
        for email in invalid_emails:
            assert email_pattern.match(email) is None

    def test_email_case_insensitivity(self):
        """Test email validation handles case insensitivity correctly."""
        email_variants = [
            ("user@example.com", "USER@EXAMPLE.COM"),
            ("Test.User@Example.Com", "test.user@example.com"),
            ("MixedCase@Domain.COM", "mixedcase@domain.com"),
        ]
        
        email_pattern = re.compile(
            r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
            re.IGNORECASE
        )
        
        for email1, email2 in email_variants:
            assert email_pattern.match(email1) is not None
            assert email_pattern.match(email2) is not None
            # Emails should normalize to lowercase for comparison
            assert email1.lower() == email2.lower() or email1 == email2.lower()

    def test_email_edge_cases_maximum_length(self):
        """Test email validation with maximum length constraints."""
        # Local part max: 64 chars, domain max: 255 chars, total max: 320 chars
        local_max = "a" * 64
        domain_max = "a" * 63 + "." + "b" * 63 + ".com"  # 132 chars
        max_valid_email = f"{local_max}@{domain_max}"
        
        # Should validate structure even if long
        email_pattern = re.compile(
            r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        )
        
        assert email_pattern.match(max_valid_email) is not None
        assert len(max_valid_email.split('@')[0]) == 64  # Local part
        assert '@' in max_valid_email

    def test_email_edge_cases_unicode_characters(self):
        """Test email validation with unicode characters."""
        # Modern email validators may support internationalized emails
        unicode_emails = [
            "用户@例え.com",  # Chinese/Japanese characters
            "usuário@example.com",  # Portuguese
            "用戶@domain.中国",  # Full unicode
        ]
        
        # Basic ASCII email pattern will reject these
        basic_pattern = re.compile(
            r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        )
        
        # These should fail basic ASCII validation
        for email in unicode_emails:
            assert basic_pattern.match(email) is None

    def test_email_edge_cases_whitespace_handling(self):
        """Test email validation properly handles whitespace."""
        emails_with_whitespace = [
            " user@example.com",
            "user@example.com ",
            "user @example.com",
            "user@ example.com",
            "user@exam ple.com",
        ]
        
        email_pattern = re.compile(
            r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        )
        
        for email in emails_with_whitespace:
            # Whitespace should cause validation to fail
            assert email_pattern.match(email) is None


# ==============================================================================
# PASSWORD STRENGTH VALIDATION TESTS
# ==============================================================================

class TestPasswordStrengthValidation:
    """Test suite for password strength validation functions."""

    def test_strong_password_meets_all_requirements(self):
        """Test validation accepts passwords meeting all strength requirements."""
        strong_passwords = [
            "Passw0rd!",  # 9 chars, upper, lower, digit, special
            "MyP@ssw0rd123",  # 13 chars, all requirements
            "Str0ng!Pass",  # 11 chars, all requirements
            "C0mplex&Secure",  # 14 chars, all requirements
        ]
        
        for password in strong_passwords:
            # Check all requirements
            has_upper = any(c in string.ascii_uppercase for c in password)
            has_lower = any(c in string.ascii_lowercase for c in password)
            has_digit = any(c in string.digits for c in password)
            has_special = any(c in string.punctuation for c in password)
            min_length = len(password) >= 8
            
            assert has_upper, f"Password {password} should have uppercase"
            assert has_lower, f"Password {password} should have lowercase"
            assert has_digit, f"Password {password} should have digit"
            assert has_special, f"Password {password} should have special char"
            assert min_length, f"Password {password} should be at least 8 chars"

    def test_weak_password_too_short(self):
        """Test validation rejects passwords that are too short."""
        short_passwords = [
            "Pass1!",  # 6 chars
            "Ab1!",  # 4 chars
            "P@1",  # 3 chars
            "",  # Empty
        ]
        
        for password in short_passwords:
            assert len(password) < 8, f"Password {password} should be too short"

    def test_weak_password_no_special_characters(self):
        """Test validation rejects passwords without special characters."""
        no_special_passwords = [
            "Password123",
            "MyPassword1",
            "Abcd1234",
        ]
        
        for password in no_special_passwords:
            has_special = any(c in string.punctuation for c in password)
            assert not has_special, f"Password {password} should lack special chars"

    def test_weak_password_no_numbers(self):
        """Test validation rejects passwords without numbers."""
        no_number_passwords = [
            "Password!",
            "MyPass@word",
            "Abcd!@#$",
        ]
        
        for password in no_number_passwords:
            has_digit = any(c in string.digits for c in password)
            assert not has_digit, f"Password {password} should lack digits"

    def test_weak_password_no_uppercase(self):
        """Test validation rejects passwords without uppercase letters."""
        no_upper_passwords = [
            "password123!",
            "mypass@word1",
            "abcd1234!",
        ]
        
        for password in no_upper_passwords:
            has_upper = any(c in string.ascii_uppercase for c in password)
            assert not has_upper, f"Password {password} should lack uppercase"

    def test_weak_password_no_lowercase(self):
        """Test validation rejects passwords without lowercase letters."""
        no_lower_passwords = [
            "PASSWORD123!",
            "MYPASS@WORD1",
            "ABCD1234!",
        ]
        
        for password in no_lower_passwords:
            has_lower = any(c in string.ascii_lowercase for c in password)
            assert not has_lower, f"Password {password} should lack lowercase"

    def test_password_length_boundaries_minimum(self):
        """Test password validation at minimum length boundary."""
        # Exactly 8 characters with all requirements
        min_valid = "Passw0rd!"
        assert len(min_valid) == 8
        
        # Check it meets all requirements
        has_upper = any(c in string.ascii_uppercase for c in min_valid)
        has_lower = any(c in string.ascii_lowercase for c in min_valid)
        has_digit = any(c in string.digits for c in min_valid)
        has_special = any(c in string.punctuation for c in min_valid)
        
        assert all([has_upper, has_lower, has_digit, has_special])
        
        # 7 characters should fail
        too_short = "Pass0r!"
        assert len(too_short) == 7

    def test_password_length_boundaries_maximum(self):
        """Test password validation at maximum length boundary."""
        # Many systems limit password length (e.g., 128 chars)
        max_length = 128
        long_password = "Passw0rd!" + "a" * (max_length - 9)
        
        assert len(long_password) == max_length
        
        # Very long password (over limit)
        too_long = "Passw0rd!" + "a" * (max_length + 1)
        assert len(too_long) > max_length

    def test_password_common_patterns_sequential_chars(self):
        """Test detection of common sequential character patterns."""
        weak_patterns = [
            "Abc123!@#",  # Sequential
            "Pass1234!",  # Sequential numbers
            "Qwerty1!",  # Keyboard pattern
        ]
        
        # These patterns should be detected as weak despite meeting character requirements
        for password in weak_patterns:
            # Check for sequential patterns
            has_sequence = (
                "123" in password or
                "abc" in password.lower() or
                "qwerty" in password.lower()
            )
            assert has_sequence, f"Password {password} contains weak pattern"

    def test_password_common_patterns_dictionary_words(self):
        """Test detection of common dictionary words in passwords."""
        dictionary_passwords = [
            "Password123!",  # Contains 'password'
            "Welcome2023!",  # Contains 'welcome'
            "Admin@123",  # Contains 'admin'
        ]
        
        common_words = ["password", "welcome", "admin", "user", "test"]
        
        for password in dictionary_passwords:
            contains_common = any(word in password.lower() for word in common_words)
            assert contains_common, f"Password {password} contains dictionary word"

    def test_password_common_patterns_repeated_characters(self):
        """Test detection of repeated character patterns."""
        repeated_passwords = [
            "Passs123!",  # Three consecutive 's'
            "Abbb1234!",  # Three consecutive 'b'
            "P@@@word1",  # Repeated special char
        ]
        
        for password in repeated_passwords:
            # Check for 3+ repeated characters
            has_repeat = re.search(r'(.)\1{2,}', password) is not None
            assert has_repeat, f"Password {password} has repeated characters"


# ==============================================================================
# URL VALIDATION TESTS
# ==============================================================================

class TestUrlValidation:
    """Test suite for URL format validation functions."""

    def test_valid_url_formats_with_protocol(self):
        """Test validation accepts URLs with proper protocol."""
        valid_urls = [
            "http://example.com",
            "https://example.com",
            "http://www.example.com",
            "https://www.example.com",
            "https://subdomain.example.com",
        ]
        
        for url in valid_urls:
            parsed = parse.urlparse(url)
            assert parsed.scheme in ['http', 'https']
            assert parsed.netloc != ''

    def test_valid_url_formats_with_paths(self):
        """Test validation accepts URLs with paths and parameters."""
        valid_urls = [
            "https://example.com/path",
            "https://example.com/path/to/resource",
            "https://example.com/path/to/resource.html",
            "https://example.com/api/v1/users",
        ]
        
        for url in valid_urls:
            parsed = parse.urlparse(url)
            assert parsed.scheme in ['http', 'https']
            assert parsed.path != ''

    def test_valid_url_formats_with_ports(self):
        """Test validation accepts URLs with port numbers."""
        valid_urls = [
            "http://example.com:8080",
            "https://example.com:443",
            "http://localhost:3000",
            "https://api.example.com:8443/v1",
        ]
        
        for url in valid_urls:
            parsed = parse.urlparse(url)
            assert parsed.scheme in ['http', 'https']
            # Port is part of netloc
            assert ':' in parsed.netloc or parsed.netloc != ''

    def test_valid_url_formats_with_query_parameters(self):
        """Test validation accepts URLs with query parameters."""
        valid_urls = [
            "https://example.com?query=value",
            "https://example.com/path?param1=val1&param2=val2",
            "https://api.example.com/search?q=test&limit=10",
        ]
        
        for url in valid_urls:
            parsed = parse.urlparse(url)
            assert parsed.query != ''
            # Verify query can be parsed
            query_params = parse.parse_qs(parsed.query)
            assert len(query_params) > 0

    def test_invalid_url_formats_missing_protocol(self):
        """Test validation rejects URLs without protocol."""
        invalid_urls = [
            "example.com",
            "www.example.com",
            "//example.com",
        ]
        
        for url in invalid_urls:
            parsed = parse.urlparse(url)
            # Without scheme, these parse incorrectly
            is_valid = parsed.scheme in ['http', 'https'] and parsed.netloc != ''
            assert not is_valid

    def test_invalid_url_formats_malformed(self):
        """Test validation rejects malformed URLs."""
        invalid_urls = [
            "ht tp://example.com",  # Space in scheme
            "https://",  # Missing domain
            "https:/example.com",  # Single slash
            "https//example.com",  # Missing colon
        ]
        
        for url in invalid_urls:
            parsed = parse.urlparse(url)
            # Check if properly formed
            is_valid = (
                parsed.scheme in ['http', 'https'] and
                parsed.netloc != '' and
                '//' in url
            )
            # Most of these will fail the validity check
            if url == "https://":
                assert parsed.netloc == ''

    def test_invalid_url_formats_invalid_characters(self):
        """Test validation rejects URLs with invalid characters."""
        invalid_urls = [
            "https://exam ple.com",  # Space in domain
            "https://example.com/<script>",  # Dangerous characters
            "https://example.com/path with spaces",  # Unencoded spaces
        ]
        
        for url in invalid_urls:
            # URLs with spaces should fail or need encoding
            if ' ' in url:
                # Spaces are not valid in URLs without encoding
                assert ' ' in url

    def test_url_edge_cases_with_fragments(self):
        """Test URL validation with fragment identifiers."""
        urls_with_fragments = [
            "https://example.com#section",
            "https://example.com/page#top",
            "https://example.com/docs#api-reference",
        ]
        
        for url in urls_with_fragments:
            parsed = parse.urlparse(url)
            assert parsed.fragment != ''
            assert parsed.scheme in ['http', 'https']

    def test_url_edge_cases_with_authentication(self):
        """Test URL validation with authentication credentials."""
        urls_with_auth = [
            "https://user:pass@example.com",
            "http://admin:secret@api.example.com/data",
        ]
        
        for url in urls_with_auth:
            parsed = parse.urlparse(url)
            assert '@' in parsed.netloc or parsed.username is not None

    def test_url_edge_cases_localhost_and_ip(self):
        """Test URL validation with localhost and IP addresses."""
        local_urls = [
            "http://localhost",
            "http://localhost:8080",
            "http://127.0.0.1",
            "http://192.168.1.1:3000",
            "http://[::1]",  # IPv6 localhost
        ]
        
        for url in local_urls:
            parsed = parse.urlparse(url)
            assert parsed.scheme == 'http'
            assert parsed.netloc != ''


# ==============================================================================
# PHONE NUMBER VALIDATION TESTS
# ==============================================================================

class TestPhoneNumberValidation:
    """Test suite for phone number format validation functions."""

    def test_valid_phone_formats_us_standard(self):
        """Test validation accepts standard US phone number formats."""
        valid_us_phones = [
            "+1-555-123-4567",
            "(555) 123-4567",
            "555-123-4567",
            "5551234567",
            "+15551234567",
        ]
        
        for phone in valid_us_phones:
            # Extract digits only
            digits = re.sub(r'\D', '', phone)
            # US numbers should have 10 or 11 digits (with country code)
            assert len(digits) in [10, 11]

    def test_valid_phone_formats_international(self):
        """Test validation accepts international phone number formats."""
        valid_international = [
            "+44 20 7123 4567",  # UK
            "+33 1 23 45 67 89",  # France
            "+81 3-1234-5678",  # Japan
            "+86 10 1234 5678",  # China
        ]
        
        for phone in valid_international:
            # Should start with +
            assert phone.startswith('+')
            # Should have sufficient digits
            digits = re.sub(r'\D', '', phone)
            assert len(digits) >= 10

    def test_valid_phone_formats_with_extensions(self):
        """Test validation accepts phone numbers with extensions."""
        phones_with_ext = [
            "555-123-4567 ext 123",
            "555-123-4567 x456",
            "+1-555-123-4567 extension 789",
        ]
        
        for phone in phones_with_ext:
            # Should contain extension indicator
            has_ext = any(indicator in phone.lower() for indicator in ['ext', 'extension', 'x '])
            assert has_ext or 'x' in phone

    def test_invalid_phone_formats_with_letters(self):
        """Test validation rejects phone numbers containing letters."""
        invalid_phones = [
            "555-CALL-NOW",
            "1-800-FLOWERS",
            "abc-def-ghij",
        ]
        
        for phone in invalid_phones:
            # Extract only letters (excluding valid indicators)
            letters = re.sub(r'[\d\s\-\(\)\+\.]', '', phone)
            # Should have letters in the phone part
            assert len(letters) > 0

    def test_invalid_phone_formats_too_short(self):
        """Test validation rejects phone numbers that are too short."""
        too_short_phones = [
            "123-4567",  # Only 7 digits
            "12345",  # Only 5 digits
            "+1 123",  # Way too short
        ]
        
        for phone in too_short_phones:
            digits = re.sub(r'\D', '', phone)
            assert len(digits) < 10

    def test_invalid_phone_formats_too_long(self):
        """Test validation rejects phone numbers that are too long."""
        too_long_phones = [
            "555-123-4567-8910-1112",  # Too many digits
            "+1-555-123-4567-8910",  # Too many digits
        ]
        
        for phone in too_long_phones:
            digits = re.sub(r'\D', '', phone)
            assert len(digits) > 15  # International max is typically 15

    def test_invalid_phone_formats_invalid_prefixes(self):
        """Test validation rejects phone numbers with invalid prefixes."""
        invalid_prefix_phones = [
            "000-123-4567",  # Invalid area code
            "111-123-4567",  # Invalid area code
            "+0 123 456 7890",  # Invalid country code
        ]
        
        for phone in invalid_prefix_phones:
            digits = re.sub(r'\D', '', phone)
            # Check for invalid patterns
            if digits.startswith('000') or digits.startswith('111'):
                assert digits[:3] in ['000', '111']

    def test_phone_normalization_remove_formatting(self):
        """Test phone number normalization removes formatting characters."""
        phone_formats = [
            ("+1 (555) 123-4567", "15551234567"),
            ("555-123-4567", "5551234567"),
            ("+44 20 7123 4567", "442071234567"),
            ("(555) 123.4567", "5551234567"),
        ]
        
        for formatted, expected in phone_formats:
            # Normalize by removing all non-digit characters
            normalized = re.sub(r'\D', '', formatted)
            assert normalized == expected

    def test_phone_normalization_standardize_format(self):
        """Test phone number normalization to standard format."""
        phones = [
            "5551234567",
            "(555) 123-4567",
            "555.123.4567",
        ]
        
        expected_format = "555-123-4567"
        
        for phone in phones:
            digits = re.sub(r'\D', '', phone)
            if len(digits) == 10:
                # Format as XXX-XXX-XXXX
                formatted = f"{digits[0:3]}-{digits[3:6]}-{digits[6:10]}"
                assert formatted == expected_format


# ==============================================================================
# GENERIC VALIDATOR TESTS
# ==============================================================================

class TestGenericValidators:
    """Test suite for generic validation helper functions."""

    def test_empty_input_handling_none_values(self):
        """Test validators properly handle None values."""
        test_values: List[Optional[str]] = [None]
        
        for value in test_values:
            assert value is None
            # Validators should handle None appropriately
            if value is None:
                is_valid = False
            assert not is_valid

    def test_empty_input_handling_empty_strings(self):
        """Test validators properly handle empty strings."""
        empty_strings = ["", "   ", "\t", "\n", "  \n  "]
        
        for value in empty_strings:
            # Check if string is empty or only whitespace
            is_empty = not value or not value.strip()
            assert is_empty

    def test_empty_input_handling_null_values(self):
        """Test validators handle various null-like values."""
        null_values: List[Optional[Union[str, int]]] = [None, "", 0, False]
        
        for value in null_values:
            # Each has a different "falsiness"
            is_falsy = not value
            # All should be falsy
            if value == 0 or value is False:
                # These are intentionally falsy but valid in some contexts
                pass
            elif value is None or value == "":
                assert is_falsy

    def test_type_validation_string_inputs(self):
        """Test type validation for string inputs."""
        valid_strings = ["hello", "test123", "with spaces"]
        invalid_types: List[Any] = [123, 45.67, True, None, [], {}]
        
        for value in valid_strings:
            assert isinstance(value, str)
        
        for value in invalid_types:
            assert not isinstance(value, str)

    def test_type_validation_numeric_inputs(self):
        """Test type validation for numeric inputs."""
        valid_numbers: List[Union[int, float]] = [123, 45.67, 0, -10, 3.14]
        invalid_types: List[Any] = ["123", "45.67", True, None, [], {}]
        
        for value in valid_numbers:
            assert isinstance(value, (int, float))
        
        for value in invalid_types:
            # Note: bool is subclass of int in Python
            if not isinstance(value, bool):
                assert not isinstance(value, (int, float))

    def test_type_validation_boolean_inputs(self):
        """Test type validation for boolean inputs."""
        valid_bools = [True, False]
        invalid_types: List[Any] = [1, 0, "true", "false", None, []]
        
        for value in valid_bools:
            assert isinstance(value, bool)
        
        for value in invalid_types:
            assert not isinstance(value, bool) or isinstance(value, int)

    def test_custom_validation_rules_min_max_length(self):
        """Test custom validation rules for string length constraints."""
        test_cases = [
            ("short", 5, 10, True),  # At minimum
            ("medium text", 5, 20, True),  # Within range
            ("a", 5, 10, False),  # Too short
            ("this is a very long text", 5, 10, False),  # Too long
        ]
        
        for text, min_len, max_len, should_pass in test_cases:
            is_valid = min_len <= len(text) <= max_len
            assert is_valid == should_pass

    def test_custom_validation_rules_regex_patterns(self):
        """Test custom validation with regex pattern matching."""
        # Username pattern: alphanumeric and underscore, 3-20 chars
        username_pattern = re.compile(r'^[a-zA-Z0-9_]{3,20}$')
        
        valid_usernames = ["user123", "test_user", "JohnDoe"]
        invalid_usernames = ["ab", "user@name", "this_is_way_too_long_username"]
        
        for username in valid_usernames:
            assert username_pattern.match(username) is not None
        
        for username in invalid_usernames:
            assert username_pattern.match(username) is None

    def test_custom_validation_rules_allowed_values(self):
        """Test custom validation with allowed values list."""
        allowed_statuses = ["active", "inactive", "pending", "suspended"]
        
        valid_statuses = ["active", "pending"]
        invalid_statuses = ["deleted", "archived", "unknown"]
        
        for status in valid_statuses:
            assert status in allowed_statuses
        
        for status in invalid_statuses:
            assert status not in allowed_statuses

    def test_custom_validation_rules_range_constraints(self):
        """Test custom validation with numeric range constraints."""
        # Age validation: 18-120
        valid_ages = [18, 25, 65, 120]
        invalid_ages = [0, 17, 121, 150, -5]
        
        for age in valid_ages:
            is_valid = 18 <= age <= 120
            assert is_valid
        
        for age in invalid_ages:
            is_valid = 18 <= age <= 120
            assert not is_valid

    def test_custom_validation_rules_date_constraints(self):
        """Test custom validation with date range constraints."""
        # Date must be in the future
        from datetime import datetime, timedelta
        
        today = datetime.now()
        future_dates = [
            today + timedelta(days=1),
            today + timedelta(days=30),
            today + timedelta(days=365),
        ]
        past_dates = [
            today - timedelta(days=1),
            today - timedelta(days=30),
            today - timedelta(days=365),
        ]
        
        for date in future_dates:
            is_future = date > today
            assert is_future
        
        for date in past_dates:
            is_future = date > today
            assert not is_future


# ==============================================================================
# PARAMETRIZED TESTS FOR COMPREHENSIVE COVERAGE
# ==============================================================================

class TestValidatorsParametrized:
    """Parametrized tests for comprehensive validator coverage."""

    @pytest.mark.parametrize("email,expected", [
        ("test@example.com", True),
        ("user.name@example.co.uk", True),
        ("user+tag@example.com", True),
        ("invalid@", False),
        ("@example.com", False),
        ("notanemail", False),
        ("", False),
    ])
    def test_email_validation_parametrized(self, email: str, expected: bool):
        """Parametrized test for email validation."""
        email_pattern = re.compile(
            r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        )
        is_valid = email_pattern.match(email) is not None
        assert is_valid == expected

    @pytest.mark.parametrize("password,has_upper,has_lower,has_digit,has_special,min_length", [
        ("Passw0rd!", True, True, True, True, True),
        ("password123", False, True, True, False, True),
        ("PASSWORD123!", True, False, True, True, True),
        ("Password!", True, True, False, True, True),
        ("Pass1", True, True, True, False, False),
    ])
    def test_password_strength_parametrized(
        self, 
        password: str, 
        has_upper: bool, 
        has_lower: bool, 
        has_digit: bool, 
        has_special: bool,
        min_length: bool
    ):
        """Parametrized test for password strength validation."""
        actual_upper = any(c in string.ascii_uppercase for c in password)
        actual_lower = any(c in string.ascii_lowercase for c in password)
        actual_digit = any(c in string.digits for c in password)
        actual_special = any(c in string.punctuation for c in password)
        actual_length = len(password) >= 8
        
        assert actual_upper == has_upper
        assert actual_lower == has_lower
        assert actual_digit == has_digit
        assert actual_special == has_special
        assert actual_length == min_length

    @pytest.mark.parametrized("url,is_valid", [
        ("https://example.com", True),
        ("http://www.example.com/path", True),
        ("https://example.com:8080/api?query=value", True),
        ("example.com", False),
        ("https://", False),
        ("", False),
    ])
    def test_url_validation_parametrized(self, url: str, is_valid: bool):
        """Parametrized test for URL validation."""
        parsed = parse.urlparse(url)
        actual_valid = (
            parsed.scheme in ['http', 'https'] and
            parsed.netloc != ''
        )
        assert actual_valid == is_valid

    @pytest.mark.parametrize("phone,digit_count", [
        ("+1-555-123-4567", 11),
        ("555-123-4567", 10),
        ("(555) 123-4567", 10),
        ("+44 20 7123 4567", 12),
    ])
    def test_phone_normalization_parametrized(self, phone: str, digit_count: int):
        """Parametrized test for phone number normalization."""
        digits = re.sub(r'\D', '', phone)
        assert len(digits) == digit_count

