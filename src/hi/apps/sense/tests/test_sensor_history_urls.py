import logging

from hi.apps.sense.sensor_history_urls import (
    sensor_history_details_url,
    sensor_history_video_browse_url,
)
from hi.testing.base_test_case import BaseTestCase

logging.disable( logging.CRITICAL )


class TestSensorHistoryVideoBrowseUrl( BaseTestCase ):
    """``sensor_history_video_browse_url`` returns the most-specific
    appropriate URL: the per-event detail URL when the data point
    itself has a stream, else the per-sensor timeline URL when the
    sensor produces streams generally, else ``None``."""

    def test_specific_event_url_when_data_point_has_stream(self):
        url = sensor_history_video_browse_url(
            entity_id = 1, sensor_id = 2, sensor_history_id = 3,
            has_event_video_clip = True, provides_event_video_clip = True,
        )
        self.assertIsNotNone( url )
        self.assertIn( '3', url )

    def test_per_sensor_timeline_when_only_sensor_provides(self):
        # No data-point-level stream, but the sensor produces streams.
        # Fall back to the per-sensor timeline URL (no sensor_history_id
        # in the path).
        url = sensor_history_video_browse_url(
            entity_id = 1, sensor_id = 2, sensor_history_id = 3,
            has_event_video_clip = False, provides_event_video_clip = True,
        )
        self.assertIsNotNone( url )
        self.assertNotIn( '3', url )

    def test_none_when_neither_stream_capability(self):
        url = sensor_history_video_browse_url(
            entity_id = 1, sensor_id = 2, sensor_history_id = 3,
            has_event_video_clip = False, provides_event_video_clip = False,
        )
        self.assertIsNone( url )

    def test_none_when_has_stream_but_no_history_id(self):
        # has_event_video_clip=True without a sensor_history_id can't form
        # a per-event URL; the fallback (provides_event_video_clip=False)
        # also doesn't apply, so the result is None.
        url = sensor_history_video_browse_url(
            entity_id = 1, sensor_id = 2, sensor_history_id = None,
            has_event_video_clip = True, provides_event_video_clip = False,
        )
        self.assertIsNone( url )

    def test_falls_back_to_per_sensor_when_has_stream_but_no_history_id(self):
        # Edge: has_event_video_clip=True but sensor_history_id missing.
        # If the sensor itself provides streams, fall back to the
        # per-sensor timeline.
        url = sensor_history_video_browse_url(
            entity_id = 1, sensor_id = 2, sensor_history_id = None,
            has_event_video_clip = True, provides_event_video_clip = True,
        )
        self.assertIsNotNone( url )
        self.assertIn( '1', url )
        self.assertIn( '2', url )


class TestSensorHistoryDetailsUrl( BaseTestCase ):
    """``sensor_history_details_url`` returns the details modal URL
    when both a sensor_history_id and detail attributes are present;
    ``None`` otherwise."""

    def test_url_returned_when_has_details_and_id(self):
        url = sensor_history_details_url(
            sensor_history_id = 42, has_details = True,
        )
        self.assertIsNotNone( url )
        self.assertIn( '42', url )

    def test_none_when_no_details(self):
        url = sensor_history_details_url(
            sensor_history_id = 42, has_details = False,
        )
        self.assertIsNone( url )

    def test_none_when_no_history_id(self):
        url = sensor_history_details_url(
            sensor_history_id = None, has_details = True,
        )
        self.assertIsNone( url )
