import logging
from typing import List, Optional

from hi.integrations.models import IntegrationAttribute

from .enums import FrigateAttributeType
from .frigate_client import FrigateClient

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
        value_by_name = {
            attr.integration_attr_type: attr.value for attr in integration_attributes
        }
        return {
            FrigateClient.BASE_URL: value_by_name.get( FrigateAttributeType.BASE_URL.name ),
            FrigateClient.AUTH_HEADER: value_by_name.get( FrigateAttributeType.AUTH_HEADER.name ),
        }
