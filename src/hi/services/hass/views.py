from django.core.exceptions import BadRequest
from django.db import transaction

from django.shortcuts import render
from django.views.generic import View

from hi.integrations.forms import IntegrationAttributeFormSet
from hi.integrations.integration_manager import IntegrationManager

from hi.hi_async_view import HiModalView

from .hass_metadata import HassMetaData
from .hass_mixins import HassMixin
from .hass_sync import HassSynchronizer


class HassSettingsView( View, HassMixin ):

    def post( self, request, *args, **kwargs ):
        integration_data = IntegrationManager().get_integration_data(
            integration_id = HassMetaData.integration_id,
        )
        if not integration_data.is_enabled:
            raise BadRequest( 'HAss is not enabled' )

        integration_attribute_formset = IntegrationAttributeFormSet(
            request.POST,
            request.FILES,
            instance = integration_data.integration,
            prefix = f'integration-{integration_data.integration_id}',
        )
        if integration_attribute_formset.is_valid():
            with transaction.atomic():
                integration_attribute_formset.save()

            self.hass_manager().notify_settings_changed()

        context = {
            'integration_attribute_formset': integration_attribute_formset,
            'history_url_name': 'integration_attribute_history',
            'restore_url_name': 'integration_attribute_restore',
        }
        return render( request, 'hass/panes/hass_settings.html', context )

    
class HassSyncView( HiModalView ):

    def get_template_name( self ) -> str:
        return 'common/modals/processing_result.html'

    def post(self, request, *args, **kwargs):

        processing_result = HassSynchronizer().sync()
        context = {
            'processing_result': processing_result,
        }
        return self.modal_response( request, context )
