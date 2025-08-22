import logging
from unittest.mock import patch

from django.urls import reverse

from hi.apps.notify.models import UnsubscribedEmail
from hi.testing.view_test_base import SyncViewTestCase

logging.disable(logging.CRITICAL)


class TestEmailUnsubscribeView(SyncViewTestCase):
    """
    Tests for EmailUnsubscribeView - demonstrates unsubscribe flow testing.
    This view handles email unsubscription requests with token validation.
    """

    def setUp(self):
        super().setUp()
        self.test_email = 'test@example.com'
        # Mock the hash function to return a predictable token
        self.test_token = 'test_token_123'

    @patch('hi.apps.notify.views.hash_with_seed')
    def test_unsubscribe_with_valid_token(self, mock_hash):
        """Test successful unsubscribe with valid token."""
        mock_hash.return_value = self.test_token

        url = reverse('notify_email_unsubscribe', kwargs={
            'email': self.test_email,
            'token': self.test_token
        })
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertTemplateRendered(response, 'notify/pages/email_unsubscribe_success.html')
        
        # Check that email was added to unsubscribed list
        self.assertTrue(
            UnsubscribedEmail.objects.filter(email=self.test_email).exists()
        )

    @patch('hi.apps.notify.views.hash_with_seed')
    def test_unsubscribe_with_invalid_token(self, mock_hash):
        """Test unsubscribe fails with invalid token."""
        mock_hash.return_value = 'different_token'

        url = reverse('notify_email_unsubscribe', kwargs={
            'email': self.test_email,
            'token': self.test_token
        })
        response = self.client.get(url)

        # Should raise BadRequest (400)
        self.assertEqual(response.status_code, 400)
        
        # Check that email was NOT added to unsubscribed list
        self.assertFalse(
            UnsubscribedEmail.objects.filter(email=self.test_email).exists()
        )

    @patch('hi.apps.notify.views.hash_with_seed')
    def test_unsubscribe_already_unsubscribed(self, mock_hash):
        """Test unsubscribe when email is already unsubscribed."""
        mock_hash.return_value = self.test_token
        
        # Pre-create unsubscribed email
        UnsubscribedEmail.objects.create(email=self.test_email)

        url = reverse('notify_email_unsubscribe', kwargs={
            'email': self.test_email,
            'token': self.test_token
        })
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertTemplateRendered(response, 'notify/pages/email_unsubscribe_success.html')
        
        # Should still have exactly one unsubscribed record
        self.assertEqual(
            UnsubscribedEmail.objects.filter(email=self.test_email).count(),
            1
        )

    def test_unsubscribe_missing_email(self):
        """Test unsubscribe fails when email is missing."""
        # NOTE: This tests the view's internal validation logic
        # We patch kwargs to simulate empty email reaching the view
        with patch.object(self.client, 'get'):
            from hi.apps.notify.views import EmailUnsubscribeView
            view = EmailUnsubscribeView()
            from django.test import RequestFactory
            request = RequestFactory().get('/test/')
            
            # Test view method directly with empty email
            with self.assertRaises(Exception) as context:
                view.get(request, email='', token=self.test_token)
            
            # Should raise BadRequest
            self.assertIn('BadRequest', str(type(context.exception)))

    def test_unsubscribe_missing_token(self):
        """Test unsubscribe fails when token is missing."""
        # NOTE: This tests the view's internal validation logic
        # We patch kwargs to simulate empty token reaching the view
        with patch.object(self.client, 'get'):
            from hi.apps.notify.views import EmailUnsubscribeView
            view = EmailUnsubscribeView()
            from django.test import RequestFactory
            request = RequestFactory().get('/test/')
            
            # Test view method directly with empty token
            with self.assertRaises(Exception) as context:
                view.get(request, email=self.test_email, token='')
            
            # Should raise BadRequest
            self.assertIn('BadRequest', str(type(context.exception)))

    @patch('hi.apps.notify.views.hash_with_seed')
    def test_email_in_context(self, mock_hash):
        """Test that email is passed to template context."""
        mock_hash.return_value = self.test_token

        url = reverse('notify_email_unsubscribe', kwargs={
            'email': self.test_email,
            'token': self.test_token
        })
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertEqual(response.context['email'], self.test_email)

    @patch('hi.apps.notify.views.hash_with_seed')
    @patch('hi.apps.notify.models.UnsubscribedEmail.objects.create')
    def test_handle_database_error_gracefully(self, mock_create, mock_hash):
        """Test that database errors are handled gracefully."""
        mock_hash.return_value = self.test_token
        mock_create.side_effect = Exception('Database error')

        url = reverse('notify_email_unsubscribe', kwargs={
            'email': self.test_email,
            'token': self.test_token
        })
        response = self.client.get(url)

        # Should still render success page even if database error occurs
        self.assertSuccessResponse(response)
        self.assertTemplateRendered(response, 'notify/pages/email_unsubscribe_success.html')

    @patch('hi.apps.notify.views.hash_with_seed')
    def test_case_insensitive_email_check(self, mock_hash):
        """Test that email check is case-insensitive."""
        mock_hash.return_value = self.test_token
        
        # Create unsubscribed email with lowercase
        UnsubscribedEmail.objects.create(email='test@example.com')

        # Try to unsubscribe with uppercase
        url = reverse('notify_email_unsubscribe', kwargs={
            'email': 'TEST@EXAMPLE.COM',
            'token': self.test_token
        })
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        # Should recognize as already unsubscribed and not create duplicate
        self.assertEqual(
            UnsubscribedEmail.objects.filter(email__iexact='test@example.com').count(),
            1
        )
