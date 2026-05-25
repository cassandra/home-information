from dataclasses import dataclass

from hi.integrations.models import Integration
from hi.integrations.transient_models import IntegrationMetaData

from .integration_gateway import IntegrationGateway


@dataclass
class IntegrationData:

    integration_gateway   : IntegrationGateway
    integration           : Integration

    def __repr__(self):
        return self.__str__()
    
    def __str__(self):
        return self.integration_id
    
    @property
    def integration_id(self) -> str:
        return self.integration_metadata.integration_id

    @property
    def integration_metadata(self) -> IntegrationMetaData:
        return self.integration_gateway.get_metadata()

    @property
    def label(self) -> IntegrationMetaData:
        return self.integration_metadata.label

    @property
    def is_enabled(self):
        return self.integration.is_enabled

    @property
    def is_paused(self):
        return self.integration.is_paused

