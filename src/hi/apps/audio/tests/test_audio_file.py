import logging

from hi.apps.audio.audio_file import AudioFile
from hi.tests.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestAudioFile(BaseTestCase):

    def test_audio_file_url_generation(self):
        """Test URL generation logic - critical for audio file serving."""
        # Test URL generation for different audio files
        info_url = AudioFile.INFO.url
        warning_url = AudioFile.WARNING.url
        critical_url = AudioFile.CRITICAL.url
        
        # URLs should contain the audio path and filename
        self.assertIn('audio/', info_url)
        self.assertIn('info.wav', info_url)
        
        self.assertIn('audio/', warning_url)
        self.assertIn('warning.wav', warning_url)
        
        self.assertIn('audio/', critical_url)
        self.assertIn('critical.wav', critical_url)
        
        # URLs should be different
        self.assertNotEqual(info_url, warning_url)
        self.assertNotEqual(warning_url, critical_url)
        return

    def test_audio_file_base_filename_property(self):
        """Test base_filename property - critical for file mapping."""
        # Test that base filenames match expected values
        self.assertEqual(AudioFile.INFO.base_filename, 'info.wav')
        self.assertEqual(AudioFile.WARNING.base_filename, 'warning.wav')
        self.assertEqual(AudioFile.CRITICAL.base_filename, 'critical.wav')
        self.assertEqual(AudioFile.CHIME.base_filename, 'chime.wav')
        self.assertEqual(AudioFile.BUZZER.base_filename, 'buzzer.wav')
        return

    def test_audio_file_labels(self):
        """Test AudioFile labels - important for UI display."""
        self.assertEqual(AudioFile.INFO.label, 'Info')
        self.assertEqual(AudioFile.WARNING.label, 'Warning')
        self.assertEqual(AudioFile.CRITICAL.label, 'Critical')
        self.assertEqual(AudioFile.CHIME.label, 'Chime')
        self.assertEqual(AudioFile.BUZZER.label, 'Buzzer')
        self.assertEqual(AudioFile.TORNADO_SIREN.label, 'Tornado Siren')
        return

    def test_audio_file_alarm_related_files_exist(self):
        """Test that alarm-related audio files exist - critical for alert functionality."""
        # Should have audio files for all alarm levels
        alarm_related_files = [AudioFile.INFO, AudioFile.WARNING, AudioFile.CRITICAL]
        
        for audio_file in alarm_related_files:
            # Should have proper label and filename
            self.assertIsNotNone(audio_file.label)
            self.assertIsNotNone(audio_file.base_filename)
            self.assertTrue(audio_file.base_filename.endswith('.wav'))
            
            # URL should be generated
            url = audio_file.url
            self.assertIsNotNone(url)
            self.assertIn('audio/', url)
        return

    def test_audio_file_uniqueness(self):
        """Test AudioFile enum value uniqueness - critical for avoiding conflicts."""
        # All base filenames should be unique
        filenames = [audio_file.base_filename for audio_file in AudioFile]
        unique_filenames = set(filenames)
        self.assertEqual(len(filenames), len(unique_filenames))
        
        # All labels should be unique
        labels = [audio_file.label for audio_file in AudioFile]
        unique_labels = set(labels)
        self.assertEqual(len(labels), len(unique_labels))
        return