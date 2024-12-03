from hi.integrations.core.integration_controller import IntegrationController
from hi.integrations.core.integration_key import IntegrationKey
from hi.integrations.core.transient_models import IntegrationControlResult


class HassController( IntegrationController ):

    def do_control( self,
                    integration_key  : IntegrationKey,
                    control_value    : str             ) -> IntegrationControlResult:

        # zzz Needs implementation

        return IntegrationControlResult()
    
