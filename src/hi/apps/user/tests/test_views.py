import logging
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.urls import reverse

from hi.apps.notify.email_sender import EmailSender
from hi.apps.user.magic_code_generator import MagicCodeStatus, MagicCodeGenerator
from hi.apps.user.signin_manager import SigninManager
from hi.tests.view_test_base import SyncViewTestCase

logging.disable(logging.CRITICAL)

User = get_user_model()


class TestUserSigninView(SyncViewTestCase):
    """
    Tests for UserSigninView - demonstrates user authentication testing.
    This view handles email-based signin requests.
    """

    def setUp(self):
        super().setUp()
        # Use the user from parent setUp()

    @patch.object(EmailSender, 'is_email_configured')
    def test_get_signin_page_email_configured(self, mock_is_configured):
        """Test getting signin page when email is configured."""
        mock_is_configured.return_value = True

        url = reverse('user_signin')
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertHtmlResponse(response)
        self.assertTemplateRendered(response, 'user/pages/signin.html')
        self.assertEqual(response.context['email_not_configured'], False)

    @patch.object(EmailSender, 'is_email_configured')
    def test_get_signin_page_email_not_configured(self, mock_is_configured):
        """Test getting signin page when email is not configured."""
        mock_is_configured.return_value = False

        url = reverse('user_signin')
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertEqual(response.context['email_not_configured'], True)

    def test_post_signin_already_authenticated(self):
        """Test POST request when user is already authenticated."""
        # Force authentication
        self.client.force_login(self.user)

        url = reverse('user_signin')
        response = self.client.post(url, {'email': 'test@example.com'})

        self.assertEqual(response.status_code, 400)

    def test_post_signin_no_email(self):
        """Test POST request without email."""
        url = reverse('user_signin')
        response = self.client.post(url, {})

        self.assertEqual(response.status_code, 400)

    def test_post_signin_invalid_email(self):
        """Test POST request with invalid email."""
        url = reverse('user_signin')
        response = self.client.post(url, {'email': 'invalid-email'})

        self.assertEqual(response.status_code, 400)

    @patch('hi.apps.user.views.SendMagicLinkEmailView')
    def test_post_signin_existing_user(self, mock_send_view_class):
        """Test POST request with existing user email."""
        from django.http import HttpResponse
        mock_send_view = mock_send_view_class.return_value
        mock_send_view.send_signin_magic_link.return_value = HttpResponse('mock_response')

        url = reverse('user_signin')
        _ = self.client.post(url, {'email': self.user.email})

        # Should delegate to SendMagicLinkEmailView
        mock_send_view.send_signin_magic_link.assert_called_once()
        call_kwargs = mock_send_view.send_signin_magic_link.call_args[1]
        self.assertEqual(call_kwargs['override_user'], self.user)

    @patch('hi.apps.user.views.SigninMagicCodeView')
    def test_post_signin_nonexistent_user(self, mock_magic_code_view_class):
        """Test POST request with nonexistent user email."""
        from django.http import HttpResponse
        mock_magic_code_view = mock_magic_code_view_class.return_value
        mock_magic_code_view.get_response.return_value = HttpResponse('mock_response')

        url = reverse('user_signin')
        _ = self.client.post(url, {'email': 'nonexistent@example.com'})

        # Should delegate to SigninMagicCodeView
        mock_magic_code_view.get_response.assert_called_once()

    def test_post_signin_email_validation_error(self):
        """Test POST request with email that fails validation."""
        url = reverse('user_signin')
        # Pass actually invalid email format that will fail Django's validate_email
        response = self.client.post(url, {'email': 'not-an-email'})

        self.assertEqual(response.status_code, 400)


