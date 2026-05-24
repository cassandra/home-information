from hi.integrations.transient_models import IntegrationDetails
from hi.integrations.transient_models import IntegrationControlResult


class IntegrationController:

    def do_control( self,
                    integration_details : IntegrationDetails,
                    hi_control_value    : str                ) -> IntegrationControlResult:
        raise NotImplementedError('Subclasses must override this method')
