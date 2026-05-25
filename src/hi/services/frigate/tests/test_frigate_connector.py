import logging
from unittest.mock import Mock

from django.test import TestCase

from hi.apps.control.models import Controller
from hi.apps.entity.enums import EntityStateType, EntityType
from hi.apps.entity.models import Entity
from hi.apps.event.models import EventDefinition
from hi.apps.sense.models import Sensor

from hi.services.frigate.frigate_manager import FrigateManager
from hi.services.frigate.frigate_metadata import FrigateMetaData
from hi.services.frigate.frigate_connector import FrigateConnector

logging.disable( logging.CRITICAL )


class _FrigateSyncTestBase( TestCase ):

    def setUp(self):
        self.synchronizer = FrigateConnector()
        self.mock_manager = Mock( spec = FrigateManager )
        # Default: alarm-event auto-creation off so tests that don't
        # care about it don't silently exercise the event-creation
        # path. Tests that need it set this to True explicitly.
        self.mock_manager.should_add_alarm_events = False
        self.synchronizer._frigate_manager = self.mock_manager

    def _set_upstream_cameras( self, cameras : list ) -> None:
        """Configure the mocked client to return the given camera list.

        ``cameras`` accepts either bare camera-name strings or
        ``(name, config_dict)`` tuples for tests that want to set
        per-camera config fields like ``friendly_name``."""
        self.mock_manager.frigate_client = Mock()
        normalized = []
        for entry in cameras:
            if isinstance( entry, tuple ):
                name, config = entry
            else:
                name, config = entry, { 'enabled': True }
            normalized.append( { 'name': name, 'config': config } )
        self.mock_manager.frigate_client.get_cameras.return_value = normalized