class TestSendMagicLinkEmailView(SyncViewTestCase):
    """
    Tests for SendMagicLinkEmailView - demonstrates magic link email testing.
    This view sends magic link emails for authentication.
    """

    def setUp(self):
        super().setUp()
        # Use the user from parent setUp()

    @patch.object(SigninManager, 'send_signin_magic_link_email')
    @patch('hi.apps.user.views.SigninMagicCodeView')
    def test_send_signin_magic_link(self, mock_magic_code_view_class, mock_send_email):
        """Test sending signin magic link email."""
        mock_magic_code_view = mock_magic_code_view_class.return_value
        mock_magic_code_view.get_response.return_value = 'mock_response'

        from hi.apps.user.views import SendMagicLinkEmailView
        view = SendMagicLinkEmailView()
        
        # Create a mock request
        request = self.client.get('/').wsgi_request
        
        _ = view.send_signin_magic_link(
            request=request,
            override_user=self.user
        )

        # Should call signin manager to send email
        mock_send_email.assert_called_once()
        
        # Should delegate to magic code view for response
        mock_magic_code_view.get_response.assert_called_once()

    @patch.object(SigninManager, 'send_signin_magic_link_email')
    @patch('hi.apps.user.views.SigninMagicCodeView')
    def test_send_magic_link_creates_user_auth_data(self, mock_magic_code_view_class, mock_send_email):
        """Test that user authentication data is created properly."""
        mock_magic_code_view = mock_magic_code_view_class.return_value
        mock_magic_code_view.get_response.return_value = 'mock_response'

        from hi.apps.user.views import SendMagicLinkEmailView
        view = SendMagicLinkEmailView()
        
        # Create a mock request
        request = self.client.get('/').wsgi_request
        
        view.send_signin_magic_link(
            request=request,
            override_user=self.user
        )

        # Should pass user auth data to signin manager
        mock_send_email.assert_called_once()
        call_args = mock_send_email.call_args[1]
        self.assertIn('user_auth_data', call_args)


class TestSigninMagicCodeView(SyncViewTestCase):
    """
    Tests for SigninMagicCodeView - demonstrates magic code verification testing.
    This view handles magic code form submission and verification.
    """

    def setUp(self):
        super().setUp()
        # Use the user from parent setUp()

    def test_get_response_method(self):
        """Test the get_response method renders correctly."""
        from hi.apps.user.views import SigninMagicCodeView
        from hi.apps.user.forms import SigninMagicCodeForm
        
        view = SigninMagicCodeView()
        form = SigninMagicCodeForm(initial={'email_address': 'test@example.com'})
        
        # Create a mock request
        request = self.client.get('/').wsgi_request
        
        response = view.get_response(request=request, magic_code_form=form)
        
        # Should render the magic code template
        self.assertEqual(response.status_code, 200)

    def test_post_invalid_form(self):
        """Test POST request with invalid form data."""
        url = reverse('user_signin_magic_code')
        # Send completely empty data which should make the form invalid
        response = self.client.post(url, {})

        self.assertEqual(response.status_code, 400)

    def test_post_nonexistent_user(self):
        """Test POST request with nonexistent user email."""
        url = reverse('user_signin_magic_code')
        response = self.client.post(url, {
            'email_address': 'nonexistent@example.com',
            'magic_code': '123456'
        })

        self.assertEqual(response.status_code, 400)

    @patch.object(MagicCodeGenerator, 'check_magic_code')
    def test_post_invalid_magic_code(self, mock_check_code):
        """Test POST request with invalid magic code."""
        # Mock invalid magic code
        mock_check_code.return_value = MagicCodeStatus.INVALID

        url = reverse('user_signin_magic_code')
        response = self.client.post(url, {
            'email_address': self.user.email,
            'magic_code': '123456'
        })

        self.assertEqual(response.status_code, 400)

    @patch.object(MagicCodeGenerator, 'check_magic_code')
    def test_post_expired_magic_code(self, mock_check_code):
        """Test POST request with expired magic code."""
        # Mock expired magic code
        mock_check_code.return_value = MagicCodeStatus.EXPIRED

        url = reverse('user_signin_magic_code')
        response = self.client.post(url, {
            'email_address': self.user.email,
            'magic_code': '123456'
        })

        self.assertEqual(response.status_code, 400)

    @patch.object(MagicCodeGenerator, 'expire_magic_code')
    @patch.object(SigninManager, 'do_login')
    @patch.object(MagicCodeGenerator, 'check_magic_code')
    @patch('hi.apps.user.forms.SigninMagicCodeForm')
    def test_post_valid_magic_code(self, mock_form_class, mock_check_code, mock_do_login, mock_expire_code):
        """Test POST request with valid magic code."""
        # Mock valid form
        mock_form = Mock()
        mock_form.is_valid.return_value = True
        mock_form.cleaned_data = {
            'email_address': self.user.email,
            'magic_code': '123456'
        }
        mock_form_class.return_value = mock_form

        # Mock valid magic code
        mock_check_code.return_value = MagicCodeStatus.VALID

        url = reverse('user_signin_magic_code')
        response = self.client.post(url, {
            'email_address': self.user.email,
            'magic_code': '123456'
        })

        self.assertEqual(response.status_code, 302)
        expected_url = reverse('home')
        self.assertEqual(response.url, expected_url)
        
        # Should perform login and expire code
        mock_do_login.assert_called_once()
        mock_expire_code.assert_called_once()


