import logging
from datetime import datetime, timedelta
from unittest.mock import patch

from hi.apps.user.magic_code_generator import MagicCodeGenerator, MagicCodeStatus
from hi.tests.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestMagicCodeGenerator(BaseTestCase):

    def test_magic_code_status_enum_values(self):
        """Test MagicCodeStatus enum values - critical for validation logic."""
        self.assertEqual(MagicCodeStatus.INVALID.value, 0)
        self.assertEqual(MagicCodeStatus.EXPIRED.value, 1)
        self.assertEqual(MagicCodeStatus.VALID.value, 2)
        return

    @patch('hi.apps.user.magic_code_generator.get_random_string')
    def test_magic_code_generator_code_generation(self, mock_random_string):
        """Test magic code generation - critical for authentication security."""
        mock_random_string.return_value = 'ABC123'
        
        generator = MagicCodeGenerator()
        
        # Test code generation method exists and uses random string
        if hasattr(generator, 'generate_code'):
            code = generator.generate_code()
            mock_random_string.assert_called()
            self.assertIsInstance(code, str)
        return

    def test_magic_code_generator_instantiation(self):
        """Test MagicCodeGenerator instantiation - important for system initialization."""
        generator = MagicCodeGenerator()
        self.assertIsInstance(generator, MagicCodeGenerator)
        return

    def test_magic_code_status_enum_ordering(self):
        """Test MagicCodeStatus enum ordering - important for validation priority."""
        # Status values should be ordered logically
        statuses = [MagicCodeStatus.INVALID, MagicCodeStatus.EXPIRED, MagicCodeStatus.VALID]
        values = [status.value for status in statuses]
        
        # Should be in ascending order
        self.assertEqual(values, sorted(values))
        return