import logging
from unittest.mock import AsyncMock, Mock, patch
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpRequest
from django.test import override_settings

from hi.apps.notify.email_sender import EmailData, EmailSender, UnsubscribedEmailError
from hi.apps.notify.models import UnsubscribedEmail
from hi.testing.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestEmailData(BaseTestCase):

    def test_email_data_creation_with_required_fields(self):
        """Test EmailData dataclass creation with required fields."""
        request = Mock(spec=HttpRequest)
        email_data = EmailData(
            request=request,
            subject_template_name='test_subject.txt',
            message_text_template_name='test_message.txt',
            message_html_template_name='test_message.html',
            to_email_address='test@example.com'
        )
        
        self.assertEqual(email_data.request, request)
        self.assertEqual(email_data.subject_template_name, 'test_subject.txt')
        self.assertEqual(email_data.message_text_template_name, 'test_message.txt')
        self.assertEqual(email_data.message_html_template_name, 'test_message.html')
        self.assertEqual(email_data.to_email_address, 'test@example.com')
        self.assertIsNone(email_data.from_email_address)
        self.assertEqual(email_data.template_context, {})
        self.assertIsNone(email_data.files)
        self.assertTrue(email_data.non_blocking)
        self.assertIsNone(email_data.override_to_email_address)

    def test_email_data_creation_with_list_of_email_addresses(self):
        """Test EmailData accepts list of email addresses."""
        request = Mock(spec=HttpRequest)
        email_addresses = ['test1@example.com', 'test2@example.com']
        
        email_data = EmailData(
            request=request,
            subject_template_name='test_subject.txt',
            message_text_template_name='test_message.txt',
            message_html_template_name='test_message.html',
            to_email_address=email_addresses
        )
        
        self.assertEqual(email_data.to_email_address, email_addresses)

    def test_email_data_creation_with_all_optional_fields(self):
        """Test EmailData creation with all optional fields specified."""
        request = Mock(spec=HttpRequest)
        template_context = {'key': 'value'}
        files = ['attachment.pdf']
        
        email_data = EmailData(
            request=request,
            subject_template_name='test_subject.txt',
            message_text_template_name='test_message.txt',
            message_html_template_name='test_message.html',
            to_email_address='test@example.com',
            from_email_address='sender@example.com',
            template_context=template_context,
            files=files,
            non_blocking=False,
            override_to_email_address='override@example.com'
        )
        
        self.assertEqual(email_data.from_email_address, 'sender@example.com')
        self.assertEqual(email_data.template_context, template_context)
        self.assertEqual(email_data.files, files)
        self.assertFalse(email_data.non_blocking)
        self.assertEqual(email_data.override_to_email_address, 'override@example.com')


