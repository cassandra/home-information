import logging
from unittest.mock import Mock, patch

from custom.models import CustomUser
from django.test import RequestFactory

from hi.apps.notify.email_sender import EmailData
from hi.apps.user.signin_manager import SigninManager
from hi.testing.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestSigninManager(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()
        self.user = CustomUser.objects.create_user(
            email='test@example.com',
            password='testpass'
        )

    def test_signin_manager_singleton_behavior(self):
        """Test SigninManager follows singleton pattern correctly."""
        manager1 = SigninManager()
        manager2 = SigninManager()
        
        # Both instances should be the same object
        self.assertIs(manager1, manager2)

    def test_signin_manager_initialization(self):
        """Test SigninManager initializes correctly with template constants."""
        manager = SigninManager()
        
        # Verify template name constants are set
        self.assertEqual(manager.SIGNIN_SUBJECT_TEMPLATE_NAME, 'user/emails/signin_magic_link_subject.txt')
        self.assertEqual(manager.SIGNIN_MESSAGE_TEXT_TEMPLATE_NAME, 'user/emails/signin_magic_link_message.txt')
        self.assertEqual(manager.SIGNIN_MESSAGE_HTML_TEMPLATE_NAME, 'user/emails/signin_magic_link_message.html')

    @patch('hi.apps.user.signin_manager.EmailSender')
    def test_send_signin_magic_link_email_creates_proper_email_data(self, mock_email_sender_class):
        """Test magic link email generation creates correct EmailData and sends successfully."""
        mock_email_sender = Mock()
        mock_email_sender_class.return_value = mock_email_sender
        
        request = self.factory.get('/signin')
        request.META['HTTP_HOST'] = 'testserver'
        request.META['SERVER_PORT'] = '80'
        
        user_auth_data = Mock()
        user_auth_data.email_address = 'test@example.com'
        user_auth_data.token = 'test-token-123'
        user_auth_data.magic_code = 'abc123'
        
        manager = SigninManager()
        result = manager.send_signin_magic_link_email(request, user_auth_data)
        
        # Verify EmailSender was created with correct data
        mock_email_sender_class.assert_called_once()
        email_data_arg = mock_email_sender_class.call_args[1]['data']
        
        self.assertIsInstance(email_data_arg, EmailData)
        self.assertEqual(email_data_arg.request, request)
        self.assertEqual(email_data_arg.subject_template_name, 'user/emails/signin_magic_link_subject.txt')
        self.assertEqual(email_data_arg.message_text_template_name, 'user/emails/signin_magic_link_message.txt')
        self.assertEqual(email_data_arg.message_html_template_name, 'user/emails/signin_magic_link_message.html')
        self.assertEqual(email_data_arg.to_email_address, 'test@example.com')
        self.assertTrue(email_data_arg.non_blocking)
        
        # Verify template context contains required data
        template_context = email_data_arg.template_context
        self.assertIn('page_url', template_context)
        self.assertIn('magic_code', template_context)
        self.assertEqual(template_context['magic_code'], 'abc123')
        self.assertIn('/user/signin/magic/link/', template_context['page_url'])
        self.assertIn('test-token-123', template_context['page_url'])
        self.assertIn('test@example.com', template_context['page_url'])
        
        # Verify email was sent
        mock_email_sender.send.assert_called_once()
        
        # Verify method returns success
        self.assertTrue(result)

    @patch('hi.apps.user.signin_manager.django_login')
    def test_do_login_performs_django_login(self, mock_django_login):
        """Test do_login calls Django's login function."""
        request = Mock()
        request.user = self.user
        
        manager = SigninManager()
        manager.do_login(request, verified_email=False)
        
        mock_django_login.assert_called_once_with(request, self.user)

    @patch('hi.apps.user.signin_manager.django_login')
    def test_do_login_sets_email_verified_when_verified_email_true(self, mock_django_login):
        """Test do_login sets email_verified flag when verified_email=True."""
        request = Mock()
        request.user = self.user
        self.user.email_verified = False
        
        manager = SigninManager()
        manager.do_login(request, verified_email=True)
        
        # Verify email_verified flag is set and user is saved
        self.assertTrue(self.user.email_verified)
        mock_django_login.assert_called_once_with(request, self.user)

    @patch('hi.apps.user.signin_manager.django_login')
    def test_do_login_skips_email_verification_when_already_verified(self, mock_django_login):
        """Test do_login skips email verification when user already verified."""
        request = Mock()
        request.user = self.user
        self.user.email_verified = True
        original_save = self.user.save
        save_call_count = 0
        
        def count_save(*args, **kwargs):
            nonlocal save_call_count
            save_call_count += 1
            return original_save(*args, **kwargs)
        
        self.user.save = count_save
        
        manager = SigninManager()
        manager.do_login(request, verified_email=True)
        
        # Verify email_verified remains True and no extra save occurred
        self.assertTrue(self.user.email_verified)
        self.assertEqual(save_call_count, 0)  # No save should be called
        mock_django_login.assert_called_once_with(request, self.user)

    @patch('hi.apps.user.signin_manager.django_login')
    def test_do_login_skips_email_verification_when_verified_email_false(self, mock_django_login):
        """Test do_login skips email verification when verified_email=False."""
        request = Mock()
        request.user = self.user
        self.user.email_verified = False
        original_save = self.user.save
        save_call_count = 0
        
        def count_save(*args, **kwargs):
            nonlocal save_call_count
            save_call_count += 1
            return original_save(*args, **kwargs)
        
        self.user.save = count_save
        
        manager = SigninManager()
        manager.do_login(request, verified_email=False)
        
        # Verify email_verified remains False and no save occurred
        self.assertFalse(self.user.email_verified)
        self.assertEqual(save_call_count, 0)  # No save should be called
        mock_django_login.assert_called_once_with(request, self.user)

    def test_signin_manager_template_constants_are_strings(self):
        """Test SigninManager template constants are properly defined strings."""
        manager = SigninManager()
        
        # Verify all template constants are strings
        self.assertIsInstance(manager.SIGNIN_SUBJECT_TEMPLATE_NAME, str)
        self.assertIsInstance(manager.SIGNIN_MESSAGE_TEXT_TEMPLATE_NAME, str)
        self.assertIsInstance(manager.SIGNIN_MESSAGE_HTML_TEMPLATE_NAME, str)
        
        # Verify they follow expected naming pattern
        self.assertTrue(manager.SIGNIN_SUBJECT_TEMPLATE_NAME.endswith('.txt'))
        self.assertTrue(manager.SIGNIN_MESSAGE_TEXT_TEMPLATE_NAME.endswith('.txt'))
        self.assertTrue(manager.SIGNIN_MESSAGE_HTML_TEMPLATE_NAME.endswith('.html'))
