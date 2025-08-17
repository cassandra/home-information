import logging

from django import forms
from django.test import TestCase

from hi.apps.user.forms import SigninMagicCodeForm
from hi.apps.user.magic_code_generator import MagicCodeGenerator

logging.disable(logging.CRITICAL)


class TestSigninMagicCodeForm(TestCase):

    def test_signin_magic_code_form_initialization(self):
        """Test SigninMagicCodeForm initializes correctly with default configuration."""
        form = SigninMagicCodeForm()
        
        # Verify form has expected fields
        self.assertIn('email_address', form.fields)
        self.assertIn('magic_code', form.fields)

    def test_email_address_field_configuration(self):
        """Test email_address field has correct widget and validation settings."""
        form = SigninMagicCodeForm()
        email_field = form.fields['email_address']
        
        # Verify field type and max length
        self.assertIsInstance(email_field, forms.CharField)
        self.assertEqual(email_field.max_length, 128)
        
        # Verify hidden input widget
        self.assertIsInstance(email_field.widget, forms.HiddenInput)

    def test_magic_code_field_configuration(self):
        """Test magic_code field has correct widget and validation settings."""
        form = SigninMagicCodeForm()
        magic_code_field = form.fields['magic_code']
        
        # Verify field type and properties
        self.assertIsInstance(magic_code_field, forms.CharField)
        self.assertEqual(magic_code_field.max_length, 2 * MagicCodeGenerator.MAGIC_CODE_LENGTH)
        self.assertTrue(magic_code_field.required)
        self.assertEqual(magic_code_field.label, '')

    def test_magic_code_field_widget_attributes(self):
        """Test magic_code field widget has correct HTML attributes."""
        form = SigninMagicCodeForm()
        magic_code_field = form.fields['magic_code']
        
        # Verify widget type
        self.assertIsInstance(magic_code_field.widget, forms.TextInput)
        
        # Verify widget attributes
        widget_attrs = magic_code_field.widget.attrs
        self.assertEqual(widget_attrs['autofocus'], 'autofocus')
        self.assertEqual(widget_attrs['placeholder'], 'access code')
        self.assertEqual(widget_attrs['width'], str(2 * MagicCodeGenerator.MAGIC_CODE_LENGTH))

    def test_form_validation_with_valid_data(self):
        """Test form validation passes with valid email and magic code."""
        form_data = {
            'email_address': 'test@example.com',
            'magic_code': 'abc123'
        }
        form = SigninMagicCodeForm(data=form_data)
        
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['email_address'], 'test@example.com')
        self.assertEqual(form.cleaned_data['magic_code'], 'abc123')

    def test_form_validation_fails_without_magic_code(self):
        """Test form validation fails when magic_code is missing."""
        form_data = {
            'email_address': 'test@example.com',
            'magic_code': ''
        }
        form = SigninMagicCodeForm(data=form_data)
        
        self.assertFalse(form.is_valid())
        self.assertIn('magic_code', form.errors)

    def test_form_validation_fails_without_email_address(self):
        """Test form validation fails when email_address is missing."""
        form_data = {
            'email_address': '',
            'magic_code': 'abc123'
        }
        form = SigninMagicCodeForm(data=form_data)
        
        self.assertFalse(form.is_valid())
        self.assertIn('email_address', form.errors)

    def test_form_handles_magic_code_length_constraint(self):
        """Test form handles magic code length based on generator constraints."""
        # Test with code at max length (should be valid)
        max_length_code = 'x' * (2 * MagicCodeGenerator.MAGIC_CODE_LENGTH)
        form_data = {
            'email_address': 'test@example.com',
            'magic_code': max_length_code
        }
        form = SigninMagicCodeForm(data=form_data)
        
        self.assertTrue(form.is_valid())

    def test_form_handles_oversized_magic_code(self):
        """Test form validation fails with oversized magic code."""
        # Test with code exceeding max length (should be invalid)
        oversized_code = 'x' * (2 * MagicCodeGenerator.MAGIC_CODE_LENGTH + 1)
        form_data = {
            'email_address': 'test@example.com',
            'magic_code': oversized_code
        }
        form = SigninMagicCodeForm(data=form_data)
        
        self.assertFalse(form.is_valid())
        self.assertIn('magic_code', form.errors)

    def test_form_initialization_with_initial_data(self):
        """Test form initialization with initial email address."""
        initial_data = {'email_address': 'initial@example.com'}
        form = SigninMagicCodeForm(initial=initial_data)
        
        # Verify initial data is set
        self.assertEqual(form.initial['email_address'], 'initial@example.com')
        
        # Verify field still has correct configuration
        email_field = form.fields['email_address']
        self.assertIsInstance(email_field.widget, forms.HiddenInput)

    def test_form_magic_code_length_matches_generator_configuration(self):
        """Test form magic code max length correctly reflects generator configuration."""
        form = SigninMagicCodeForm()
        magic_code_field = form.fields['magic_code']
        
        # Verify max length is exactly double the generator's code length
        expected_max_length = 2 * MagicCodeGenerator.MAGIC_CODE_LENGTH
        self.assertEqual(magic_code_field.max_length, expected_max_length)
        
        # Verify widget width attribute matches max length
        widget_width = magic_code_field.widget.attrs['width']
        self.assertEqual(widget_width, str(expected_max_length))

    def test_form_field_ordering(self):
        """Test form fields appear in expected order."""
        form = SigninMagicCodeForm()
        field_names = list(form.fields.keys())
        
        # Verify email_address comes before magic_code
        self.assertEqual(field_names[0], 'email_address')
        self.assertEqual(field_names[1], 'magic_code')

    def test_form_handles_whitespace_in_magic_code(self):
        """Test form accepts magic code with whitespace (Django strips leading/trailing whitespace)."""
        form_data = {
            'email_address': 'test@example.com',
            'magic_code': ' abc 123 '
        }
        form = SigninMagicCodeForm(data=form_data)
        
        # Form validation should pass (Django strips leading/trailing whitespace by default)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['magic_code'], 'abc 123')
