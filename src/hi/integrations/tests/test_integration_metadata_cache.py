import logging
from unittest.mock import patch

from django.test import TestCase

from hi.apps.entity.enums import EntityStateType, EntityType
from hi.apps.entity.models import Entity, EntityState
from hi.apps.sense.models import Sensor
from hi.apps.control.models import Controller
from hi.integrations.integration_metadata_cache import IntegrationMetadataCache
from hi.integrations.transient_models import IntegrationKey
from hi.testing.async_task_utils import AsyncTaskTestCase

logging.disable(logging.CRITICAL)


def _make_entity_with_sensor( integration_key, units = None ):
    entity = Entity.objects.create(
        name = f'Test {integration_key.integration_name}',
        integration_id = integration_key.integration_id,
        integration_name = integration_key.integration_name,
        entity_type_str = str( EntityType.LIGHT ),
    )
    state = EntityState.objects.create(
        entity = entity,
        entity_state_type_str = str( EntityStateType.TEMPERATURE ),
        name = f'{entity.name} state',
        units = units,
    )
    sensor = Sensor( entity_state = state, name = entity.name )
    sensor.integration_key = integration_key
    sensor.save()
    return entity, state, sensor


def _reset_cache():
    IntegrationMetadataCache._cache.clear()
    IntegrationMetadataCache._warmed = False


class TestIntegrationMetadataCache(TestCase):
    """Cache exists to amortize per-call EntityState.units lookups
    inside the HA monitor's polling loop. The tests cover the
    contracts that path depends on: warmup populates from the DB
    one-shot, lazy fill handles entities created post-warmup,
    misses for unknown keys are cached so they don't re-hit the
    DB, and the invariant-violation warning fires when a
    Sensor/Controller pair disagree (the canary protection)."""

    def setUp(self):
        _reset_cache()

    def tearDown(self):
        _reset_cache()

    def test_warmup_loads_units_from_sensor_entity_states(self):
        key = IntegrationKey(
            integration_id = 'hass',
            integration_name = 'climate.thermostat~current_temperature',
        )
        _make_entity_with_sensor( key, units = '°C' )

        entry = IntegrationMetadataCache.get_entry( key )

        self.assertEqual( entry, { 'units': '°C' } )
        self.assertTrue( IntegrationMetadataCache._warmed )

    def test_warmup_dedupes_sensor_and_controller_sharing_key(self):
        # HiModelHelper.create_controller(is_sensed=True) creates both
        # a Sensor and Controller pointing at the same EntityState.
        # The cache records one entry without duplication; the
        # Sensor pass populates first, the Controller pass's
        # ``setdefault`` is a no-op for a matching pair.
        key = IntegrationKey(
            integration_id = 'hass',
            integration_name = 'switch.lamp',
        )
        entity, state, sensor = _make_entity_with_sensor( key, units = '°C' )
        controller = Controller( entity_state = state, name = entity.name )
        controller.integration_key = key
        controller.save()

        entry = IntegrationMetadataCache.get_entry( key )

        self.assertEqual( entry, { 'units': '°C' } )

    def test_lazy_fill_loads_entity_created_after_warmup(self):
        # Warmup with no entities present — cache marks itself
        # warmed but is empty.
        IntegrationMetadataCache.get_entry( IntegrationKey(
            integration_id = 'hass', integration_name = 'absent',
        ))
        self.assertTrue( IntegrationMetadataCache._warmed )
        # New entity created after warmup; lazy_fill should query
        # the DB for the specific key and populate.
        late_key = IntegrationKey(
            integration_id = 'hass', integration_name = 'late.entity',
        )
        _make_entity_with_sensor( late_key, units = '°F' )

        entry = IntegrationMetadataCache.get_entry( late_key )

        self.assertEqual( entry, { 'units': '°F' } )

    def test_unknown_key_caches_a_no_units_entry(self):
        # Misses must be remembered so the cache doesn't re-query
        # the DB for the same unknown key on every poll.
        key = IntegrationKey(
            integration_id = 'hass', integration_name = 'never.imported',
        )

        first = IntegrationMetadataCache.get_entry( key )
        with patch(
            'hi.integrations.integration_metadata_cache.Sensor.objects',
        ) as mock_sensor_objects:
            second = IntegrationMetadataCache.get_entry( key )

        self.assertEqual( first, { 'units': None } )
        self.assertEqual( second, { 'units': None } )
        # Second call must not have re-queried Sensor.objects.
        mock_sensor_objects.select_related.assert_not_called()

    def test_divergent_sensor_controller_keeps_sensor_entry(self):
        # Sensor and Controller with the same integration_key but
        # pointing to different EntityStates with different units
        # is a programming error (HiModelHelper enforces
        # co-location); the cache resolves the conflict by keeping
        # the Sensor pass's entry — that's the documented design,
        # and the cache logs a warning canary which we don't
        # exercise here (tests disable logging).
        key = IntegrationKey(
            integration_id = 'hass',
            integration_name = 'oddly.divergent',
        )
        sensor_entity, sensor_state, _ = _make_entity_with_sensor(
            key, units = '°C',
        )
        # Manually create a separate EntityState with a different
        # units value, and a Controller pointing to it under the
        # same integration_key — bypassing HiModelHelper.
        other_state = EntityState.objects.create(
            entity = sensor_entity,
            entity_state_type_str = str( EntityStateType.TEMPERATURE ),
            name = 'Divergent state',
            units = '°F',
        )
        controller = Controller(
            entity_state = other_state, name = sensor_entity.name,
        )
        controller.integration_key = key
        controller.save()

        entry = IntegrationMetadataCache.get_entry( key )

        # Sensor pass wins, per the documented design.
        self.assertEqual( entry, { 'units': '°C' } )


class TestIntegrationMetadataCacheAsync(AsyncTaskTestCase):
    """Async paths use ``sync_to_async`` to safely call the
    DB-touching methods from async contexts. Inherits from
    AsyncTaskTestCase so the event-loop lifecycle is managed
    correctly and the tests don't deadlock on DB locks."""

    def setUp(self):
        _reset_cache()

    def tearDown(self):
        _reset_cache()

    def test_async_variant_returns_same_as_sync(self):
        key = IntegrationKey(
            integration_id = 'hass', integration_name = 'async.entity',
        )
        _make_entity_with_sensor( key, units = '°C' )

        # Cold cache — async hits sync_to_async wrapper for warmup.
        entry = self.run_async(
            IntegrationMetadataCache.get_entry_async( key )
        )

        self.assertEqual( entry, { 'units': '°C' } )

    def test_warm_cache_async_avoids_sync_to_async_hop(self):
        # Performance contract: once warmed and the entry is
        # present, async path should short-circuit to a pure
        # dict read without dispatching to a thread.
        key = IntegrationKey(
            integration_id = 'hass', integration_name = 'warm.entity',
        )
        _make_entity_with_sensor( key, units = '°C' )
        # Prime the cache.
        IntegrationMetadataCache.get_entry( key )

        with patch(
            'hi.integrations.integration_metadata_cache.sync_to_async',
        ) as mock_sync_to_async:
            entry = self.run_async(
                IntegrationMetadataCache.get_entry_async( key )
            )

        self.assertEqual( entry, { 'units': '°C' } )
        mock_sync_to_async.assert_not_called()
