"""
Mock implementations for external API services used in testing.

This module provides comprehensive mock implementations for various external services
including email providers, payment gateways, SMS services, OAuth providers, and
monitoring services. These mocks allow tests to run in isolation without making
real HTTP requests to external APIs.

Usage:
    # Using pytest fixtures
    def test_send_email(mock_email_api):
        result = mock_email_api.send_email(
            to='test@example.com',
            subject='Test',
            body='Test message'
        )
        assert result['status'] == 'sent'

    # Using mock helpers with responses library
    @responses.activate
    def test_api_call():
        mock_api_success('https://api.example.com/endpoint', {'data': 'value'})
        # Make your API call and test
"""

import pytest
import responses
import requests_mock
import json
import re
import time
import uuid
from typing import Dict, List, Optional, Any, Union, Callable
from datetime import datetime, timedelta
from unittest.mock import MagicMock
from copy import deepcopy


class MockEmailService:
    """
    Mock email service supporting SMTP, SendGrid, Mailgun, and AWS SES.
    
    Simulates email sending operations without actual network calls.
    Tracks all email send attempts for verification in tests.
    """
    
    def __init__(self, provider: str = 'sendgrid'):
        """
        Initialize mock email service.
        
        Args:
            provider: Email provider name ('sendgrid', 'mailgun', 'smtp', 'aws_ses')
        """
        self.provider = provider
        self.send_history: List[Dict[str, Any]] = []
        self._provider_config = {
            'sendgrid': {'api_key': 'mock_sendgrid_key', 'api_url': 'https://api.sendgrid.com/v3/mail/send'},
            'mailgun': {'api_key': 'mock_mailgun_key', 'domain': 'mock.mailgun.org'},
            'smtp': {'host': 'smtp.mock.com', 'port': 587, 'username': 'mock_user'},
            'aws_ses': {'region': 'us-east-1', 'access_key': 'mock_access_key'}
        }
    
    def send_email(self, to: Union[str, List[str]], subject: str, body: str,
                   from_email: Optional[str] = None, cc: Optional[List[str]] = None,
                   bcc: Optional[List[str]] = None, attachments: Optional[List[Dict]] = None,
                   html: bool = False) -> Dict[str, Any]:
        """
        Mock sending an email.
        
        Args:
            to: Recipient email address(es)
            subject: Email subject line
            body: Email body content
            from_email: Sender email address
            cc: CC recipients
            bcc: BCC recipients
            attachments: List of attachment dictionaries
            html: Whether body is HTML content
            
        Returns:
            Dict containing send status and message ID
        """
        message_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        # Normalize to list
        recipients = [to] if isinstance(to, str) else to
        
        email_data = {
            'message_id': message_id,
            'to': recipients,
            'subject': subject,
            'body': body,
            'from': from_email or f'noreply@{self.provider}.com',
            'cc': cc or [],
            'bcc': bcc or [],
            'attachments': attachments or [],
            'html': html,
            'provider': self.provider,
            'timestamp': timestamp,
            'status': 'sent'
        }
        
        self.send_history.append(email_data)
        
        return {
            'status': 'sent',
            'message_id': message_id,
            'timestamp': timestamp,
            'provider': self.provider
        }
    
    def send_template_email(self, to: Union[str, List[str]], template_id: str,
                           template_data: Dict[str, Any], from_email: Optional[str] = None) -> Dict[str, Any]:
        """
        Mock sending a templated email.
        
        Args:
            to: Recipient email address(es)
            template_id: Template identifier
            template_data: Data to populate template variables
            from_email: Sender email address
            
        Returns:
            Dict containing send status and message ID
        """
        message_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        recipients = [to] if isinstance(to, str) else to
        
        email_data = {
            'message_id': message_id,
            'to': recipients,
            'template_id': template_id,
            'template_data': deepcopy(template_data),
            'from': from_email or f'noreply@{self.provider}.com',
            'provider': self.provider,
            'timestamp': timestamp,
            'status': 'sent'
        }
        
        self.send_history.append(email_data)
        
        return {
            'status': 'sent',
            'message_id': message_id,
            'timestamp': timestamp,
            'template_id': template_id,
            'provider': self.provider
        }
    
    def verify_email(self, email: str) -> Dict[str, Any]:
        """
        Mock email address verification.
        
        Args:
            email: Email address to verify
            
        Returns:
            Dict containing verification status and details
        """
        # Simple email format validation
        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        is_valid_format = bool(email_pattern.match(email))
        
        # Mock additional verification checks
        domain = email.split('@')[1] if '@' in email else ''
        
        return {
            'email': email,
            'valid': is_valid_format,
            'format_valid': is_valid_format,
            'domain': domain,
            'mx_records_exist': is_valid_format,  # Mock MX record check
            'disposable': 'temp' in domain or 'disposable' in domain,
            'timestamp': datetime.now().isoformat()
        }
    
    def configure_provider(self, provider: str, config: Optional[Dict[str, Any]] = None) -> None:
        """
        Configure the email provider.
        
        Args:
            provider: Provider name
            config: Optional configuration dictionary
        """
        self.provider = provider
        if config:
            self._provider_config[provider] = config
    
    def get_send_history(self) -> List[Dict[str, Any]]:
        """
        Get history of all sent emails.
        
        Returns:
            List of email send records
        """
        return deepcopy(self.send_history)
    
    def clear_history(self) -> None:
        """Clear the email send history."""
        self.send_history.clear()


