import logging

from django.test import TestCase

from hi.apps.user.constants import UserConstants
from hi.apps.user.forms import SigninMagicCodeForm

logging.disable(logging.CRITICAL)


class TestSigninMagicCodeForm(TestCase):

    def is_valid(self, email_address='test@example.com', magic_code='abcdef'):
        return SigninMagicCodeForm(data={
            'email_address': email_address,
            'magic_code': magic_code,
        }).is_valid()

    def test_email_and_code_are_valid(self):
        self.assertTrue(self.is_valid())

    def test_missing_fields_are_invalid(self):
        self.assertFalse(self.is_valid(magic_code=''))
        self.assertFalse(self.is_valid(email_address=''))

    def test_code_with_room_for_separators_is_valid_but_no_longer(self):
        room = 2 * UserConstants.MAGIC_CODE_KEYPAD.length

        self.assertTrue(self.is_valid(magic_code='x' * room))
        self.assertFalse(self.is_valid(magic_code='x' * (room + 1)))
