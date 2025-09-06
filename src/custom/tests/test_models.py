import logging

from django.contrib.auth import get_user_model
from django.test import TestCase

from custom.models import CustomUser

logging.disable(logging.CRITICAL)


class UsersManagersTests(TestCase):

    def test_create_user(self):
        User = get_user_model()
        user = User.objects.create_user()
        self.assertIsInstance( user, CustomUser  )
        user = User.objects.create_user(email=None, password="foo")
        self.assertIsInstance( user, CustomUser  )
        user = User.objects.create_user(email="")
        self.assertIsInstance( user, CustomUser  )
        user = User.objects.create_user(email="     ")
        self.assertIsInstance( user, CustomUser  )
        user = User.objects.create_user(email="     ")  # Should force to None so no duplicate
        self.assertIsInstance( user, CustomUser  )
        user = User.objects.create_user(email="normal@example.com", password="foo")
        self.assertIsInstance( user, CustomUser  )
        self.assertEqual(user.email, "normal@example.com")
        self.assertTrue( len(user.email) > 10 )
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        return
    
    def test_create_superuser(self):
        User = get_user_model()
        admin_user = User.objects.create_user(email=None, password="foo")
        self.assertIsInstance( admin_user, CustomUser  )
        admin_user = User.objects.create_superuser(email="super@example.com", password="foo")
        self.assertIsInstance( admin_user, CustomUser  )
        self.assertEqual(admin_user.email, "super@example.com")
        self.assertTrue( len(admin_user.email) > 10 )
        self.assertTrue(admin_user.is_active)
        self.assertTrue(admin_user.is_staff)
        self.assertTrue(admin_user.is_superuser)
        with self.assertRaises(ValueError):
            User.objects.create_superuser(
                email="super@example.com", password="foo", is_superuser=False)
        return

