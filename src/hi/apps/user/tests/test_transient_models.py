import logging
from unittest.mock import Mock, patch

from custom.models import CustomUser
from django.test import RequestFactory

from hi.apps.user.transient_models import UserAuthenticationData
from hi.tests.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestUserAuthenticationData(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()
        self.user = CustomUser.objects.create_user(
            email='test@example.com',
            password='testpass'
        )

    @patch('hi.apps.user.transient_models.MagicCodeGenerator')
    @patch('hi.apps.user.transient_models.PasswordResetTokenGenerator')
    def test_user_authentication_data_initialization_with_request_user(self, mock_token_gen_class, mock_magic_gen_class):
        """Test UserAuthenticationData initializes correctly with request user."""
        # Mock the generators
        mock_token_generator = Mock()
        mock_token_generator.make_token.return_value = 'test-token-123'
        mock_token_gen_class.return_value = mock_token_generator
        
        mock_magic_generator = Mock()
        mock_magic_generator.make_magic_code.return_value = 'abc123'
        mock_magic_gen_class.return_value = mock_magic_generator
        
        request = self.factory.get('/test')
        request.user = self.user
        request.session = {}
        
        auth_data = UserAuthenticationData(request)
        
        # Verify properties return expected values
        self.assertEqual(auth_data.user, self.user)
        self.assertEqual(auth_data.email_address, 'test@example.com')
        self.assertEqual(auth_data.token, 'test-token-123')
        self.assertEqual(auth_data.magic_code, 'abc123')
        
        # Verify generators were called correctly
        mock_token_generator.make_token.assert_called_once_with(user=self.user)
        mock_magic_generator.make_magic_code.assert_called_once_with(request)

    @patch('hi.apps.user.transient_models.MagicCodeGenerator')
    @patch('hi.apps.user.transient_models.PasswordResetTokenGenerator')
    def test_user_authentication_data_initialization_with_override_user(self, mock_token_gen_class, mock_magic_gen_class):
        """Test UserAuthenticationData uses override_user when provided."""
        mock_token_generator = Mock()
        mock_token_generator.make_token.return_value = 'override-token-456'
        mock_token_gen_class.return_value = mock_token_generator
        
        mock_magic_generator = Mock()
        mock_magic_generator.make_magic_code.return_value = 'xyz789'
        mock_magic_gen_class.return_value = mock_magic_generator
        
        override_user = CustomUser.objects.create_user(
            email='override@example.com',
            password='overridepass'
        )
        
        request = self.factory.get('/test')
        request.user = self.user
        request.session = {}
        
        auth_data = UserAuthenticationData(request, override_user=override_user)
        
        # Verify override user is used instead of request user
        self.assertEqual(auth_data.user, override_user)
        self.assertEqual(auth_data.email_address, 'override@example.com')
        self.assertEqual(auth_data.token, 'override-token-456')
        
        # Verify token was generated for override user
        mock_token_generator.make_token.assert_called_once_with(user=override_user)

    @patch('hi.apps.user.transient_models.MagicCodeGenerator')
    @patch('hi.apps.user.transient_models.PasswordResetTokenGenerator')
    def test_user_authentication_data_initialization_with_override_email(self, mock_token_gen_class, mock_magic_gen_class):
        """Test UserAuthenticationData uses override_email when provided."""
        mock_token_generator = Mock()
        mock_token_generator.make_token.return_value = 'email-token-789'
        mock_token_gen_class.return_value = mock_token_generator
        
        mock_magic_generator = Mock()
        mock_magic_generator.make_magic_code.return_value = 'def456'
        mock_magic_gen_class.return_value = mock_magic_generator
        
        request = self.factory.get('/test')
        request.user = self.user
        request.session = {}
        
        auth_data = UserAuthenticationData(request, override_email='custom@example.com')
        
        # Verify override email is used instead of user email
        self.assertEqual(auth_data.user, self.user)
        self.assertEqual(auth_data.email_address, 'custom@example.com')
        self.assertEqual(auth_data.token, 'email-token-789')
        
        # Verify token was still generated for the actual user
        mock_token_generator.make_token.assert_called_once_with(user=self.user)

    @patch('hi.apps.user.transient_models.forms.SigninMagicCodeForm')
    @patch('hi.apps.user.transient_models.MagicCodeGenerator')
    @patch('hi.apps.user.transient_models.PasswordResetTokenGenerator')
    def test_user_authentication_data_creates_magic_code_form(self, mock_token_gen_class, mock_magic_gen_class, mock_form_class):
        """Test UserAuthenticationData creates SigninMagicCodeForm with correct initial data."""
        mock_token_generator = Mock()
        mock_token_generator.make_token.return_value = 'form-token-abc'
        mock_token_gen_class.return_value = mock_token_generator
        
        mock_magic_generator = Mock()
        mock_magic_generator.make_magic_code.return_value = 'form123'
        mock_magic_gen_class.return_value = mock_magic_generator
        
        mock_form = Mock()
        mock_form_class.return_value = mock_form
        
        request = self.factory.get('/test')
        request.user = self.user
        request.session = {}
        
        auth_data = UserAuthenticationData(request)
        
        # Verify form was created with correct initial data
        mock_form_class.assert_called_once_with(
            initial={'email_address': 'test@example.com'}
        )
        
        # Verify magic_code_form property returns the form
        self.assertEqual(auth_data.magic_code_form, mock_form)

    @patch('hi.apps.user.transient_models.MagicCodeGenerator')
    @patch('hi.apps.user.transient_models.PasswordResetTokenGenerator')
    def test_user_authentication_data_properties_are_readonly(self, mock_token_gen_class, mock_magic_gen_class):
        """Test UserAuthenticationData properties provide read-only access."""
        mock_token_generator = Mock()
        mock_token_generator.make_token.return_value = 'readonly-token'
        mock_token_gen_class.return_value = mock_token_generator
        
        mock_magic_generator = Mock()
        mock_magic_generator.make_magic_code.return_value = 'readonly123'
        mock_magic_gen_class.return_value = mock_magic_generator
        
        request = self.factory.get('/test')
        request.user = self.user
        request.session = {}
        
        auth_data = UserAuthenticationData(request)
        
        # Verify all properties are accessible
        self.assertIsNotNone(auth_data.user)
        self.assertIsNotNone(auth_data.email_address)
        self.assertIsNotNone(auth_data.token)
        self.assertIsNotNone(auth_data.magic_code)
        self.assertIsNotNone(auth_data.magic_code_form)
        
        # Verify properties cannot be set (should raise AttributeError)
        with self.assertRaises(AttributeError):
            auth_data.user = Mock()
        with self.assertRaises(AttributeError):
            auth_data.email_address = 'new@example.com'
        with self.assertRaises(AttributeError):
            auth_data.token = 'new-token'
        with self.assertRaises(AttributeError):
            auth_data.magic_code = 'new-code'

    @patch('hi.apps.user.transient_models.MagicCodeGenerator')
    @patch('hi.apps.user.transient_models.PasswordResetTokenGenerator')
    def test_user_authentication_data_with_both_overrides(self, mock_token_gen_class, mock_magic_gen_class):
        """Test UserAuthenticationData handles both user and email overrides correctly."""
        mock_token_generator = Mock()
        mock_token_generator.make_token.return_value = 'both-override-token'
        mock_token_gen_class.return_value = mock_token_generator
        
        mock_magic_generator = Mock()
        mock_magic_generator.make_magic_code.return_value = 'both123'
        mock_magic_gen_class.return_value = mock_magic_generator
        
        override_user = CustomUser.objects.create_user(
            email='both_override@example.com',
            password='bothpass'
        )
        
        request = self.factory.get('/test')
        request.user = self.user
        request.session = {}
        
        auth_data = UserAuthenticationData(
            request,
            override_user=override_user,
            override_email='completely_different@example.com'
        )
        
        # Verify override user is used for user property and token generation
        self.assertEqual(auth_data.user, override_user)
        # Verify override email is used for email_address property
        self.assertEqual(auth_data.email_address, 'completely_different@example.com')
        
        # Verify token was generated for override user, not original user
        mock_token_generator.make_token.assert_called_once_with(user=override_user)
