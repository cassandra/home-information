import logging

from hi.apps.console.transient_models import TransientViewSuggestion
from hi.apps.entity.enums import VideoStreamType
from hi.apps.entity.transient_models import VideoStream
from hi.testing.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestTransientViewSuggestion(BaseTestCase):
    """Test TransientViewSuggestion model for auto-view functionality."""

    def test_transient_view_suggestion_creation(self):
        """Test creating a TransientViewSuggestion with basic parameters."""
        suggestion = TransientViewSuggestion(
            url='/console/entity/video-stream/123/',
            duration_seconds=30,
            priority=5,
            trigger_reason='motion_detected'
        )
        
        self.assertEqual(suggestion.url, '/console/entity/video-stream/123/')
        self.assertEqual(suggestion.duration_seconds, 30)
        self.assertEqual(suggestion.priority, 5)
        self.assertEqual(suggestion.trigger_reason, 'motion_detected')

    def test_transient_view_suggestion_is_dataclass(self):
        """Test that TransientViewSuggestion behaves as a proper dataclass."""
        suggestion = TransientViewSuggestion(
            url='/test/url/',
            duration_seconds=60,
            priority=3,
            trigger_reason='test'
        )
        
        # Should be able to access fields
        self.assertTrue(hasattr(suggestion, 'url'))
        self.assertTrue(hasattr(suggestion, 'duration_seconds'))
        self.assertTrue(hasattr(suggestion, 'priority'))
        self.assertTrue(hasattr(suggestion, 'trigger_reason'))
        
        # Should have string representation
        suggestion_str = str(suggestion)
        self.assertIn('TransientViewSuggestion', suggestion_str)
        self.assertIn('/test/url/', suggestion_str)

    def test_transient_view_suggestion_with_different_priorities(self):
        """Test TransientViewSuggestion with different priority values."""
        high_priority = TransientViewSuggestion(
            url='/high/priority/url/',
            duration_seconds=45,
            priority=10,
            trigger_reason='critical_alert'
        )
        
        low_priority = TransientViewSuggestion(
            url='/low/priority/url/',
            duration_seconds=15,
            priority=1, 
            trigger_reason='info_update'
        )
        
        self.assertEqual(high_priority.priority, 10)
        self.assertEqual(low_priority.priority, 1)
        self.assertGreater(high_priority.priority, low_priority.priority)

    def test_transient_view_suggestion_with_various_trigger_reasons(self):
        """Test TransientViewSuggestion with different trigger reasons."""
        reasons = [
            'motion_detected',
            'door_opened', 
            'alarm_triggered',
            'weather_alert',
            'security_breach'
        ]
        
        for reason in reasons:
            suggestion = TransientViewSuggestion(
                url=f'/console/view/{reason}/',
                duration_seconds=30,
                priority=5,
                trigger_reason=reason
            )
            self.assertEqual(suggestion.trigger_reason, reason)


class TestVideoStream(BaseTestCase):
    """Test VideoStream model for video streaming functionality."""

    def test_video_stream_creation_with_minimal_fields(self):
        """Test creating a VideoStream with minimal required fields."""
        video_stream = VideoStream(
            stream_type=VideoStreamType.URL
        )
        
        self.assertEqual(video_stream.stream_type, VideoStreamType.URL)
        self.assertIsNone(video_stream.source_url)
        self.assertEqual(video_stream.metadata, {})

    def test_video_stream_creation_with_all_fields(self):
        """Test creating a VideoStream with all fields populated."""
        metadata = {
            'width': 1920,
            'height': 1080,
            'fps': 30,
            'codec': 'h264'
        }
        
        video_stream = VideoStream(
            stream_type=VideoStreamType.URL,
            source_url='https://example.com/stream.m3u8',
            metadata=metadata
        )
        
        self.assertEqual(video_stream.stream_type, VideoStreamType.URL)
        self.assertEqual(video_stream.source_url, 'https://example.com/stream.m3u8')
        self.assertEqual(video_stream.metadata, metadata)
        self.assertEqual(video_stream.metadata['width'], 1920)
        self.assertEqual(video_stream.metadata['fps'], 30)

    def test_video_stream_with_different_stream_types(self):
        """Test VideoStream creation with different stream types."""
        # Test URL stream
        url_stream = VideoStream(
            stream_type=VideoStreamType.URL,
            source_url='http://camera.local/mjpeg'
        )
        self.assertEqual(url_stream.stream_type, VideoStreamType.URL)
        
        # Test OTHER stream  
        other_stream = VideoStream(
            stream_type=VideoStreamType.OTHER,
            source_url='https://stream.example.com/playlist.m3u8'
        )
        self.assertEqual(other_stream.stream_type, VideoStreamType.OTHER)

    def test_video_stream_metadata_defaults_to_empty_dict(self):
        """Test that VideoStream metadata defaults to empty dictionary."""
        video_stream = VideoStream(
            stream_type=VideoStreamType.URL,
            source_url='http://test.local/stream'
        )
        
        self.assertIsInstance(video_stream.metadata, dict)
        self.assertEqual(len(video_stream.metadata), 0)

    def test_video_stream_metadata_can_store_various_types(self):
        """Test that VideoStream metadata can store different data types."""
        metadata = {
            'resolution': '1920x1080',
            'fps': 30,
            'bitrate': 5000.5,
            'has_audio': True,
            'supported_formats': ['h264', 'mjpeg'],
            'camera_info': {
                'manufacturer': 'TestCam',
                'model': 'TC-1000'
            }
        }
        
        video_stream = VideoStream(
            stream_type=VideoStreamType.URL,
            source_url='https://test.local/stream.m3u8',
            metadata=metadata
        )
        
        self.assertIsInstance(video_stream.metadata['resolution'], str)
        self.assertIsInstance(video_stream.metadata['fps'], int)
        self.assertIsInstance(video_stream.metadata['bitrate'], float)
        self.assertIsInstance(video_stream.metadata['has_audio'], bool)
        self.assertIsInstance(video_stream.metadata['supported_formats'], list)
        self.assertIsInstance(video_stream.metadata['camera_info'], dict)

    def test_video_stream_is_dataclass(self):
        """Test that VideoStream behaves as a proper dataclass."""
        video_stream = VideoStream(
            stream_type=VideoStreamType.URL,
            source_url='http://test.local/mjpeg',
            metadata={'test': 'value'}
        )
        
        # Should have string representation
        stream_str = str(video_stream)
        self.assertIn('VideoStream', stream_str)
        
        # Should be able to access all fields
        self.assertTrue(hasattr(video_stream, 'stream_type'))
        self.assertTrue(hasattr(video_stream, 'source_url'))
        self.assertTrue(hasattr(video_stream, 'metadata'))

    def test_video_stream_with_none_source_url(self):
        """Test VideoStream with None source_url (valid use case)."""
        video_stream = VideoStream(
            stream_type=VideoStreamType.URL,
            source_url=None
        )
        
        self.assertEqual(video_stream.stream_type, VideoStreamType.URL)
        self.assertIsNone(video_stream.source_url)
