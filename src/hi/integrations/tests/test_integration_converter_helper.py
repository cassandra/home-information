import logging

from django.test import TestCase

from hi.integrations.integration_converter_helper import IntegrationConverterHelper
from hi.integrations.integration_metadata_cache import IntegrationMetadataCache
from hi.integrations.transient_models import IntegrationKey
from hi.testing.async_task_utils import AsyncTaskTestCase

logging.disable(logging.CRITICAL)


def _seed_cache_entry( integration_key, units ):
    """Pre-populate the metadata cache so the converter helpers
    don't need real Sensor/Controller rows for unit-translation
    tests that only exercise the helper's conversion math."""
    cache = IntegrationMetadataCache()
    cache._warmed = True
    cache._cache[ integration_key ] = { 'units': units }


def _reset_cache():
    cache = IntegrationMetadataCache()
    cache._cache.clear()
    cache._warmed = False


class TestToEntityStateValue(TestCase):
    """Inbound boundary: integration's external value (e.g., HA's
    reported °F) → EntityState's stored unit (canonical °C). Cache
    holds the target unit; helper applies Pint conversion."""

    def setUp(self):
        _reset_cache()

    def tearDown(self):
        _reset_cache()

    def _key(self, name='test'):
        return IntegrationKey( integration_id = 'hass', integration_name = name )

    def test_converts_fahrenheit_to_canonical_celsius(self):
        key = self._key( 'climate.zoo~current_temperature' )
        _seed_cache_entry( key, units = '°C' )

        result = IntegrationConverterHelper.to_entity_state_value(
            external_value = 70.0,
            external_unit = '°F',
            integration_key = key,
        )

        self.assertAlmostEqual( result, 21.111, places = 2 )

    def test_passthrough_when_units_match(self):
        key = self._key( 'climate.zoo~current_temperature' )
        _seed_cache_entry( key, units = '°C' )

        result = IntegrationConverterHelper.to_entity_state_value(
            external_value = 22.0,
            external_unit = '°C',
            integration_key = key,
        )

        self.assertEqual( result, 22.0 )

    def test_passthrough_when_no_target_unit(self):
        # Cache says no units (e.g., ON/OFF state) — converter must
        # not try to translate.
        key = self._key( 'switch.outlet' )
        _seed_cache_entry( key, units = None )

        result = IntegrationConverterHelper.to_entity_state_value(
            external_value = 50.0,
            external_unit = '%',
            integration_key = key,
        )

        self.assertEqual( result, 50.0 )


class TestFromEntityStateValue(TestCase):
    """Outbound boundary: HI's stored value (canonical °C) →
    integration's required external unit (e.g., HA's °F)."""

    def setUp(self):
        _reset_cache()

    def tearDown(self):
        _reset_cache()

    def _key(self, name='test'):
        return IntegrationKey( integration_id = 'hass', integration_name = name )

    def test_converts_canonical_celsius_to_fahrenheit(self):
        key = self._key( 'climate.zoo~target_temperature' )
        _seed_cache_entry( key, units = '°C' )

        result = IntegrationConverterHelper.from_entity_state_value(
            entity_state_value = 22.0,
            external_unit = '°F',
            integration_key = key,
        )

        self.assertAlmostEqual( result, 71.6, places = 2 )

    def test_passthrough_when_units_match(self):
        key = self._key( 'climate.zoo~target_temperature' )
        _seed_cache_entry( key, units = '°C' )

        result = IntegrationConverterHelper.from_entity_state_value(
            entity_state_value = 22.0,
            external_unit = '°C',
            integration_key = key,
        )

        self.assertEqual( result, 22.0 )

    def test_passthrough_when_no_source_unit(self):
        # An EntityState without units (e.g., a discrete enum
        # state) must not be translated even if the dispatch
        # specifies an external_unit.
        key = self._key( 'switch.lamp' )
        _seed_cache_entry( key, units = None )

        result = IntegrationConverterHelper.from_entity_state_value(
            entity_state_value = 1.0,
            external_unit = '°F',
            integration_key = key,
        )

        self.assertEqual( result, 1.0 )

    def test_round_trip_to_then_from_preserves_value(self):
        # to_entity_state_value followed by from_entity_state_value
        # with the same external_unit must round-trip with at most
        # one Pint hop's worth of float imprecision.
        key = self._key( 'climate.zoo~target_temperature' )
        _seed_cache_entry( key, units = '°C' )

        canonical = IntegrationConverterHelper.to_entity_state_value(
            external_value = 75.0, external_unit = '°F', integration_key = key,
        )
        external = IntegrationConverterHelper.from_entity_state_value(
            entity_state_value = canonical,
            external_unit = '°F',
            integration_key = key,
        )

        self.assertAlmostEqual( external, 75.0, places = 6 )


class TestAsyncConverterHelpers(AsyncTaskTestCase):
    """Async variants delegate to the cache's async API, which uses
    sync_to_async for DB safety. AsyncTaskTestCase manages the
    event-loop lifecycle so these don't deadlock on DB locks."""

    def setUp(self):
        _reset_cache()

    def tearDown(self):
        _reset_cache()

    def _key(self, name='test'):
        return IntegrationKey( integration_id = 'hass', integration_name = name )

    def test_to_entity_state_value_async_matches_sync(self):
        key = self._key( 'climate.zoo~current_temperature' )
        _seed_cache_entry( key, units = '°C' )

        sync_result = IntegrationConverterHelper.to_entity_state_value(
            external_value = 70.0, external_unit = '°F', integration_key = key,
        )
        async_result = self.run_async(
            IntegrationConverterHelper.to_entity_state_value_async(
                external_value = 70.0, external_unit = '°F', integration_key = key,
            )
        )

        self.assertEqual( sync_result, async_result )

    def test_from_entity_state_value_async_matches_sync(self):
        key = self._key( 'climate.zoo~target_temperature' )
        _seed_cache_entry( key, units = '°C' )

        sync_result = IntegrationConverterHelper.from_entity_state_value(
            entity_state_value = 22.0, external_unit = '°F', integration_key = key,
        )
        async_result = self.run_async(
            IntegrationConverterHelper.from_entity_state_value_async(
                entity_state_value = 22.0, external_unit = '°F', integration_key = key,
            )
        )

        self.assertEqual( sync_result, async_result )
