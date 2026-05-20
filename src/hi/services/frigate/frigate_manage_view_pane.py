from typing import Dict

from hi.integrations.integration_data import IntegrationData
from hi.integrations.integration_manage_view_pane import IntegrationManageViewPane


class FrigateManageViewPane( IntegrationManageViewPane ):
    """Management-pane backing for the Settings → Integrations →
    Frigate page. Renders the management template; v1 doesn't add
    any custom context beyond what the framework provides.
    """

    def get_template_name( self ) -> str:
        return 'frigate/panes/frigate_manage.html'

    def get_template_context( self, integration_data : IntegrationData ) -> Dict[ str, object ]:
        return {}
