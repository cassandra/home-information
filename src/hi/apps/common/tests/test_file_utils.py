from unittest.mock import patch

from hi.apps.common.file_utils import derive_new_unique_filename, generate_unique_filename
from hi.testing.base_test_case import BaseTestCase


class TestDeriveNewUniqueFilename(BaseTestCase):

    @patch('hi.apps.common.file_utils.time')
    def test_replaces_existing_timestamp(self, mock_time):
        """An existing timestamp suffix is replaced, not appended."""
        mock_time.time.return_value = 9999999999
        result = derive_new_unique_filename('location/svg/my-file-1713285600.svg')
        self.assertEqual(result, 'location/svg/my-file-9999999999.svg')

    @patch('hi.apps.common.file_utils.time')
    def test_adds_timestamp_when_none_exists(self, mock_time):
        """A filename without a timestamp gets one added."""
        mock_time.time.return_value = 9999999999
        result = derive_new_unique_filename('location/svg/my-file.svg')
        self.assertEqual(result, 'location/svg/my-file-9999999999.svg')

    @patch('hi.apps.common.file_utils.time')
    def test_preserves_directory_path(self, mock_time):
        """The directory portion of the path is preserved."""
        mock_time.time.return_value = 1000000000
        result = derive_new_unique_filename('some/deep/path/file-5555.svg')
        self.assertEqual(result, 'some/deep/path/file-1000000000.svg')

    @patch('hi.apps.common.file_utils.time')
    def test_preserves_extension(self, mock_time):
        """The file extension is preserved."""
        mock_time.time.return_value = 1000000000
        result = derive_new_unique_filename('file-5555.html')
        self.assertEqual(result, 'file-1000000000.html')

    @patch('hi.apps.common.file_utils.time')
    def test_does_not_accumulate_timestamps(self, mock_time):
        """Calling repeatedly does not grow the filename."""
        mock_time.time.return_value = 1111111111
        first = derive_new_unique_filename('location/svg/my-file-1000000000.svg')
        self.assertEqual(first, 'location/svg/my-file-1111111111.svg')

        mock_time.time.return_value = 2222222222
        second = derive_new_unique_filename(first)
        self.assertEqual(second, 'location/svg/my-file-2222222222.svg')

    @patch('hi.apps.common.file_utils.time')
    def test_handles_name_with_hyphens_and_digits(self, mock_time):
        """Hyphens in the base name that are not timestamps are preserved."""
        mock_time.time.return_value = 9999999999
        result = derive_new_unique_filename('location/svg/single-story-0-1713285600.svg')
        self.assertEqual(result, 'location/svg/single-story-0-9999999999.svg')

    @patch('hi.apps.common.file_utils.time')
    def test_round_trip_with_generate_unique_filename(self, mock_time):
        """Output of generate_unique_filename is handled correctly."""
        mock_time.time.return_value = 1000000000
        generated = generate_unique_filename('location/svg/blank.svg')
        self.assertEqual(generated, 'location/svg/blank-1000000000.svg')

        mock_time.time.return_value = 2000000000
        derived = derive_new_unique_filename(generated)
        self.assertEqual(derived, 'location/svg/blank-2000000000.svg')
