"""Gateway-level + manager URL-helper tests for the Frigate integration.

These cover:
  * ``FrigateManager.get_camera_snapshot_url`` / ``get_event_snapshot_url``
    — the URL helpers HI uses to point at Frigate's still-image
    endpoints.
  * ``FrigateGateway.get_entity_video_snapshot`` — entry point the
    presentation layer uses to fetch a live snapshot for a camera
    entity.
  * ``FrigateManager._reload_implementation`` health-recording —
    keeps the aggregate health honest so the UI banner doesn't show
    a degraded state while the monitor is reporting Healthy.
"""
import logging
from unittest.mock import Mock, patch

from django.test import TestCase

from hi.apps.entity.enums import EntityType
from hi.apps.entity.models import Entity
from hi.apps.system.enums import ApiHealthStatusType, HealthStatusType
from hi.integrations.models import Integration

from hi.apps.entity.enums import VideoStreamType
from hi.apps.sense.transient_models import SensorResponse
from hi.services.frigate.enums import FrigateAttributeType
from hi.services.frigate.frigate_manager import FrigateManager
from hi.services.frigate.frigate_metadata import FrigateMetaData
from hi.services.frigate.integration import FrigateGateway
from hi.integrations.models import IntegrationAttribute
from hi.integrations.transient_models import IntegrationKey

logging.disable( logging.CRITICAL )


class TestFrigateManagerSnapshotUrls( TestCase ):
    """Helpers that build the still-image URLs HI emits in <img>
    tags (camera snapshot) and on SensorResponses (event snapshot).
    Returning ``None`` when the client is unavailable lets callers
    treat "no client yet" the same as "no snapshot capability"."""

    def setUp(self):
        self.manager = FrigateManager()
        self.mock_client = Mock( base_url = 'http://frigate.example' )

    def test_camera_snapshot_url_uses_latest_jpg_path(self):
        with patch.object(
            type( self.manager ), 'frigate_client',
            new_callable = lambda: property( lambda _ : self.mock_client ),
        ):
            url = self.manager.get_camera_snapshot_url( camera_name = 'front_yard' )
        self.assertIsNotNone( url )
        self.assertTrue( url.startswith( 'http://frigate.example/api/front_yard/latest.jpg' ) )
        # Cache-bust param keeps re-rendered <img> tags from showing
        # the prior frame.
        self.assertIn( '_t=', url )

    def test_event_snapshot_url_uses_events_snapshot_jpg_path(self):
        with patch.object(
            type( self.manager ), 'frigate_client',
            new_callable = lambda: property( lambda _ : self.mock_client ),
        ):
            url = self.manager.get_event_snapshot_url( event_id = '42' )
        self.assertIsNotNone( url )
        self.assertTrue(
            url.startswith( 'http://frigate.example/api/events/42/snapshot.jpg' )
        )
        self.assertIn( '_t=', url )

    def test_snapshot_urls_return_none_when_client_unavailable(self):
        """Integration disabled / unconfigured ⇒ no client ⇒ no URL.
        Callers must treat ``None`` as "no snapshot capability"."""
        with patch.object(
            type( self.manager ), 'frigate_client',
            new_callable = lambda: property( lambda _ : None ),
        ):
            self.assertIsNone(
                self.manager.get_camera_snapshot_url( camera_name = 'front_yard' )
            )
            self.assertIsNone(
                self.manager.get_event_snapshot_url( event_id = '42' )
            )


