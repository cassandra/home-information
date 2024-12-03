from dataclasses import dataclass

from hi.apps.common.processing_result import ProcessingResult

from .enums import IntegrationAttributeType
from .models import Integration


@dataclass
class IntegrationMetaData:

    integration_id         : str  # An identifier that must be unique across all integrations
    manage_url_name        : str  # URL for main page for managing the integration
    label                  : str  # For human-friendly displaying
    attribute_type         : IntegrationAttributeType
    allow_entity_deletion  : bool

    
@dataclass
class IntegrationData:

    integration_metadata  : IntegrationMetaData
    integration           : Integration


@dataclass
class IntegrationControlResult:
    new_value          : str
    processing_result  : ProcessingResult
