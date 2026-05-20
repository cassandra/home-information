import logging
from unittest.mock import Mock

from django.test import TestCase

from hi.apps.entity.enums import EntityStateType, EntityType
from hi.apps.entity.models import Entity
from hi.apps.sense.models import Sensor

from hi.services.frigate.frigate_manager import FrigateManager
from hi.services.frigate.frigate_metadata import FrigateMetaData
from hi.services.frigate.frigate_sync import FrigateSynchronizer

logging.disable( logging.CRITICAL )


class _FrigateSyncTestBase( TestCase ):

    def setUp(self):
        self.synchronizer = FrigateSynchronizer()
        self.mock_manager = Mock( spec = FrigateManager )
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
        result = self.synchronizer._sync_impl( is_initial_import = True )
        self.assertEqual( result.title, 'Import Result' )
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
        result = self.synchronizer._sync_impl( is_initial_import = True )

        entities = list( Entity.objects.filter(
            integration_id = FrigateMetaData.integration_id,
        ))
        self.assertEqual( len( entities ), 1 )
        entity = entities[0]
        self.assertEqual( entity.name, 'front_yard' )
        self.assertEqual( entity.entity_type_str, str( EntityType.CAMERA ) )
        self.assertEqual( entity.integration_name, 'camera.front_yard' )
        self.assertTrue( entity.has_video_stream )
        self.assertTrue( entity.has_video_snapshot )

        sensors = list( Sensor.objects.filter( entity_state__entity = entity ))
        self.assertEqual( len( sensors ), 1 )
        sensor = sensors[0]
        self.assertEqual(
            sensor.entity_state.entity_state_type_str,
            str( EntityStateType.OBJECT_PRESENCE ),
        )
        self.assertEqual( sensor.integration_name, 'camera.object.front_yard' )

        self.assertIn( 'front_yard', result.created_list )
        self.assertEqual( result.error_list, [] )

    def test_sync_is_idempotent_for_existing_cameras(self):
        self._set_upstream_cameras( [ 'front_yard' ] )
        first = self.synchronizer._sync_impl( is_initial_import = True )
        self.assertEqual( len( first.created_list ), 1 )

        # Second sync against the same upstream — no new entities,
        # no new sensors, and no error rows.
        second = self.synchronizer._sync_impl( is_initial_import = False )
        self.assertEqual( second.created_list, [] )
        self.assertEqual( second.error_list, [] )
        self.assertEqual(
            Entity.objects.filter(
                integration_id = FrigateMetaData.integration_id,
            ).count(),
            1,
        )
        sensors = Sensor.objects.filter(
            entity_state__entity__integration_id = FrigateMetaData.integration_id,
        )
        self.assertEqual( sensors.count(), 1 )

    def test_sync_removes_entities_for_cameras_no_longer_present(self):
        self._set_upstream_cameras( [ 'front_yard', 'back_door' ] )
        self.synchronizer._sync_impl( is_initial_import = True )
        self.assertEqual(
            Entity.objects.filter(
                integration_id = FrigateMetaData.integration_id,
            ).count(),
            2,
        )

        # Drop 'back_door' upstream. Refresh sync should remove it.
        self._set_upstream_cameras( [ 'front_yard' ] )
        result = self.synchronizer._sync_impl( is_initial_import = False )

        remaining_names = list( Entity.objects.filter(
            integration_id = FrigateMetaData.integration_id,
        ).values_list( 'name', flat = True ))
        self.assertEqual( remaining_names, [ 'front_yard' ] )
        self.assertEqual( result.error_list, [] )

    def test_sync_preserves_user_edited_name_on_update(self):
        self._set_upstream_cameras( [ 'front_yard' ] )
        self.synchronizer._sync_impl( is_initial_import = True )

        entity = Entity.objects.get(
            integration_id = FrigateMetaData.integration_id,
        )
        entity.name = 'Front Porch'
        entity.has_video_stream = False  # toggle off so update flips it back
        entity.save()

        result = self.synchronizer._sync_impl( is_initial_import = False )

        entity.refresh_from_db()
        self.assertEqual( entity.name, 'Front Porch' )
        self.assertTrue( entity.has_video_stream )
        self.assertEqual( result.error_list, [] )

    def test_sync_uses_friendly_name_when_present(self):
        """Real Frigate carries a ``friendly_name`` on each camera's
        config for display; HI should prefer it over the snake_case
        camera key so the imported entity has a human-readable name."""
        self._set_upstream_cameras( [
            ( 'front_yard', { 'enabled': True, 'friendly_name': 'Front Yard' } ),
            ( 'back_door', { 'enabled': True } ),  # no friendly_name
        ])
        self.synchronizer._sync_impl( is_initial_import = True )

        names_by_key = dict( Entity.objects.filter(
            integration_id = FrigateMetaData.integration_id,
        ).values_list( 'integration_name', 'name' ))
        self.assertEqual( names_by_key[ 'camera.front_yard' ], 'Front Yard' )
        # No friendly_name → falls back to the camera key.
        self.assertEqual( names_by_key[ 'camera.back_door' ], 'back_door' )

    def test_sync_creates_multiple_camera_entities(self):
        self._set_upstream_cameras( [ 'front_yard', 'back_door', 'driveway' ] )
        result = self.synchronizer._sync_impl( is_initial_import = True )

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
