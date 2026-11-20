import logging

from django.test import TestCase

from hi.apps.user.constants import UserConstants
from hi.apps.user.forms import SigninMagicCodeForm

logging.disable(logging.CRITICAL)


class TestSigninMagicCodeForm(TestCase):

    def is_valid(self, magic_code):
        return SigninMagicCodeForm(data={'magic_code': magic_code}).is_valid()

    def test_missing_code_is_invalid(self):
        self.assertFalse(self.is_valid(''))

    def test_code_with_room_for_separators_is_valid_but_no_longer(self):
        room = 2 * UserConstants.MAGIC_CODE_KEYPAD.length

        self.assertTrue(self.is_valid('x' * room))
        self.assertFalse(self.is_valid('x' * (room + 1)))