class TestFrigateGatewayVideoSnapshot( TestCase ):
    """``FrigateGateway.get_entity_video_snapshot`` — the presentation
    layer's entry point for a live still frame on a Frigate camera
    entity. Should return ``None`` for non-Frigate entities, entities
    that have opted out (``has_video_snapshot=False``), or when no
    client is available; otherwise a ``VideoSnapshot`` pointing at
    the live JPEG URL."""

    def setUp(self):
        self.gateway = FrigateGateway()

    def _make_camera_entity( self,
                             integration_name      : str  = 'camera.front_yard',
                             has_video_snapshot   : bool = True,
                             integration_id        : str  = None ) -> Entity:
        return Entity.objects.create(
            name = 'Front Yard',
            entity_type_str = str( EntityType.CAMERA ),
            integration_id = integration_id or FrigateMetaData.integration_id,
            integration_name = integration_name,
            has_video_snapshot = has_video_snapshot,
            has_video_stream = True,
        )

    def test_returns_snapshot_for_frigate_camera_entity(self):
        entity = self._make_camera_entity()
        with patch.object(
            FrigateManager, 'get_camera_snapshot_url',
            return_value = 'http://frigate.example/api/front_yard/latest.jpg?_t=1',
        ):
            snapshot = self.gateway.get_entity_video_snapshot( entity = entity )
        self.assertIsNotNone( snapshot )
        self.assertEqual(
            snapshot.source_url,
            'http://frigate.example/api/front_yard/latest.jpg?_t=1',
        )
        self.assertEqual( snapshot.metadata, { 'camera_name': 'front_yard' } )

    def test_returns_none_when_entity_opts_out_of_snapshots(self):
        entity = self._make_camera_entity( has_video_snapshot = False )
        self.assertIsNone( self.gateway.get_entity_video_snapshot( entity = entity ))

    def test_returns_none_for_non_frigate_entity(self):
        entity = self._make_camera_entity( integration_id = 'some.other.integration' )
        self.assertIsNone( self.gateway.get_entity_video_snapshot( entity = entity ))

    def test_returns_none_when_integration_name_lacks_camera_prefix(self):
        """Defensive: integration_name should always start with
        ``camera.`` for a Frigate camera entity, but a stray
        non-camera Frigate row shouldn't crash the snapshot path."""
        entity = self._make_camera_entity( integration_name = 'system' )
        self.assertIsNone( self.gateway.get_entity_video_snapshot( entity = entity ))

    def test_returns_none_when_manager_has_no_client(self):
        """When the client isn't built yet (integration disabled),
        ``get_camera_snapshot_url`` returns ``None`` — the gateway
        propagates that as "no snapshot capability"."""
        entity = self._make_camera_entity()
        with patch.object(
            FrigateManager, 'get_camera_snapshot_url', return_value = None,
        ):
            self.assertIsNone( self.gateway.get_entity_video_snapshot( entity = entity ))


class TestFrigateManagerEventClipUrl( TestCase ):

    def setUp(self):
        self.manager = FrigateManager()
        self.mock_client = Mock( base_url = 'http://frigate.example' )

    def test_event_clip_url_uses_clip_mp4_path(self):
        with patch.object(
            type( self.manager ), 'frigate_client',
            new_callable = lambda: property( lambda _ : self.mock_client ),
        ):
            url = self.manager.get_event_clip_url( event_id = '42' )
        self.assertIsNotNone( url )
        self.assertTrue(
            url.startswith( 'http://frigate.example/api/events/42/clip.mp4' )
        )
        self.assertIn( '_t=', url )

    def test_event_clip_url_returns_none_when_client_unavailable(self):
        with patch.object(
            type( self.manager ), 'frigate_client',
            new_callable = lambda: property( lambda _ : None ),
        ):
            self.assertIsNone( self.manager.get_event_clip_url( event_id = '42' ))


