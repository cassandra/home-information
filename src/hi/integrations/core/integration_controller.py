from .integration_key import IntegrationKey
from .transient_models import IntegrationControlResult


class IntegrationController:

    def do_control( self,
                    integration_key  : IntegrationKey,
                    control_value    : str             ) -> IntegrationControlResult:
        raise NotImplementedError('Subclasses must override this method')
