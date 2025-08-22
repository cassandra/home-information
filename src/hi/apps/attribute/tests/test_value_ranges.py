import logging
from unittest.mock import patch

from hi.apps.attribute.value_ranges import PredefinedValueRanges
from hi.testing.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestPredefinedValueRanges(BaseTestCase):

    def test_predefined_value_ranges_known_ids_mapping(self):
        """Test known ID to choices mapping - critical for predefined attribute functionality."""
        # Test that all predefined IDs are in the mapping
        expected_ids = {
            PredefinedValueRanges.TIMEZONE_CHOICES_ID,
            PredefinedValueRanges.UNITS_CHOICES_ID,
            PredefinedValueRanges.THEME_CHOICES_ID,
            PredefinedValueRanges.AUDIO_FILE_CHOICES_ID,
            PredefinedValueRanges.TIME_OF_DAY_CHOICES_ID,
        }
        
        actual_ids = set(PredefinedValueRanges.ID_TO_CHOICES.keys())
        self.assertEqual(actual_ids, expected_ids)
        return

    def test_predefined_value_ranges_get_choices_valid_id(self):
        """Test get_choices with valid ID - critical for choices lookup."""
        # Test with a known ID
        choices = PredefinedValueRanges.get_choices(PredefinedValueRanges.TIME_OF_DAY_CHOICES_ID)
        
        # Should return a list of tuples
        self.assertIsInstance(choices, list)
        if choices:  # If not empty
            self.assertIsInstance(choices[0], tuple)
            self.assertEqual(len(choices[0]), 2)  # Each choice should be (value, label)
        return

    def test_predefined_value_ranges_get_choices_invalid_id(self):
        """Test get_choices with invalid ID - error handling."""
        choices = PredefinedValueRanges.get_choices('invalid.id')
        
        # Should return None for unknown IDs
        self.assertIsNone(choices)
        return

    @patch('hi.apps.attribute.value_ranges.TIMEZONE_NAME_LIST')
    def test_predefined_value_ranges_timezone_choices_generation(self, mock_timezone_list):
        """Test timezone choices generation - complex list processing."""
        mock_timezone_list = ['UTC', 'America/New_York', 'Europe/London']
        
        # Patch the ID_TO_CHOICES to use our mock
        with patch.object(PredefinedValueRanges, 'ID_TO_CHOICES', {
            PredefinedValueRanges.TIMEZONE_CHOICES_ID: [(x, x) for x in mock_timezone_list]
        }):
            choices = PredefinedValueRanges.get_choices(PredefinedValueRanges.TIMEZONE_CHOICES_ID)
            
            expected = [('UTC', 'UTC'), ('America/New_York', 'America/New_York'), ('Europe/London', 'Europe/London')]
            self.assertEqual(choices, expected)
        return

    def test_predefined_value_ranges_id_constants_immutability(self):
        """Test predefined ID constants - critical for API stability."""
        # These constants should never change as they may be stored in database
        self.assertEqual(PredefinedValueRanges.TIMEZONE_CHOICES_ID, 'hi.timezone')
        self.assertEqual(PredefinedValueRanges.UNITS_CHOICES_ID, 'hi.units')
        self.assertEqual(PredefinedValueRanges.THEME_CHOICES_ID, 'hi.theme')
        self.assertEqual(PredefinedValueRanges.AUDIO_FILE_CHOICES_ID, 'hi.audio.file')
        self.assertEqual(PredefinedValueRanges.TIME_OF_DAY_CHOICES_ID, 'hi.datetime.time-of-day')
        return

    @patch('hi.apps.attribute.value_ranges.DisplayUnits')
    @patch('hi.apps.attribute.value_ranges.Theme')
    @patch('hi.apps.attribute.value_ranges.AudioFile')
    def test_predefined_value_ranges_enum_integration(self, mock_audio_file, mock_theme, mock_display_units):
        """Test integration with enum choices - external dependency handling."""
        # Mock the enum choices methods
        mock_display_units.choices.return_value = [('metric', 'Metric'), ('imperial', 'Imperial')]
        mock_theme.choices.return_value = [('light', 'Light'), ('dark', 'Dark')]
        mock_audio_file.choices.return_value = [('beep.wav', 'Beep'), ('chime.wav', 'Chime')]
        
        # Test that the mapping calls the enum methods
        with patch.object(PredefinedValueRanges, 'ID_TO_CHOICES', {
            PredefinedValueRanges.UNITS_CHOICES_ID: mock_display_units.choices(),
            PredefinedValueRanges.THEME_CHOICES_ID: mock_theme.choices(),
            PredefinedValueRanges.AUDIO_FILE_CHOICES_ID: mock_audio_file.choices(),
        }):
            units_choices = PredefinedValueRanges.get_choices(PredefinedValueRanges.UNITS_CHOICES_ID)
            theme_choices = PredefinedValueRanges.get_choices(PredefinedValueRanges.THEME_CHOICES_ID)
            audio_choices = PredefinedValueRanges.get_choices(PredefinedValueRanges.AUDIO_FILE_CHOICES_ID)
            
            self.assertEqual(units_choices, [('metric', 'Metric'), ('imperial', 'Imperial')])
            self.assertEqual(theme_choices, [('light', 'Light'), ('dark', 'Dark')])
            self.assertEqual(audio_choices, [('beep.wav', 'Beep'), ('chime.wav', 'Chime')])
        return
