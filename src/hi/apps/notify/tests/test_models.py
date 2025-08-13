import logging
from django.db import IntegrityError

from hi.apps.notify.models import UnsubscribedEmail
from hi.tests.base_test_case import BaseTestCase

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
