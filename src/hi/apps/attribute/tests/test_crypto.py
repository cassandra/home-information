"""
Unit tests for hi.apps.attribute.crypto

Covers get_cipher(), encrypt_value() and decrypt_value() including edge cases,
error handling, and missing-key misconfiguration.
"""
import logging

from cryptography.fernet import Fernet
from hi.testing.base_test_case import BaseTestCase
from hi.apps.attribute.crypto import encrypt_value, decrypt_value, get_cipher

logging.disable(logging.CRITICAL)

TEST_ENCRYPTION_KEY = Fernet.generate_key().decode('utf-8')


class TestGetCipher(BaseTestCase):
    """Tests for get_cipher() – settings wiring and error handling."""

    def test_returns_fernet_instance_when_key_is_configured(self):
        """get_cipher() should return a Fernet object when MASTER_ENCRYPTION_KEY is set."""
        with self.settings(MASTER_ENCRYPTION_KEY=TEST_ENCRYPTION_KEY):
            cipher = get_cipher()
        self.assertIsInstance(cipher, Fernet)

    def test_raises_value_error_when_key_is_empty(self):
        """get_cipher() must raise ValueError when MASTER_ENCRYPTION_KEY is absent or empty."""
        invalid_keys = [None, '']

        for key in invalid_keys:
            with self.subTest(key=key):
                with self.settings(MASTER_ENCRYPTION_KEY=key):
                    with self.assertRaises(ValueError) as ctx:
                        get_cipher()
                    
                    self.assertIn('MASTER_ENCRYPTION_KEY', str(ctx.exception))

    def test_raises_error_when_key_is_invalid(self):
        """get_cipher() must raise ValueError or TypeError for invalid keys."""
        invalid_format_keys = [
            'too_short_key',
            'this_key_is_way_too_long_to_be_a_valid_fernet_key',
            'not_base64_!@#$%^&*()',
            123456789,
            ['a_list_instead_of_string'],
        ]

        for invalid_key in invalid_format_keys:
            with self.subTest(invalid_key=invalid_key):
                with self.settings(MASTER_ENCRYPTION_KEY=invalid_key):
                    with self.assertRaises((ValueError, TypeError)):
                        get_cipher()


class TestEncryptValue(BaseTestCase):
    """Tests for encrypt_value()."""

    def test_encrypt_returns_non_empty_string(self):
        """Encrypting a plain text value should produce a non-empty token string."""
        with self.settings(MASTER_ENCRYPTION_KEY=TEST_ENCRYPTION_KEY):
            result = encrypt_value('my_secret')
        self.assertIsInstance(result, str)
        self.assertTrue(result)

    def test_encrypted_value_differs_from_plain_text(self):
        """The ciphertext must not equal the original plain text."""
        plain = 'my_secret'
        with self.settings(MASTER_ENCRYPTION_KEY=TEST_ENCRYPTION_KEY):
            result = encrypt_value(plain)
        self.assertNotEqual(result, plain)

    def test_two_encryptions_of_same_value_differ(self):
        """Fernet uses a random Initialization Vector (IV), so two encryptions of the same plain text differ."""
        with self.settings(MASTER_ENCRYPTION_KEY=TEST_ENCRYPTION_KEY):
            first = encrypt_value('my_secret')
            second = encrypt_value('my_secret')
        self.assertNotEqual(first, second)

    def test_returns_falsy_values_unchanged(self):
        """encrypt_value() should return falsy values ('', None) unchanged."""
        falsy_values = ['', None]

        with self.settings(MASTER_ENCRYPTION_KEY=TEST_ENCRYPTION_KEY):
            for value in falsy_values:
                with self.subTest(value=value):
                    result = encrypt_value(value)
                    self.assertEqual(result, value)

    def test_encrypts_unicode_text(self):
        """encrypt_value() should handle UTF-8 content such as accented characters."""
        unicode_text = 'café résumé naïve'
        with self.settings(MASTER_ENCRYPTION_KEY=TEST_ENCRYPTION_KEY):
            result = encrypt_value(unicode_text)
        self.assertIsInstance(result, str)
        self.assertNotEqual(result, unicode_text)

    def test_raises_without_key_configured(self):
        """encrypt_value() must propagate the ValueError from get_cipher()."""
        with self.settings(MASTER_ENCRYPTION_KEY=None):
            with self.assertRaises(ValueError):
                encrypt_value('my_secret')


class TestDecryptValue(BaseTestCase):
    """Tests for decrypt_value()."""

    def test_decrypt_recovers_original_plain_text(self):
        """Round-trip: decrypt(encrypt(x)) == x."""
        plain = 'my_secret'
        with self.settings(MASTER_ENCRYPTION_KEY=TEST_ENCRYPTION_KEY):
            recovered = decrypt_value( encrypt_value(plain) )
        self.assertEqual(recovered, plain)

    def test_decrypt_recovers_unicode_text(self):
        """Round-trip with non-ASCII characters should preserve all code-points."""
        plain = 'pässwörd_ñoño'
        with self.settings(MASTER_ENCRYPTION_KEY=TEST_ENCRYPTION_KEY):
            recovered = decrypt_value( encrypt_value(plain) )
        self.assertEqual(recovered, plain)

    def test_returns_falsy_values_unchanged(self):
        """decrypt_value() must return falsy values ('', None) without attempting decryption."""
        falsy_values = ['', None]

        with self.settings(MASTER_ENCRYPTION_KEY=TEST_ENCRYPTION_KEY):
            for value in falsy_values:
                with self.subTest(value=value):
                    result = decrypt_value(value)
                    self.assertEqual(result, value)

    def test_raises_without_key_configured(self):
        """decrypt_value() must propagate the ValueError from get_cipher()."""
        with self.settings(MASTER_ENCRYPTION_KEY=None):
            with self.assertRaises(ValueError):
                decrypt_value('my_secret')


class TestEncryptDecryptRoundTrip(BaseTestCase):
    """Integration-style round-trip tests ensuring symmetry."""

    def test_round_trip_preserves_whitespace(self):
        """Leading/trailing whitespace in the plain text must be preserved."""
        plain = '   padded value   '
        with self.settings(MASTER_ENCRYPTION_KEY=TEST_ENCRYPTION_KEY):
            self.assertEqual(decrypt_value(encrypt_value(plain)), plain)

    def test_round_trip_preserves_newlines(self):
        """Newline characters inside the value must survive the round-trip."""
        plain = 'line1\nline2\nline3'
        with self.settings(MASTER_ENCRYPTION_KEY=TEST_ENCRYPTION_KEY):
            self.assertEqual(decrypt_value(encrypt_value(plain)), plain)

    def test_round_trip_preserves_special_characters(self):
        """Special characters (symbols, punctuation) must be preserved exactly."""
        plain = '!@#$%^&*()_+-=[]{}|;\':",.<>?/`~\\'
        with self.settings(MASTER_ENCRYPTION_KEY=TEST_ENCRYPTION_KEY):
            self.assertEqual(decrypt_value(encrypt_value(plain)), plain)

    def test_round_trip_with_long_value(self):
        """Encryption/decryption must work for values well beyond a single block."""
        plain = 'A' * 10_000
        with self.settings(MASTER_ENCRYPTION_KEY=TEST_ENCRYPTION_KEY):
            self.assertEqual(decrypt_value(encrypt_value(plain)), plain)
