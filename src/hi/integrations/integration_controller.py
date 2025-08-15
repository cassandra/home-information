from .integration_key import IntegrationData
from .transient_models import IntegrationControlResult


class IntegrationController:

    def do_control( self,
                    integration_data : IntegrationData,
                    control_value    : str             ) -> IntegrationControlResult:
        raise NotImplementedError('Subclasses must override this method')
