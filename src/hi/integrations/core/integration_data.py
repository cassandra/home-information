from dataclasses import dataclass

from .integration_gateway import IntegrationGateway
from .models import Integration
from .transient_models import IntegrationMetaData


@dataclass
class IntegrationData:

    integration_gateway   : IntegrationGateway
    integration           : Integration

    @property
    def integration_id(self) -> str:
        return self.integration_meta_data.integration_id

    @property
    def integration_metadata(self) -> IntegrationMetaData:
        return self.integration_gateway.get_meta_data()

    @property
    def is_enabled(self):
        return self.integration.is_enabled
    