class TestFrigateGatewayEventSnapshotUrl( TestCase ):
    """``FrigateGateway.get_sensor_response_event_snapshot_url``
    builds the snapshot URL fresh from the response's correlation_id
    each call so the URL always reflects current manager state."""

    def setUp(self):
        self.gateway = FrigateGateway()

    def _make_response( self, has_snapshot = True, correlation_id = 'evt-1' ):
        from datetime import datetime
        return SensorResponse(
            integration_key = IntegrationKey(
                integration_id = FrigateMetaData.integration_id,
                integration_name = 'camera.object.front_yard',
            ),
            value = 'object_person',
            timestamp = datetime.now(),
            correlation_id = correlation_id,
            has_event_video_snapshot = has_snapshot,
        )

    def test_returns_url_for_snapshot_bearing_response(self):
        response = self._make_response()
        with patch.object(
            FrigateManager, 'get_event_snapshot_url',
            return_value = 'http://frigate.example/api/events/evt-1/snapshot.jpg?_t=1',
        ):
            url = self.gateway.get_sensor_response_event_snapshot_url(
                sensor_response = response,
            )
        self.assertEqual(
            url, 'http://frigate.example/api/events/evt-1/snapshot.jpg?_t=1',
        )

    def test_returns_none_when_response_has_no_snapshot(self):
        response = self._make_response( has_snapshot = False )
        self.assertIsNone(
            self.gateway.get_sensor_response_event_snapshot_url(
                sensor_response = response,
            )
        )

    def test_returns_none_when_response_has_no_correlation_id(self):
        response = self._make_response( correlation_id = None )
        self.assertIsNone(
            self.gateway.get_sensor_response_event_snapshot_url(
                sensor_response = response,
            )
        )


class TestFrigateGatewayVideoStream( TestCase ):
    """``FrigateGateway.get_sensor_response_video_stream`` returns
    the event clip MP4 URL for SensorResponses carrying a clip; None
    otherwise (no clip flag, no event id, or no client)."""

    def setUp(self):
        self.gateway = FrigateGateway()

    def _make_response(
            self, has_clip = True, correlation_id = 'evt-1',
    ) -> SensorResponse:
        from datetime import datetime
        return SensorResponse(
            integration_key = IntegrationKey(
                integration_id = FrigateMetaData.integration_id,
                integration_name = 'camera.object.front_yard',
            ),
            value = 'object_person',
            timestamp = datetime.now(),
            correlation_id = correlation_id,
            has_event_video_clip = has_clip,
        )

    def test_returns_mp4_stream_for_clip_bearing_response(self):
        response = self._make_response()
        with patch.object(
            FrigateManager, 'get_event_clip_url',
            return_value = 'http://frigate.example/api/events/evt-1/clip.mp4?_t=1',
        ):
            stream = self.gateway.get_sensor_response_video_stream(
                sensor_response = response,
            )
        self.assertIsNotNone( stream )
        self.assertEqual( stream.stream_type, VideoStreamType.MP4 )
        self.assertEqual(
            stream.source_url,
            'http://frigate.example/api/events/evt-1/clip.mp4?_t=1',
        )
        self.assertEqual( stream.metadata, { 'event_id': 'evt-1' } )

    def test_returns_none_when_response_has_no_clip(self):
        response = self._make_response( has_clip = False )
        self.assertIsNone(
            self.gateway.get_sensor_response_video_stream( sensor_response = response )
        )

    def test_returns_none_when_response_has_no_correlation_id(self):
        response = self._make_response( correlation_id = None )
        self.assertIsNone(
            self.gateway.get_sensor_response_video_stream( sensor_response = response )
        )

    def test_returns_none_when_manager_has_no_client(self):
        response = self._make_response()
        with patch.object(
            FrigateManager, 'get_event_clip_url', return_value = None,
        ):
            self.assertIsNone(
                self.gateway.get_sensor_response_video_stream( sensor_response = response )
            )


