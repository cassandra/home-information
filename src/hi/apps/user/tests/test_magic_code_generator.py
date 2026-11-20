import logging
from unittest.mock import Mock, patch

from hi.apps.user.magic_code_generator import MagicCodeGenerator, MagicCodeStatus
from hi.testing.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestMagicCodeGenerator(BaseTestCase):

    EMAIL = 'user@example.com'

    def setUp(self):
        super().setUp()
        self.generator = MagicCodeGenerator()
        self.mock_request = Mock()
        self.mock_request.session = {}

    def make_code(self):
        return self.generator.make_magic_code(self.mock_request, email_address=self.EMAIL)

    def redeem(self, magic_code, email_address=EMAIL):
        return self.generator.redeem_magic_code(self.mock_request,
                                                email_address=email_address,
                                                magic_code=magic_code)

    def test_make_magic_code_uses_allowed_alphabet(self):
        magic_code = self.make_code()

        self.assertEqual(len(magic_code), MagicCodeGenerator.MAGIC_CODE_LENGTH)
        self.assertTrue(all(c in MagicCodeGenerator.MAGIC_CODE_CHARS for c in magic_code))

    def test_correct_code_is_valid_and_single_use(self):
        magic_code = self.make_code()

        self.assertEqual(self.redeem(magic_code), MagicCodeStatus.VALID)
        self.assertEqual(self.redeem(magic_code), MagicCodeStatus.INVALID)

    def test_code_entry_ignores_case_whitespace_and_dashes(self):
        magic_code = self.make_code()

        result = self.redeem(f' {magic_code[:3].upper()}-{magic_code[3:]} ')

        self.assertEqual(result, MagicCodeStatus.VALID)

    def test_no_code_in_session_is_invalid(self):
        self.assertEqual(self.redeem('abcdef'), MagicCodeStatus.INVALID)

    def test_correct_code_with_different_email_is_invalid(self):
        magic_code = self.make_code()

        self.assertEqual(self.redeem(magic_code, email_address='other@example.com'), MagicCodeStatus.INVALID)

    def test_wrong_guesses_under_limit_keep_code_usable(self):
        magic_code = self.make_code()
        for _ in range(MagicCodeGenerator.MAX_FAILED_ATTEMPTS - 1):
            self.assertEqual(self.redeem('wxyzwx'), MagicCodeStatus.INVALID)

        self.assertEqual(self.redeem(magic_code), MagicCodeStatus.VALID)

    def test_reaching_failed_attempt_limit_discards_code(self):
        magic_code = self.make_code()
        for _ in range(MagicCodeGenerator.MAX_FAILED_ATTEMPTS - 1):
            self.redeem('wxyzwx')

        final_attempt = self.redeem(magic_code, email_address='other@example.com')

        self.assertEqual(final_attempt, MagicCodeStatus.TOO_MANY_ATTEMPTS)
        self.assertEqual(self.redeem(magic_code), MagicCodeStatus.INVALID)

    def test_new_code_resets_failed_attempts(self):
        self.make_code()
        for _ in range(MagicCodeGenerator.MAX_FAILED_ATTEMPTS - 1):
            self.redeem('wxyzwx')
        magic_code = self.make_code()
        for _ in range(MagicCodeGenerator.MAX_FAILED_ATTEMPTS - 1):
            self.redeem('wxyzwx')

        self.assertEqual(self.redeem(magic_code), MagicCodeStatus.VALID)

    @patch.object(MagicCodeGenerator, 'get_elapsed_seconds')
    def test_old_code_is_expired_and_discarded(self, mock_elapsed_seconds):
        mock_elapsed_seconds.return_value = 1000
        magic_code = self.make_code()
        mock_elapsed_seconds.return_value = 1000 + MagicCodeGenerator.MAGIC_CODE_TIMEOUT_SECS + 1

        self.assertEqual(self.redeem(magic_code), MagicCodeStatus.EXPIRED)
        self.assertEqual(self.redeem(magic_code), MagicCodeStatus.INVALID)

    @patch.object(MagicCodeGenerator, 'get_elapsed_seconds')
    def test_code_at_timeout_boundary_is_valid(self, mock_elapsed_seconds):
        mock_elapsed_seconds.return_value = 1000
        magic_code = self.make_code()
        mock_elapsed_seconds.return_value = 1000 + MagicCodeGenerator.MAGIC_CODE_TIMEOUT_SECS

        self.assertEqual(self.redeem(magic_code), MagicCodeStatus.VALID)
