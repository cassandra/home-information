from typing import Dict

from hi.integrations.forms import IntegrationAttributeFormSet
from hi.integrations.integration_data import IntegrationData
from hi.integrations.integration_manage_view_pane import IntegrationManageViewPane


class ZmManageViewPane( IntegrationManageViewPane ):

    def get_template_name( self ) -> str:
        return 'zoneminder/panes/zm_manage.html'

    def get_template_context( self, integration_data : IntegrationData ) -> Dict[ str, object ]:

        integration_attribute_formset = IntegrationAttributeFormSet(
            instance = integration_data.integration,
            prefix = f'integration-{integration_data.integration_id}',
            form_kwargs = {
                'show_as_editable': True,
            },
        )
        return {
            'integration_attribute_formset': integration_attribute_formset,
        }


