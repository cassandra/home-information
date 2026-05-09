from typing import Dict, List, Optional

from hi.apps.sense.sensor_response_manager import SensorResponseMixin

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