class MockPaymentGateway:
    """
    Mock payment gateway supporting Stripe, PayPal, and Square.
    
    Simulates payment processing operations without real transactions.
    Tracks all transaction attempts for verification in tests.
    """
    
    def __init__(self, provider: str = 'stripe'):
        """
        Initialize mock payment gateway.
        
        Args:
            provider: Payment provider name ('stripe', 'paypal', 'square')
        """
        self.provider = provider
        self.transaction_history: List[Dict[str, Any]] = []
        self._provider_config = {
            'stripe': {'api_key': 'sk_test_mock_stripe_key', 'api_url': 'https://api.stripe.com/v1'},
            'paypal': {'client_id': 'mock_paypal_client', 'secret': 'mock_paypal_secret'},
            'square': {'access_token': 'mock_square_token', 'location_id': 'mock_location'}
        }
    
    def create_charge(self, amount: float, currency: str = 'usd',
                     source: Optional[str] = None, customer_id: Optional[str] = None,
                     description: Optional[str] = None, metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Mock creating a payment charge.
        
        Args:
            amount: Charge amount
            currency: Currency code
            source: Payment source token
            customer_id: Customer identifier
            description: Charge description
            metadata: Additional metadata
            
        Returns:
            Dict containing charge details and status
        """
        charge_id = f'ch_{uuid.uuid4().hex[:24]}'
        timestamp = datetime.now().isoformat()
        
        # Simulate different outcomes based on amount
        if amount < 0:
            status = 'failed'
            failure_message = 'Invalid amount'
        elif amount > 999999:
            status = 'failed'
            failure_message = 'Amount exceeds maximum'
        else:
            status = 'succeeded'
            failure_message = None
        
        charge_data = {
            'id': charge_id,
            'amount': amount,
            'currency': currency.lower(),
            'status': status,
            'source': source or f'card_{uuid.uuid4().hex[:16]}',
            'customer_id': customer_id,
            'description': description,
            'metadata': deepcopy(metadata) if metadata else {},
            'provider': self.provider,
            'timestamp': timestamp,
            'failure_message': failure_message
        }
        
        self.transaction_history.append(charge_data)
        
        return {
            'id': charge_id,
            'status': status,
            'amount': amount,
            'currency': currency.lower(),
            'timestamp': timestamp,
            'failure_message': failure_message
        }
    
    def refund(self, charge_id: str, amount: Optional[float] = None,
              reason: Optional[str] = None) -> Dict[str, Any]:
        """
        Mock refunding a charge.
        
        Args:
            charge_id: Original charge identifier
            amount: Refund amount (None for full refund)
            reason: Refund reason
            
        Returns:
            Dict containing refund details and status
        """
        refund_id = f'rf_{uuid.uuid4().hex[:24]}'
        timestamp = datetime.now().isoformat()
        
        # Find original charge
        original_charge = None
        for txn in self.transaction_history:
            if txn.get('id') == charge_id:
                original_charge = txn
                break
        
        if not original_charge:
            return {
                'id': refund_id,
                'status': 'failed',
                'error': 'Charge not found',
                'timestamp': timestamp
            }
        
        refund_amount = amount or original_charge.get('amount', 0)
        
        refund_data = {
            'id': refund_id,
            'charge_id': charge_id,
            'amount': refund_amount,
            'currency': original_charge.get('currency', 'usd'),
            'status': 'succeeded',
            'reason': reason,
            'provider': self.provider,
            'timestamp': timestamp
        }
        
        self.transaction_history.append(refund_data)
        
        return {
            'id': refund_id,
            'status': 'succeeded',
            'amount': refund_amount,
            'charge_id': charge_id,
            'timestamp': timestamp
        }
    
    def create_customer(self, email: str, name: Optional[str] = None,
                       metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Mock creating a customer.
        
        Args:
            email: Customer email
            name: Customer name
            metadata: Additional metadata
            
        Returns:
            Dict containing customer details
        """
        customer_id = f'cus_{uuid.uuid4().hex[:24]}'
        timestamp = datetime.now().isoformat()
        
        customer_data = {
            'id': customer_id,
            'email': email,
            'name': name,
            'metadata': deepcopy(metadata) if metadata else {},
            'provider': self.provider,
            'created': timestamp
        }
        
        self.transaction_history.append(customer_data)
        
        return {
            'id': customer_id,
            'email': email,
            'name': name,
            'created': timestamp
        }
    
    def attach_payment_method(self, customer_id: str, payment_method: str) -> Dict[str, Any]:
        """
        Mock attaching a payment method to a customer.
        
        Args:
            customer_id: Customer identifier
            payment_method: Payment method token or ID
            
        Returns:
            Dict containing attachment status
        """
        timestamp = datetime.now().isoformat()
        
        attachment_data = {
            'customer_id': customer_id,
            'payment_method': payment_method,
            'status': 'attached',
            'provider': self.provider,
            'timestamp': timestamp
        }
        
        self.transaction_history.append(attachment_data)
        
        return {
            'status': 'attached',
            'customer_id': customer_id,
            'payment_method': payment_method,
            'timestamp': timestamp
        }
    
    def get_transaction_history(self) -> List[Dict[str, Any]]:
        """
        Get history of all transactions.
        
        Returns:
            List of transaction records
        """
        return deepcopy(self.transaction_history)
    
    def set_provider(self, provider: str) -> None:
        """
        Set the payment provider.
        
        Args:
            provider: Provider name
        """
        self.provider = provider
    
    def clear_history(self) -> None:
        """Clear the transaction history."""
        self.transaction_history.clear()


class MockSMSService:
    """
    Mock SMS service supporting Twilio and Nexmo/Vonage.
    
    Simulates SMS sending operations without actual network calls.
    Tracks all SMS send attempts for verification in tests.
    """
    
    def __init__(self, provider: str = 'twilio'):
        """
        Initialize mock SMS service.
        
        Args:
            provider: SMS provider name ('twilio', 'nexmo', 'vonage')
        """
        self.provider = provider
        self.message_history: List[Dict[str, Any]] = []
        self._provider_config = {
            'twilio': {'account_sid': 'mock_twilio_sid', 'auth_token': 'mock_twilio_token'},
            'nexmo': {'api_key': 'mock_nexmo_key', 'api_secret': 'mock_nexmo_secret'},
            'vonage': {'api_key': 'mock_vonage_key', 'api_secret': 'mock_vonage_secret'}
        }
    
    def send_sms(self, to: str, message: str, from_number: Optional[str] = None) -> Dict[str, Any]:
        """
        Mock sending an SMS message.
        
        Args:
            to: Recipient phone number
            message: SMS message content
            from_number: Sender phone number
            
        Returns:
            Dict containing send status and message ID
        """
        message_id = f'SM{uuid.uuid4().hex[:32]}'
        timestamp = datetime.now().isoformat()
        
        # Validate phone number format (basic check)
        phone_pattern = re.compile(r'^\+?[1-9]\d{1,14}$')
        is_valid = bool(phone_pattern.match(to.replace(' ', '').replace('-', '')))
        
        if not is_valid:
            status = 'failed'
            error = 'Invalid phone number format'
        elif len(message) > 1600:
            status = 'failed'
            error = 'Message exceeds maximum length'
        else:
            status = 'sent'
            error = None
        
        sms_data = {
            'message_id': message_id,
            'to': to,
            'message': message,
            'from': from_number or f'+1555{self.provider[:4]}',
            'status': status,
            'error': error,
            'provider': self.provider,
            'timestamp': timestamp
        }
        
        self.message_history.append(sms_data)
        
        return {
            'message_id': message_id,
            'status': status,
            'to': to,
            'timestamp': timestamp,
            'error': error
        }
    
    def send_verification_code(self, to: str, code: Optional[str] = None) -> Dict[str, Any]:
        """
        Mock sending a verification code via SMS.
        
        Args:
            to: Recipient phone number
            code: Verification code (generated if not provided)
            
        Returns:
            Dict containing send status and verification details
        """
        verification_code = code or str(uuid.uuid4().int)[:6]
        message = f'Your verification code is: {verification_code}'
        
        result = self.send_sms(to, message)
        result['verification_code'] = verification_code
        
        return result
    
    def check_delivery_status(self, message_id: str) -> Dict[str, Any]:
        """
        Mock checking SMS delivery status.
        
        Args:
            message_id: Message identifier
            
        Returns:
            Dict containing delivery status details
        """
        # Find message in history
        message = None
        for msg in self.message_history:
            if msg.get('message_id') == message_id:
                message = msg
                break
        
        if not message:
            return {
                'message_id': message_id,
                'status': 'not_found',
                'error': 'Message not found'
            }
        
        # Simulate delivery progression
        return {
            'message_id': message_id,
            'status': 'delivered',
            'sent_at': message.get('timestamp'),
            'delivered_at': datetime.now().isoformat(),
            'provider': self.provider
        }
    
    def get_message_history(self) -> List[Dict[str, Any]]:
        """
        Get history of all sent messages.
        
        Returns:
            List of message send records
        """
        return deepcopy(self.message_history)
    
    def set_provider(self, provider: str) -> None:
        """
        Set the SMS provider.
        
        Args:
            provider: Provider name
        """
        self.provider = provider
    
    def clear_history(self) -> None:
        """Clear the message history."""
        self.message_history.clear()


class MockOAuthProvider:
    """
    Mock OAuth provider supporting Google, GitHub, Facebook, and Auth0.
    
    Simulates OAuth authentication flows without real external authentication.
    Tracks all OAuth operations for verification in tests.
    """
    
    def __init__(self, provider: str = 'google'):
        """
        Initialize mock OAuth provider.
        
        Args:
            provider: OAuth provider name ('google', 'github', 'facebook', 'auth0')
        """
        self.provider = provider
        self.token_history: List[Dict[str, Any]] = []
        self._provider_config = {
            'google': {
                'client_id': 'mock_google_client_id',
                'client_secret': 'mock_google_secret',
                'auth_url': 'https://accounts.google.com/o/oauth2/v2/auth',
                'token_url': 'https://oauth2.googleapis.com/token'
            },
            'github': {
                'client_id': 'mock_github_client_id',
                'client_secret': 'mock_github_secret',
                'auth_url': 'https://github.com/login/oauth/authorize',
                'token_url': 'https://github.com/login/oauth/access_token'
            },
            'facebook': {
                'client_id': 'mock_facebook_app_id',
                'client_secret': 'mock_facebook_secret',
                'auth_url': 'https://www.facebook.com/v12.0/dialog/oauth',
                'token_url': 'https://graph.facebook.com/v12.0/oauth/access_token'
            },
            'auth0': {
                'client_id': 'mock_auth0_client_id',
                'client_secret': 'mock_auth0_secret',
                'domain': 'mock-tenant.auth0.com'
            }
        }
    
    def get_authorization_url(self, redirect_uri: str, state: Optional[str] = None,
                             scope: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Mock generating OAuth authorization URL.
        
        Args:
            redirect_uri: Callback URL after authorization
            state: State parameter for CSRF protection
            scope: List of requested permissions
            
        Returns:
            Dict containing authorization URL and state
        """
        config = self._provider_config.get(self.provider, {})
        auth_url = config.get('auth_url', f'https://mock-{self.provider}.com/oauth/authorize')
        
        state_param = state or uuid.uuid4().hex
        scope_param = ' '.join(scope) if scope else 'openid profile email'
        
        # Construct mock authorization URL
        url = (f"{auth_url}?"
               f"client_id={config.get('client_id', 'mock_client')}&"
               f"redirect_uri={redirect_uri}&"
               f"state={state_param}&"
               f"scope={scope_param}&"
               f"response_type=code")
        
        return {
            'authorization_url': url,
            'state': state_param,
            'provider': self.provider
        }
    
    def exchange_code_for_token(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """
        Mock exchanging authorization code for access token.
        
        Args:
            code: Authorization code
            redirect_uri: Original redirect URI
            
        Returns:
            Dict containing access token and related data
        """
        access_token = f'mock_{self.provider}_access_token_{uuid.uuid4().hex}'
        refresh_token = f'mock_{self.provider}_refresh_token_{uuid.uuid4().hex}'
        expires_in = 3600  # 1 hour
        expires_at = (datetime.now() + timedelta(seconds=expires_in)).isoformat()
        
        token_data = {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'token_type': 'Bearer',
            'expires_in': expires_in,
            'expires_at': expires_at,
            'scope': 'openid profile email',
            'provider': self.provider,
            'issued_at': datetime.now().isoformat()
        }
        
        self.token_history.append(token_data)
        
        return token_data
    
    def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """
        Mock fetching user information using access token.
        
        Args:
            access_token: OAuth access token
            
        Returns:
            Dict containing user profile information
        """
        # Generate mock user data based on provider
        user_id = f'{self.provider}_{uuid.uuid4().hex[:16]}'
        
        user_info = {
            'id': user_id,
            'email': f'user_{user_id[:8]}@example.com',
            'name': f'Test User {user_id[:8]}',
            'picture': f'https://mock-{self.provider}.com/avatar/{user_id}.jpg',
            'verified_email': True,
            'provider': self.provider
        }
        
        # Add provider-specific fields
        if self.provider == 'google':
            user_info['given_name'] = 'Test'
            user_info['family_name'] = 'User'
        elif self.provider == 'github':
            user_info['login'] = f'testuser{user_id[:8]}'
            user_info['avatar_url'] = user_info.pop('picture')
        elif self.provider == 'facebook':
            user_info['first_name'] = 'Test'
            user_info['last_name'] = 'User'
        
        return user_info
    
    def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Mock refreshing an access token.
        
        Args:
            refresh_token: Refresh token
            
        Returns:
            Dict containing new access token
        """
        new_access_token = f'mock_{self.provider}_access_token_{uuid.uuid4().hex}'
        expires_in = 3600
        expires_at = (datetime.now() + timedelta(seconds=expires_in)).isoformat()
        
        token_data = {
            'access_token': new_access_token,
            'token_type': 'Bearer',
            'expires_in': expires_in,
            'expires_at': expires_at,
            'provider': self.provider,
            'issued_at': datetime.now().isoformat()
        }
        
        self.token_history.append(token_data)
        
        return token_data
    
    def revoke_token(self, token: str) -> Dict[str, Any]:
        """
        Mock revoking an access or refresh token.
        
        Args:
            token: Token to revoke
            
        Returns:
            Dict containing revocation status
        """
        return {
            'status': 'revoked',
            'token': token[:20] + '...',  # Truncated for security
            'provider': self.provider,
            'revoked_at': datetime.now().isoformat()
        }
    
    def set_provider(self, provider: str) -> None:
        """
        Set the OAuth provider.
        
        Args:
            provider: Provider name
        """
        self.provider = provider
    
    def get_token_history(self) -> List[Dict[str, Any]]:
        """
        Get history of all token operations.
        
        Returns:
            List of token operation records
        """
        return deepcopy(self.token_history)


class MockMonitoringService:
    """
    Mock monitoring service supporting Sentry, DataDog, and New Relic.
    
    Simulates error tracking and monitoring without real service calls.
    Tracks all captured events for verification in tests.
    """
    
    def __init__(self, provider: str = 'sentry'):
        """
        Initialize mock monitoring service.
        
        Args:
            provider: Monitoring provider name ('sentry', 'datadog', 'newrelic')
        """
        self.provider = provider
        self.captured_events: List[Dict[str, Any]] = []
        self.context_data: Dict[str, Any] = {}
        self._provider_config = {
            'sentry': {'dsn': 'https://mock@sentry.io/123456'},
            'datadog': {'api_key': 'mock_datadog_key', 'app_key': 'mock_app_key'},
            'newrelic': {'license_key': 'mock_newrelic_key'}
        }
    
    def capture_exception(self, exception: Exception, extra: Optional[Dict] = None,
                         tags: Optional[Dict] = None, level: str = 'error') -> str:
        """
        Mock capturing an exception.
        
        Args:
            exception: Exception object to capture
            extra: Additional context data
            tags: Tags to attach to the event
            level: Severity level
            
        Returns:
            Event ID
        """
        event_id = uuid.uuid4().hex
        timestamp = datetime.now().isoformat()
        
        event_data = {
            'event_id': event_id,
            'type': 'exception',
            'exception': {
                'type': type(exception).__name__,
                'value': str(exception),
                'module': exception.__class__.__module__
            },
            'level': level,
            'extra': deepcopy(extra) if extra else {},
            'tags': deepcopy(tags) if tags else {},
            'context': deepcopy(self.context_data),
            'provider': self.provider,
            'timestamp': timestamp
        }
        
        self.captured_events.append(event_data)
        
        return event_id
    
    def capture_message(self, message: str, level: str = 'info',
                       extra: Optional[Dict] = None, tags: Optional[Dict] = None) -> str:
        """
        Mock capturing a message.
        
        Args:
            message: Message text
            level: Severity level
            extra: Additional context data
            tags: Tags to attach to the event
            
        Returns:
            Event ID
        """
        event_id = uuid.uuid4().hex
        timestamp = datetime.now().isoformat()
        
        event_data = {
            'event_id': event_id,
            'type': 'message',
            'message': message,
            'level': level,
            'extra': deepcopy(extra) if extra else {},
            'tags': deepcopy(tags) if tags else {},
            'context': deepcopy(self.context_data),
            'provider': self.provider,
            'timestamp': timestamp
        }
        
        self.captured_events.append(event_data)
        
        return event_id
    
    def set_context(self, key: str, value: Any) -> None:
        """
        Set context data for subsequent events.
        
        Args:
            key: Context key
            value: Context value
        """
        self.context_data[key] = value
    
    def clear_context(self) -> None:
        """Clear all context data."""
        self.context_data.clear()
    
    def get_captured_events(self, event_type: Optional[str] = None,
                           level: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get captured events with optional filtering.
        
        Args:
            event_type: Filter by event type ('exception', 'message')
            level: Filter by severity level
            
        Returns:
            List of captured event records
        """
        events = deepcopy(self.captured_events)
        
        if event_type:
            events = [e for e in events if e.get('type') == event_type]
        
        if level:
            events = [e for e in events if e.get('level') == level]
        
        return events
    
    def set_provider(self, provider: str) -> None:
        """
        Set the monitoring provider.
        
        Args:
            provider: Provider name
        """
        self.provider = provider
    
    def clear_history(self) -> None:
        """Clear captured events and context."""
        self.captured_events.clear()
        self.context_data.clear()


# Helper functions for common mock scenarios using responses library

def mock_api_success(url: str, response_data: Dict[str, Any],
                    status: int = 200, method: str = 'GET') -> None:
    """
    Mock a successful API response.
    
    Args:
        url: API endpoint URL
        response_data: Response payload
        status: HTTP status code
        method: HTTP method
    """
    method_map = {
        'GET': responses.GET,
        'POST': responses.POST,
        'PUT': responses.PUT,
        'DELETE': responses.DELETE,
        'PATCH': responses.PATCH
    }
    
    responses.add(
        method_map.get(method.upper(), responses.GET),
        url,
        json=response_data,
        status=status
    )


def mock_api_error(url: str, status: int = 400, error_message: str = 'Bad Request',
                  method: str = 'GET') -> None:
    """
    Mock an API error response.
    
    Args:
        url: API endpoint URL
        status: HTTP error status code
        error_message: Error message
        method: HTTP method
    """
    method_map = {
        'GET': responses.GET,
        'POST': responses.POST,
        'PUT': responses.PUT,
        'DELETE': responses.DELETE,
        'PATCH': responses.PATCH
    }
    
    responses.add(
        method_map.get(method.upper(), responses.GET),
        url,
        json={'error': error_message, 'status': status},
        status=status
    )


def mock_api_timeout(url: str, method: str = 'GET') -> None:
    """
    Mock an API timeout scenario.
    
    Args:
        url: API endpoint URL
        method: HTTP method
    """
    import requests
    
    method_map = {
        'GET': responses.GET,
        'POST': responses.POST,
        'PUT': responses.PUT,
        'DELETE': responses.DELETE,
        'PATCH': responses.PATCH
    }
    
    def timeout_callback(request):
        raise requests.exceptions.Timeout('Request timed out')
    
    responses.add_callback(
        method_map.get(method.upper(), responses.GET),
        url,
        callback=timeout_callback
    )


def mock_rate_limit(url: str, retry_after: int = 60, method: str = 'GET') -> None:
    """
    Mock an API rate limit response.
    
    Args:
        url: API endpoint URL
        retry_after: Seconds until retry allowed
        method: HTTP method
    """
    method_map = {
        'GET': responses.GET,
        'POST': responses.POST,
        'PUT': responses.PUT,
        'DELETE': responses.DELETE,
        'PATCH': responses.PATCH
    }
    
    responses.add(
        method_map.get(method.upper(), responses.GET),
        url,
        json={'error': 'Rate limit exceeded', 'retry_after': retry_after},
        status=429,
        headers={'Retry-After': str(retry_after)}
    )


# Pytest fixtures for easy test integration

@pytest.fixture
def mock_email_api():
    """
    Pytest fixture providing a mock email service.
    
    Returns:
        MockEmailService instance
    """
    service = MockEmailService()
    yield service
    service.clear_history()


@pytest.fixture
def mock_payment_api():
    """
    Pytest fixture providing a mock payment gateway.
    
    Returns:
        MockPaymentGateway instance
    """
    gateway = MockPaymentGateway()
    yield gateway
    gateway.clear_history()


@pytest.fixture
def mock_sms_api():
    """
    Pytest fixture providing a mock SMS service.
    
    Returns:
        MockSMSService instance
    """
    service = MockSMSService()
    yield service
    service.clear_history()


@pytest.fixture
def mock_oauth():
    """
    Pytest fixture providing a mock OAuth provider.
    
    Returns:
        MockOAuthProvider instance
    """
    provider = MockOAuthProvider()
    yield provider


@pytest.fixture
def mock_monitoring():
    """
    Pytest fixture providing a mock monitoring service.
    
    Returns:
        MockMonitoringService instance
    """
    service = MockMonitoringService()
    yield service
    service.clear_history()

