from typing import Dict


class IntegrationManageViewPane:
    """ For integrations to override to define the management interface. """
    
    def get_template_name( self ) -> str:
        raise NotImplementedError('Subclasses must override this method')

    def get_template_context( self, integration_data ) -> Dict[ str, object ]:
        raise NotImplementedError('Subclasses must override this method')