class TestSigninMagicLinkView(SyncViewTestCase):
    """
    Tests for SigninMagicLinkView - demonstrates magic link authentication testing.
    This view handles magic link clicks from emails.
    """

    def setUp(self):
        super().setUp()
        # Use the user from parent setUp()

    def test_get_missing_token(self):
        """Test GET request with missing token."""
        from django.urls.exceptions import NoReverseMatch
        with self.assertRaises(NoReverseMatch):
            reverse('user_signin_magic_link', kwargs={
                'email': self.user.email,
                'token': ''
            })

    def test_get_missing_email(self):
        """Test GET request with missing email."""
        from django.urls.exceptions import NoReverseMatch
        with self.assertRaises(NoReverseMatch):
            reverse('user_signin_magic_link', kwargs={
                'email': '',
                'token': 'test-token'
            })

    def test_get_nonexistent_user(self):
        """Test GET request with nonexistent user email."""
        url = reverse('user_signin_magic_link', kwargs={
            'email': 'nonexistent@example.com',
            'token': 'test-token'
        })
        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)

    @patch.object(PasswordResetTokenGenerator, 'check_token')
    def test_get_invalid_token(self, mock_check_token):
        """Test GET request with invalid token."""
        mock_check_token.return_value = False

        url = reverse('user_signin_magic_link', kwargs={
            'email': self.user.email,
            'token': 'invalid-token'
        })
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertTemplateRendered(response, 'user/pages/signin_magic_bad_link.html')

    @patch.object(SigninManager, 'do_login')
    @patch.object(PasswordResetTokenGenerator, 'check_token')
    def test_get_valid_token(self, mock_check_token, mock_do_login):
        """Test GET request with valid token."""
        mock_check_token.return_value = True

        url = reverse('user_signin_magic_link', kwargs={
            'email': self.user.email,
            'token': 'valid-token'
        })
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        expected_url = reverse('home')
        self.assertEqual(response.url, expected_url)
        
        # Should perform login
        mock_do_login.assert_called_once()

    @patch.object(PasswordResetTokenGenerator, 'check_token')
    def test_token_validation_called_correctly(self, mock_check_token):
        """Test that token validation is called with correct parameters."""
        mock_check_token.return_value = True

        url = reverse('user_signin_magic_link', kwargs={
            'email': self.user.email,
            'token': 'test-token'
        })
        _ = self.client.get(url)

        # Should check token with user and token
        mock_check_token.assert_called_once_with(user=self.user, token='test-token')

    def test_post_not_allowed(self):
        """Test that POST requests are not allowed."""
        url = reverse('user_signin_magic_link', kwargs={
            'email': self.user.email,
            'token': 'test-token'
        })
        response = self.client.post(url)

        self.assertEqual(response.status_code, 405)
        
