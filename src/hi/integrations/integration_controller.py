from .transient_models import IntegrationDetails
from .transient_models import IntegrationControlResult


class IntegrationController:

    def do_control( self,
                    integration_details : IntegrationDetails,
                    control_value       : str                ) -> IntegrationControlResult:
        raise NotImplementedError('Subclasses must override this method')
