import logging
from typing import List, Optional

from hi.integrations.models import IntegrationAttribute
from hi.integrations.transient_models import IntegrationKey

from .enums import FrigateAttributeType
from .frigate_client import FrigateClient
from .frigate_metadata import FrigateMetaData

logger = logging.getLogger(__name__)


class FrigateClientFactory:
    """Builds a ``FrigateClient`` from the integration's persisted
    attribute records. Mirrors ``ZmClientFactory`` in role: read
    attribute values out of the IntegrationAttribute list, construct
    the client. Connection validation lives on the client itself
    (``ping``); this factory is purely configuration translation.
    """

    @classmethod
    def create_client(
            cls,
            integration_attributes : List[ IntegrationAttribute ],
            timeout_secs           : Optional[ float ] = None,
    ) -> FrigateClient:
        api_options = cls._attributes_to_options( integration_attributes )
        return FrigateClient(
            api_options = api_options,
            timeout_secs = timeout_secs,
        )

    @staticmethod
    def _attributes_to_options( integration_attributes : List[ IntegrationAttribute ] ) -> dict:
        key_to_attr = {
            attr.integration_key: attr for attr in integration_attributes
        }

        def _lookup( attr_type : FrigateAttributeType ) -> Optional[ str ]:
            key = IntegrationKey(
                integration_id = FrigateMetaData.integration_id,
                integration_name = str( attr_type ),
            )
            attr = key_to_attr.get( key )
            return attr.value if attr else None
        return {
            FrigateClient.BASE_URL: _lookup( FrigateAttributeType.BASE_URL ),
            FrigateClient.AUTH_HEADER: _lookup( FrigateAttributeType.AUTH_HEADER ),
        }
