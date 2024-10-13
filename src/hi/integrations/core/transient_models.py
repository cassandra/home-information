from dataclasses import dataclass

from .enums import IntegrationAttributeType
from .models import Integration


@dataclass
class IntegrationMetaData:

    integration_id         : str  # An identifier that must be unique across all integrations
    label                  : str  # For human-friendly displaying
    attribute_type         : IntegrationAttributeType
    allow_entity_deletion  : bool

    
@dataclass
class IntegrationData:

    integration_metadata  : IntegrationMetaData
    integration           : Integration
