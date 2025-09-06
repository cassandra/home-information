from typing import Dict

from hi.apps.entity.models import Entity
from hi.integrations.integration_data import IntegrationData
from hi.integrations.integration_manage_view_pane import IntegrationManageViewPane


class HassManageViewPane( IntegrationManageViewPane ):

    def get_template_name( self ) -> str:
        return 'hass/panes/hass_manage.html'

    def get_template_context( self, integration_data : IntegrationData ) -> Dict[ str, object ]:
        
        has_entities = Entity.objects.filter( integration_id = integration_data.integration_id ).exists()
        
        return {
            'has_entities': has_entities,
        }
