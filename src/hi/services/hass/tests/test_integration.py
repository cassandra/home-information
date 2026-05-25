"""Gateway-level tests for the Home Assistant integration."""
import logging
import threading
from unittest.mock import Mock

from django.test import TestCase

from hi.apps.entity.models import Entity, EntityState
from hi.apps.sense.models import Sensor

from hi.services.hass.hass_manager import HassManager
from hi.services.hass.hass_metadata import HassMetaData
from hi.services.hass.hass_connector import HassConnector

logging.disable(logging.CRITICAL)


class GetEntityVideoSnapshotTests(TestCase):
    """The snapshot URL is composed from cached ``entity_picture``
    attrs plus the HA base URL. Covers the URL-shape branches
    (relative vs absolute) and the no-snapshot short-circuits."""

    BASE_URL = 'http://ha.local:8123/'

    def setUp(self):
        HassManager._instance = None
        HassManager._lock = threading.Lock()
        self.manager = HassManager()
        self.gateway = HassConnector()

        mock_client = Mock()
        # HassClient strips the trailing slash on construction, so
        # the property returns a non-slash-terminated string.
        mock_client.api_base_url = self.BASE_URL.rstrip('/')
        self.manager._hass_client = mock_client

    def _camera_entity(self, device_id='front_door', ha_state_id='camera.front_door'):
        """Build a camera-shaped HI Entity + camera-domain Sensor and
        rebuild the manager's entity_id -> ha_state_id map so the
        gateway's lookup resolves."""
        entity = Entity.objects.create(
            name='Front Door',
            entity_type_str='CAMERA',
            integration_id=HassMetaData.integration_id,
            integration_name=device_id,
            has_video_snapshot=True,
        )
        entity_state = EntityState.objects.create(
            entity=entity,
            entity_state_type_str='VIDEO_STREAM',
            role_str='primary',
            name='Camera',
        )
        Sensor.objects.create(
            name='Camera',
            entity_state=entity_state,
            sensor_type_str='BLOB',
            integration_id=HassMetaData.integration_id,
            integration_name=ha_state_id,
        )
        self.manager._rebuild_entity_id_to_ha_state_id_map()
        return entity

    def _prime_cache(self, integration_name, attrs):
        self.manager.update_latest_attrs_cache({
            integration_name: Mock(
                entity_id=integration_name,
                domain=integration_name.split('.')[0],
                attributes=attrs,
            ),
        })

    def test_returns_none_when_flag_is_off(self):
        entity = self._camera_entity()
        entity.has_video_snapshot = False
        entity.save()
        self.assertIsNone(self.gateway.get_entity_video_snapshot(entity))

    def test_returns_none_for_non_hass_entity(self):
        other = Entity.objects.create(
            name='Other',
            entity_type_str='CAMERA',
            integration_id='zm',
            integration_name='monitor.1',
            has_video_snapshot=True,
        )
        self.assertIsNone(self.gateway.get_entity_video_snapshot(other))

    def test_returns_none_when_cache_cold(self):
        entity = self._camera_entity()
        # No prime — cache is empty.
        self.assertIsNone(self.gateway.get_entity_video_snapshot(entity))

    def test_returns_none_when_entity_picture_missing(self):
        entity = self._camera_entity()
        self._prime_cache('camera.front_door', {'access_token': 'abc'})
        self.assertIsNone(self.gateway.get_entity_video_snapshot(entity))

    def test_composes_relative_entity_picture_against_base_url(self):
        entity = self._camera_entity()
        self._prime_cache('camera.front_door', {
            'entity_picture': '/api/camera_proxy/camera.front_door?token=abc',
        })

        result = self.gateway.get_entity_video_snapshot(entity)

        self.assertIsNotNone(result)
        self.assertEqual(
            result.source_url,
            'http://ha.local:8123/api/camera_proxy/camera.front_door?token=abc',
        )

    def test_passes_through_absolute_https_entity_picture(self):
        entity = self._camera_entity()
        self._prime_cache('camera.front_door', {
            'entity_picture': 'https://nabu.casa/snapshot/abc',
        })

        result = self.gateway.get_entity_video_snapshot(entity)

        self.assertIsNotNone(result)
        self.assertEqual(result.source_url, 'https://nabu.casa/snapshot/abc')

    def test_passes_through_absolute_http_entity_picture(self):
        entity = self._camera_entity()
        self._prime_cache('camera.front_door', {
            'entity_picture': 'http://external.cam/snap.jpg',
        })

        result = self.gateway.get_entity_video_snapshot(entity)

        self.assertIsNotNone(result)
        self.assertEqual(result.source_url, 'http://external.cam/snap.jpg')

    def test_token_rotation_reflected_after_cache_refresh(self):
        """The snapshot URL must always reflect the latest token the
        monitor cached. Catches a regression where the gateway holds
        a stale value past the next poll cycle."""
        entity = self._camera_entity()
        self._prime_cache('camera.front_door', {
            'entity_picture': '/api/camera_proxy/camera.front_door?token=v1',
        })
        first = self.gateway.get_entity_video_snapshot(entity)

        self._prime_cache('camera.front_door', {
            'entity_picture': '/api/camera_proxy/camera.front_door?token=v2',
        })
        second = self.gateway.get_entity_video_snapshot(entity)

        self.assertIn('token=v1', first.source_url)
        self.assertIn('token=v2', second.source_url)