class TestEmailSender(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.mock_request = Mock(spec=HttpRequest)
        self.base_email_data = EmailData(
            request=self.mock_request,
            subject_template_name='notify/emails/notification_subject.txt',
            message_text_template_name='notify/emails/notification_message.txt',
            message_html_template_name='notify/emails/notification_message.html',
            to_email_address='test@example.com'
        )

    def test_email_sender_initialization(self):
        """Test EmailSender initializes with EmailData."""
        sender = EmailSender(data=self.base_email_data)
        self.assertEqual(sender._data, self.base_email_data)

    def test_unsubscribed_email_check_blocks_sending(self):
        """Test that emails to unsubscribed addresses are blocked."""
        UnsubscribedEmail.objects.create(email='unsubscribed@example.com')
        
        email_data = EmailData(
            request=self.mock_request,
            subject_template_name='test_subject.txt',
            message_text_template_name='test_message.txt',
            message_html_template_name='test_message.html',
            to_email_address='unsubscribed@example.com'
        )
        
        sender = EmailSender(data=email_data)
        
        with self.assertRaises(UnsubscribedEmailError) as context:
            sender._assert_not_unsubscribed()
        
        error_message = str(context.exception)
        self.assertIn('unsubscribed@example.com', error_message)
        self.assertIn('Email address is unsubscribed', error_message)

    def test_unsubscribed_email_check_allows_subscribed_addresses(self):
        """Test that emails to subscribed addresses pass unsubscribe check."""
        sender = EmailSender(data=self.base_email_data)
        
        # Should not raise an exception
        sender._assert_not_unsubscribed()

    @patch('hi.apps.notify.email_sender.send_html_email')
    def test_url_generation_with_request(self, mock_send_email):
        """Test URL generation when request object is available."""
        self.mock_request.build_absolute_uri.side_effect = [
            'http://testserver/',
            'http://testserver/home/',
            'http://testserver/notify/email/unsubscribe/abc123/test@example.com'
        ]
        
        with patch.object(EmailSender, '_assert_email_configured'):
            with patch.object(EmailSender, '_assert_not_unsubscribed'):
                sender = EmailSender(data=self.base_email_data)
                sender._send_helper()
        
        # Verify send_html_email was called
        self.assertTrue(mock_send_email.called)
        call_kwargs = mock_send_email.call_args[1]
        context = call_kwargs['context']
        
        # Check that URLs were properly generated
        self.assertEqual(context['BASE_URL'], 'http://testserver')
        self.assertEqual(context['HOME_URL'], 'http://testserver/home/')
        self.assertIn('UNSUBSCRIBE_URL', context)
        self.assertIn('test@example.com', context['UNSUBSCRIBE_URL'])

    @override_settings(BASE_URL_FOR_EMAIL_LINKS='https://production.com')
    @patch('hi.apps.notify.email_sender.send_html_email')
    def test_url_generation_without_request(self, mock_send_email):
        """Test URL generation when request is None (background tasks)."""
        email_data = EmailData(
            request=None,
            subject_template_name='test_subject.txt',
            message_text_template_name='test_message.txt',
            message_html_template_name='test_message.html',
            to_email_address='test@example.com'
        )
        
        with patch.object(EmailSender, '_assert_email_configured'):
            with patch.object(EmailSender, '_assert_not_unsubscribed'):
                sender = EmailSender(data=email_data)
                sender._send_helper()
        
        # Verify send_html_email was called
        self.assertTrue(mock_send_email.called)
        call_kwargs = mock_send_email.call_args[1]
        context = call_kwargs['context']
        
        # Check that URLs use settings-based BASE_URL
        self.assertEqual(context['BASE_URL'], 'https://production.com')
        self.assertEqual(context['HOME_URL'], 'https://production.com/')
        self.assertIn('UNSUBSCRIBE_URL', context)
        self.assertIn('https://production.com/notify/email/unsubscribe/', context['UNSUBSCRIBE_URL'])

    @patch('hi.apps.notify.email_sender.send_html_email')
    def test_override_to_email_address_functionality(self, mock_send_email):
        """Test that override_to_email_address is used when specified."""
        mock_request = Mock(spec=HttpRequest)
        mock_request.build_absolute_uri.return_value = 'http://testserver/'
        
        email_data = EmailData(
            request=mock_request,
            subject_template_name='test_subject.txt',
            message_text_template_name='test_message.txt',
            message_html_template_name='test_message.html',
            to_email_address='original@example.com',
            override_to_email_address='override@example.com'
        )
        
        with patch.object(EmailSender, '_assert_email_configured'):
            with patch.object(EmailSender, '_assert_not_unsubscribed'):
                sender = EmailSender(data=email_data)
                sender._send_helper()
        
        # Verify the override email was used
        call_kwargs = mock_send_email.call_args[1]
        self.assertEqual(call_kwargs['to_email_addresses'], 'override@example.com')

    @patch('hi.apps.notify.email_sender.send_html_email')
    def test_template_context_merging(self, mock_send_email):
        """Test that custom template context is merged with generated URLs."""
        mock_request = Mock(spec=HttpRequest)
        mock_request.build_absolute_uri.return_value = 'http://testserver/'
        
        custom_context = {'notification': {'title': 'Test Notification'}}
        email_data = EmailData(
            request=mock_request,
            subject_template_name='test_subject.txt',
            message_text_template_name='test_message.txt',
            message_html_template_name='test_message.html',
            to_email_address='test@example.com',
            template_context=custom_context
        )
        
        with patch.object(EmailSender, '_assert_email_configured'):
            with patch.object(EmailSender, '_assert_not_unsubscribed'):
                sender = EmailSender(data=email_data)
                sender._send_helper()
        
        call_kwargs = mock_send_email.call_args[1]
        context = call_kwargs['context']
        
        # Check that custom context is preserved
        self.assertIn('notification', context)
        self.assertEqual(context['notification']['title'], 'Test Notification')
        
        # Check that generated URLs are also present
        self.assertIn('BASE_URL', context)
        self.assertIn('HOME_URL', context)
        self.assertIn('UNSUBSCRIBE_URL', context)

    def test_email_configuration_validation_success(self):
        """Test email configuration validation passes when all settings present."""
        with override_settings(
            EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend',
            EMAIL_HOST='smtp.example.com',
            EMAIL_PORT=587,
            EMAIL_HOST_USER='user@example.com',
            DEFAULT_FROM_EMAIL='noreply@example.com',
            SERVER_EMAIL='server@example.com'
        ):
            sender = EmailSender(data=self.base_email_data)
            
            # Should not raise an exception
            sender._assert_email_configured()
            
            # Class methods should also work
            self.assertTrue(EmailSender.is_email_configured())
            self.assertEqual(EmailSender.get_missing_email_setting_names(), [])

    def test_email_configuration_validation_failure(self):
        """Test email configuration validation fails when settings missing."""
        with override_settings(
            EMAIL_BACKEND='',
            EMAIL_HOST='',
            EMAIL_PORT=587,
            EMAIL_HOST_USER='user@example.com',
            DEFAULT_FROM_EMAIL='',
            SERVER_EMAIL='server@example.com'
        ):
            sender = EmailSender(data=self.base_email_data)
            
            with self.assertRaises(ImproperlyConfigured) as context:
                sender._assert_email_configured()
            
            error_message = str(context.exception)
            self.assertIn('Email is not configured', error_message)
            self.assertIn('EMAIL_BACKEND', error_message)
            self.assertIn('EMAIL_HOST', error_message)
            self.assertIn('DEFAULT_FROM_EMAIL', error_message)
            
            # Class methods should also detect issues
            self.assertFalse(EmailSender.is_email_configured())
            missing_settings = EmailSender.get_missing_email_setting_names()
            self.assertIn('EMAIL_BACKEND', missing_settings)
            self.assertIn('EMAIL_HOST', missing_settings)
            self.assertIn('DEFAULT_FROM_EMAIL', missing_settings)

    @patch('hi.apps.notify.email_sender.send_html_email')
    def test_send_method_integration(self, mock_send_email):
        """Test complete send() method integration."""
        mock_request = Mock(spec=HttpRequest)
        mock_request.build_absolute_uri.return_value = 'http://testserver/'
        
        email_data = EmailData(
            request=mock_request,
            subject_template_name='notify/emails/notification_subject.txt',
            message_text_template_name='notify/emails/notification_message.txt',
            message_html_template_name='notify/emails/notification_message.html',
            to_email_address='test@example.com'
        )
        
        with patch.object(EmailSender, '_assert_email_configured'):
            sender = EmailSender(data=email_data)
            sender.send()
        
        # Verify email was sent
        self.assertTrue(mock_send_email.called)
        call_kwargs = mock_send_email.call_args[1]
        
        # Verify all required parameters were passed
        self.assertEqual(call_kwargs['subject_template_name'], 'notify/emails/notification_subject.txt')
        self.assertEqual(call_kwargs['message_text_template_name'], 'notify/emails/notification_message.txt')
        self.assertEqual(call_kwargs['message_html_template_name'], 'notify/emails/notification_message.html')
        self.assertEqual(call_kwargs['to_email_addresses'], 'test@example.com')
        self.assertEqual(call_kwargs['request'], mock_request)
        self.assertTrue(call_kwargs['non_blocking'])

    @patch('hi.apps.notify.email_sender.send_html_email')
    def test_send_async_method_integration(self, mock_send_email):
        """Test complete send_async() method integration."""
        mock_request = Mock(spec=HttpRequest)
        mock_request.build_absolute_uri.return_value = 'http://testserver/'
        
        email_data = EmailData(
            request=mock_request,
            subject_template_name='notify/emails/notification_subject.txt',
            message_text_template_name='notify/emails/notification_message.txt',
            message_html_template_name='notify/emails/notification_message.html',
            to_email_address='test@example.com'
        )
        
        async def async_test():
            with patch.object(EmailSender, '_assert_email_configured'):
                with patch.object(EmailSender, '_assert_not_unsubscribed_async', new_callable=AsyncMock):
                    sender = EmailSender(data=email_data)
                    await sender.send_async()
            
            # Verify email was sent
            self.assertTrue(mock_send_email.called)
        
        # Run the async test
        import asyncio
        asyncio.run(async_test())
