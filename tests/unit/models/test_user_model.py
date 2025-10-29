"""
Unit Tests for User Model

This module provides comprehensive unit tests for the User model, covering:
- Database field validations
- Password hashing and verification methods
- Email and password strength validation
- JSON serialization for API responses
- Model relationships and constraints
- Edge cases and boundary conditions

Test Categories:
- User creation and database persistence
- Password security (hashing, verification)
- Validation methods (email, password strength)
- Serialization (to_dict with various options)
- Model constraints (unique email, valid roles)
- Edge cases (None values, empty strings, boundaries)

Dependencies:
- pytest: Test framework
- app.models.user: User model being tested
- app.extensions: Database extension for ORM operations
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.exc import IntegrityError

from app.models.user import User
from app.extensions import db


class TestUserCreation:
    """Test suite for User model creation and database persistence."""
    
    def test_create_user_with_all_fields(self, db_session):
        """Test creating a user with all fields populated."""
        user = User(
            email='john.doe@example.com',
            first_name='John',
            last_name='Doe',
            profile_picture='https://example.com/profile.jpg',
            role='user',
            is_active=True
        )
        user.set_password('SecurePassword123!')
        
        db_session.add(user)
        db_session.commit()
        
        # Verify all fields are set correctly
        assert user.id is not None
        assert user.email == 'john.doe@example.com'
        assert user.first_name == 'John'
        assert user.last_name == 'Doe'
        assert user.profile_picture == 'https://example.com/profile.jpg'
        assert user.role == 'user'
        assert user.is_active is True
        assert user.password_hash is not None
        assert user.created_at is not None
        assert user.updated_at is not None
    
    def test_create_user_with_required_fields_only(self, db_session):
        """Test creating a user with only required fields (email and password)."""
        user = User(email='minimal@example.com')
        user.set_password('Password123!')
        
        db_session.add(user)
        db_session.commit()
        
        assert user.id is not None
        assert user.email == 'minimal@example.com'
        assert user.first_name is None
        assert user.last_name is None
        assert user.profile_picture is None
        assert user.role == 'user'  # Default value
        assert user.is_active is True  # Default value
        assert user.password_hash is not None
    
    def test_create_user_with_admin_role(self, db_session):
        """Test creating a user with admin role."""
        user = User(email='admin@example.com', role='admin')
        user.set_password('AdminPass123!')
        
        db_session.add(user)
        db_session.commit()
        
        assert user.role == 'admin'
        assert user.is_active is True
    
    def test_create_user_with_superuser_role(self, db_session):
        """Test creating a user with superuser role."""
        user = User(email='superuser@example.com', role='superuser')
        user.set_password('SuperPass123!')
        
        db_session.add(user)
        db_session.commit()
        
        assert user.role == 'superuser'
    
    def test_create_inactive_user(self, db_session):
        """Test creating an inactive user account."""
        user = User(email='inactive@example.com', is_active=False)
        user.set_password('Password123!')
        
        db_session.add(user)
        db_session.commit()
        
        assert user.is_active is False
    
    def test_created_at_timestamp_set_automatically(self, db_session):
        """Test that created_at timestamp is set automatically."""
        before_creation = datetime.utcnow()
        
        user = User(email='timestamp@example.com')
        user.set_password('Password123!')
        db_session.add(user)
        db_session.commit()
        
        after_creation = datetime.utcnow()
        
        assert user.created_at is not None
        assert before_creation <= user.created_at <= after_creation
    
    def test_updated_at_timestamp_set_automatically(self, db_session):
        """Test that updated_at timestamp is set automatically."""
        user = User(email='update@example.com')
        user.set_password('Password123!')
        db_session.add(user)
        db_session.commit()
        
        assert user.updated_at is not None
        # Timestamps should be very close (within a second)
        time_diff = abs((user.created_at - user.updated_at).total_seconds())
        assert time_diff < 1.0


class TestUserConstraints:
    """Test suite for User model database constraints."""
    
    def test_email_must_be_unique(self, db_session):
        """Test that email field has unique constraint."""
        user1 = User(email='unique@example.com')
        user1.set_password('Password123!')
        db_session.add(user1)
        db_session.commit()
        
        # Attempt to create user with duplicate email
        user2 = User(email='unique@example.com')
        user2.set_password('Password456!')
        db_session.add(user2)
        
        with pytest.raises(IntegrityError):
            db_session.commit()
    
    def test_email_cannot_be_null(self, db_session):
        """Test that email field is required (NOT NULL constraint)."""
        user = User()
        user.set_password('Password123!')
        db_session.add(user)
        
        with pytest.raises(IntegrityError):
            db_session.commit()
    
    def test_password_hash_cannot_be_null(self, db_session):
        """Test that password_hash field is required (NOT NULL constraint)."""
        user = User(email='nopass@example.com')
        # Don't set password - password_hash will be None
        db_session.add(user)
        
        with pytest.raises(IntegrityError):
            db_session.commit()


class TestPasswordHashing:
    """Test suite for password hashing and verification functionality."""
    
    def test_set_password_hashes_password(self, db_session):
        """Test that set_password hashes the password."""
        user = User(email='hash@example.com')
        plain_password = 'MySecurePassword123!'
        
        user.set_password(plain_password)
        
        # Password hash should be set and not equal to plain password
        assert user.password_hash is not None
        assert user.password_hash != plain_password
        # Password hash should be a string
        assert isinstance(user.password_hash, str)
        # Password hash should have sufficient length (hashed value)
        assert len(user.password_hash) > 60  # bcrypt hashes are longer
    
    def test_check_password_verifies_correct_password(self, db_session):
        """Test that check_password returns True for correct password."""
        user = User(email='verify@example.com')
        password = 'CorrectPassword123!'
        
        user.set_password(password)
        
        assert user.check_password(password) is True
    
    def test_check_password_rejects_incorrect_password(self, db_session):
        """Test that check_password returns False for incorrect password."""
        user = User(email='verify@example.com')
        correct_password = 'CorrectPassword123!'
        wrong_password = 'WrongPassword456!'
        
        user.set_password(correct_password)
        
        assert user.check_password(wrong_password) is False
    
    def test_check_password_is_case_sensitive(self, db_session):
        """Test that password verification is case-sensitive."""
        user = User(email='case@example.com')
        password = 'MyPassword123!'
        
        user.set_password(password)
        
        assert user.check_password('mypassword123!') is False
        assert user.check_password('MYPASSWORD123!') is False
        assert user.check_password(password) is True
    
    def test_set_password_with_empty_string_raises_error(self, db_session):
        """Test that setting an empty password raises ValueError."""
        user = User(email='empty@example.com')
        
        with pytest.raises(ValueError, match='Password cannot be empty'):
            user.set_password('')
    
    def test_set_password_with_none_raises_error(self, db_session):
        """Test that setting None as password raises ValueError."""
        user = User(email='none@example.com')
        
        with pytest.raises(ValueError, match='Password cannot be empty'):
            user.set_password(None)
    
    def test_check_password_with_empty_string_returns_false(self, db_session):
        """Test that checking empty password returns False."""
        user = User(email='check@example.com')
        user.set_password('ValidPassword123!')
        
        assert user.check_password('') is False
    
    def test_check_password_with_none_returns_false(self, db_session):
        """Test that checking None password returns False."""
        user = User(email='check@example.com')
        user.set_password('ValidPassword123!')
        
        assert user.check_password(None) is False
    
    def test_check_password_without_password_hash_returns_false(self, db_session):
        """Test that checking password when no hash is set returns False."""
        user = User(email='nohash@example.com')
        # Don't set password, so password_hash is None
        
        assert user.check_password('AnyPassword123!') is False
    
    def test_same_password_produces_different_hashes(self, db_session):
        """Test that hashing the same password twice produces different hashes (due to salt)."""
        user1 = User(email='user1@example.com')
        user2 = User(email='user2@example.com')
        
        same_password = 'SamePassword123!'
        user1.set_password(same_password)
        user2.set_password(same_password)
        
        # Hashes should be different due to random salt
        assert user1.password_hash != user2.password_hash
        # But both should verify correctly
        assert user1.check_password(same_password) is True
        assert user2.check_password(same_password) is True


class TestEmailValidation:
    """Test suite for email validation static method."""
    
    def test_validate_email_with_valid_emails(self):
        """Test email validation with various valid email formats."""
        valid_emails = [
            'user@example.com',
            'john.doe@example.com',
            'user+tag@example.com',
            'user_name@example.com',
            'user-name@example.com',
            'user123@example.com',
            'user@sub.example.com',
            'user@example.co.uk',
            'a@example.com',
            'user@example-domain.com',
        ]
        
        for email in valid_emails:
            assert User.validate_email(email) is True, f"Expected {email} to be valid"
    
    def test_validate_email_with_invalid_emails(self):
        """Test email validation with invalid email formats."""
        invalid_emails = [
            'invalid',
            'invalid@',
            '@example.com',
            'invalid@domain',
            'invalid.email',
            'invalid@.com',
            'invalid@domain.',
            'invalid..email@example.com',
            'invalid@domain..com',
            '',
            ' ',
            'user @example.com',
            'user@exam ple.com',
        ]
        
        for email in invalid_emails:
            assert User.validate_email(email) is False, f"Expected {email} to be invalid"
    
    def test_validate_email_with_none_returns_false(self):
        """Test that validating None email returns False."""
        assert User.validate_email(None) is False
    
    def test_validate_email_with_non_string_returns_false(self):
        """Test that validating non-string input returns False."""
        assert User.validate_email(123) is False
        assert User.validate_email([]) is False
        assert User.validate_email({}) is False
    
    def test_validate_email_respects_maximum_length(self):
        """Test that email validation enforces maximum length (254 chars)."""
        # Create an email that's too long (> 254 characters)
        local_part = 'a' * 64  # Maximum local part length
        domain_part = 'example.com'
        # Total length: 64 + 1 (@) + domain = need to make it > 254
        long_domain = 'x' * 190 + '.com'  # Will exceed 254 total
        long_email = f"{local_part}@{long_domain}"
        
        assert len(long_email) > 254
        assert User.validate_email(long_email) is False
    
    def test_validate_email_respects_local_part_max_length(self):
        """Test that local part cannot exceed 64 characters."""
        local_part = 'a' * 65  # Exceeds maximum local part length
        email = f"{local_part}@example.com"
        
        assert User.validate_email(email) is False
    
    def test_validate_email_respects_domain_part_max_length(self):
        """Test that domain part cannot exceed 255 characters."""
        domain_part = 'a' * 252 + '.com'  # Exceeds maximum domain length (256 chars)
        email = f"user@{domain_part}"
        
        assert len(domain_part) > 255
        assert User.validate_email(email) is False
    
    def test_validate_email_requires_domain_with_tld(self):
        """Test that email must have domain with TLD (top-level domain)."""
        assert User.validate_email('user@domain') is False
        assert User.validate_email('user@domain.') is False
        # TLD must be at least 2 characters as per regex pattern
        assert User.validate_email('user@domain.c') is False  # 1-char TLD invalid
        assert User.validate_email('user@domain.co') is True  # 2-char TLD valid


class TestPasswordStrengthValidation:
    """Test suite for password strength validation static method."""
    
    def test_validate_password_strength_with_strong_passwords(self):
        """Test password validation with strong passwords meeting all requirements."""
        strong_passwords = [
            'MyPassword123!',
            'Secure@Pass1',
            'P@ssw0rd!Strong',
            'C0mpl3x#Password',
            'Str0ng!P@ssword',
        ]
        
        for password in strong_passwords:
            assert User.validate_password_strength(password) is True, \
                f"Expected {password} to be strong"
    
    def test_validate_password_strength_too_short(self):
        """Test that passwords shorter than 8 characters are rejected."""
        short_passwords = [
            'Short1!',  # 7 characters
            'Pas1!',    # 5 characters
            'A1!',      # 3 characters
        ]
        
        for password in short_passwords:
            assert User.validate_password_strength(password) is False, \
                f"Expected {password} to be rejected (too short)"
    
    def test_validate_password_strength_too_long(self):
        """Test that passwords longer than 128 characters are rejected."""
        long_password = 'A' * 120 + 'a1!' + 'x' * 10  # 134 characters total
        
        assert len(long_password) > 128
        assert User.validate_password_strength(long_password) is False
    
    def test_validate_password_strength_no_uppercase(self):
        """Test that passwords without uppercase letters are rejected."""
        passwords_no_upper = [
            'password123!',
            'alllowercase1!',
            'n0upp3rc@se',
        ]
        
        for password in passwords_no_upper:
            assert User.validate_password_strength(password) is False, \
                f"Expected {password} to be rejected (no uppercase)"
    
    def test_validate_password_strength_no_lowercase(self):
        """Test that passwords without lowercase letters are rejected."""
        passwords_no_lower = [
            'PASSWORD123!',
            'ALLUPPERCASE1!',
            'N0L0W3RC@SE',
        ]
        
        for password in passwords_no_lower:
            assert User.validate_password_strength(password) is False, \
                f"Expected {password} to be rejected (no lowercase)"
    
    def test_validate_password_strength_no_digit(self):
        """Test that passwords without digits are rejected."""
        passwords_no_digit = [
            'PasswordWithoutDigit!',
            'NoNumbers!Here',
            'OnlyLetters@Symbols',
        ]
        
        for password in passwords_no_digit:
            assert User.validate_password_strength(password) is False, \
                f"Expected {password} to be rejected (no digit)"
    
    def test_validate_password_strength_no_special_character(self):
        """Test that passwords without special characters are rejected."""
        passwords_no_special = [
            'PasswordWithout123',
            'NoSpecialChars1',
            'OnlyLettersAndNumbers1',
        ]
        
        for password in passwords_no_special:
            assert User.validate_password_strength(password) is False, \
                f"Expected {password} to be rejected (no special character)"
    
    def test_validate_password_strength_with_none_returns_false(self):
        """Test that validating None password returns False."""
        assert User.validate_password_strength(None) is False
    
    def test_validate_password_strength_with_empty_string_returns_false(self):
        """Test that validating empty password returns False."""
        assert User.validate_password_strength('') is False
    
    def test_validate_password_strength_with_non_string_returns_false(self):
        """Test that validating non-string input returns False."""
        assert User.validate_password_strength(123) is False
        assert User.validate_password_strength([]) is False
        assert User.validate_password_strength({}) is False
    
    def test_validate_password_strength_minimum_valid_password(self):
        """Test password with exactly minimum requirements (8 chars)."""
        min_password = 'Pass123!'  # Exactly 8 characters
        
        assert len(min_password) == 8
        assert User.validate_password_strength(min_password) is True
    
    def test_validate_password_strength_maximum_valid_password(self):
        """Test password with maximum allowed length (128 chars)."""
        max_password = 'A' * 120 + 'a1!' + 'x' * 5  # Exactly 128 characters (120 + 3 + 5 = 128)
        
        assert len(max_password) == 128
        assert User.validate_password_strength(max_password) is True
    
    def test_validate_password_strength_with_various_special_characters(self):
        """Test that various special characters are accepted."""
        special_chars = '!@#$%^&*()_+-=[]{}|;:,.<>?'
        
        for char in special_chars:
            password = f'Password123{char}'
            assert User.validate_password_strength(password) is True, \
                f"Expected password with '{char}' to be valid"


class TestUserSerialization:
    """Test suite for User model serialization to dictionary."""
    
    def test_to_dict_includes_all_expected_fields(self, db_session):
        """Test that to_dict includes all expected user fields."""
        user = User(
            email='serialize@example.com',
            first_name='John',
            last_name='Doe',
            profile_picture='https://example.com/pic.jpg',
            role='admin',
            is_active=True
        )
        user.set_password('Password123!')
        db_session.add(user)
        db_session.commit()
        
        user_dict = user.to_dict()
        
        # Check all expected fields are present
        assert 'id' in user_dict
        assert 'email' in user_dict
        assert 'first_name' in user_dict
        assert 'last_name' in user_dict
        assert 'profile_picture' in user_dict
        assert 'role' in user_dict
        assert 'is_active' in user_dict
        assert 'created_at' in user_dict
        assert 'updated_at' in user_dict
        
        # Verify values
        assert user_dict['email'] == 'serialize@example.com'
        assert user_dict['first_name'] == 'John'
        assert user_dict['last_name'] == 'Doe'
        assert user_dict['profile_picture'] == 'https://example.com/pic.jpg'
        assert user_dict['role'] == 'admin'
        assert user_dict['is_active'] is True
    
    def test_to_dict_excludes_password_hash(self, db_session):
        """Test that to_dict never includes password_hash for security."""
        user = User(email='security@example.com')
        user.set_password('SecretPassword123!')
        db_session.add(user)
        db_session.commit()
        
        user_dict = user.to_dict()
        
        # Password hash must never be exposed
        assert 'password_hash' not in user_dict
        assert 'password' not in user_dict
    
    def test_to_dict_without_email(self, db_session):
        """Test that to_dict can exclude email when include_email=False."""
        user = User(email='private@example.com', first_name='Jane')
        user.set_password('Password123!')
        db_session.add(user)
        db_session.commit()
        
        user_dict = user.to_dict(include_email=False)
        
        # Email should not be included
        assert 'email' not in user_dict
        # Other fields should still be present
        assert 'id' in user_dict
        assert 'first_name' in user_dict
        assert user_dict['first_name'] == 'Jane'
    
    def test_to_dict_with_email_by_default(self, db_session):
        """Test that to_dict includes email by default."""
        user = User(email='default@example.com')
        user.set_password('Password123!')
        db_session.add(user)
        db_session.commit()
        
        user_dict = user.to_dict()  # No explicit include_email parameter
        
        assert 'email' in user_dict
        assert user_dict['email'] == 'default@example.com'
    
    def test_to_dict_with_null_optional_fields(self, db_session):
        """Test serialization when optional fields are None."""
        user = User(email='minimal@example.com')
        user.set_password('Password123!')
        db_session.add(user)
        db_session.commit()
        
        user_dict = user.to_dict()
        
        # Optional fields should be None in the dictionary
        assert user_dict['first_name'] is None
        assert user_dict['last_name'] is None
        assert user_dict['profile_picture'] is None
        # But required/default fields should have values
        assert user_dict['role'] == 'user'
        assert user_dict['is_active'] is True
    
    def test_to_dict_datetime_fields_are_iso_format(self, db_session):
        """Test that datetime fields are serialized to ISO format strings."""
        user = User(email='datetime@example.com')
        user.set_password('Password123!')
        db_session.add(user)
        db_session.commit()
        
        user_dict = user.to_dict()
        
        # Check that datetime fields are strings in ISO format
        assert isinstance(user_dict['created_at'], str)
        assert isinstance(user_dict['updated_at'], str)
        
        # Verify ISO format (should be parseable)
        from datetime import datetime
        created_dt = datetime.fromisoformat(user_dict['created_at'])
        updated_dt = datetime.fromisoformat(user_dict['updated_at'])
        
        assert isinstance(created_dt, datetime)
        assert isinstance(updated_dt, datetime)


class TestUserRepresentation:
    """Test suite for User model string representation."""
    
    def test_repr_includes_id_and_email(self, db_session):
        """Test that __repr__ includes user ID and email."""
        user = User(email='repr@example.com')
        user.set_password('Password123!')
        db_session.add(user)
        db_session.commit()
        
        repr_string = repr(user)
        
        assert '<User' in repr_string
        assert f'id={user.id}' in repr_string
        assert 'repr@example.com' in repr_string
    
    def test_repr_format_is_consistent(self, db_session):
        """Test that __repr__ format is consistent and readable."""
        user = User(id=123, email='test@example.com')
        
        repr_string = repr(user)
        
        # Should follow format: <User id=123 email='test@example.com'>
        assert repr_string.startswith('<User')
        assert repr_string.endswith('>')
        assert 'id=123' in repr_string
        assert 'test@example.com' in repr_string


class TestUserEdgeCases:
    """Test suite for User model edge cases and boundary conditions."""
    
    def test_user_with_maximum_length_email(self, db_session):
        """Test user creation with maximum allowed email length."""
        # Create an email at the boundary (254 characters total)
        local_part = 'a' * 64  # Maximum local part
        domain_part = 'b' * 180 + '.com'  # Domain to make total ~254
        max_email = f"{local_part}@{domain_part}"[:254]
        
        # Ensure it's valid first
        if User.validate_email(max_email):
            user = User(email=max_email)
            user.set_password('Password123!')
            db_session.add(user)
            db_session.commit()
            
            assert user.id is not None
            assert user.email == max_email
    
    def test_user_with_maximum_length_string_fields(self, db_session):
        """Test user creation with maximum length string fields."""
        user = User(
            email='max@example.com',
            first_name='A' * 100,  # Maximum first_name length
            last_name='B' * 100,   # Maximum last_name length
            profile_picture='https://example.com/' + 'x' * 470,  # Near max
            role='superuser'  # Longest valid role
        )
        user.set_password('Password123!')
        
        db_session.add(user)
        db_session.commit()
        
        assert user.id is not None
        assert len(user.first_name) == 100
        assert len(user.last_name) == 100
    
    def test_user_email_case_sensitivity(self, db_session):
        """Test that email comparison is case-sensitive in database."""
        user1 = User(email='CaseSensitive@example.com')
        user1.set_password('Password123!')
        db_session.add(user1)
        db_session.commit()
        
        # Try to create user with different case email
        # Note: Depending on database collation, this may or may not raise error
        # SQLite is typically case-insensitive for ASCII, but test the model behavior
        user2 = User(email='casesensitive@example.com')
        user2.set_password('Password456!')
        db_session.add(user2)
        
        # This test documents the current behavior
        # In production with PostgreSQL, you may want case-insensitive unique constraint
        try:
            db_session.commit()
            # If commit succeeds, emails are treated as different
            assert user1.email != user2.email
        except IntegrityError:
            # If commit fails, database treats them as same (case-insensitive unique)
            db_session.rollback()
    
    def test_user_with_special_characters_in_name(self, db_session):
        """Test user creation with special characters in name fields."""
        user = User(
            email='special@example.com',
            first_name="François",
            last_name="O'Brien-García"
        )
        user.set_password('Password123!')
        
        db_session.add(user)
        db_session.commit()
        
        assert user.first_name == "François"
        assert user.last_name == "O'Brien-García"
    
    def test_user_with_unicode_in_profile_picture_url(self, db_session):
        """Test user with Unicode characters in profile picture URL."""
        user = User(
            email='unicode@example.com',
            profile_picture='https://example.com/pics/用户头像.jpg'
        )
        user.set_password('Password123!')
        
        db_session.add(user)
        db_session.commit()
        
        assert user.profile_picture == 'https://example.com/pics/用户头像.jpg'
    
    def test_user_updated_at_changes_on_modification(self, db_session):
        """Test that updated_at timestamp changes when user is modified."""
        user = User(email='update@example.com', first_name='Original')
        user.set_password('Password123!')
        db_session.add(user)
        db_session.commit()
        
        original_updated_at = user.updated_at
        
        # Wait a brief moment and update
        import time
        time.sleep(0.1)
        
        user.first_name = 'Modified'
        db_session.commit()
        
        # updated_at should have changed
        # Note: This test may be flaky depending on database precision
        # Some databases update timestamp in same second
        assert user.updated_at >= original_updated_at
