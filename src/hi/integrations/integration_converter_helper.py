from typing import Any, Dict, List, Optional

from hi.apps.sense.sensor_response_manager import SensorResponseMixin
from hi.units import UnitQuantity

from .integration_metadata_cache import IntegrationMetadataCache
from .transient_models import IntegrationKey


class IntegrationConverterHelper:
    """Shared classmethod helpers for integration converters
    (which are stateless containers of related methods).

    The cached ``_Internal`` instance bridges this classmethod
    facade to the project's instance-method ``SensorResponseMixin``
    pattern so manager access still goes through the mixin's
    coordination path. The proper fix is to make converters
    Singleton instances and inherit ``SensorResponseMixin``
    directly; deferred because the converter call surface is
    pervasively classmethod-based and that conversion is a much
    larger change.
    """

    class _Internal( SensorResponseMixin ):
        pass

    _internal_instance = None

    @classmethod
    def _sensor_response_manager(cls):
        if cls._internal_instance is None:
            cls._internal_instance = cls._Internal()
        return cls._internal_instance.sensor_response_manager()

    @classmethod
    def get_latest_state_values(
            cls, integration_keys : List[IntegrationKey],
    ) -> Dict[IntegrationKey, Optional[str]]:
        response_map = cls._sensor_response_manager().get_latest_sensor_response_map(
            integration_keys = integration_keys,
        )
        return {
            integration_key: ( response.value if response else None )
            for integration_key, response in response_map.items()
        }

    @classmethod
    def get_cache_entry(
            cls, integration_key : IntegrationKey,
    ) -> Dict[str, Any]:
        """Return cached EntityState metadata used by integration
        value translation. The dict has a ``units`` key holding the
        EntityState.units string (or None when no translation is
        needed). Backed by ``IntegrationMetadataCache`` (process-wide,
        lazy-warmed)."""
        return IntegrationMetadataCache.get_entry( integration_key )

    @classmethod
    async def get_cache_entry_async(
            cls, integration_key : IntegrationKey,
    ) -> Dict[str, Any]:
        """Async variant of ``get_cache_entry`` for use from async
        monitor / converter paths."""
        return await IntegrationMetadataCache.get_entry_async( integration_key )

    @classmethod
    def to_entity_state_value(
            cls,
            external_value   : float,
            external_unit    : str,
            integration_key  : IntegrationKey,
    ) -> float:
        """Inbound boundary: translate a numeric value from the
        integration's external unit (e.g., HA's reported
        ``unit_of_measurement``) to the EntityState's stored unit.
        The target unit is read from the IntegrationMetadataCache.
        Pass-through when the EntityState has no units or the units
        already match."""
        target_unit = cls.get_cache_entry(
            integration_key,
        ).get( 'units' )
        return cls._convert_between_units(
            value = external_value,
            from_unit = external_unit,
            to_unit = target_unit,
        )

    @classmethod
    async def to_entity_state_value_async(
            cls,
            external_value   : float,
            external_unit    : str,
            integration_key  : IntegrationKey,
    ) -> float:
        """Async variant of ``to_entity_state_value`` for use from
        async monitor paths. Cache lookup goes through
        sync_to_async; conversion arithmetic is pure-Python."""
        entry = await cls.get_cache_entry_async( integration_key )
        return cls._convert_between_units(
            value = external_value,
            from_unit = external_unit,
            to_unit = entry.get( 'units' ),
        )

    @classmethod
    def from_entity_state_value(
            cls,
            entity_state_value : float,
            external_unit      : str,
            integration_key    : IntegrationKey,
    ) -> float:
        """Outbound boundary: translate a numeric value in the
        EntityState's stored unit to the integration's external
        unit (e.g., HA's currently-reported native unit). The
        source unit is read from the IntegrationMetadataCache.
        Pass-through when the EntityState has no units or the units
        already match."""
        source_unit = cls.get_cache_entry(
            integration_key,
        ).get( 'units' )
        return cls._convert_between_units(
            value = entity_state_value,
            from_unit = source_unit,
            to_unit = external_unit,
        )

    @classmethod
    async def from_entity_state_value_async(
            cls,
            entity_state_value : float,
            external_unit      : str,
            integration_key    : IntegrationKey,
    ) -> float:
        """Async variant of ``from_entity_state_value``."""
        entry = await cls.get_cache_entry_async( integration_key )
        return cls._convert_between_units(
            value = entity_state_value,
            from_unit = entry.get( 'units' ),
            to_unit = external_unit,
        )

    @staticmethod
    def _convert_between_units(
            value     : float,
            from_unit : Optional[str],
            to_unit   : Optional[str],
    ) -> float:
        """Pure-Python Pint conversion between unit strings.
        Pass-through when either side is missing or the units
        already match. Defensive on parse failures so a malformed
        unit string never raises into the converter call sites."""
        if not from_unit or not to_unit or from_unit == to_unit:
            return value
        try:
            return UnitQuantity( value, from_unit ).to( to_unit ).magnitude
        except Exception:
            return value
