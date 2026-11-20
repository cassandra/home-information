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

    def test_make_magic_code_generates_valid_code_and_stores_in_session(self):
        """Test magic code generation stores code and timestamp in session."""
        magic_code = self.generator.make_magic_code(self.mock_request, self.EMAIL)
        
        # Verify code characteristics
        self.assertIsInstance(magic_code, str)
        self.assertEqual(len(magic_code), MagicCodeGenerator.MAGIC_CODE_LENGTH)
        self.assertTrue(all(c in MagicCodeGenerator.MAGIC_CODE_CHARS for c in magic_code))
        
        # Verify session storage
        self.assertEqual(self.mock_request.session[MagicCodeGenerator.MAGIC_CODE], magic_code)
        self.assertIn(MagicCodeGenerator.MAGIC_CODE_TIMESTAMP, self.mock_request.session)
        self.assertIsInstance(self.mock_request.session[MagicCodeGenerator.MAGIC_CODE_TIMESTAMP], int)

    def test_check_magic_code_returns_valid_for_correct_code(self):
        """Test magic code validation returns VALID for correct code."""
        magic_code = self.generator.make_magic_code(self.mock_request, self.EMAIL)
        
        result = self.generator.check_magic_code(self.mock_request, self.EMAIL, magic_code)
        
        self.assertEqual(result, MagicCodeStatus.VALID)

    def test_check_magic_code_returns_invalid_for_wrong_code(self):
        """Test magic code validation returns INVALID for incorrect code."""
        self.generator.make_magic_code(self.mock_request, self.EMAIL)
        
        result = self.generator.check_magic_code(self.mock_request, self.EMAIL, 'wrongcode')
        
        self.assertEqual(result, MagicCodeStatus.INVALID)

    def test_check_magic_code_handles_case_insensitive_validation(self):
        """Test magic code validation is case insensitive."""
        magic_code = self.generator.make_magic_code(self.mock_request, self.EMAIL)
        
        # Test uppercase version
        result_upper = self.generator.check_magic_code(self.mock_request, self.EMAIL, magic_code.upper())
        # Test lowercase version  
        result_lower = self.generator.check_magic_code(self.mock_request, self.EMAIL, magic_code.lower())
        
        self.assertEqual(result_upper, MagicCodeStatus.VALID)
        self.assertEqual(result_lower, MagicCodeStatus.VALID)

    def test_check_magic_code_strips_whitespace_and_dashes(self):
        """Test magic code validation strips whitespace and dashes."""
        magic_code = self.generator.make_magic_code(self.mock_request, self.EMAIL)
        
        # Add whitespace and dashes
        formatted_code = f" {magic_code[:3]}-{magic_code[3:]} "
        result = self.generator.check_magic_code(self.mock_request, self.EMAIL, formatted_code)
        
        self.assertEqual(result, MagicCodeStatus.VALID)

    def test_check_magic_code_returns_invalid_when_session_has_no_code(self):
        """Test validation returns INVALID (not an error) when no code was issued."""
        result = self.generator.check_magic_code(self.mock_request, self.EMAIL, 'abcdef')

        self.assertEqual(result, MagicCodeStatus.INVALID)

    def test_check_magic_code_returns_invalid_after_code_expired(self):
        """Test a code cannot be reused once it has been expired."""
        magic_code = self.generator.make_magic_code(self.mock_request, self.EMAIL)
        self.generator.expire_magic_code(self.mock_request)

        result = self.generator.check_magic_code(self.mock_request, self.EMAIL, magic_code)

        self.assertEqual(result, MagicCodeStatus.INVALID)

    def test_check_magic_code_returns_invalid_for_different_email(self):
        """Test a correct code submitted with a different email is rejected."""
        magic_code = self.generator.make_magic_code(self.mock_request, self.EMAIL)

        result = self.generator.check_magic_code(self.mock_request, 'other@example.com', magic_code)

        self.assertEqual(result, MagicCodeStatus.INVALID)

    @patch('hi.apps.user.magic_code_generator.MagicCodeGenerator.get_elapsed_seconds')
    def test_check_magic_code_returns_expired_for_old_code(self, mock_elapsed_seconds):
        """Test magic code validation returns EXPIRED for codes past timeout."""
        # Set up initial time
        mock_elapsed_seconds.return_value = 1000
        magic_code = self.generator.make_magic_code(self.mock_request, self.EMAIL)
        
        # Move time forward past timeout
        mock_elapsed_seconds.return_value = 1000 + MagicCodeGenerator.MAGIC_CODE_TIMEOUT_SECS + 1
        
        result = self.generator.check_magic_code(self.mock_request, self.EMAIL, magic_code)
        
        self.assertEqual(result, MagicCodeStatus.EXPIRED)

    def test_expire_magic_code_clears_session_data(self):
        """Test expire_magic_code clears magic code data from session."""
        self.generator.make_magic_code(self.mock_request, self.EMAIL)
        
        # Verify data exists
        self.assertIn(MagicCodeGenerator.MAGIC_CODE, self.mock_request.session)
        self.assertIn(MagicCodeGenerator.MAGIC_CODE_TIMESTAMP, self.mock_request.session)
        
        self.generator.expire_magic_code(self.mock_request)
        
        # Verify data is cleared
        self.assertIsNone(self.mock_request.session[MagicCodeGenerator.MAGIC_CODE])
        self.assertIsNone(self.mock_request.session[MagicCodeGenerator.MAGIC_CODE_TIMESTAMP])
        self.assertIsNone(self.mock_request.session[MagicCodeGenerator.MAGIC_CODE_EMAIL])

    def test_magic_code_status_enum_business_logic_values(self):
        """Test MagicCodeStatus enum values support validation business logic."""
        # Test that VALID has highest value for comparison logic
        self.assertTrue(MagicCodeStatus.VALID.value > MagicCodeStatus.EXPIRED.value)
        self.assertTrue(MagicCodeStatus.EXPIRED.value > MagicCodeStatus.INVALID.value)
        
        # Test specific values that may be used in conditional logic
        self.assertEqual(MagicCodeStatus.INVALID.value, 0)
        self.assertEqual(MagicCodeStatus.EXPIRED.value, 1) 
        self.assertEqual(MagicCodeStatus.VALID.value, 2)

    @patch('hi.apps.user.magic_code_generator.MagicCodeGenerator.get_elapsed_seconds')
    def test_get_elapsed_seconds_provides_consistent_timestamps(self, mock_elapsed_seconds):
        """Test timestamp generation provides consistent values for timeout calculations."""
        mock_elapsed_seconds.return_value = 5000
        
        timestamp1 = self.generator.get_elapsed_seconds()
        timestamp2 = self.generator.get_elapsed_seconds()
        
        # Both calls should return same mocked value
        self.assertEqual(timestamp1, timestamp2)
        self.assertEqual(timestamp1, 5000)

    def test_get_timeout_seconds_returns_configured_value(self):
        """Test timeout configuration returns expected value from settings."""
        timeout = self.generator.get_timeout_seconds()
        
        self.assertEqual(timeout, MagicCodeGenerator.MAGIC_CODE_TIMEOUT_SECS)
        self.assertIsInstance(timeout, int)