class TestFrigateManagerHealthRecording( TestCase ):
    """``FrigateManager._reload_implementation`` records the manager's
    own health based on what reload actually does (DB read + client
    construction). The api_health_status slot is reserved for actual
    API-call outcomes set by ``api_call_context`` wrappers; reload
    never touches it because reload doesn't call the API."""

    def setUp(self):
        # FrigateManager is a singleton — health state from prior tests
        # leaks otherwise. Force a fresh provider setup on both slots.
        self.manager = FrigateManager()
        self.manager._health_status = self.manager.initial_health_status
        if hasattr( self.manager, '_api_health_status' ):
            del self.manager._api_health_status

    def test_no_integration_row_records_disabled(self):
        Integration.objects.filter(
            integration_id = FrigateMetaData.integration_id,
        ).delete()
        self.manager._reload_implementation()
        self.assertEqual(
            self.manager.health_status._base_status,
            HealthStatusType.DISABLED,
        )
        self.assertEqual(
            self.manager.api_health_status.status,
            ApiHealthStatusType.UNKNOWN,
        )
        self.assertIsNone( self.manager._frigate_client )

    def test_disabled_integration_records_disabled(self):
        integration, _ = Integration.objects.get_or_create(
            integration_id = FrigateMetaData.integration_id,
            defaults = { 'is_enabled': False },
        )
        integration.is_enabled = False
        integration.save()
        self.manager._reload_implementation()
        self.assertEqual(
            self.manager.health_status._base_status,
            HealthStatusType.DISABLED,
        )
        self.assertEqual(
            self.manager.api_health_status.status,
            ApiHealthStatusType.UNKNOWN,
        )
        self.assertIsNone( self.manager._frigate_client )

    def test_successful_reload_records_manager_healthy_and_leaves_api_unknown(self):
        integration, _ = Integration.objects.get_or_create(
            integration_id = FrigateMetaData.integration_id,
            defaults = { 'is_enabled': True },
        )
        integration.is_enabled = True
        integration.save()
        with patch(
            'hi.services.frigate.frigate_manager.FrigateClientFactory.create_client',
            return_value = Mock( base_url = 'http://frigate.example' ),
        ):
            self.manager._reload_implementation()
        self.assertEqual(
            self.manager.health_status._base_status,
            HealthStatusType.HEALTHY,
        )
        self.assertEqual(
            self.manager.api_health_status.status,
            ApiHealthStatusType.UNKNOWN,
        )
        self.assertIsNotNone( self.manager._frigate_client )

    def test_client_build_failure_records_manager_error_and_leaves_api_unknown(self):
        integration, _ = Integration.objects.get_or_create(
            integration_id = FrigateMetaData.integration_id,
            defaults = { 'is_enabled': True },
        )
        integration.is_enabled = True
        integration.save()
        with patch(
            'hi.services.frigate.frigate_manager.FrigateClientFactory.create_client',
            side_effect = ValueError( 'Base URL is required.' ),
        ):
            self.manager._reload_implementation()
        self.assertEqual(
            self.manager.health_status._base_status,
            HealthStatusType.ERROR,
        )
        self.assertEqual(
            self.manager.api_health_status.status,
            ApiHealthStatusType.UNKNOWN,
        )
        self.assertIsNone( self.manager._frigate_client )


class TestFrigateManagerShouldAddAlarmEvents( TestCase ):
    """``FrigateManager.should_add_alarm_events`` reads the boolean
    ``ADD_ALARM_EVENTS`` integration attribute. Default off so a
    freshly-imported install isn't unexpectedly noisy with alarms."""

    def setUp(self):
        self.manager = FrigateManager()
        # Bypass ensure_initialized so the test fixture's
        # _attribute_map isn't clobbered by a reload triggered on
        # first property read.
        self.manager._was_initialized = True
        self.manager._attribute_map = {}

    def _make_attribute( self, value : str ) -> IntegrationAttribute:
        return IntegrationAttribute(
            integration_key = IntegrationKey(
                integration_id = FrigateMetaData.integration_id,
                integration_name = str( FrigateAttributeType.ADD_ALARM_EVENTS ),
            ),
            value = value,
        )

    def test_default_when_attribute_absent_is_false(self):
        self.assertFalse( self.manager.should_add_alarm_events )

    def test_attribute_true_value_returns_true(self):
        self.manager._attribute_map = {
            FrigateAttributeType.ADD_ALARM_EVENTS: self._make_attribute( 'True' ),
        }
        self.assertTrue( self.manager.should_add_alarm_events )

    def test_attribute_false_value_returns_false(self):
        self.manager._attribute_map = {
            FrigateAttributeType.ADD_ALARM_EVENTS: self._make_attribute( 'False' ),
        }
        self.assertFalse( self.manager.should_add_alarm_events )
