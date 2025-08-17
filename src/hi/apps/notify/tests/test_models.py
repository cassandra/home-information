import logging
from unittest.mock import Mock
from django.db import IntegrityError
from django.contrib.auth import get_user_model

from hi.apps.notify.models import UnsubscribedEmail
from hi.tests.base_test_case import BaseTestCase

User = get_user_model()

logging.disable(logging.CRITICAL)


class TestUnsubscribedEmail(BaseTestCase):

    def test_unsubscribed_email_uniqueness_constraint(self):
        """Test email uniqueness constraint - critical for data integrity."""
        # Create first unsubscribed email
        UnsubscribedEmail.objects.create(email='test@example.com')
        
        # Duplicate email should fail
        with self.assertRaises(IntegrityError):
            UnsubscribedEmail.objects.create(email='test@example.com')
        return

    def test_unsubscribed_email_valid_email_format(self):
        """Test valid email format acceptance - important for data validation."""
        valid_emails = [
            'user@example.com',
            'user.name@example.com',
            'user+tag@example.com',
            'user_name@sub.example.com'
        ]
        
        for email in valid_emails:
            with self.subTest(email=email):
                unsubscribed = UnsubscribedEmail.objects.create(email=email)
                self.assertEqual(unsubscribed.email, email)
        return

    def test_unsubscribed_email_created_datetime_indexing(self):
        """Test created_datetime field indexing - critical for query performance."""
        unsubscribed = UnsubscribedEmail.objects.create(email='test@example.com')
        
        # Test that datetime queries work efficiently
        # (The actual index performance isn't testable in unit tests,
        # but we can verify the field is accessible and queryable)
        recent_unsubscribed = UnsubscribedEmail.objects.filter(
            created_datetime__gte=unsubscribed.created_datetime
        )
        self.assertIn(unsubscribed, recent_unsubscribed)
        return

    def test_unsubscribed_email_manager_usage(self):
        """Test custom manager usage - important for query interface."""
        from hi.apps.notify.managers import UnsubscribedEmailManager
        
        # Should use custom manager
        self.assertIsInstance(UnsubscribedEmail.objects, UnsubscribedEmailManager)
        return


class TestUnsubscribedEmailManager(BaseTestCase):

    def test_exists_by_email_with_subscribed_email(self):
        """Test exists_by_email returns False for subscribed email."""
        # Email not in unsubscribed list should return False
        result = UnsubscribedEmail.objects.exists_by_email('subscribed@example.com')
        self.assertFalse(result)

    def test_exists_by_email_with_unsubscribed_email(self):
        """Test exists_by_email returns True for unsubscribed email."""
        # Create unsubscribed email
        UnsubscribedEmail.objects.create(email='unsubscribed@example.com')
        
        # Should return True
        result = UnsubscribedEmail.objects.exists_by_email('unsubscribed@example.com')
        self.assertTrue(result)

    def test_exists_by_email_case_insensitive_matching(self):
        """Test exists_by_email performs case-insensitive matching."""
        # Create unsubscribed email in lowercase
        UnsubscribedEmail.objects.create(email='test@example.com')
        
        # Should match regardless of case
        test_cases = [
            'test@example.com',     # exact match
            'TEST@EXAMPLE.COM',     # uppercase
            'Test@Example.Com',     # mixed case
            'test@EXAMPLE.com',     # mixed case domain
        ]
        
        for email in test_cases:
            with self.subTest(email=email):
                result = UnsubscribedEmail.objects.exists_by_email(email)
                self.assertTrue(result, f"Failed to match case variation: {email}")

    def test_exists_by_email_with_empty_string(self):
        """Test exists_by_email handles empty string gracefully."""
        result = UnsubscribedEmail.objects.exists_by_email('')
        self.assertFalse(result)

    def test_exists_by_email_with_none_value(self):
        """Test exists_by_email handles None value gracefully."""
        result = UnsubscribedEmail.objects.exists_by_email(None)
        self.assertFalse(result)

    def test_exists_by_email_with_whitespace_only(self):
        """Test exists_by_email handles whitespace-only string."""
        result = UnsubscribedEmail.objects.exists_by_email('   ')
        self.assertFalse(result)

    def test_exists_by_user_with_valid_user_and_subscribed_email(self):
        """Test exists_by_user returns False for user with subscribed email."""
        # Create user with email
        user = User.objects.create_user(
            email='subscribed@example.com',
            password='testpass'
        )
        
        result = UnsubscribedEmail.objects.exists_by_user(user)
        self.assertFalse(result)

    def test_exists_by_user_with_valid_user_and_unsubscribed_email(self):
        """Test exists_by_user returns True for user with unsubscribed email."""
        # Create user with email
        user = User.objects.create_user(
            email='unsubscribed@example.com',
            password='testpass'
        )
        
        # Create unsubscribed email entry
        UnsubscribedEmail.objects.create(email='unsubscribed@example.com')
        
        result = UnsubscribedEmail.objects.exists_by_user(user)
        self.assertTrue(result)

    def test_exists_by_user_with_user_without_email(self):
        """Test exists_by_user handles user without email gracefully."""
        # Create user without email
        user = User.objects.create_user(
            email='',  # Empty email
            password='testpass'
        )
        
        result = UnsubscribedEmail.objects.exists_by_user(user)
        self.assertFalse(result)

    def test_exists_by_user_with_user_with_none_email(self):
        """Test exists_by_user handles user with None email gracefully."""
        # Create user and set email to None
        user = User.objects.create_user(
            email='temp@example.com',
            password='testpass'
        )
        user.email = None
        user.save()
        
        result = UnsubscribedEmail.objects.exists_by_user(user)
        self.assertFalse(result)

    def test_exists_by_user_case_insensitive_email_matching(self):
        """Test exists_by_user performs case-insensitive email matching."""
        # Create unsubscribed email in lowercase
        UnsubscribedEmail.objects.create(email='test@example.com')
        
        # Create user with uppercase email
        user = User.objects.create_user(
            email='TEST@EXAMPLE.COM',
            password='testpass'
        )
        
        # Should match despite case difference
        result = UnsubscribedEmail.objects.exists_by_user(user)
        self.assertTrue(result)

    def test_exists_by_user_with_mock_user_object(self):
        """Test exists_by_user works with mock user objects."""
        # Create unsubscribed email
        UnsubscribedEmail.objects.create(email='mock@example.com')
        
        # Create mock user object
        mock_user = Mock()
        mock_user.email = 'mock@example.com'
        
        result = UnsubscribedEmail.objects.exists_by_user(mock_user)
        self.assertTrue(result)

    def test_exists_by_user_delegates_to_exists_by_email(self):
        """Test exists_by_user properly delegates to exists_by_email method."""
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass'
        )
        
        # Test delegation behavior by verifying the result is consistent
        # with direct exists_by_email call
        result_via_user = UnsubscribedEmail.objects.exists_by_user(user)
        result_via_email = UnsubscribedEmail.objects.exists_by_email(user.email)
        
        # Both should return the same result
        self.assertEqual(result_via_user, result_via_email)
        
        # Create unsubscribed email and test again
        UnsubscribedEmail.objects.create(email='test@example.com')
        
        result_via_user_after = UnsubscribedEmail.objects.exists_by_user(user)
        result_via_email_after = UnsubscribedEmail.objects.exists_by_email(user.email)
        
        # Both should still return the same result
        self.assertEqual(result_via_user_after, result_via_email_after)
        self.assertTrue(result_via_user_after)  # Should now be True
