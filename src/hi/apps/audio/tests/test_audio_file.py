import logging

from hi.apps.audio.audio_file import AudioFile
from hi.tests.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestAudioFile(BaseTestCase):

    def test_url_generation_produces_valid_static_paths(self):
        """Test that URL generation produces valid static file paths for serving."""
        # Test key audio files used in the system
        test_files = [AudioFile.INFO, AudioFile.WARNING, AudioFile.CRITICAL, AudioFile.TORNADO_SIREN]
        
        for audio_file in test_files:
            url = audio_file.url
            
            # URLs should be valid static paths for web serving
            self.assertTrue(url.startswith('/static/audio/'))
            self.assertTrue(url.endswith('.wav'))
            self.assertIn(audio_file.base_filename, url)
        return

    def test_enum_lookup_by_name_works(self):
        """Test that AudioFile.from_name() lookup works for audio manager functionality."""
        # Test lookup functionality that audio manager depends on
        info_file = AudioFile.from_name('INFO')
        self.assertEqual(info_file, AudioFile.INFO)
        
        warning_file = AudioFile.from_name('WARNING')
        self.assertEqual(warning_file, AudioFile.WARNING)
        
        # Test case insensitive lookup
        critical_file = AudioFile.from_name('critical')
        self.assertEqual(critical_file, AudioFile.CRITICAL)
        return

    def test_audio_file_enum_provides_required_alarm_files(self):
        """Test that required audio files for alarm system are available."""
        # Alarm system requires these specific files
        required_alarm_files = {
            'INFO': AudioFile.INFO,
            'WARNING': AudioFile.WARNING, 
            'CRITICAL': AudioFile.CRITICAL,
            'TORNADO_SIREN': AudioFile.TORNADO_SIREN
        }
        
        for name, expected_file in required_alarm_files.items():
            # Should be able to lookup by name
            found_file = AudioFile.from_name(name)
            self.assertEqual(found_file, expected_file)
            
            # Should have valid URL for serving
            url = found_file.url
            self.assertIsNotNone(url)
            self.assertIn('.wav', url)
        return

    def test_url_generation_uses_base_filename_in_path(self):
        """Test that URL generation includes the base filename in the path."""
        # Test that URLs include the base filename correctly
        chime_url = AudioFile.CHIME.url
        self.assertIn('chime.wav', chime_url)
        
        tornado_url = AudioFile.TORNADO_SIREN.url
        self.assertIn('tornado-siren.wav', tornado_url)
        
        info_url = AudioFile.INFO.url
        self.assertIn('info.wav', info_url)
        return

    def test_audio_file_initialization_sets_properties_correctly(self):
        """Test that AudioFile enum values are initialized with correct properties."""
        # Test a representative sample
        test_cases = [
            (AudioFile.INFO, 'Info', 'info.wav'),
            (AudioFile.TORNADO_SIREN, 'Tornado Siren', 'tornado-siren.wav'),
            (AudioFile.BUZZER, 'Buzzer', 'buzzer.wav')
        ]
        
        for audio_file, expected_label, expected_filename in test_cases:
            self.assertEqual(audio_file.label, expected_label)
            self.assertEqual(audio_file.base_filename, expected_filename)
        return

    def test_audio_file_lookup_handles_invalid_names_with_error(self):
        """Test that AudioFile.from_name() raises ValueError for invalid names."""
        # Should raise ValueError for non-existent names
        with self.assertRaises(ValueError) as context:
            AudioFile.from_name('NONEXISTENT_FILE')
        
        self.assertIn('Unknown name value "NONEXISTENT_FILE"', str(context.exception))
        self.assertIn('AudioFile', str(context.exception))
        
        # Should raise ValueError for empty string
        with self.assertRaises(ValueError) as context:
            AudioFile.from_name('')
        
        self.assertIn('Unknown name value ""', str(context.exception))
        
        # Should raise ValueError for None
        with self.assertRaises(ValueError) as context:
            AudioFile.from_name(None)
        
        self.assertIn('Unknown name value "None"', str(context.exception))
        return

    def test_audio_file_lookup_handles_case_insensitive_matching(self):
        """Test that AudioFile.from_name() handles case variations correctly."""
        # Should work with lowercase
        result = AudioFile.from_name('info')
        self.assertEqual(result, AudioFile.INFO)
        
        # Should work with uppercase
        result = AudioFile.from_name('WARNING')
        self.assertEqual(result, AudioFile.WARNING)
        
        # Should work with mixed case
        result = AudioFile.from_name('ChImE')
        self.assertEqual(result, AudioFile.CHIME)
        
        # Should work with extra whitespace
        result = AudioFile.from_name('  critical  ')
        self.assertEqual(result, AudioFile.CRITICAL)
        return

    def test_audio_file_safe_lookup_returns_default_for_invalid_names(self):
        """Test that AudioFile.from_name_safe() returns default for invalid names."""
        # Should return default (first enum value) for invalid names
        result = AudioFile.from_name_safe('NONEXISTENT_FILE')
        expected_default = AudioFile.default()
        self.assertEqual(result, expected_default)
        
        # Should return default for None
        result = AudioFile.from_name_safe(None)
        self.assertEqual(result, expected_default)
        
        # Should return default for empty string
        result = AudioFile.from_name_safe('')
        self.assertEqual(result, expected_default)
        
        # Should still work normally for valid names
        result = AudioFile.from_name_safe('INFO')
        self.assertEqual(result, AudioFile.INFO)
        return

    def test_audio_file_special_none_value_handling(self):
        """Test that AudioFile.from_name() handles special '_none_' value correctly."""
        # Should return None for special '_none_' value
        result = AudioFile.from_name('_none_')
        self.assertIsNone(result)
        return

