"""Gateway-level + manager URL-helper tests for the Frigate integration.

These cover:
  * ``FrigateManager.get_camera_snapshot_url`` / ``get_event_snapshot_url``
    — the URL helpers HI uses to point at Frigate's still-image
    endpoints.
  * ``FrigateGateway.get_entity_video_snapshot`` — entry point the
    presentation layer uses to fetch a live snapshot for a camera
    entity.
"""
import logging
from unittest.mock import Mock, patch

from django.test import TestCase

from hi.apps.entity.enums import EntityType
from hi.apps.entity.models import Entity

from hi.services.frigate.frigate_manager import FrigateManager
from hi.services.frigate.frigate_metadata import FrigateMetaData
from hi.services.frigate.integration import FrigateGateway

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