class TestFrigateSyncImpl( _FrigateSyncTestBase ):

    def test_sync_returns_error_when_client_missing(self):
        self.mock_manager.frigate_client = None
        result = self.synchronizer._sync_impl( is_initial_connect = True )
        self.assertEqual( result.title, 'Connect Result' )
        self.assertEqual( len( result.error_list ), 1 )
        self.assertIn( 'integration disabled', result.error_list[0].lower() )
        self.assertEqual( Entity.objects.count(), 0 )

    def test_sync_creates_entity_with_object_presence_sensor(self):
        """Each Frigate camera becomes one HI CAMERA entity carrying
        a single OBJECT_PRESENCE sensor. Frigate couples motion to
        object detection (no motion-without-class signal on the events
        API), so OBJECT_PRESENCE subsumes the "is motion happening"
        signal and a separate MOVEMENT sensor would always mirror it."""
        self._set_upstream_cameras( [ 'front_yard' ] )
        result = self.synchronizer._sync_impl( is_initial_connect = True )

        entities = list( Entity.objects.filter(
            integration_id = FrigateMetaData.integration_id,
        ))
        self.assertEqual( len( entities ), 1 )
        entity = entities[0]
        self.assertEqual( entity.name, 'front_yard' )
        self.assertEqual( entity.entity_type_str, str( EntityType.CAMERA ) )
        self.assertEqual( entity.integration_name, 'camera.front_yard' )
        # Frigate v1 has no native MJPEG/RTSP — the camera presents
        # as a pollable snapshot, not a native stream.
        self.assertFalse( entity.has_video_stream )
        self.assertTrue( entity.has_video_snapshot )
        self.assertEqual(
            entity.video_snapshot_stream_fps,
            self.synchronizer.CAMERA_SNAPSHOT_STREAM_FPS,
        )

        sensors = list( Sensor.objects.filter(
            entity_state__entity = entity,
            entity_state__entity_state_type_str = str( EntityStateType.OBJECT_PRESENCE ),
        ))
        self.assertEqual( len( sensors ), 1 )
        sensor = sensors[0]
        self.assertEqual( sensor.integration_name, 'camera.object.front_yard' )
        # Frigate stores a clip + snapshot per event by default;
        # advertise both capabilities so the Video Browse / history
        # views offer the playback affordances.
        self.assertTrue( sensor.provides_event_video_clip )
        self.assertTrue( sensor.provides_event_video_snapshot )

        # v1 exposes no Controllers — Frigate's only HTTP-reachable
        # operator-toggle (cameras.<name>.detect.enabled) is a config
        # edit rather than transient state, so we don't surface it
        # as a HI control. See FrigateController docstring.
        controllers = list( Controller.objects.filter( entity_state__entity = entity ))
        self.assertEqual( controllers, [] )

        self.assertIn( 'front_yard', result.created_list )
        self.assertEqual( result.error_list, [] )

    def test_sync_is_idempotent_for_existing_cameras(self):
        self._set_upstream_cameras( [ 'front_yard' ] )
        first = self.synchronizer._sync_impl( is_initial_connect = True )
        self.assertEqual( len( first.created_list ), 1 )

        # Second sync against the same upstream — no new entities,
        # no new sensors, and no error rows.
        second = self.synchronizer._sync_impl( is_initial_connect = False )
        self.assertEqual( second.created_list, [] )
        self.assertEqual( second.error_list, [] )
        self.assertEqual(
            Entity.objects.filter(
                integration_id = FrigateMetaData.integration_id,
            ).count(),
            1,
        )
        object_presence_sensors = Sensor.objects.filter(
            entity_state__entity__integration_id = FrigateMetaData.integration_id,
            entity_state__entity_state_type_str = str( EntityStateType.OBJECT_PRESENCE ),
        )
        self.assertEqual( object_presence_sensors.count(), 1 )

    def test_sync_removes_entities_for_cameras_no_longer_present(self):
        self._set_upstream_cameras( [ 'front_yard', 'back_door' ] )
        self.synchronizer._sync_impl( is_initial_connect = True )
        self.assertEqual(
            Entity.objects.filter(
                integration_id = FrigateMetaData.integration_id,
            ).count(),
            2,
        )

        # Drop 'back_door' upstream. Refresh sync should remove it.
        self._set_upstream_cameras( [ 'front_yard' ] )
        result = self.synchronizer._sync_impl( is_initial_connect = False )

        remaining_names = list( Entity.objects.filter(
            integration_id = FrigateMetaData.integration_id,
        ).values_list( 'name', flat = True ))
        self.assertEqual( remaining_names, [ 'front_yard' ] )
        self.assertEqual( result.error_list, [] )

    def test_sync_preserves_user_edited_name_on_update(self):
        self._set_upstream_cameras( [ 'front_yard' ] )
        self.synchronizer._sync_impl( is_initial_connect = True )

        entity = Entity.objects.get(
            integration_id = FrigateMetaData.integration_id,
        )
        entity.name = 'Front Porch'
        # Toggle integration-owned flags away from the canonical
        # values so the update path has something to heal.
        entity.has_video_snapshot = False
        entity.video_snapshot_stream_fps = None
        entity.save()

        result = self.synchronizer._sync_impl( is_initial_connect = False )

        entity.refresh_from_db()
        self.assertEqual( entity.name, 'Front Porch' )
        self.assertTrue( entity.has_video_snapshot )
        self.assertEqual(
            entity.video_snapshot_stream_fps,
            self.synchronizer.CAMERA_SNAPSHOT_STREAM_FPS,
        )
        self.assertEqual( result.error_list, [] )

    def test_sync_heals_stale_has_video_stream_flag(self):
        """Self-heal: entities created by the earlier sync revision
        flagged ``has_video_stream=True``, but Frigate v1 has no
        native stream. The update path must flip that off so the
        Live View pane routes to the snapshot-as-stream branch
        instead of the (broken) native-stream branch."""
        self._set_upstream_cameras( [ 'front_yard' ] )
        self.synchronizer._sync_impl( is_initial_connect = True )

        entity = Entity.objects.get(
            integration_id = FrigateMetaData.integration_id,
        )
        entity.has_video_stream = True  # simulate the stale shape
        entity.save( update_fields = [ 'has_video_stream' ] )

        self.synchronizer._sync_impl( is_initial_connect = False )
        entity.refresh_from_db()
        self.assertFalse( entity.has_video_stream )

    def test_sync_uses_friendly_name_when_present(self):
        """Real Frigate carries a ``friendly_name`` on each camera's
        config for display; HI should prefer it over the snake_case
        camera key so the imported entity has a human-readable name."""
        self._set_upstream_cameras( [
            ( 'front_yard', { 'enabled': True, 'friendly_name': 'Front Yard' } ),
            ( 'back_door', { 'enabled': True } ),  # no friendly_name
        ])
        self.synchronizer._sync_impl( is_initial_connect = True )

        names_by_key = dict( Entity.objects.filter(
            integration_id = FrigateMetaData.integration_id,
        ).values_list( 'integration_name', 'name' ))
        self.assertEqual( names_by_key[ 'camera.front_yard' ], 'Front Yard' )
        # No friendly_name → falls back to the camera key.
        self.assertEqual( names_by_key[ 'camera.back_door' ], 'back_door' )

    def test_sync_creates_multiple_camera_entities(self):
        self._set_upstream_cameras( [ 'front_yard', 'back_door', 'driveway' ] )
        result = self.synchronizer._sync_impl( is_initial_connect = True )

        names = set( Entity.objects.filter(
            integration_id = FrigateMetaData.integration_id,
        ).values_list( 'name', flat = True ))
        self.assertEqual( names, { 'front_yard', 'back_door', 'driveway' } )
        self.assertEqual( set( result.created_list ), names )

        # Placement input should carry one group with all three cameras.
        self.assertIsNotNone( result.placement_input )
        self.assertEqual( len( result.placement_input.groups ), 1 )
        self.assertEqual( result.placement_input.groups[0].label, 'Cameras' )
        self.assertEqual( len( result.placement_input.groups[0].items ), 3 )

    def test_sync_skips_event_definition_when_alarm_events_disabled(self):
        # Default in setUp is should_add_alarm_events=False.
        self._set_upstream_cameras( [ 'front_yard' ] )
        self.synchronizer._sync_impl( is_initial_connect = True )
        self.assertEqual(
            EventDefinition.objects.filter(
                integration_id = FrigateMetaData.integration_id,
            ).count(),
            0,
        )

    def test_sync_creates_event_definition_when_alarm_events_enabled(self):
        self.mock_manager.should_add_alarm_events = True
        self._set_upstream_cameras( [ 'front_yard' ] )
        self.synchronizer._sync_impl( is_initial_connect = True )

        event_definitions = list( EventDefinition.objects.filter(
            integration_id = FrigateMetaData.integration_id,
        ))
        self.assertEqual( len( event_definitions ), 1 )
        event_definition = event_definitions[0]
        self.assertEqual(
            event_definition.integration_name,
            'camera.object.event.front_yard',
        )
        # One clause keyed on the OBJECT_PRESENCE sensor with the
        # conservative EQ OBJECT_PERSON default (see Issue #346 for
        # the broader operator vocabulary that would let this default
        # widen to "any non-NONE detection").
        clauses = list( event_definition.event_clauses.all() )
        self.assertEqual( len( clauses ), 1 )
        self.assertEqual( clauses[0].value, 'object_person' )
        self.assertEqual(
            clauses[0].entity_state.entity_state_type_str,
            str( EntityStateType.OBJECT_PRESENCE ),
        )

    def test_sync_is_idempotent_for_event_definitions(self):
        self.mock_manager.should_add_alarm_events = True
        self._set_upstream_cameras( [ 'front_yard' ] )
        self.synchronizer._sync_impl( is_initial_connect = True )
        self.synchronizer._sync_impl( is_initial_connect = False )
        # Second sync against the same upstream — no new event
        # definitions; existing entity's update path doesn't
        # re-create the definition.
        self.assertEqual(
            EventDefinition.objects.filter(
                integration_id = FrigateMetaData.integration_id,
            ).count(),
            1,
        )
